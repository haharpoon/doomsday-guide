#!/usr/bin/env python3
"""Load doomsday guide sheets from Markdown files.

Writers edit files in the content directory. The keyboard guide and the
touch guide both read this module, so the wording can change without a
Python edit.

Search order for that directory:

1. ``DOOMSDAY_CONTENT``, when it points at a directory
2. ``/usr/local/share/doomsday/content``
3. ``content`` next to the running script, then next to this file

A missing directory yields an empty guide. Callers keep running.
"""

import os
import re
import sys
from pathlib import Path

FIXED_CONTENT = Path("/usr/local/share/doomsday/content")
IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")
HEADING_RE = re.compile(r"(?m)^## ")
_BLOCK_MARKERS = ("|", ">", "|-", ">-", "|+", ">+")


class Topic:
    def __init__(self, slug, title, order, intro, book, hint, parent, merge, tint, cards, path):
        self.slug = slug
        self.title = title
        self.order = order
        self.intro = intro or ""
        self.book = book
        self.hint = hint or ""
        self.parent = parent
        self.merge = bool(merge)
        self.tint = bool(tint)
        self.cards = list(cards)
        self.path = path


class CardEntry:
    """One card in the startup search index.

    ``body`` is the same string the topic already holds. ``title_fold`` and
    ``body_fold`` are built once so a keystroke does not walk the files again.
    """

    __slots__ = (
        "topic_slug",
        "topic_title",
        "title",
        "body",
        "tint",
        "title_fold",
        "body_fold",
        "letter",
    )

    def __init__(self, topic_slug, topic_title, title, body, tint):
        self.topic_slug = topic_slug
        self.topic_title = topic_title
        self.title = title
        self.body = body
        self.tint = bool(tint)
        self.title_fold = " ".join((title or "").split()).casefold()
        self.body_fold = fold_search_text(body)
        self.letter = index_letter(title)


class Guide:
    def __init__(self, topics, directory):
        self.topics = topics
        self.directory = directory
        # Built once here, at load, and reused for every keystroke.
        self.index = build_card_index(self)

    def home_topics(self):
        rows = [topic for topic in self.topics.values() if not topic.parent]
        rows.sort(key=_topic_sort)
        return rows

    def nested(self, slug):
        rows = [
            topic
            for topic in self.topics.values()
            if topic.parent == slug and not topic.merge
        ]
        rows.sort(key=_topic_sort)
        return rows

    def cards(self, slug):
        """Cards for one topic, with ``merge: cards`` children placed first."""
        topic = self.topics.get(slug)
        if topic is None:
            return []
        merged = [
            child
            for child in self.topics.values()
            if child.parent == slug and child.merge
        ]
        merged.sort(key=_topic_sort)
        found = []
        for child in merged:
            found.extend(child.cards)
        found.extend(topic.cards)
        return found

    def plain(self, slug):
        """Body text for a one-card topic. Several cards are joined by a blank line."""
        cards = self.cards(slug)
        if len(cards) == 1:
            return cards[0][1]
        return "\n\n".join(body for _name, body in cards)

    def present(self, slug):
        """How a topic should open: search, a single sheet, or a menu of cards."""
        topic = self.topics.get(slug)
        if topic is None:
            return None
        cards = self.cards(slug)
        children = self.nested(slug)
        if not cards and not children and topic.book is not None:
            kind = "search"
        elif len(cards) == 1 and not children:
            kind = "sheet"
        else:
            kind = "menu"
        return {
            "kind": kind,
            "topic": topic,
            "cards": cards,
            "children": children,
            "book": topic.book,
        }


def _topic_sort(topic):
    return (topic.order is None, topic.order if topic.order is not None else 0, topic.slug)


# A-Z, then a bucket for titles that start with a digit ("12 V systems").
INDEX_LETTERS = tuple(chr(code) for code in range(ord("A"), ord("Z") + 1)) + ("#",)


def index_letter(title):
    """Jump-list bucket for a card title. Letters win over a leading digit."""
    for char in (title or "").strip():
        if char.isalpha():
            return char.upper()
        if char.isdigit():
            return "#"
    return "#"


def fold_search_text(body):
    """Case-folded body text for matching. Image paths are dropped; alt text stays."""

    def repl(match):
        alt = match.group(1).strip()
        return f" {alt} " if alt else " "

    text = IMAGE_RE.sub(repl, body or "")
    return " ".join(text.split()).casefold()


