"""The real `LLMPort` — OpenAI chat completions, metered.

This is the ONE place the OpenAI SDK is imported (Hard Constraint #5 / #7). Everything the rules
require of a client wrapper lives here rather than at the call sites:

* **`max_tokens` is always sent.** The port makes it a required keyword, and this adapter has no
  code path that omits it — runaway generation is the top cost risk.
* **Every call is metered**: model, prompt/completion tokens, USD cost, latency, and the caller's
  idempotency key are logged on one line.
* **Retries do not double-bill.** A repeated `idempotency_key` returns the cached `Generation`
  without touching the network, which matters because the turn loop keys on
  `{knower}:{chapter}:{fact_count}` — a retried turn is the *same* turn.
* **Cost is never invented.** An unpriced model logs a warning and reports `0.0` rather than a
  plausible-looking number; a fabricated cost flows straight into the budget guard and makes it
  confidently wrong. Zero is visibly missing data.

`.claude/rules/llm-storytelling.md` §§1-5.
"""

import logging
import time
from typing import Any, Protocol

from pydantic import SecretStr

from story_engine.ports.llm import Generation
from story_engine.shared.errors import BudgetExceededError, GenerationError

logger = logging.getLogger(__name__)

PRICING_USD_PER_MTOK: dict[str, tuple[float, float]] = {
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4.1": (2.00, 8.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1-nano": (0.10, 0.40),
    "gpt-5": (1.25, 10.00),
    "gpt-5-mini": (0.25, 2.00),
    "gpt-5-nano": (0.05, 0.40),
}
"""(input, output) USD per million tokens. A model absent from this table is *unpriced*, not free —
see `_cost_usd`."""

_FIXED_TEMPERATURE_PREFIXES = ("gpt-5", "o1", "o3", "o4")
"""Reasoning-family models reject any temperature but the default, so it is omitted for them rather
than sent and rejected. Prose temperature is a hint, not a guarantee we can make on every model."""

_RETRYABLE_STATUS = frozenset({408, 409, 429, 500, 502, 503, 504})


class _ChatClient(Protocol):
    """The slice of the OpenAI SDK this adapter uses, so tests can supply a double."""

    @property
    def chat(self) -> Any: ...


