"""MediaWiki markup parsing — pure functions, no HTTP.

Wikitext, not rendered HTML, is what this adapter reads. Verified 2026-07-25 on `dexter.fandom.com`:
`prop=extracts` is not installed on Fandom wikis, so the only two ways to read a page are
`action=parse` (HTML) and `prop=revisions&rvprop=content` (wikitext). Wikitext wins because
the *structure we need is only present there*: an infobox arrives as named parameters
(`|relatives = [[Dexter Morgan]] <small>(younger brother)</small>`) which parse into typed
relationships, whereas the rendered form is a presentational `<aside class="portable-infobox">`
whose label/value pairing depends on skin CSS classes. One request yields both the relationship
graph and the lead prose.

Everything here is deliberately format-level and returns primitives; `fandom_wiki.py` maps those onto
domain models so the two concerns stay separately testable. Nothing here decides whether an
observation is *true* — see `canon_basis.py` for the novel-vs-screen labelling that makes it safe to
use at all.
"""

import re
from dataclasses import dataclass, field

# Markup that carries no narrative signal and would corrupt parameter splitting (galleries embed
# `|`-separated captions, refs embed arbitrary markup).
_CONTAINER_RE = re.compile(
    r"<\s*(gallery|ref|references|table|imagemap|poem)\b[^>]*>.*?<\s*/\s*\1\s*>",
    re.IGNORECASE | re.DOTALL,
)
_SELF_CLOSING_REF_RE = re.compile(r"<\s*ref\b[^>]*/\s*>", re.IGNORECASE)
_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_TABLE_RE = re.compile(r"^\{\|.*?^\|\}", re.MULTILINE | re.DOTALL)
_HEADING_RE = re.compile(r"^\s*={2,}\s*(.+?)\s*={2,}\s*$", re.MULTILINE)
_TAG_RE = re.compile(r"<[^>]+>")
_BREAK_RE = re.compile(r"<\s*br\s*/?\s*>", re.IGNORECASE)
_BOLD_RE = re.compile(r"'''(.+?)'''", re.DOTALL)
_QUOTE_MARKS_RE = re.compile(r"'{2,5}")
_LINK_RE = re.compile(r"\[\[([^\[\]]+?)\]\]")
_EXTERNAL_LINK_RE = re.compile(r"\[(?:https?|//)\S+?(?:\s+([^\]]*))?\]")
_ASSET_LINK_PREFIX = ("file:", "image:", "category:", "media:", "видео:", "video:")
_BULLET_RE = re.compile(r"^[*#:;]+\s*", re.MULTILINE)
_PARENTHETICAL_RE = re.compile(r"\(([^()]*)\)")
# A bolded narrative role is not a name. Also covers the work-title words that leak from a lead's
# later sentences ("...also appears in the '''Dexter Novels'''").
_ROLE_NOUN_RE = re.compile(
    r"\b(?:antagonists?|protagonists?|deuteragonist|tritagonist|characters?|villains?|"
    r"heroe?s?|heroine|narrator|series|seasons?|episodes?|franchise|novels?|comics?|"
    r"films?|movies?|shows?|books?|games?)\b",
    re.IGNORECASE,
)
_PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n")
# A bare rank or honorific is not a name. Wikis put them in `aliases` ("Captain" for Maria LaGuerta),
# where as a match term they would fire on every blurb containing the word.
RANK_WORDS = frozenset(
    {
        "captain",
        "sergeant",
        "sgt",
        "detective",
        "lieutenant",
        "lt",
        "officer",
        "doctor",
        "dr",
        "professor",
        "mr",
        "mrs",
        "ms",
        "miss",
        "sir",
        "agent",
        "father",
        "mother",
        "sister",
        "brother",
        "nurse",
        "chief",
    }
)
_WHITESPACE_RE = re.compile(r"[ \t]+")
_BLANK_RUN_RE = re.compile(r"\n{3,}")
_ENTRY_SPLIT_RE = re.compile(r"\n+")

# Infobox parameters that describe how a page LOOKS. Excluded from facts so a bible carries canon,
# not layout. A drop-list generalizes across wikis far better than a per-wiki allow-list.
PRESENTATIONAL_FIELDS = frozenset(
    {
        "image",
        "image2",
        "imagebg",
        "images",
        "photo",
        "picture",
        "portrait",
        "logo",
        "icon",
        "caption",
        "imagecaption",
        "imagewidth",
        "width",
        "height",
        "size",
        "px",
        "pixels",
        "align",
        "alignment",
        "color",
        "colour",
        "backcolor",
        "altbackcolor",
        "bordercolor",
        "borderradius",
        "bgcolor",
        "fontcolor",
        "textcolor",
        "maxwidth",
        "style",
        "class",
        "name",
        "title",
        "description",
        "hidden",
        "collapse",
    }
)

