#!/usr/bin/env python3
"""Offline doomsday field guide for this Pi.

The sheets live in Markdown files under the content directory.
See content/README.md. This program is the keyboard menu.
"""

import os
import re
import shutil
import sys
import textwrap
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

HOST = "http://127.0.0.1:8080"
NOTES = Path("/var/lib/kiwix/notes/field.txt")
MED = "wikipedia_en_medicine_nopic_2026-04"
VOY = "wikivoyage_en_all_nopic_2026-09"

BANNER = r"""
######   ####   ####  #   #  ####  ######  ####  #   #
#    #  #    # #    # ## ## #      #    # #    # #   #
#    #  #    # #    # # # #  ####  #    # ######  # #
#    #  #    # #    # #   #      # #    # #    #   #
######   ####   ####  #   #  ####  ###### #    #   #

 #####  #   #  #####  ######  ######
#       #   #    #    #    #  #
#  ###  #   #    #    #    #  #####
#    #  #   #    #    #    #  #
 #####   ###   #####  ######  ######
""".strip("\n")

SMALL_BANNER = r"""
+--------------------------------------------------------+
|  D O O M S D A Y   F I E L D   G U I D E               |
|  offline survival sheets . no network needed           |
+--------------------------------------------------------+
""".strip("\n")


class _EmptyGuide:
    """Used when the content directory or content.py is missing."""

    directory = None
    topics = {}

    def home_topics(self):
        return []

    def nested(self, _slug):
        return []

    def cards(self, _slug):
        return []

    def plain(self, _slug):
        return ""

    def present(self, _slug):
        return None

    index = ()


def _import_content():
    here = os.path.dirname(os.path.abspath(__file__))
    if here and here not in sys.path:
        sys.path.insert(0, here)
    try:
        import content as module
    except ImportError:
        return None
    return module


content = _import_content()


def _load_guide():
    if content is None:
        sys.stderr.write("field: content.py is not installed. Search still works.\n")
        return _EmptyGuide()
    try:
        return content.load_guide()
    except Exception as error:
        sys.stderr.write(f"field: could not load guide sheets ({error})\n")
        return _EmptyGuide()


GUIDE = _load_guide()
SHELTER = GUIDE.cards("shelter")
WATER = GUIDE.cards("water")
FIRE = GUIDE.cards("fire")
KNOTS_MAIN = GUIDE.cards("knots_main")
KNOTS_MORE = GUIDE.cards("knots_more")
_WHICH = GUIDE.cards("knot_which")
KNOT_WHICH = _WHICH[0][1] if _WHICH else ""
FOOD = GUIDE.plain("food")
SANITATION = GUIDE.plain("sanitation")
NAVIGATION = GUIDE.plain("navigation")
SIGNALS = GUIDE.plain("signals")
CLOTHING = GUIDE.plain("clothing")


def term_size():
    size = shutil.get_terminal_size((80, 24))
    return size.columns, size.lines


def compact():
    cols, rows = term_size()
    return cols < 80 or rows < 30


def is_console():
    return sys.stdout.isatty() and __import__("os").environ.get("TERM") == "linux"


def set_palette():
    """Pip-Boy green on the Linux console (OSC P n rrggbb). No-op elsewhere."""
    if is_console():
        sys.stdout.write("\033]P21AFF80\033]PA1AFF80\033]P80A5C2E")
        sys.stdout.flush()


def reset_palette():
    if is_console():
        sys.stdout.write("\033]R")
        sys.stdout.flush()


def paint(code, text):
    if sys.stdout.isatty():
        return f"\033[{code}m{text}\033[0m"
    return text


def green(text):
    return paint("32", text)


def bright(text):
    return paint("1;32", text)


def dim(text):
    return paint("2", text)


def pause(msg="Enter returns. q goes back. "):
    nxt = input(dim("-- " + msg + "-- ")).strip().lower()
    return nxt in ("q", "b", "quit")


def wrap_text(text):
    width = max(20, term_size()[0] - 2)
    out = []
    for paragraph in text.splitlines():
        if not paragraph.strip():
            out.append("")
            continue
        stripped = paragraph.strip()
        if paragraph.startswith("  ") or set(stripped) <= set(r"\/|_()XO-:. "):
            out.append(paragraph.rstrip())
        else:
            out.extend(textwrap.wrap(paragraph, width=width) or [""])
    return "\n".join(out)


def show_pages(text):
    lines = wrap_text(text).splitlines() or ["(empty)"]
    height = max(4, term_size()[1] - 3)
    index = 0
    while index < len(lines):
        print("\n".join(lines[index : index + height]))
        index += height
        if index >= len(lines):
            pause("end of this sheet. Enter returns. ")
            return
        nxt = input(dim(f"-- {index}/{len(lines)}  Enter next page. q back -- ")).strip().lower()
        if nxt in ("q", "b", "quit"):
            return


