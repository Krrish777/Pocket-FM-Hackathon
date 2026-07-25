"""Classify a wiki page as novel canon, screen canon, both, or unknown.

**This is the module that addresses `project_context.md` §11 OD-2.** Our knowledge base is novel-based
(§6.1) while fan fiction is predominantly screen-based (§6.4); without a per-entity basis label, a wiki
scrape silently injects screen canon. So every page is classified before anything derived from it is
emitted.

The signal is the page's own categories, verified live on `dexter.fandom.com` 2026-07-25:

* The novel and screen versions of a character are **separate pages** — `Brian Moser` (screen) and
  `Brian Moser (Novels)` (novel), the latter in `Category:Characters (Novels)`.
* `Category:Characters (Novels)` had 82 article members; `Category:Locations (Novels)` had 5;
  `Category:Characters with Television Counterparts` had 16 — the wiki's own novel/screen crosswalk.
* Per-book categories exist (`Category:Darkly Dreaming Dexter characters`), and the book titles are
  enumerable from `Category:Novels`, so they are discovered rather than hardcoded.
* Screen membership shows up as `Category:Season N characters` and per-show variants
  (`Characters (New Blood)`, `Characters (Original Sin)`, `Characters (Resurrection)`).

**Honest limits.** A page with neither signal is `UNKNOWN`, never novel. `SCREEN` means "the wiki marks
this as screen and shows no novel marking" — it is *strong evidence of* but not *proof of* screen-only
status, because absence of a novel page is not absence from the novels. Downstream must treat `SCREEN`
as a flag to review, per §6.4, not as a verdict. The category vocabulary is also fandom-specific: the
defaults here were tuned on the Dexter wiki and are injectable for any other.
"""

import re
from dataclasses import dataclass

from story_engine.domain.models.wiki_index import WikiCanonBasis

# Book-canon markers. "(Novels)" / "(Novels/Comics)" is the qualifier this wiki uses on both page
# titles and category names; the bare word covers `Category:Minor characters (Novels)` variants.
DEFAULT_NOVEL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\(novels?(?:\s*/\s*comics?)?\)", re.IGNORECASE),
    re.compile(r"\bnovels?\b", re.IGNORECASE),
    re.compile(r"\bbooks?\b", re.IGNORECASE),
)

# Screen-canon markers. `season <n>` and `episode` are the load-bearing ones: every screen character
# sampled live carried at least one `Season N characters` category.
DEFAULT_SCREEN_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bseasons?\s*\d+\b", re.IGNORECASE),
    re.compile(r"\bepisodes?\b", re.IGNORECASE),
    re.compile(r"\b(?:pilot|finale)\s+characters\b", re.IGNORECASE),
    re.compile(r"\b(?:tv|television)\s+series\b", re.IGNORECASE),
)

# Page-title qualifiers that mark a variant of an entity that also exists elsewhere. Stripped to get
# the canonical name, so `Brian Moser (Novels)` merges with `Brian Moser`.
_VARIANT_QUALIFIER_RE = re.compile(
    r"\s*\((?:novels?|comics?|books?|novels?\s*/\s*comics?|"
    r"tv\s*series|television\s*series|series|show|film|movie|games?|character)\)\s*$",
    re.IGNORECASE,
)
_CATEGORY_PREFIX_RE = re.compile(r"^category:", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class BasisRules:
    """The category vocabulary that distinguishes book canon from screen canon on one wiki.

    `novel_work_titles` is discovered from the wiki's own `Category:Novels` rather than hardcoded, so
    per-book categories like "Darkly Dreaming Dexter characters" are recognized without this module
    knowing any book titles.
    """

    novel_patterns: tuple[re.Pattern[str], ...] = DEFAULT_NOVEL_PATTERNS
    screen_patterns: tuple[re.Pattern[str], ...] = DEFAULT_SCREEN_PATTERNS
    novel_work_titles: frozenset[str] = frozenset()


def canonical_name(page_title: str) -> str:
    """Strip a media-variant qualifier from a page title to get the entity's canonical name.

    `"Brian Moser (Novels)" -> "Brian Moser"`. Only known media qualifiers are stripped, so a title
    that genuinely contains a parenthetical (`"Rudy Cooper (Alias)"`) is left intact.
    """
    return (
        _VARIANT_QUALIFIER_RE.sub("", page_title.strip()).strip() or page_title.strip()
    )


def classify(
    page_title: str, categories: tuple[str, ...], rules: BasisRules | None = None
) -> tuple[WikiCanonBasis, tuple[str, ...]]:
    """Classify one page's canon basis, returning the basis and the evidence for it.

    The evidence is returned so the call is auditable: `project_context.md` §5.4 requires that any
    claim can show what it was checked against, and "why is this labelled screen" is such a claim.

    Args:
        page_title: The wiki page title, which may itself carry a `(Novels)` qualifier.
        categories: Category names for the page, with or without the `Category:` prefix.
        rules: Category vocabulary to apply; the Dexter-tuned defaults are used if omitted.

    Returns:
        The basis, and the titles/categories that produced it — empty when nothing matched.
    """
    active = rules or BasisRules()
    evidence_novel: list[str] = []
    evidence_screen: list[str] = []

    if any(p.search(page_title) for p in active.novel_patterns):
        evidence_novel.append(page_title)

    for raw in categories:
        name = _CATEGORY_PREFIX_RE.sub("", raw).strip()
        if not name:
            continue
        if _is_novel_category(name, active):
            evidence_novel.append(f"Category:{name}")
        elif any(p.search(name) for p in active.screen_patterns):
            evidence_screen.append(f"Category:{name}")

    if evidence_novel and evidence_screen:
        basis = WikiCanonBasis.BOTH
    elif evidence_novel:
        basis = WikiCanonBasis.NOVEL
    elif evidence_screen:
        basis = WikiCanonBasis.SCREEN
    else:
        basis = WikiCanonBasis.UNKNOWN
    return basis, tuple(evidence_novel + evidence_screen)


def _is_novel_category(name: str, rules: BasisRules) -> bool:
    """Return True when a category name marks book canon, by pattern or by book title."""
    if any(pattern.search(name) for pattern in rules.novel_patterns):
        return True
    lowered = name.lower()
    return any(lowered.startswith(title) for title in rules.novel_work_titles)