class OpenAILLM:
    """OpenAI-backed `LLMPort` with cost metering, retries, and idempotent replay."""

    def __init__(
        self,
        *,
        api_key: SecretStr | None = None,
        client: _ChatClient | None = None,
        budget_usd: float | None = None,
        max_attempts: int = 3,
        backoff_seconds: float = 1.0,
        timeout_seconds: float = 60.0,
    ) -> None:
        """Build the adapter.

        Args:
            api_key: The OpenAI key. Required unless `client` is supplied.
            client: A pre-built SDK client (or a test double). Injected so the unit suite can
                exercise every branch without a key or a network.
            budget_usd: Cumulative spend ceiling for this adapter's lifetime. `None` disables the
                guard. Checked *before* a call, using spend already booked.
            max_attempts: Total attempts per call, including the first.
            backoff_seconds: Base delay; attempt n waits `backoff_seconds * 2**(n-1)`.
            timeout_seconds: Per-request timeout handed to the SDK.

        Raises:
            GenerationError: Neither `client` nor `api_key` was supplied — refused at construction
                rather than at the first call, so a misconfigured process dies at boot instead of
                mid-demo.
        """
        if client is None:
            if api_key is None:
                raise GenerationError(
                    "OpenAILLM needs an api_key (set OPENAI_API_KEY) or an injected client"
                )
            client = _build_sdk_client(api_key, timeout_seconds)

        self._client = client
        self._budget_usd = budget_usd
        self._max_attempts = max_attempts
        self._backoff_seconds = backoff_seconds
        self._spent_usd = 0.0
        self._replays: dict[str, Generation] = {}

    @property
    def spent_usd(self) -> float:
        """Total USD booked by this adapter so far (replays are not re-counted)."""
        return self._spent_usd

    def generate(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        max_tokens: int,
        temperature: float,
        idempotency_key: str | None = None,
    ) -> Generation:
        """Generate a completion, metered and retried.

        Raises:
            BudgetExceededError: Spend already booked has reached the configured ceiling.
            GenerationError: The provider failed after `max_attempts`, or returned a response with
                no usable content.
        """
        if idempotency_key is not None and idempotency_key in self._replays:
            logger.info("llm replay key=%s (not re-billed)", idempotency_key)
            return self._replays[idempotency_key]

        if self._budget_usd is not None and self._spent_usd >= self._budget_usd:
            raise BudgetExceededError(
                f"spent ${self._spent_usd:.4f} has reached the ${self._budget_usd:.2f} ceiling",
                context={"spent_usd": self._spent_usd, "limit_usd": self._budget_usd},
            )

        generation = self._call_with_retries(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            idempotency_key=idempotency_key,
        )

        self._spent_usd += generation.cost_usd
        if idempotency_key is not None:
            self._replays[idempotency_key] = generation
        return generation

    # --- internals ----------------------------------------------------------------------

    def _call_with_retries(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        max_tokens: int,
        temperature: float,
        idempotency_key: str | None,
    ) -> Generation:
        last_error: Exception | None = None
        for attempt in range(1, self._max_attempts + 1):
            started = time.monotonic()
            try:
                response = self._client.chat.completions.create(
                    **self._request_kwargs(
                        messages=messages,
                        model=model,
                        max_tokens=max_tokens,
                        temperature=temperature,
                    )
                )
            except (
                Exception
            ) as exc:  # boundary: the SDK's error taxonomy is vendor-specific
                last_error = exc
                if not _is_retryable(exc) or attempt == self._max_attempts:
                    raise GenerationError(
                        f"openai call failed after {attempt} attempt(s): {exc}",
                        context={"model": model, "attempt": attempt},
                    ) from exc
                delay = self._backoff_seconds * (2 ** (attempt - 1))
                logger.warning(
                    "llm attempt %d/%d failed (%s); retrying in %.1fs",
                    attempt,
                    self._max_attempts,
                    type(exc).__name__,
                    delay,
                )
                time.sleep(delay)
                continue

            latency_ms = (time.monotonic() - started) * 1000
            return self._to_generation(
                response,
                model=model,
                latency_ms=latency_ms,
                idempotency_key=idempotency_key,
            )

        # Unreachable: the loop either returns or raises. Kept so a future edit cannot fall
        # through to an implicit None.
        raise GenerationError(
            f"openai call exhausted {self._max_attempts} attempts",
            context={"model": model},
        ) from last_error

    @staticmethod
    def _request_kwargs(
        *,
        messages: list[dict[str, str]],
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            # `max_completion_tokens` is the current spelling and the only one newer models
            # accept; the deprecated `max_tokens` is rejected outright by them.
            "max_completion_tokens": max_tokens,
        }
        if not model.startswith(_FIXED_TEMPERATURE_PREFIXES):
            kwargs["temperature"] = temperature
        return kwargs

    def _to_generation(
        self,
        response: Any,
        *,
        model: str,
        latency_ms: float,
        idempotency_key: str | None,
    ) -> Generation:
        """Validate the provider payload at the boundary before it reaches the core.

        Model output is untrusted input: an empty completion (a length-capped refusal, a
        content filter) must fail loudly here rather than travel on as an empty scene.
        """
        choices = getattr(response, "choices", None)
        if not choices:
            raise GenerationError(
                "openai returned no choices", context={"model": model}
            )
        content = getattr(choices[0].message, "content", None)
        if not content or not content.strip():
            finish_reason = getattr(choices[0], "finish_reason", "unknown")
            raise GenerationError(
                f"openai returned empty content (finish_reason={finish_reason})",
                context={"model": model, "finish_reason": finish_reason},
            )

        usage = getattr(response, "usage", None)
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        reported_model = str(getattr(response, "model", model) or model)
        cost = _cost_usd(reported_model, prompt_tokens, completion_tokens)

        logger.info(
            "llm model=%s prompt_tokens=%d completion_tokens=%d cost_usd=%.6f "
            "latency_ms=%.0f key=%s",
            reported_model,
            prompt_tokens,
            completion_tokens,
            cost,
            latency_ms,
            idempotency_key or "-",
        )
        return Generation(
            output=content,
            model=reported_model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost,
        )


def _cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Price a call, or report 0.0 loudly when the model is not in the table.

    Dated snapshots (`gpt-4o-2024-08-06`) price as their base model; a longest-prefix match keeps
    the table from needing a row per snapshot.
    """
    matches = [name for name in PRICING_USD_PER_MTOK if model.startswith(name)]
    if not matches:
        logger.warning(
            "no price for model %s; reporting cost_usd=0.0 (spend is UNMETERED for this call)",
            model,
        )
        return 0.0
    input_rate, output_rate = PRICING_USD_PER_MTOK[max(matches, key=len)]
    return (prompt_tokens * input_rate + completion_tokens * output_rate) / 1_000_000


def _is_retryable(exc: Exception) -> bool:
    """Retry transient transport/rate-limit failures only; a 400 will fail identically forever."""
    status = getattr(exc, "status_code", None)
    if isinstance(status, int):
        return status in _RETRYABLE_STATUS
    return type(exc).__name__ in {
        "APIConnectionError",
        "APITimeoutError",
        "RateLimitError",
        "InternalServerError",
    }


def _build_sdk_client(api_key: SecretStr, timeout_seconds: float) -> Any:
    """Import and construct the SDK client.

    Imported lazily so the package stays importable — and the whole unit suite stays runnable —
    on a machine where the OpenAI SDK is not installed.
    """
    try:
        from openai import OpenAI
    except (
        ImportError
    ) as exc:  # pragma: no cover - exercised by environment, not by tests
        raise GenerationError(
            "the openai package is not installed; run `uv sync`"
        ) from exc
    return OpenAI(api_key=api_key.get_secret_value(), timeout=timeout_seconds)
