"""The playable layer: what a turn is, what a choice does, and what the receipt shows.

These are the shapes the player-facing loop moves through. They are deliberately *thin* — a turn
carries no character state of its own, because `project_context.md` §4.4 puts all character state in
one uniform schema in the canon store. A `Turn` is a rendering of that state, never a second copy
of it.

The asymmetry to notice: `Consequence` describes what a choice *does to the world*, and it is
authored data, not model output. `project_context.md` §4.4 requires state transitions to be computed
in code — the model renders prose, it never decides who learned what.
"""

from pydantic import Field, model_validator

from story_engine.domain.base import DomainModel
from story_engine.domain.models.canon import ChapterIndex, Presence


class Consequence(DomainModel):
    """What taking a choice makes true, and who is there to see it.

    `roster` is the whole epistemic mechanism: whoever is present learns the new fact, and whoever
    is merely `REFERENCED` — or absent entirely — does not. That single field is what makes the
    ripple real instead of narrated.
    """

    subject_id: str = Field(min_length=1)
    predicate: str = Field(min_length=1)
    object_literal: str = Field(min_length=1)
    roster: tuple[Presence, ...] = Field(min_length=1)
    secret: bool = Field(
        default=False,
        description="True when only the people present may ever know this. False means the "
        "audience learns it too, so the fact is stored untracked and governed by reveal time.",
    )
    discloses: tuple[str, ...] = Field(
        default=(),
        description="Ids of EXISTING secrets this scene lets its witnesses in on. This is the "
        "channel that makes knowledge compound rather than merely accumulate: a choice at turn 3 "
        "that puts Doakes in the room is how Doakes comes to know something Dexter has held since "
        "chapter 1, and why replaying the same branch as Deborah shows her still ignorant of it.",
    )


class ChoiceOption(DomainModel):
    """One branch offered at a decision point.

    `source_work_id` is what keeps `project_context.md` §5.2 honest: an option is supposed to come
    from a divergence real fan fiction already wrote, not from our imagination. `None` marks an
    option that was generated rather than mined, so the distinction stays auditable instead of
    becoming a claim nobody can check.
    """

    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    source_work_id: str | None = None
    consequence: Consequence

    @property
    def is_canon_baseline(self) -> bool:
        """Whether this option is what the novel actually did."""
        return self.source_work_id is None and self.id.endswith(":canon")


class Citation(DomainModel):
    """One line of the receipt — a checked claim and where in the source it came from."""

    fact_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    chapter: ChapterIndex
    quote: str = Field(min_length=1)


class Turn(DomainModel):
    """One rendered beat of a playthrough, from one character's point of view.

    `withheld_count` is reported rather than hidden. Per `.claude/rules/testing.md` the guard's
    asymmetry is deliberate — a leak is a hard failure, over-withholding is a *metric* — so the
    number of facts kept out of this turn is surfaced, not swallowed.
    """

    index: int = Field(ge=0)
    chapter: ChapterIndex
    protagonist: str = Field(min_length=1)
    scene: str = Field(min_length=1)
    choices: tuple[ChoiceOption, ...] = ()
    citations: tuple[Citation, ...] = ()
    withheld_count: int = Field(ge=0)

    @model_validator(mode="after")
    def _offers_a_playable_number_of_choices(self) -> "Turn":
        """2-4 options, or none at all when the run has ended (`project_context.md` §4 step 3).

        One option is not a choice, and more than four stops being a decision and starts being a
        menu — the bound is in the spec, so it is enforced here rather than trusted to callers.
        """
        if self.choices and not 2 <= len(self.choices) <= 4:
            raise ValueError(
                f"a decision point offers 2-4 options, got {len(self.choices)}; "
                f"use an empty tuple to end the run"
            )
        seen = [choice.id for choice in self.choices]
        if len(seen) != len(set(seen)):
            raise ValueError("choice ids must be unique within a turn")
        return self


class Playthrough(DomainModel):
    """The run so far: which fork it lives on, who is being played, and how deep it has gone."""

    fork_id: str = Field(min_length=1)
    protagonist: str = Field(min_length=1)
    chapter: ChapterIndex
    turns: tuple[Turn, ...] = ()

    MAX_DEPTH: int = 10
    """`project_context.md` §4.1: a ceiling, not a target. The system must not require 10 and must
    not break before 10."""

    @property
    def depth(self) -> int:
        return len(self.turns)

    @property
    def is_complete(self) -> bool:
        return self.depth >= self.MAX_DEPTH
