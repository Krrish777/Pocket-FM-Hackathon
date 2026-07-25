"""Episode generation use-case (application service).

Orchestrates ports only — never a vendor SDK. STARTER flow: assemble context from memory, render a
versioned prompt, call the one LLM wrapper, return a validated Episode. Refine to the brief; add a
`continuity_checker` pass before accepting output (see research/memory-and-persistence.md).
"""

from story_engine.domain.models import Episode
from story_engine.ports.episode_log_repository import EpisodeLogRepositoryPort
from story_engine.ports.llm import LLMPort
from story_engine.ports.prompt_store import PromptStorePort
from story_engine.ports.story_bible_repository import StoryBibleRepositoryPort


class EpisodeGenerator:
    """Generate the next episode of a series from a target beat."""

    def __init__(
        self,
        *,
        llm: LLMPort,
        prompts: PromptStorePort,
        bible: StoryBibleRepositoryPort,
        episodes: EpisodeLogRepositoryPort,
    ) -> None:
        self._llm = llm
        self._prompts = prompts
        self._bible = bible
        self._episodes = episodes

    def generate(self, series_id: str, *, beat: str, max_tokens: int = 2000) -> Episode:
        """Generate the next episode. STARTER — refine prompt name/version and context to the brief."""
        bible = self._bible.get_bible(series_id)
        recent = self._episodes.get_recent(series_id, n=3)
        prompt = self._prompts.render(
            "episode_generation",
            version="v1",
            variables={"bible": bible, "recent": recent, "beat": beat},
        )
        result = self._llm.generate(
            messages=[{"role": "user", "content": prompt}],
            model=bible.series_id,  # placeholder; wire real model id from settings
            max_tokens=max_tokens,
            temperature=0.8,
        )
        next_number = len(recent) + 1
        return Episode(
            number=next_number, title=f"Episode {next_number}", body=result.output
        )
