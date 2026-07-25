"""Central logging configuration.

Call `configure_logging()` EXACTLY ONCE from the composition root (`bootstrap`/entry points) — never
at import time of a shared module, never inside domain code. Modules just do
`logger = logging.getLogger(__name__)`. Stdlib `dictConfig` variant (zero extra deps); swap the
formatter for structlog/JSON later if desired. See .claude/rules/python-design.md.
"""

from logging.config import dictConfig


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging once, writing single-line records to stdout."""
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
                },
            },
            "handlers": {
                "stdout": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {"handlers": ["stdout"], "level": level},
        }
    )
