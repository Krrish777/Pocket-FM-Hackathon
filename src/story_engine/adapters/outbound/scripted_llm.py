"""A deterministic `LLMPort` — replays authored scenes, and composes one when none is scripted.

Two jobs, both about removing a live model from paths where it is a liability:

* **The demo.** A rehearsed run should not depend on a network round trip in front of judges. Every
  beat of the scripted path is authored ahead of time and replayed byte-for-byte, so the demo cannot
  be broken by a timeout, a rate limit, or an unlucky sample.
* **The tests.** `.claude/rules/testing.md` forbids asserting on generated text and requires the LLM
  to be mocked in unit tests. This adapter makes the turn loop fully exercisable — including its
  branching, propagation, and receipt behaviour — without a key.

It is **not** a fake that pretends to be a model. When a beat is not scripted it composes prose
mechanically from the packet, and the result is obviously mechanical. That is deliberate: a fallback
good enough to be mistaken for the real renderer would hide the fact that nothing was scripted.

The same philosophy applies to `IntentRouter`'s classification calls (`prompts/interpret_intent/`):
this adapter recognizes that prompt structurally (see `_INTENT_MARKER`) and answers with valid JSON
chosen by plain keyword overlap between the typed action and each offered option's label — a rule
transparent enough to read at a glance, never a disguised model. It is not scripted-mode
special-casing inside the router: `IntentRouter` stays provider-agnostic and never learns this
adapter exists; the detection lives entirely here, on the rendered prompt text it is handed.

Swap in a real provider adapter behind the same port when one is configured; nothing else changes.
"""

import json
import re
from collections.abc import Mapping

from story_engine.ports.llm import Generation

MODEL_NAME = "scripted"

_FACT_LINE = re.compile(
    r"^- (?P<subject>\S+) (?P<predicate>\S+) (?P<object>.*)$", re.MULTILINE
)
_PROTAGONIST = re.compile(r"point of view of (?P<name>.+?)\.$", re.MULTILINE)

_KNOWLEDGE_BLOCK = re.compile(
    r"WHAT .+? KNOWS AT THIS POINT.*?\n(?P<facts>.*?)(?=\nRULES:)", re.DOTALL
)
"""Isolates the knowledge list before any bullet is parsed.

The template renders both the known facts *and* the upcoming options as `- ` bullets, so a naive
line scan reads the menu as if it were memory. It did, and the narration recited the player's
choices back at them — with the prompt three lines above saying never to name them. Scoping the
scan to the block that ends at `RULES:` is what keeps the option list out of the prose.
"""

_INTENT_MARKER = "Respond with JSON only, no other text and no code fence"
"""A line from `prompts/interpret_intent/v1.jinja` that is present verbatim in every rendering of
that template, regardless of the player's action or which options are on offer, and that no prose
render prompt would ever contain. Detecting on this structural instruction — rather than a
substring of the player's typed action or the options themselves — is what keeps this branch from
ever firing on a render prompt, and from being defeated by a player typing something that merely
looks like JSON.
"""

_INTENT_ACTION = re.compile(
    r'in their own words:\n\n"(?P<action>.*?)"\n\nThe options actually on offer'
)
_INTENT_OPTION = re.compile(
    r"^- id: (?P<id>\S+)\n {2}label: (?P<label>.*)$", re.MULTILINE
)

_TOKEN = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "to",
        "and",
        "or",
        "i",
        "you",
        "in",
        "on",
        "at",
        "of",
        "with",
        "for",
        "is",
        "it",
        "this",
        "that",
        "my",
        "your",
    }
)


def _tokenize(text: str) -> frozenset[str]:
    """Lowercase word tokens with stopwords stripped, for the intent-matching overlap rule."""
    return frozenset(
        word for word in _TOKEN.findall(text.lower()) if word not in _STOPWORDS
    )


