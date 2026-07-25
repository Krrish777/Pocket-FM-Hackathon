"""The turn loop: one choice in, one rendered beat out, with knowledge propagated in between.

This is the core loop of `project_context.md` §4, and its shape is dictated by §4.4:

    assemble the actor's filtered view
      -> apply the chosen consequence to world state   (deterministic, in code)
      -> propagate knowledge from who was present       (deterministic, in code)
      -> render ONE scene from the updated view         (the only model call)

**Exactly one model call per turn, and it decides nothing.** Every state transition above happens
in code before the renderer is invoked. That is not a performance choice: the epistemic guarantee
comes from what is *absent from the assembled context*, not from asking a model to withhold. A fact
that never enters the prompt cannot leak, whereas a fact placed in the prompt with an instruction to
ignore it is one sampling accident away from the stage.

The renderer takes the character as a **parameter**, never a constant, which is what makes
`replay_as` (§8.1 — the closing demo beat) a re-render rather than a rewrite.
"""

import logging
from datetime import UTC, datetime

from story_engine.domain.enums import AssertionMode, FactStatus
from story_engine.domain.models.canon import (
    Awareness,
    ChapterIndex,
    Fact,
    Provenance,
    Scene,
)
from story_engine.domain.models.play import (
    ChoiceOption,
    Citation,
    Consequence,
    Playthrough,
    Turn,
)
from story_engine.domain.propagation import witnesses_learn
from story_engine.ports.branch_oracle import BranchOraclePort
from story_engine.ports.canon_store import CanonStorePort
from story_engine.ports.llm import LLMPort
from story_engine.ports.prompt_store import PromptStorePort
from story_engine.services.working_memory import MemoryPacket, WorkingMemory
from story_engine.shared.errors import StoryEngineError

logger = logging.getLogger(__name__)

RENDER_PROMPT = "render_scene"
RENDER_PROMPT_VERSION = "v1"
"""Pinned, never "latest by accident" — a prompt change must be a reviewable diff
(`.claude/rules/llm-storytelling.md` §2)."""

MAX_SCENE_TOKENS = 700
TEMPERATURE = 0.8
"""High, deliberately: this call produces prose and nothing else. Every continuity-critical
decision was already made in code before we got here, so there is nothing for a low temperature
to protect."""

CITATION_LIMIT = 3


class PlaythroughError(StoryEngineError):
    """A turn could not be taken."""

    code = "playthrough_failed"


class UnknownChoiceError(PlaythroughError):
    """The chosen option was not among those offered."""

    code = "unknown_choice"