# Parameters whose values are lists of OTHER entities. These become relationships instead of facts.
RELATIONSHIP_FIELDS: dict[str, str] = {
    "relatives": "relative",
    "known relatives": "relative",
    "family": "family",
    "relationships": "relationship",
    "spouse": "spouse",
    "spouses": "spouse",
    "husband": "spouse",
    "wife": "spouse",
    "children": "child",
    "parents": "parent",
    "father": "parent",
    "mother": "parent",
    "siblings": "sibling",
    "significant other": "partner",
    "significant others": "partner",
    "love interest": "partner",
    "love interests": "partner",
    "romances": "partner",
    "partner": "partner",
    "partners": "partner",
    "allies": "ally",
    "friends": "friend",
    "enemies": "enemy",
    "affiliation": "affiliation",
    "affiliations": "affiliation",
    "allegiance": "affiliation",
    "employer": "employer",
    "team": "affiliation",
    "organization": "affiliation",
    "victims": "victim",
    "killed by": "killer",
    "creator": "creator",
}

# Parameters that name the entity by another name. Mined for aliases so "Rita Bennett" still finds
# the page titled "Rita Morgan" — verified live: it is neither the title nor a redirect, it appears
# only in `full name` and bolded in the lead sentence.
ALIAS_FIELDS = frozenset(
    {"aliases", "alias", "full name", "fullname", "real name", "other names", "aka"}
)

# Fields whose value states whether the entity is still alive.
STATUS_FIELDS = ("status", "current status", "state")

# Parameter names that mark a template as an entity profile rather than decoration. The template
# carrying the most of these wins — Fandom pages stack several templates (`Tabs`,
# `CharacterPicture`, `DualProfile`) and only one is the infobox.
PROFILE_SIGNAL_FIELDS = frozenset(
    {
        *RELATIONSHIP_FIELDS,
        *ALIAS_FIELDS,
        *STATUS_FIELDS,
        "age",
        "gender",
        "born",
        "birth_date",
        "death_date",
        "died",
        "species",
        "occupation",
        "profession",
        "job",
        "residence",
        "address",
        "nationality",
        "ethnicity",
        "first_appearance",
        "last_appearance",
        "first appearance",
        "last appearance",
        "seasons",
        "episodecount",
        "actor",
        "portrayed by",
        "hair",
        "eyes",
        "marital status",
        "nicknames",
        "moniker",
        "location",
        "type",
        "airdate",
        "writer",
        "director",
    }
)

# Values that mean "no data" and must not become a fact or a relationship.
_NULL_VALUES = frozenset(
    {
        "",
        "-",
        "--",
        "n/a",
        "na",
        "none",
        "none known",
        "unknown",
        "unnamed",
        "tbd",
        "tba",
        "?",
        "???",
    }
)

_MAX_FIELD_VALUE = 2000
_MAX_ALIAS_LENGTH = 80


@dataclass(slots=True)
class WikiTemplate:
    """One `{{Name|param=value}}` invocation, with its named parameters lowercased."""

    name: str
    params: dict[str, str] = field(default_factory=dict)

    @property
    def profile_score(self) -> int:
        """How many parameters look like entity-profile data rather than styling."""
        return len(PROFILE_SIGNAL_FIELDS & self.params.keys())


def preprocess(markup: str) -> str:
    """Remove comments, refs, galleries, and tables — markup that carries no canon."""
    without_comments = _COMMENT_RE.sub("", markup)
    without_containers = _CONTAINER_RE.sub("", without_comments)
    without_refs = _SELF_CLOSING_REF_RE.sub("", without_containers)
    return _TABLE_RE.sub("", without_refs)


def parse_templates(markup: str) -> tuple[WikiTemplate, ...]:
    """Return the top-level `{{...}}` invocations in `markup`, outermost only.

    Nested templates stay inside their parent's parameter values; a bible needs the parent's shape,
    and re-parsing children would double-count profile signals.
    """
    templates: list[WikiTemplate] = []
    index = 0
    length = len(markup)
    while index < length:
        start = markup.find("{{", index)
        if start == -1:
            break
        end = _matching_brace(markup, start)
        if end == -1:
            break
        templates.append(_parse_template(markup[start + 2 : end]))
        index = end + 2
    return tuple(templates)