def build_card_index(guide):
    """Every card, once, alphabetical.

    A ``merge: cards`` file is listed under its parent (that is where the menu
    shows it), not as its own topic. A nested topic (``parent`` set, not merged)
    keeps its own cards under its own title, so a Signals & Radio sub-topic is
    searchable on its own. Topics with no cards add nothing.
    """
    topics = getattr(guide, "topics", None) or {}
    entries = []
    for topic in topics.values():
        if topic.merge and topic.parent in topics:
            continue
        for name, body in guide.cards(topic.slug):
            entries.append(
                CardEntry(
                    topic.slug,
                    topic.title,
                    name,
                    body,
                    topic.tint,
                )
            )
    entries.sort(
        key=lambda entry: (
            entry.title_fold,
            entry.topic_title.casefold(),
            entry.topic_slug,
        )
    )
    return tuple(entries)


def search_cards(entries, query):
    """Rank cards for a typed query.

    Every word must appear, case-insensitive, in the title or the body.
    Cards whose titles contain every word come first (titles that start with
    the query, then the rest, A–Z). Body matches follow, A–Z. An empty query
    matches nothing.
    """
    folded = " ".join((query or "").split()).casefold()
    tokens = folded.split()
    if not tokens:
        return []
    title_hits = []
    body_hits = []
    for entry in entries:
        in_title = all(token in entry.title_fold for token in tokens)
        if in_title:
            title_hits.append(entry)
            continue
        if all(token in entry.title_fold or token in entry.body_fold for token in tokens):
            body_hits.append(entry)

    def title_key(entry):
        starts = entry.title_fold.startswith(folded) or entry.title_fold.startswith(tokens[0])
        return (
            0 if starts else 1,
            entry.title_fold,
            entry.topic_title.casefold(),
            entry.topic_slug,
        )

    title_hits.sort(key=title_key)
    body_hits.sort(
        key=lambda entry: (
            entry.title_fold,
            entry.topic_title.casefold(),
            entry.topic_slug,
        )
    )
    return title_hits + body_hits


def _script_content_dirs():
    found = []
    argv0 = sys.argv[0] if sys.argv else ""
    if argv0:
        found.append(Path(argv0).resolve().parent / "content")
    found.append(Path(__file__).resolve().parent / "content")
    main = sys.modules.get("__main__")
    main_file = getattr(main, "__file__", None)
    if main_file:
        found.append(Path(main_file).resolve().parent / "content")
    unique = []
    for path in found:
        if path not in unique:
            unique.append(path)
    return unique


def _has_topics(path):
    if not path.is_dir():
        return False
    for entry in path.iterdir():
        if entry.is_file() and entry.suffix.lower() == ".md" and entry.name.lower() != "readme.md":
            return True
    return False


def find_content_dir():
    """Return the content directory, or None when no sheets are installed."""
    env = os.environ.get("DOOMSDAY_CONTENT", "").strip()
    if env:
        path = Path(env)
        if path.is_dir():
            return path
        sys.stderr.write(f"content: DOOMSDAY_CONTENT is not a directory ({path})\n")
        return None
    if _has_topics(FIXED_CONTENT):
        return FIXED_CONTENT
    for candidate in _script_content_dirs():
        if _has_topics(candidate):
            return candidate
    return None


def _unquote(value):
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def _parse_bool(value, default=True):
    text = _unquote(value).strip().lower()
    if text in ("1", "true", "yes", "on"):
        return True
    if text in ("0", "false", "no", "off"):
        return False
    return default


def _parse_order(value):
    text = _unquote(value).strip()
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    if number.is_integer():
        return int(number)
    return number


def parse_front_matter(raw):
    """Parse the small YAML subset used by the sheet files."""
    meta = {}
    lines = raw.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip() or line.lstrip().startswith("#"):
            index += 1
            continue
        if ":" not in line:
            index += 1
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value in _BLOCK_MARKERS:
            fold = value.startswith(">")
            index += 1
            block = []
            while index < len(lines):
                nxt = lines[index]
                if nxt.startswith((" ", "\t")):
                    block.append(nxt.strip())
                    index += 1
                    continue
                if not nxt.strip():
                    follower = lines[index + 1] if index + 1 < len(lines) else ""
                    if follower.startswith((" ", "\t")):
                        block.append("")
                        index += 1
                        continue
                break
            text = "\n".join(block).strip()
            if fold:
                paragraphs = []
                current = []
                for part in text.split("\n"):
                    if part:
                        current.append(part)
                    else:
                        if current:
                            paragraphs.append(" ".join(current))
                            current = []
                        paragraphs.append("")
                if current:
                    paragraphs.append(" ".join(current))
                text = "\n".join(paragraphs).strip()
            meta[key] = text
            continue
        meta[key] = _unquote(value)
        index += 1
    return meta


