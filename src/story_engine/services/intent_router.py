"""Natural-language intent routing: map the player's typed action onto an offered option.

This module is a **router onto a constrained action set**, not an open-ended action interpreter.
The turn loop already offers 2-4 authored options (`ChoiceOption`, from the Branch Oracle); a
player may type their action in their own words instead of picking a number, and `IntentRouter`
classifies that text onto one of those options — or onto nothing, if none is a confident match.

`PlaythroughService.advance` remains the sole applier of a consequence (`services/playthrough.py`).
`IntentRouter.resolve` returns a `choice_id` and nothing else: it never touches the canon store,
never mutates a `Playthrough`, and never calls `advance` itself. Model output is untrusted input —
a `choice_id` the model invented, one that was not among the options it was given, is rejected to
`None` before it ever reaches a caller. That rejection is the security property of this module.
"""

import hashlib
import json
import logging
import re

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from story_engine.domain.base import DomainModel
from story_engine.domain.models.play import ChoiceOption
from story_engine.ports.llm import LLMPort
from story_engine.ports.prompt_store import PromptStorePort

logger = logging.getLogger(__name__)

PROMPT_NAME = "interpret_intent"
PROMPT_VERSION = "v1"
"""Pinned, never "latest by accident" (.claude/rules/llm-storytelling.md §2)."""

MAX_INTENT_TOKENS = 200
TEMPERATURE = 0.2
"""Low, deliberately: intent routing is a structured, continuity-critical classification, not
prose, so a low temperature protects it the way `render_scene`'s high temperature does not need
to (.claude/rules/llm-storytelling.md §3)."""

_CODE_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


class ResolvedIntent(DomainModel):
    """The outcome of routing the player's typed action onto one of the offered options.

    `choice_id` is `None` whenever nothing offered was a confident match — including, always, when
    the model named an option that was never offered. This type carries no consequence of its own;
    only `PlaythroughService.advance`, given a `choice_id` it independently finds among the current
    turn's options, ever changes canon state.
    """

    choice_id: str | None
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = Field(
        min_length=1,
        description="One short sentence, shown to the player as 'you chose to ...'.",
    )


class _ModelIntentResponse(BaseModel):
    """The raw shape required of the model's JSON before any of it is trusted.

    Deliberately lenient on unknown fields (`extra='ignore'`): a stray field the model added is not
    a security concern. A `choice_id` that was never offered *is* — but that check happens in
    `IntentRouter.resolve`, against the actual options in play, not here.
    """

    model_config = ConfigDict(extra="ignore")

    choice_id: str | None = None
    confidence: float = 0.0
    reasoning: str = ""


class IntentRouter:
    """Routes the player's typed action onto one of the options currently on offer.

    This is intent ROUTING onto a constrained action set: the model sees only the offered
    options' ids and labels — never their consequences — and returns at most one of those ids.
    It cannot decide state, cannot invent an option, and cannot see what an option does to the
    world before the player commits to it.
    """

    def __init__(
        self,
        *,
        llm: LLMPort,
        prompts: PromptStorePort,
        model: str,
        threshold: float = 0.6,
    ) -> None:
        self._llm = llm
        self._prompts = prompts
        self._model = model
        self._threshold = threshold

    def resolve(
        self,
        *,
        action: str,
        options: tuple[ChoiceOption, ...],
        protagonist: str,
    ) -> ResolvedIntent:
        """Classify `action` onto one of `options`, or report no confident match.

        Spends no model call when `options` is empty — there is nothing to route the player's
        typed action onto, so classifying against an empty set would only spend a call to learn
        what step 1 already knows. Every other path below either returns a `choice_id` drawn
        verbatim from `options`, or `None`.
        """
        if not options:
            return ResolvedIntent(
                choice_id=None,
                confidence=0.0,
                reasoning="no options were offered to route the action onto",
            )

        offered_ids = {option.id for option in options}
        prompt = self._prompts.render(
            PROMPT_NAME,
            version=PROMPT_VERSION,
            variables={
                "protagonist": protagonist,
                "action": action,
                "options": [
                    {"id": option.id, "label": option.label} for option in options
                ],
            },
        )
        generation = self._llm.generate(
            messages=[{"role": "user", "content": prompt}],
            model=self._model,
            max_tokens=MAX_INTENT_TOKENS,
            temperature=TEMPERATURE,
            idempotency_key=self._idempotency_key(action, options, protagonist),
        )

        parsed = self._parse(generation.output)
        if parsed is None:
            return ResolvedIntent(
                choice_id=None,
                confidence=0.0,
                reasoning="the model's response could not be parsed as intent JSON",
            )

        if parsed.choice_id is not None and parsed.choice_id not in offered_ids:
            logger.warning(
                "intent router: model returned choice_id %r not among offered options %s "
                "for protagonist %r; rejecting the typed action to no-match",
                parsed.choice_id,
                sorted(offered_ids),
                protagonist,
            )
            return ResolvedIntent(
                choice_id=None,
                confidence=parsed.confidence,
                reasoning="the model named an option that was not actually offered",
            )

        if parsed.confidence < self._threshold:
            return ResolvedIntent(
                choice_id=None,
                confidence=parsed.confidence,
                reasoning=parsed.reasoning
                or "confidence was below the intent-routing threshold",
            )

        return ResolvedIntent(
            choice_id=parsed.choice_id,
            confidence=parsed.confidence,
            reasoning=parsed.reasoning or "matched the closest offered option",
        )

    @staticmethod
    def _idempotency_key(
        action: str, options: tuple[ChoiceOption, ...], protagonist: str
    ) -> str:
        """Same player action against the same option set replays the same routing decision.

        Uses `hashlib.sha256`, not the builtin `hash()` — `hash()` is randomised per process by
        `PYTHONHASHSEED` and would defeat replay across restarts.
        """
        payload = action + "|" + "|".join(option.id for option in options)
        digest = hashlib.sha256(payload.encode()).hexdigest()[:16]
        return f"intent:{protagonist}:{digest}"

    @staticmethod
    def _parse(output: str) -> _ModelIntentResponse | None:
        """Parse the model's JSON, tolerating a ```json fence around it.

        Anything that fails to parse or fails the schema is the caller's cue to fall back to
        `choice_id=None` — model output is untrusted input until it clears this gate.
        """
        stripped = _CODE_FENCE.sub("", output.strip()).strip()
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            logger.warning(
                "intent router: model response was not valid JSON: %.200r", output
            )
            return None

        if not isinstance(payload, dict):
            logger.warning(
                "intent router: model response JSON was not an object: %.200r", output
            )
            return None

        try:
            return _ModelIntentResponse.model_validate(payload)
        except ValidationError as exc:
            logger.warning(
                "intent router: model response failed schema validation: %s", exc
            )
            return None