def select_profile_template(templates: tuple[WikiTemplate, ...]) -> WikiTemplate | None:
    """Return the template most likely to be the entity infobox, or None if none qualifies.

    Chosen by how many recognized profile parameters a template carries rather than by name, because
    the name differs per wiki and even per page — `dexter.fandom.com` uses `DualProfile` for Brian
    Moser and `CharacterProfile` for Rita Morgan.
    """
    best: WikiTemplate | None = None
    for template in templates:
        if template.profile_score < 2:
            continue
        if best is None or template.profile_score > best.profile_score:
            best = template
    return best


def lead_wikitext(markup: str) -> str:
    """Return the lead section's markup — everything before the first `== Heading ==`.

    The lead is a wiki's own one-paragraph answer to "who is this", which is the summary an entity
    vocabulary needs; deeper sections are episode-by-episode recap. Returned as markup rather than
    prose so `lead_aliases` can still mine its bold markup for names.
    """
    body = preprocess(markup)
    heading = _HEADING_RE.search(body)
    if heading is not None:
        body = body[: heading.start()]
    return _strip_top_level_templates(body).strip()


def lead_section(markup: str) -> str:
    """Return the lead section as plain prose."""
    return strip_markup(lead_wikitext(markup))


def strip_markup(markup: str) -> str:
    """Convert wikitext to plain prose, resolving links to their display text."""
    text = _BREAK_RE.sub("\n", markup)
    text = _TAG_RE.sub("", text)
    text = _LINK_RE.sub(_render_link, text)
    text = _EXTERNAL_LINK_RE.sub(lambda m: m.group(1) or "", text)
    text = _QUOTE_MARKS_RE.sub("", text)
    text = _BULLET_RE.sub("", text)
    lines = [_WHITESPACE_RE.sub(" ", line).strip() for line in text.splitlines()]
    return _BLANK_RUN_RE.sub("\n\n", "\n".join(lines)).strip()


def lead_aliases(lead_markup: str) -> tuple[str, ...]:
    """Return the alternative names bolded in the lead's opening paragraph.

    A wiki lead bolds every name the subject goes by — "'''Brian Moser''', also known as '''The Ice
    Truck Killer''' or '''Rudy Cooper'''" — the cheapest reliable alias source there is. But it bolds
    other things too, and taking them all poisons name matching: an unfiltered pass on the live wiki
    gave Leon Prater the aliases "Angel Batista", "Serial Killers", and "Maria LaGuerta", which then
    made *any* mention of those characters resolve to Leon Prater. Three filters fix it:

    * **Opening paragraph only** — later paragraphs bold work titles ("Dexter Novels", "Season One").
    * **No wikilink inside** — a bolded link points at ANOTHER entity, never at another name for this
      one. This is what removes "Angel Batista" and "DEXTER".
    * **Looks like a name** — starts uppercase and is not a narrative role. Removes "secondary
      antagonist", "main character".
    """
    seen: dict[str, str] = {}
    for match in _BOLD_RE.finditer(_opening_paragraph(lead_markup)):
        raw = match.group(1)
        if _LINK_RE.search(raw):
            continue
        cleaned = clean_value(raw)
        if not _is_usable_alias(cleaned):
            continue
        if not cleaned[:1].isupper() or _ROLE_NOUN_RE.search(cleaned):
            continue
        seen.setdefault(cleaned.lower(), cleaned)
    return tuple(seen.values())


def clean_value(value: str) -> str:
    """Reduce one infobox parameter value to a single-line plain string."""
    return strip_markup(value).replace("\n", " ").strip(" ,;·—-")[:_MAX_FIELD_VALUE]


def is_null_value(value: str) -> bool:
    """Return True when a cleaned value means "no data"."""
    return value.strip().lower() in _NULL_VALUES


def split_entries(value: str) -> tuple[str, ...]:
    """Split a list-valued parameter into its entries on `<br>` and newlines."""
    normalized = _BREAK_RE.sub("\n", value)
    return tuple(
        entry
        for entry in (e.strip() for e in _ENTRY_SPLIT_RE.split(normalized))
        if entry
    )