class ScriptedLLM:
    """Replays scripted responses by idempotency key; composes a plain beat otherwise."""

    def __init__(self, script: Mapping[str, str] | None = None) -> None:
        """Configure the scripted beats.

        Args:
            script: Maps an idempotency key to the exact text to return for it. The turn loop
                keys on `"{character}:{chapter}:{fact_count}"`, so a scripted run is addressed by
                *who is looking and when* — which is exactly what changes on a replay-as-another-
                character pass, and why the same branch can be scripted twice without collision.
        """
        self._script = dict(script or {})

    @property
    def scripted_keys(self) -> frozenset[str]:
        """Which beats are authored. Lets a rehearsal assert its whole path is covered."""
        return frozenset(self._script)

    def generate(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        max_tokens: int,
        temperature: float,
        idempotency_key: str | None = None,
    ) -> Generation:
        """Return the scripted beat for `idempotency_key`, or compose one from the prompt."""
        if idempotency_key is not None and idempotency_key in self._script:
            return self._generation(self._script[idempotency_key], messages)

        prompt = messages[-1]["content"] if messages else ""
        if _INTENT_MARKER in prompt:
            return self._generation(self._match_intent(prompt), messages)
        return self._generation(self._compose(prompt), messages)

    @staticmethod
    def _match_intent(prompt: str) -> str:
        """Answer an `interpret_intent` prompt with valid, schema-conforming JSON.

        The rule is plain keyword overlap: tokenize the player's typed action and each offered
        option's label (lowercased, stopwords stripped), and pick the option sharing the most
        tokens with the action. Zero shared tokens with every option keeps the null path
        reachable — a typed action unrelated to anything on offer must still resolve to no match,
        not to an arbitrarily-guessed option. Confidence is a fixed constant on a match, well
        clear of `IntentRouter`'s threshold, and `0.0` otherwise; there is no live model to hedge
        for, so a graded confidence would only dress up a coin flip as judgment.
        """
        action_match = _INTENT_ACTION.search(prompt)
        action_tokens = (
            _tokenize(action_match.group("action")) if action_match else frozenset()
        )

        best_id: str | None = None
        best_overlap = 0
        for option_match in _INTENT_OPTION.finditer(prompt):
            label_tokens = _tokenize(option_match.group("label"))
            overlap = len(action_tokens & label_tokens)
            if overlap > best_overlap:
                best_overlap = overlap
                best_id = option_match.group("id")

        if best_id is None:
            payload: dict[str, str | float | None] = {
                "choice_id": None,
                "confidence": 0.0,
                "reasoning": "scripted: no offered option shares a word with the typed action",
            }
        else:
            payload = {
                "choice_id": best_id,
                "confidence": 0.75,
                "reasoning": (
                    f"scripted: matched {best_overlap} shared word(s) with the offered option"
                ),
            }
        return json.dumps(payload)

    @staticmethod
    def _compose(prompt: str) -> str:
        """Build a readable beat out of the facts the prompt was allowed to carry.

        Reads only the assembled prompt, so it cannot surface anything the guard withheld — the
        fallback is bound by the same context the real renderer would be.
        """
        protagonist_match = _PROTAGONIST.search(prompt)
        protagonist = protagonist_match.group("name") if protagonist_match else "You"

        block = _KNOWLEDGE_BLOCK.search(prompt)
        known = (
            [
                f"{match.group('subject')} {match.group('predicate').replace('_', ' ')} "
                f"{match.group('object')}".strip()
                for match in _FACT_LINE.finditer(block.group("facts"))
                if not match.group("subject").startswith("(")
            ]
            if block
            else []
        )
        if not known:
            return (
                f"{protagonist} stands at the edge of the moment with nothing to go on. "
                f"Whatever happens next has to start from here."
            )

        head = known[0]
        rest = known[1:4]
        lines = [f"{protagonist} turns it over again: {head}."]
        if rest:
            lines.append("Behind that sits the rest of it — " + "; ".join(rest) + ".")
        lines.append(
            f"{protagonist} weighs what is actually known, which is less than it feels like, "
            f"and waits for the moment to force a hand."
        )
        return " ".join(lines)

    @staticmethod
    def _generation(output: str, messages: list[dict[str, str]]) -> Generation:
        """Report token counts as 0 rather than inventing plausible ones.

        A fabricated count would flow straight into the cost meter and make the budget dashboard
        confidently wrong. Zero is honest: no tokens were bought.
        """
        return Generation(
            output=output,
            model=MODEL_NAME,
            prompt_tokens=0,
            completion_tokens=0,
            cost_usd=0.0,
        )
