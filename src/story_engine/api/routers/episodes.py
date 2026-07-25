"""Episodes router — a thin inbound adapter that calls the application service.

No domain logic here: parse DTO → call service → map to response DTO. The service is resolved from
the container wired at the composition root.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from story_engine.api.schemas import EpisodeResponse, GenerateEpisodeRequest
from story_engine.services.episode_generator import EpisodeGenerator

router = APIRouter(prefix="/episodes", tags=["episodes"])


def get_generator(request: Request) -> EpisodeGenerator:
    """Resolve the wired EpisodeGenerator from the app container."""
    generator: EpisodeGenerator = request.app.state.container.episode_generator
    return generator


@router.post("/", response_model=EpisodeResponse)
def generate_episode(
    body: GenerateEpisodeRequest,
    generator: Annotated[EpisodeGenerator, Depends(get_generator)],
) -> EpisodeResponse:
    """Generate the next episode for a series from a target beat."""
    episode = generator.generate(body.series_id, beat=body.beat)
    return EpisodeResponse(
        number=episode.number, title=episode.title, body=episode.body
    )
