"""Play router — a thin inbound adapter over the turn loop.

No narrative logic, no state transitions, and no knowledge decisions live here: every state
transition is `PlaythroughService.advance`'s job, every intent classification is
`IntentRouter.resolve`'s job, and every visibility decision is already enforced inside
`WorkingMemory.assemble`/`CanonStorePort.visible_to` (which route through
`domain.models.canon.is_visible`). This module only parses request DTOs, calls those services, and
maps the result to response DTOs.

`TurnResponse.choices` exposes `id`, `label`, and `source_work_id` only — see
`ChoiceOptionResponse` in `api/schemas.py` for why `consequence` must never appear here.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from story_engine.api.schemas import (
    ActRequest,
    ActResponse,
    CharacterResponse,
    ChoiceOptionResponse,
    CitationResponse,
    PlayRequest,
    PlayResponse,
    ReactionResponse,
    ReplayAsRequest,
    ReplayResponse,
    TurnResponse,
)
from story_engine.bootstrap import Container
from story_engine.domain.models.canon import ChapterIndex
from story_engine.domain.models.play import ChoiceOption, Citation, Playthrough, Turn
from story_engine.domain.reactions import CharacterDirective, derive_directives
from story_engine.resources.dexter_demo import CAST, FORK_ID
from story_engine.shared.errors import PlaythroughNotFoundError

router = APIRouter(tags=["play"])

STARTING_CHAPTER: ChapterIndex = 1


def get_container(request: Request) -> Container:
    """Resolve the wired container from the app state."""
    container: Container = request.app.state.container
    return container


ContainerDep = Annotated[Container, Depends(get_container)]


@router.get("/characters", response_model=list[CharacterResponse])
def list_characters(container: ContainerDep) -> list[CharacterResponse]:
    """The playable cast, from `resources.dexter_demo.CAST`."""
    del container  # unused: CAST is a module-level constant, not per-container state
    return [
        CharacterResponse(id=character_id, name=name)
        for character_id, name in CAST.items()
    ]


@router.post("/play", response_model=PlayResponse)
def start_play(body: PlayRequest, container: ContainerDep) -> PlayResponse:
    """Begin a new run at `FORK_ID`, chapter 1, from `body.character_id`'s point of view."""
    run = container.playthrough.begin(
        fork_id=FORK_ID, protagonist=body.character_id, chapter=STARTING_CHAPTER
    )
    run_id = container.playthrough_repository.create(run)
    return PlayResponse(run_id=run_id, turn=_turn_response(run.turns[-1]))


@router.get("/play/{run_id}", response_model=PlayResponse)
def get_play(run_id: str, container: ContainerDep) -> PlayResponse:
    """Return the current turn of an in-progress run."""
    run = _load_run(container, run_id)
    return PlayResponse(run_id=run_id, turn=_turn_response(run.turns[-1]))


@router.post("/play/{run_id}/act", response_model=ActResponse)
def act(run_id: str, body: ActRequest, container: ContainerDep) -> ActResponse:
    """Route the player's typed action onto an offered choice, then advance the run.

    When `IntentRouter.resolve` finds no confident match, the turn is **not** advanced: the run is
    left exactly as it was, and the response is a 422 carrying the offered option labels so a UI
    can re-prompt the player.
    """
    run = _load_run(container, run_id)
    current = run.turns[-1]

    resolved = container.intent_router.resolve(
        action=body.action, options=current.choices, protagonist=run.protagonist
    )
    if resolved.choice_id is None:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "no_intent_match",
                "message": resolved.reasoning,
                "options": [choice.label for choice in current.choices],
            },
        )

    interpreted_as = _label_for(current.choices, resolved.choice_id)
    updated = container.playthrough.advance(run, resolved.choice_id)
    container.playthrough_repository.save(run_id, updated)

    new_turn = updated.turns[-1]
    return ActResponse(
        run_id=run_id,
        turn=_turn_response(new_turn),
        interpreted_as=interpreted_as,
        reactions=[
            _reaction_response(directive)
            for directive in _reactions(
                container, updated.protagonist, new_turn.chapter
            )
        ],
    )


@router.post("/play/{run_id}/replay-as", response_model=ReplayResponse)
def replay_as(
    run_id: str, body: ReplayAsRequest, container: ContainerDep
) -> ReplayResponse:
    """Re-render the whole run from another character's point of view.

    A read-only re-render (`PlaythroughService.replay_as`): the same branch, the same chapters —
    only the knower changes, and the spoiler guard does the rest. Not persisted back to `run_id`,
    since it is a view of the run, not a new state for it.
    """
    run = _load_run(container, run_id)
    rerendered = container.playthrough.replay_as(run, body.character_id)
    return ReplayResponse(
        run_id=run_id,
        turns=[_turn_response(turn) for turn in rerendered.turns],
    )


# --- internals: DTO mapping + guarded reaction derivation --------------------------------------


def _load_run(container: Container, run_id: str) -> Playthrough:
    run = container.playthrough_repository.get(run_id)
    if run is None:
        raise PlaythroughNotFoundError(f"no playthrough run {run_id!r}")
    return run


def _label_for(choices: tuple[ChoiceOption, ...], choice_id: str) -> str:
    """The label of the option `IntentRouter.resolve` matched.

    `IntentRouter.resolve` only ever returns a `choice_id` drawn verbatim from the options it was
    given (see `services/intent_router.py`), so `choice_id` is always among `choices` here — a
    `StopIteration` would mean that guarantee broke, which is a bug to surface loudly, not mask.
    """
    return next(choice.label for choice in choices if choice.id == choice_id)


def _reactions(
    container: Container, protagonist: str, chapter: ChapterIndex
) -> tuple[CharacterDirective, ...]:
    """What the rest of the cast is missing, recomputed for this beat.

    Mirrors `PlaythroughService._directives`: the same guarded queries
    (`WorkingMemory.assemble`, `CanonStorePort.visible_to`) that already route through
    `domain.models.canon.is_visible`, never re-derived or approximated here. Computed fresh on
    every call and never persisted, per `domain/reactions.py`.
    """
    packet = container.memory.assemble(FORK_ID, protagonist, chapter)
    return derive_directives(
        actor=protagonist,
        actor_facts=packet.facts,
        others={
            character_id: (
                name,
                container.canon_store.visible_to(FORK_ID, character_id, chapter),
            )
            for character_id, name in CAST.items()
        },
    )


def _choice_response(option: ChoiceOption) -> ChoiceOptionResponse:
    """Field-by-field mapping — see `ChoiceOptionResponse` for why this is never `model_dump()`."""
    return ChoiceOptionResponse(
        id=option.id, label=option.label, source_work_id=option.source_work_id
    )


def _citation_response(citation: Citation) -> CitationResponse:
    return CitationResponse(
        fact_id=citation.fact_id,
        source_id=citation.source_id,
        chapter=citation.chapter,
        quote=citation.quote,
    )


def _reaction_response(directive: CharacterDirective) -> ReactionResponse:
    return ReactionResponse(
        name=directive.name,
        tension=directive.tension,
        blind_spots=list(directive.blind_spots),
    )


def _turn_response(turn: Turn) -> TurnResponse:
    return TurnResponse(
        index=turn.index,
        chapter=turn.chapter,
        protagonist=turn.protagonist,
        scene=turn.scene,
        choices=[_choice_response(choice) for choice in turn.choices],
        citations=[_citation_response(citation) for citation in turn.citations],
        withheld_count=turn.withheld_count,
    )
