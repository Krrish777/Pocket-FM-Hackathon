"""Shared HTTP helpers for fanfic host adapters.

Politeness and resilience live here so every host adapter inherits the same backoff and
tag-stripping behaviour rather than reimplementing it.
"""

import html
import logging
import os
import random
import re
import time
from typing import Any

import httpx

from story_engine.shared.errors import SourceUnavailableError

logger = logging.getLogger(__name__)

# Wikimedia enforces its User-Agent policy strictly: verified 2026-07-25, a UA carrying only a
# product token gets 403, and so does a generic browser UA. The string must include a contactable
# URL or email in parentheses. Override via STORY_ENGINE_CONTACT to point at your own contact.
DEFAULT_CONTACT = "https://github.com/Krrish777"
CONTACT_ENV_VAR = "STORY_ENGINE_CONTACT"


def default_user_agent() -> str:
    """Return a policy-compliant User-Agent naming the tool and a contact point."""
    contact = os.environ.get(CONTACT_ENV_VAR, "").strip() or DEFAULT_CONTACT
    return f"story-engine-fanfic-harvest/0.1 ({contact}; hackathon research prototype)"


_RETRY_STATUS = frozenset({429, 500, 502, 503, 504})
# A closing block tag ends a paragraph, so it becomes a blank line; `<br>` is a soft break within
# one, so it becomes a single newline. Keeping them distinct preserves the author's stanza breaks.
_BLOCK_CLOSE_RE = re.compile(r"</\s*(?:p|div|h[1-6]|li|blockquote)\s*>", re.IGNORECASE)
_LINE_BREAK_RE = re.compile(r"<\s*br\s*/?\s*>", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_BLANK_RUN_RE = re.compile(r"\n{3,}")


def build_client(*, timeout: float = 20.0) -> httpx.Client:
    """Return an HTTP client configured with a descriptive agent and connection reuse."""
    return httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        headers={
            "User-Agent": default_user_agent(),
            "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )


def get_with_retry(
    client: httpx.Client,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    max_attempts: int = 4,
    base_delay: float = 1.0,
) -> httpx.Response:
    """GET `url`, retrying transient failures with exponential backoff and jitter.

    Raises:
        SourceUnavailableError: if every attempt fails or the host returns a non-retryable error.
    """
    last_detail = "no attempt made"
    for attempt in range(1, max_attempts + 1):
        try:
            response = client.get(url, params=params)
        except httpx.HTTPError as err:  # network-level: DNS, timeout, connection reset
            last_detail = f"{type(err).__name__}: {err}"
            logger.warning(
                "GET %s failed (attempt %s/%s): %s", url, attempt, max_attempts, err
            )
        else:
            if response.status_code < 400:
                return response
            last_detail = f"HTTP {response.status_code}"
            if response.status_code not in _RETRY_STATUS:
                raise SourceUnavailableError(
                    f"GET {url} returned {response.status_code}",
                    context={"url": url, "status": response.status_code},
                )
            logger.warning(
                "GET %s returned %s (attempt %s/%s)",
                url,
                response.status_code,
                attempt,
                max_attempts,
            )
        if attempt < max_attempts:
            time.sleep(base_delay * (2 ** (attempt - 1)) + random.uniform(0, 0.4))
    raise SourceUnavailableError(
        f"GET {url} failed after {max_attempts} attempts ({last_detail})",
        context={"url": url, "attempts": max_attempts, "last_detail": last_detail},
    )


def html_to_text(markup: str) -> str:
    """Convert a chapter's HTML fragment to plain text, preserving paragraph breaks."""
    with_paragraphs = _BLOCK_CLOSE_RE.sub("\n\n", markup)
    with_breaks = _LINE_BREAK_RE.sub("\n", with_paragraphs)
    stripped = _TAG_RE.sub("", with_breaks)
    unescaped = html.unescape(stripped)
    lines = [line.strip() for line in unescaped.splitlines()]
    return _BLANK_RUN_RE.sub("\n\n", "\n".join(lines)).strip()