def show_sheet(title, body):
    print()
    print(bright(title))
    print(green("On this Pi. No network."))
    print()
    shown = content.console_body(body) if content is not None else body
    show_pages(shown)


class ArticleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.parts = []
        self.capture = False
        self.depth = 0
        self.found = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("script", "style", "noscript"):
            self.skip += 1
            return
        if self.skip:
            return
        if not self.found and attrs.get("id") == "mw-content-text":
            self.found = True
            self.capture = True
            self.depth = 1
            return
        if self.capture and tag == "div":
            self.depth += 1
        if (not self.found) or self.capture:
            if tag in ("p", "h1", "h2", "h3", "h4", "li", "br", "tr", "div"):
                self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self.skip:
            self.skip -= 1
            return
        if self.capture and tag == "div":
            self.depth -= 1
            if self.depth <= 0:
                self.capture = False

    def handle_data(self, data):
        if self.skip:
            return
        if self.found and not self.capture:
            return
        text = " ".join(data.split())
        if text:
            self.parts.append(text + " ")


def fetch(url, timeout=60):
    request = urllib.request.Request(url, headers={"User-Agent": "field-terminal"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def page_length():
    rows = term_size()[1]
    return max(3, min(8, (rows - 5) // 2))


def search(query, book, start=0, timeout=60, page_size=None):
    length = page_length() if page_size is None else page_size
    params = {"pattern": query, "start": str(start), "pageLength": str(length)}
    if book:
        params["books.name"] = book
    html = fetch(HOST + "/search?" + urllib.parse.urlencode(params), timeout)
    found = re.search(r"of <b>(\d+)</b>", html)
    total = int(found.group(1)) if found else 0
    hits = []
    for href, title, cite in re.findall(
        r'<a href="(/content/[^"]+)">\s*([^<]+?)\s*</a>\s*<cite>(.*?)</cite>',
        html,
        flags=re.S,
    ):
        snippet = re.sub(r"<[^>]+>", "", cite)
        snippet = re.sub(r"\s+", " ", snippet).strip()
        hits.append((title.strip(), href, snippet))
    return total, hits


def article_text(href, timeout=60):
    parser = ArticleText()
    parser.feed(fetch(HOST + href, timeout))
    raw = "".join(parser.parts)
    lines = []
    stop = {"references", "see also", "external links", "further reading", "notes"}
    for block in raw.splitlines():
        words = " ".join(block.split())
        if not words:
            if lines and lines[-1] != "":
                lines.append("")
            continue
        if words.lower() in stop:
            break
        lines.append(words)
    return "\n".join(lines).strip() or "(No readable text in that entry.)"


def run_search(book):
    scope = (
        "the medical encyclopedia"
        if book == MED
        else "the travel guide"
        if book == VOY
        else "both archives on this Pi"
    )
    print(dim(f"Searching {scope}. This does not use the network."))
    query = input(green("look up> ")).strip()
    if not query or query.lower() in ("q", "b"):
        return
    start = 0
    while True:
        try:
            print(dim("searching..."))
            total, hits = search(query, book, start)
        except Exception as error:
            print(green(f"Library not reachable ({error})."))
            print(green("The numbered sheets in the menu still work."))
            pause()
            return
        if not hits:
            print(green("No entries."))
            pause()
            return
        print()
        print(bright(f"{total} entries. Showing {start + 1}-{start + len(hits)}."))
        for number, (title, _href, snippet) in enumerate(hits, start=1):
            print(green(f"{number}  {title}"))
            cols = term_size()[0]
            limit = max(10, cols - 4) if compact() else 200
            print(dim("   " + snippet[:limit]))
        if compact():
            print(dim("number=read  n=next  q=back"))
        else:
            print(dim("Type a number and Enter to read it. n then Enter for the next results. q back."))
        choice = input(green("read> ")).strip().lower()
        if choice in ("q", "b", ""):
            return
        if choice == "n" and start + len(hits) < total:
            start += len(hits)
            continue
        if choice.isdigit() and 1 <= int(choice) <= len(hits):
            title, href, _snippet = hits[int(choice) - 1]
            try:
                print(dim("opening..."))
                body = article_text(href)
            except Exception as error:
                print(green(f"Could not open that entry ({error})."))
                pause()
                continue
            print()
            print(bright(title))
            show_pages(body)
            continue
        print(green("Type a number, n, or q, then Enter."))


def _more_extras():
    return (
        ("places", "Places"),
        ("archives", "Search all archives"),
        ("cave", "Cave Mapper"),
    )


def _run_extra(kind):
    if kind == "places":
        open_places_note()
    elif kind == "archives":
        run_search("")
    elif kind == "cave":
        run_cavemap()
    elif kind == "medicine":
        print()
        print(bright("MEDICINE"))
        print(green("Offline medical encyclopedia on this Pi."))
        print(green("Look up a condition or a symptom: hypothermia, burn, bleeding,"))
        print(green("fracture, dehydration, diarrhea, wound, infection, frostbite."))
        print(green("This guide does not give drug doses."))
        run_search(MED)


def _offer_search(book):
    if book == MED:
        print(dim("s then Enter searches the medical archive. Enter alone returns."))
    elif book == VOY:
        print(dim("s then Enter searches the travel archive. Enter alone returns."))
    elif book == "":
        print(dim("s then Enter searches both archives. Enter alone returns."))
    else:
        print(dim("s then Enter searches the archive. Enter alone returns."))
    if input(green("field> ")).strip().lower() == "s":
        run_search(book)


def open_topic(topic):
    view = GUIDE.present(topic.slug)
    if view is None:
        print(green("That sheet is missing."))
        pause()
        return
    book = view["book"]
    if view["kind"] == "search":
        print()
        print(bright(topic.title.upper()))
        if topic.intro:
            for line in topic.intro.splitlines():
                print(green(line))
        run_search(book)
        return
    if view["kind"] == "sheet":
        show_sheet(topic.title.upper(), view["cards"][0][1])
        if book is not None:
            _offer_search(book)
        return
    while True:
        print()
        print(bright(topic.title.upper()))
        if topic.intro:
            for line in topic.intro.splitlines():
                print(green(line))
        print()
        entries = []
        for name, body in view["cards"]:
            entries.append(("card", name, body))
        for child in view["children"]:
            entries.append(("child", child.title, child))
        if topic.slug == "more":
            for kind, label in _more_extras():
                entries.append(("extra", label, kind))
        for number, entry in enumerate(entries, start=1):
            print(green(f"{number}  {entry[1]}"))
        if book is not None:
            print(green("s  Search the archive for more"))
        print(green("q  Back"))
        print(dim("Type the number, then Enter. Page Up and Page Down are not used."))
        choice = input(green("field> ")).strip().lower()
        if choice in ("q", "b", "quit", ""):
            return
        if choice == "s" and book is not None:
            run_search(book)
            continue
        if choice.isdigit() and 1 <= int(choice) <= len(entries):
            kind, label, payload = entries[int(choice) - 1]
            if kind == "card":
                show_sheet(label.upper(), payload)
            elif kind == "child":
                open_topic(payload)
            else:
                _run_extra(payload)
            continue
        print(green("Type a number from the list, then Enter."))


def home():
    print()
    if compact():
        print(bright(SMALL_BANNER))
        print(dim("Type a number, then Enter. q goes back."))
    else:
        print(bright(BANNER))
        print(green("DOOMSDAY GUIDE"))
        print(dim("On this Pi. Enter moves forward. q goes back. No Page Up or Page Down."))
        print()
    topics = GUIDE.home_topics()
    if not topics:
        print(green("Guide sheets were not found. Search on this Pi still works."))
        print(green("1  Medicine"))
        print(green("2  Search all archives"))
        print(green("q  Leave"))
        return
    for number, topic in enumerate(topics, start=1):
        print(green(f"{number}  {topic.title}"))
    print(green("q  Leave"))


def open_places_note():
    print()
    print(bright("PLACES"))
    print(green("Offline travel guide on this Pi."))
    print(green("Type a town, region, river, or country."))
    run_search(VOY)


def run_cavemap():
    """Launch Zerb's Cave Mapper if it is installed, then come back here."""
    import subprocess
    exe = shutil.which("cavemap")
    if not exe:
        print(green("Cave Mapper is not installed yet."))
        pause()
        return
    try:
        import os

        env = os.environ.copy()
        env["CAVEMAP_FROM_GUIDE"] = "1"
        subprocess.call([exe], env=env)
    except Exception as error:
        print(green(f"Cave Mapper could not start ({error})."))
        pause()


def boot_prompt():
    """Ask once at start-up whether to go straight into Cave Mapper."""
    if not shutil.which("cavemap"):
        return
    answer = input(bright("Start Cave Mapper? [y/n] ")).strip().lower()
    if answer in ("y", "yes"):
        run_cavemap()


def patched_main():
    """Open each sheet from the content files, in front-matter order."""
    boot_prompt()
    while True:
        topics = GUIDE.home_topics()
        home()
        choice = input(green("field> ")).strip().lower()
        if choice in ("q", "quit", "exit"):
            print(green("Guide closed. Type field to open it again."))
            return
        if not topics:
            if choice == "1":
                _run_extra("medicine")
                continue
            if choice == "2":
                _run_extra("archives")
                continue
            print(green("Type a number from the list, then Enter."))
            continue
        if choice.isdigit() and 1 <= int(choice) <= len(topics):
            open_topic(topics[int(choice) - 1])
            continue
        print(green("Type a number from the list, then Enter."))


if __name__ == "__main__":
    set_palette()
    try:
        patched_main()
    except (KeyboardInterrupt, EOFError):
        print()
        print(green("Guide closed. Type field to open it again."))
    finally:
        reset_palette()