def parse_cards(body, fallback_title):
    body = body.replace("\r\n", "\n").replace("\r", "\n")
    chunks = HEADING_RE.split(body)
    cards = []
    preamble = chunks[0].strip() if chunks else ""
    for chunk in chunks[1:]:
        title, _sep, rest = chunk.partition("\n")
        name = title.strip()
        if name:
            cards.append((name, rest.strip()))
    if not cards and preamble:
        cards.append((fallback_title or "Sheet", preamble))
    return cards


def parse_topic(path):
    text = path.read_text(encoding="utf-8-sig")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    meta = {}
    body = text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            meta = parse_front_matter(text[4:end])
            body = text[end + 4 :]
    slug = path.stem
    title = (meta.get("title") or "").strip() or slug.replace("_", " ").title()
    order = _parse_order(meta["order"]) if "order" in meta else None
    book = None
    if "book" in meta:
        book = meta.get("book") or ""
    elif "archive" in meta:
        book = meta.get("archive") or ""
    parent = (meta.get("parent") or "").strip() or None
    merge = (meta.get("merge") or "").strip().lower() == "cards"
    tint = _parse_bool(meta["tint"]) if "tint" in meta else True
    return Topic(
        slug=slug,
        title=title,
        order=order,
        intro=meta.get("intro") or "",
        book=book,
        hint=meta.get("hint") or "",
        parent=parent,
        merge=merge,
        tint=tint,
        cards=parse_cards(body, title),
        path=path,
    )


def load_guide(directory=None):
    """Load every topic file. A missing directory returns an empty guide.

    Pass a directory to load that folder. Pass nothing to search the usual places.
    """
    if directory is None:
        folder = find_content_dir()
    else:
        folder = Path(directory)
        if not folder.is_dir():
            return Guide({}, None)
    if folder is None:
        return Guide({}, None)
    topics = {}
    for path in sorted(folder.glob("*.md"), key=lambda item: item.name.lower()):
        if path.name.lower() == "readme.md":
            continue
        try:
            topic = parse_topic(path)
        except (OSError, UnicodeError) as error:
            sys.stderr.write(f"content: skipped {path.name} ({error})\n")
            continue
        if topic.slug in topics:
            sys.stderr.write(
                f"content: duplicate topic {topic.slug}; keeping {topics[topic.slug].path.name}\n"
            )
            continue
        topics[topic.slug] = topic
    known = set(topics)
    for topic in topics.values():
        if topic.parent and topic.parent not in known:
            sys.stderr.write(f"content: {topic.slug}.md parent '{topic.parent}' was not found\n")
    return Guide(topics, folder)


def console_body(body):
    """Replace a markdown image with the keyboard guide's one-line placeholder."""

    def repl(match):
        alt = match.group(1).strip()
        if alt:
            return f"[diagram: {alt}]"
        return "[diagram]"

    return IMAGE_RE.sub(repl, body or "")


def split_parts(body):
    """Split a card into ``("text", str)`` and ``("image", alt, relpath)`` parts."""
    parts = []
    cursor = 0
    text = body or ""
    for match in IMAGE_RE.finditer(text):
        before = text[cursor : match.start()]
        if before:
            parts.append(("text", before))
        parts.append(("image", match.group(1).strip(), match.group(2).strip()))
        cursor = match.end()
    tail = text[cursor:]
    if tail:
        parts.append(("text", tail))
    if not parts:
        parts.append(("text", text))
    return parts


def resolve_image(directory, relpath):
    """Resolve ``img/name.png`` inside the content directory.

    Returns None when the path is missing, remote, or leaves the content tree.
    """
    if directory is None or not relpath:
        return None
    relpath = relpath.split("#", 1)[0].split("?", 1)[0].strip()
    if not relpath or "://" in relpath or relpath.startswith(("/", "\\")):
        return None
    root = Path(directory).resolve()
    path = (root / relpath).resolve()
    if path != root and root not in path.parents:
        return None
    if not path.is_file():
        return None
    return path