class PlaythroughService:
    """Drives a choice-based playthrough over a fork of canon."""

    def __init__(
        self,
        *,
        store: CanonStorePort,
        memory: WorkingMemory,
        oracle: BranchOraclePort,
        llm: LLMPort,
        prompts: PromptStorePort,
        model: str = "claude-sonnet-5",
    ) -> None:
        self._store = store
        self._memory = memory
        self._oracle = oracle
        self._llm = llm
        self._prompts = prompts
        self._model = model

    # --- public API ---------------------------------------------------------------------

    def begin(
        self, *, fork_id: str, protagonist: str, chapter: ChapterIndex
    ) -> Playthrough:
        """Open a run: render the opening beat from `protagonist`'s view and offer choices."""
        turn = self._render_turn(
            fork_id=fork_id, protagonist=protagonist, chapter=chapter, index=0
        )
        return Playthrough(
            fork_id=fork_id, protagonist=protagonist, chapter=chapter, turns=(turn,)
        )

    def advance(self, run: Playthrough, choice_id: str) -> Playthrough:
        """Apply a choice, propagate what it taught, and render the next beat.

        Raises:
            UnknownChoiceError: `choice_id` was not offered on the current turn. Accepting an
                unoffered choice would let a caller apply a consequence the player never saw.
            PlaythroughError: The run has already reached its depth ceiling.
        """
        if run.is_complete:
            raise PlaythroughError(
                f"run is already {run.depth} turns deep (ceiling {run.MAX_DEPTH})"
            )

        current = run.turns[-1]
        choice = self._find_choice(current, choice_id)
        next_chapter = current.chapter + 1

        self._apply(
            fork_id=run.fork_id,
            choice=choice,
            chapter=next_chapter,
            turn_index=len(run.turns),
        )

        turn = self._render_turn(
            fork_id=run.fork_id,
            protagonist=run.protagonist,
            chapter=next_chapter,
            index=len(run.turns),
        )
        return run.model_copy(
            update={"chapter": next_chapter, "turns": (*run.turns, turn)}
        )

    def replay_as(self, run: Playthrough, character: str) -> Playthrough:
        """Re-render a finished run from another character's epistemic view.

        `project_context.md` §8.1 — the closing beat. Nothing about the world is recomputed: the
        same facts, the same chapters, the same branch. Only the *knower* changes, and the guard
        does the rest. That it costs this little is the whole point of the uniform state schema
        (§4.4): if character state were stored per-character, this would be a rewrite.
        """
        rerendered = tuple(
            self._render_turn(
                fork_id=run.fork_id,
                protagonist=character,
                chapter=turn.chapter,
                index=turn.index,
                choices=turn.choices,
            )
            for turn in run.turns
        )
        return run.model_copy(update={"protagonist": character, "turns": rerendered})

    # --- internals ----------------------------------------------------------------------

    @staticmethod
    def _find_choice(turn: Turn, choice_id: str) -> ChoiceOption:
        for option in turn.choices:
            if option.id == choice_id:
                return option
        offered = [option.id for option in turn.choices]
        raise UnknownChoiceError(
            f"{choice_id!r} was not offered on turn {turn.index}; options were {offered}"
        )

    def _apply(
        self,
        *,
        fork_id: str,
        choice: ChoiceOption,
        chapter: ChapterIndex,
        turn_index: int,
    ) -> None:
        """Write the choice's consequence into the world, then spread what it taught.

        Order matters and is not arbitrary: the new fact is written first so that a disclosure in
        the same scene can reference it, and propagation runs last so it sees the final roster.
        """
        consequence = choice.consequence
        scene = Scene(
            id=f"{fork_id}:t{turn_index}:{choice.id}",
            fork_id=fork_id,
            chapter=chapter,
            order_in_chapter=0,
            summary=choice.label,
            roster=consequence.roster,
        )

        self._store.append(self._fact_for(scene, consequence, fork_id, chapter))

        # Existing secrets the scene lets its witnesses in on. This is where knowledge compounds:
        # everything else only ever adds facts, this adds *knowers* to facts already in play.
        for fact_id in consequence.discloses:
            existing = self._store.get(fact_id)
            if existing is None:
                raise PlaythroughError(
                    f"choice {choice.id!r} discloses unknown fact {fact_id!r}"
                )
            learned = witnesses_learn(existing, scene)
            if learned is not existing and learned.knower_scope is not None:
                self._store.record_learning(fact_id, learned.knower_scope)
                logger.info(
                    "scene %s taught %s to %d knower(s)",
                    scene.id,
                    fact_id,
                    len(learned.knower_scope),
                )

    @staticmethod
    def _fact_for(
        scene: Scene, consequence: Consequence, fork_id: str, chapter: ChapterIndex
    ) -> Fact:
        """Turn a consequence into a canon fact scoped to whoever was in the room.

        A secret is stored with a `knower_scope` covering exactly the witnesses and no
        `revealed_at` — the audience has not been told. A public consequence is stored untracked,
        because attaching a scope to something everyone can see would *narrow* it (see
        `domain.propagation`).
        """
        witnesses = tuple(
            Awareness(knower=witness, learned_at=chapter)
            for witness in sorted(scene.witnesses)
        )
        return Fact(
            id=f"{scene.id}:fact",
            fork_id=fork_id,
            subject_id=consequence.subject_id,
            predicate=consequence.predicate,
            object_literal=consequence.object_literal,
            valid_from=chapter,
            revealed_at=None if consequence.secret else chapter,
            assertion_mode=AssertionMode.NARRATED,
            knower_scope=witnesses if consequence.secret else None,
            provenance=Provenance(
                source_id=f"playthrough:{fork_id}",
                chapter=chapter,
                char_start=0,
                char_end=len(scene.summary),
                quote=scene.summary,
            ),
            confidence=1.0,
            tier=1,  # a player's branch never outranks the novel (tier 0)
            status=FactStatus.ACTIVE,
            recorded_at=datetime.now(UTC),
        )

    def _render_turn(
        self,
        *,
        fork_id: str,
        protagonist: str,
        chapter: ChapterIndex,
        index: int,
        choices: tuple[ChoiceOption, ...] | None = None,
    ) -> Turn:
        packet = self._memory.assemble(fork_id, protagonist, chapter)
        offered = (
            choices
            if choices is not None
            else self._oracle.options_at(
                fork_id=fork_id, chapter=chapter, protagonist=protagonist
            )
        )
        return Turn(
            index=index,
            chapter=chapter,
            protagonist=protagonist,
            scene=self._narrate(packet, offered),
            choices=offered,
            citations=self._citations(packet),
            withheld_count=packet.withheld_count,
        )

    def _narrate(self, packet: MemoryPacket, choices: tuple[ChoiceOption, ...]) -> str:
        """The single model call. Its input is the packet — nothing the character cannot know."""
        prompt = self._prompts.render(
            RENDER_PROMPT,
            version=RENDER_PROMPT_VERSION,
            variables={
                "protagonist": packet.knower,
                "chapter": packet.chapter,
                "facts": [
                    {
                        "subject": fact.subject_id,
                        "predicate": fact.predicate,
                        "object": fact.object_literal or fact.object_id or "",
                        "quote": fact.provenance.quote,
                    }
                    for fact in packet.facts
                ],
                "choices": [choice.label for choice in choices],
            },
        )
        generation = self._llm.generate(
            messages=[{"role": "user", "content": prompt}],
            model=self._model,
            max_tokens=MAX_SCENE_TOKENS,
            temperature=TEMPERATURE,
            # Same character, same chapter, same packet -> same key, so a retry after a timeout
            # is not billed or counted twice (.claude/rules/llm-storytelling.md §4).
            idempotency_key=f"{packet.knower}:{packet.chapter}:{len(packet.facts)}",
        )
        return generation.output

    @staticmethod
    def _citations(packet: MemoryPacket) -> tuple[Citation, ...]:
        """The receipt: the canon behind this beat, traceable to where it was written."""
        return tuple(
            Citation(
                fact_id=fact.id,
                source_id=fact.provenance.source_id,
                chapter=fact.provenance.chapter,
                quote=fact.provenance.quote,
            )
            for fact in packet.facts[:CITATION_LIMIT]
        )