def parse_entity_links(value: str) -> tuple[tuple[str, str], ...]:
    """Parse a relationship-style parameter into `(target, kind)` pairs.

    Handles the three shapes seen live: `[[Dexter Morgan]] <small>(younger brother)</small>`,
    `[[Gail Brandon]] (mother)`, and the unlinked `Cecilia (unseen aunt)`. An unlinked entry is kept
    because a name canon never gave a page is still a name the story must not contradict.
    """
    pairs: list[tuple[str, str]] = []
    for entry in split_entries(value):
        stripped = _TAG_RE.sub(" ", _BREAK_RE.sub(" ", entry))
        parentheticals = _PARENTHETICAL_RE.findall(stripped)
        kind = clean_value(parentheticals[-1]) if parentheticals else ""
        remainder = _PARENTHETICAL_RE.sub(" ", stripped)
        target = _first_link_target(remainder) or clean_value(remainder)
        if not target or is_null_value(target) or len(target) > 200:
            continue
        pairs.append((target, kind[:120]))
    return tuple(pairs)


def parse_aliases(value: str) -> tuple[str, ...]:
    """Parse an alias-style parameter into distinct usable alias strings."""
    seen: dict[str, str] = {}
    for entry in split_entries(value):
        candidate = clean_value(_PARENTHETICAL_RE.sub(" ", entry))
        if _is_usable_alias(candidate):
            seen.setdefault(candidate.lower(), candidate)
    return tuple(seen.values())


# --- internals ------------------------------------------------------------------------------
def _matching_brace(markup: str, start: int) -> int:
    """Return the index of the `}}` closing the `{{` at `start`, or -1 if unbalanced."""
    depth = 0
    index = start
    length = len(markup)
    while index < length - 1:
        pair = markup[index : index + 2]
        if pair == "{{":
            depth += 1
            index += 2
            continue
        if pair == "}}":
            depth -= 1
            if depth == 0:
                return index
            index += 2
            continue
        index += 1
    return -1


def _parse_template(body: str) -> WikiTemplate:
    """Parse a template's inner text (between the braces) into a name and named parameters."""
    parts = _split_top_level(body)
    name = parts[0].strip() if parts else ""
    params: dict[str, str] = {}
    for part in parts[1:]:
        key, separator, raw_value = part.partition("=")
        if not separator:
            continue  # positional parameter: no name to key facts by, so it carries no signal
        params[key.strip().lower()] = raw_value.strip()
    return WikiTemplate(name=name, params=params)


def _split_top_level(body: str) -> list[str]:
    """Split a template body on `|` characters that are not inside a nested template or link."""
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    index = 0
    length = len(body)
    while index < length:
        pair = body[index : index + 2]
        if pair in {"{{", "[["}:
            depth += 1
            current.append(pair)
            index += 2
            continue
        if pair in {"}}", "]]"}:
            depth = max(0, depth - 1)
            current.append(pair)
            index += 2
            continue
        char = body[index]
        if char == "|" and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(char)
        index += 1
    parts.append("".join(current))
    return parts


def _strip_top_level_templates(markup: str) -> str:
    """Remove whole top-level templates, keeping the prose between them.

    Infoboxes and quote boxes precede the lead sentence; leaving them in would make the summary open
    with styling parameters.
    """
    pieces: list[str] = []
    index = 0
    length = len(markup)
    while index < length:
        start = markup.find("{{", index)
        if start == -1:
            pieces.append(markup[index:])
            break
        pieces.append(markup[index:start])
        end = _matching_brace(markup, start)
        if end == -1:
            break
        index = end + 2
    return "".join(pieces)


def _render_link(match: re.Match[str]) -> str:
    """Render `[[Target|Text]]` as its display text, dropping file and category links."""
    inner = match.group(1)
    if inner.strip().lower().startswith(_ASSET_LINK_PREFIX):
        return ""
    target, _, label = inner.partition("|")
    return (label or target).strip()


def _first_link_target(text: str) -> str:
    """Return the target of the first wikilink in `text`, ignoring asset links."""
    for match in _LINK_RE.finditer(text):
        inner = match.group(1)
        if inner.strip().lower().startswith(_ASSET_LINK_PREFIX):
            continue
        target = inner.partition("|")[0].strip()
        if target:
            return target
    return ""


def _opening_paragraph(markup: str) -> str:
    """Return the first non-empty paragraph of `markup`."""
    for block in _PARAGRAPH_SPLIT_RE.split(markup):
        if block.strip():
            return block
    return ""


def _is_usable_alias(candidate: str) -> bool:
    """Reject empties, sentinels, bare ranks, and prose-length strings that are not really names."""
    if len(candidate) < 2 or len(candidate) > _MAX_ALIAS_LENGTH:
        return False
    if is_null_value(candidate):
        return False
    if candidate.strip(" .").lower() in RANK_WORDS:
        return False
    return any(char.isalpha() for char in candidate)
