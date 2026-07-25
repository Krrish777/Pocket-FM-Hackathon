"""Unit tests for the shared HTTP retry layer.

This module carries the whole pipeline's resilience contract — backoff, which statuses are worth
retrying, and how failure is reported — and had no tests at all. Every scraper request goes
through it, so a regression here degrades every harvest silently rather than loudly.

`time.sleep` is patched out throughout: these assert the retry *policy*, not wall-clock delay.
"""

import httpx
import pytest

from story_engine.adapters.outbound.fanfic import http_util
from story_engine.adapters.outbound.fanfic.http_util import (
    CONTACT_ENV_VAR,
    default_user_agent,
    get_with_retry,
    html_to_text,
)
from story_engine.shared.errors import SourceUnavailableError

URL = "https://host.test/resource"


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the suite fast and deterministic: assert policy, not elapsed time."""
    monkeypatch.setattr(http_util.time, "sleep", lambda _seconds: None)


def _client(*responses: int | Exception) -> tuple[httpx.Client, list[str]]:
    """Return a client replaying `responses` in order, plus a log of attempted URLs."""
    calls: list[str] = []
    queue = list(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        outcome = queue.pop(0) if queue else 200
        if isinstance(outcome, Exception):
            raise outcome
        return httpx.Response(outcome, text="body")

    return httpx.Client(transport=httpx.MockTransport(handler)), calls


class TestRetryPolicy:
    def test_a_first_attempt_success_is_not_retried(self) -> None:
        client, calls = _client(200)
        assert get_with_retry(client, URL).status_code == 200
        assert len(calls) == 1

    @pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
    def test_transient_statuses_are_retried_then_succeed(self, status: int) -> None:
        client, calls = _client(status, 200)
        assert get_with_retry(client, URL).status_code == 200
        assert len(calls) == 2

    @pytest.mark.parametrize("status", [400, 401, 403, 404, 410])
    def test_non_retryable_statuses_fail_immediately(self, status: int) -> None:
        # Retrying a 403 wastes the budget and looks like abuse to the host.
        client, calls = _client(status, 200)
        with pytest.raises(SourceUnavailableError) as err:
            get_with_retry(client, URL)
        assert len(calls) == 1
        assert err.value.context["status"] == status

    def test_exhausting_attempts_raises_with_the_last_detail(self) -> None:
        client, calls = _client(503, 503, 503, 503)
        with pytest.raises(SourceUnavailableError, match="after 4 attempts"):
            get_with_retry(client, URL)
        assert len(calls) == 4

    def test_max_attempts_is_honoured(self) -> None:
        client, calls = _client(503, 503, 503, 503, 503)
        with pytest.raises(SourceUnavailableError):
            get_with_retry(client, URL, max_attempts=2)
        assert len(calls) == 2

    def test_network_errors_are_retried_not_propagated(self) -> None:
        # A DNS blip or reset must surface as the pipeline's own typed error, so callers can
        # skip one host instead of catching httpx internals.
        client, calls = _client(httpx.ConnectError("dns"), 200)
        assert get_with_retry(client, URL).status_code == 200
        assert len(calls) == 2

    def test_persistent_network_failure_becomes_a_typed_error(self) -> None:
        client, _ = _client(*[httpx.ConnectTimeout("slow")] * 4)
        with pytest.raises(SourceUnavailableError) as err:
            get_with_retry(client, URL)
        assert err.value.context["attempts"] == 4

    def test_backoff_grows_between_attempts(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        slept: list[float] = []
        monkeypatch.setattr(http_util.time, "sleep", slept.append)
        monkeypatch.setattr(http_util.random, "uniform", lambda _a, _b: 0.0)
        client, _ = _client(503, 503, 503, 503)
        with pytest.raises(SourceUnavailableError):
            get_with_retry(client, URL, base_delay=1.0)
        # Exponential, and no sleep after the final attempt.
        assert slept == [1.0, 2.0, 4.0]

    def test_params_are_forwarded(self) -> None:
        client, calls = _client(200)
        get_with_retry(client, URL, params={"id": "42"})
        assert calls[0].endswith("?id=42")


class TestUserAgent:
    def test_contact_is_overridable_by_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(CONTACT_ENV_VAR, "https://example.test/me")
        assert "https://example.test/me" in default_user_agent()

    def test_a_blank_env_falls_back_to_the_default_contact(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Wikimedia 403s a UA with no contact point, so an empty override must not blank it out.
        monkeypatch.setenv(CONTACT_ENV_VAR, "   ")
        agent = default_user_agent()
        assert "(" in agent and agent.strip().endswith(")")


class TestHtmlToText:
    def test_script_and_style_bodies_do_not_leak_into_prose(self) -> None:
        # Tag stripping alone leaves the CONTENT of these elements behind as text.
        markup = "<p>Real prose.</p><style>.a{color:red}</style>"
        assert "color:red" not in html_to_text(markup)

    def test_paragraphs_and_breaks_are_distinguished(self) -> None:
        assert html_to_text("<p>One</p><p>Two</p>") == "One\n\nTwo"
        assert html_to_text("One<br>Two") == "One\nTwo"

    def test_entities_are_unescaped(self) -> None:
        assert html_to_text("<p>&ldquo;Hi,&rdquo; she said &amp; smiled.</p>") == (
            "“Hi,” she said & smiled."
        )
