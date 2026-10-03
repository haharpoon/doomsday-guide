#!/usr/bin/env python3
"""Offline doomsday field guide for this Pi."""

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
    width = max(40, shutil.get_terminal_size((80, 24)).columns - 2)
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
    height = max(8, shutil.get_terminal_size((80, 24)).lines - 4)
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
    show_pages(body)


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


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "field-terminal"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8", errors="replace")


def search(query, book, start=0):
    params = {"pattern": query, "start": str(start), "pageLength": "8"}
    if book:
        params["books.name"] = book
    html = fetch(HOST + "/search?" + urllib.parse.urlencode(params))
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


def article_text(href):
    parser = ArticleText()
    parser.feed(fetch(HOST + href))
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
            print(dim("   " + snippet[:200]))
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


def submenu(title, intro, parts, book=None):
    while True:
        print()
        print(bright(title))
        if intro:
            print(green(intro))
        print()
        for number, (name, _body) in enumerate(parts, start=1):
            print(green(f"{number}  {name}"))
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
        if choice.isdigit() and 1 <= int(choice) <= len(parts):
            name, body = parts[int(choice) - 1]
            show_sheet(name.upper(), body)
            continue
        print(green("Type a number from the list, then Enter."))


SHELTER = [
    (
        "Choose a site",
        """
Look up before you look down. Dead limbs, loose rock, and slab snow fall on people who liked the flat spot underneath them.

Do not camp in a dry wash, a gully, or the bottom of a valley. Rain a long way upstream arrives as a wall of water. A bench a few body-lengths above the channel is safer than the sand in the channel.

Wind takes heat faster than cold air alone. Put rock, a bank, or thick brush on the windward side. Face the door and the low edge away from the wind.

In cold weather, take morning sun. In hot weather, take shade and any breeze that is not a sandblast.

Clear the ground you will lie on. A stick under your ribs will keep you awake, and awake costs heat. The earth under you is a heat sink. A bed of dry leaves, grass, or spruce tips as thick as your open hand matters more than a thin roof.

Stay back from the water's edge. You want the walk for drinking water to be short, and you want the flood line and the insects to stay over there.
""".strip(),
    ),
    (
        "Debris hut",
        """
This is the shelter to build when you have no tarp and the night will be cold. The room inside must be small. If you can sit up in it, it is too big to warm with your body.

1. Find a ridge pole longer than you are tall, strong enough to hold a wet pile of leaves. A wrist-thick pole is a start. Thicker is safer.

2. Lift one end to about hip height in the fork of a tree, or lash two sticks into a bipod and rest the ridge in the crotch. The other end of the ridge sits on the ground. You will lie along this slope, head at the high end.

3. Lay rib sticks down both sides, from the ridge to the ground. Space them about a hand apart. If leaves would fall between them, they are too far apart.

4. Lay fine twigs across the ribs so the leaves have something to sit on.

5. Pile dry leaves, ferns, grass, or bark on the ribs. The layer should be as thick as your arm is long, including over the ridge. If rain is likely, add more, and comb the outside so water sheds downhill.

6. Build the same thickness under your body. The ground will empty your heat faster than the air above you.

7. The door is only big enough to crawl through. Once you are inside, plug it with your pack or a bag stuffed with leaves.

8. A fire does not belong inside this hut. There is no chimney and the leaves will burn.

If the only leaves are wet, use them anyway. Wet insulation is poor, but wind on bare skin is worse. Keep a dry layer against you if you have one.
""".strip(),
    ),
    (
        "Lean-to",
        """
Use a lean-to when you have a fire and a clear, wind-safe place to put it. The roof is a windbreak. The fire is the heater. One does not work well without the other.

1. Set a ridge pole between two trees, about chest to head height. If you have one tree, run the ridge from the tree down to the ground and sleep with your head at the high end.

2. Lay ribs on the windward side only, sloping to the ground. Cover them with browse, bark, or a tarp. Shingle the cover so water runs down the outside, not into the bed.

3. The open side faces the fire. Lie a full body-length back from the flames. Sparks and a rolling log are the failure mode.

4. A low wall of green logs or sticks on the far side of the fire reflects heat onto you. Stack it so it cannot fall into the fire. Do not use stones from a stream bed in or next to the fire. Trapped water can burst them.

5. The bed is still mandatory. Bare ground under a good roof is still a cold night.

Keep the fire small. A fire you can step over is easier to sit close to than a bonfire you have to flee.
""".strip(),
    ),
    (
        "Tarp or sheet",
        """
A tarp is a roof, not a tent, until you close it. Pitch it so a gust cannot turn it into a sail. Tie the corners. Do not rely on the grommet alone if the cloth is old. Use a small stone in a fold, with the line around the neck of the fold, when a grommet is torn.

Lean-to: ridge line about chest height, windward edge staked to the ground, open side away from the wind. Fast to pitch. Cold, because one side is open.

A-frame: ridge lower, both long edges staked to the ground, a small opening at one end. Warmer. Pitch it so rain sheds off the sides and does not pool in the belly. If the belly holds water, lower the edges or raise the ridge.

Plow point: tie one corner to a tree at about head height. Stake the opposite corner downhill. Stake the remaining two corners out to the sides. Use this when the wind has one obvious direction. The nose points into the wind.

In every pitch, the line that takes the load should be adjustable. A taut-line hitch or a trucker's hitch lets you retighten after the cloth stretches. See Knots.

Get the cloth off your face. Condensation will wet a tarp that touches your mouth and nose all night.
""".strip(),
    ),
    (
        "Cold ground and wet clothes",
        """
Most of the heat you lose in a shelter goes into the ground and into wet cloth, not through a thin spot in the roof.

Do not lie on bare earth, rock, or a wet log. Pile dry plants, a pack, a spare layer, or boughs under your torso and hips. If the pile is only under your shoulders, your hips still pour heat downward.

Change out of wet clothes before you climb in if you have anything dry, including a dirty dry layer. Wet cotton against the skin is a cooling system. Hang the wet layer in the smoke only if you can do it without burning the shelter. Wring it first.

Eat and drink before sleep if you have safe water and food. Shivering is a fire that burns your reserves. A full belly keeps it going longer.

Vent a tight shelter a finger's width if your breath is soaking the inside. A soaked leaf pile stops insulating. A small vent and a dry plug for the door is the balance.

If you are already shivering hard, slurring, or fumbling the knots, stop improving the camp and get inside the best shelter you have. Look up hypothermia in Medicine once you are out of the wind.
""".strip(),
    ),
]

WATER = [
    (
        "Find it and carry it",
        """
Moving water that is clear, cold, and coming from upstream of camps and carcasses is a better place to start than a stagnant pool. It is still not safe to drink until you treat it.

Rain, snow, and dew are cleaner sources if you can catch them on a clean sheet or in a container. Do not eat snow for your water ration if you are already cold. Melt it first. Eating snow drops your temperature.

Morning dew can be wiped from grass with a cloth and wrung into a cup. It is slow. It is still water.

Carry water when you leave a known source. Drink before you start. A long walk between sources is how people get confused, and confusion is an early sign you will want to look up under dehydration in Medicine.

Do not drink seawater, urine, or blood. They make you more short of water, not less. Do not drink from a pool with a chemical sheen, a dead animal in it, or a smell of fuel.
""".strip(),
    ),
    (
        "Settle, filter, boil",
        """
If the water is cloudy, let it sit until the grit drops. Pour off the clear part. Pour it through a cloth, a shirt, or a bandanna to take out the rest of the silt. This step does not remove germs. It makes the next step work, and it keeps you from drinking mud.

Boil it. Bring it to a rolling boil, bubbles that do not stop when you stir, for one minute. If you are high in the mountains, boil for three minutes. Boiling is the method to trust when you can make fire.

A lid cuts the fuel you spend. Let it cool before you put it in a soft bottle you care about.

Store treated water covered. Do not dip a dirty cup into the clean pot. Pour.

If you have purification tablets or a filter you carried in, follow the instructions printed on that device. A clogged filter that you bypass is just a bottle.

When you cannot boil, and the day is sunny, use a clear plastic bottle. Fill it with the clearest water you have. Lay it on its side in full sun for at least six hours. If the sky is more than half cloud, leave it for two days. This is sunlight treatment, not boiling. Use boiling when you can.
""".strip(),
    ),
]

FIRE = [
    (
        "Site and putting it out",
        """
Clear a circle down to mineral soil, wider than the fire will be. Rake leaves and duff back until you see dirt. Roots and peat burn underground and come up later as a wildfire.

Keep the fire downwind of the shelter, a body-length away, and out from under branches. A spark in a debris hut is the end of the hut.

Build small. A fire that fits inside a ring the size of a dinner plate will boil water and dry socks. A bonfire spends your wood and drives you backward.

Before you sleep or leave: drown it, stir the ashes with a stick, drown it again, and feel for heat with the back of your hand held close, not pressed into the coals. Cold ashes are dead. Warm ashes are a fire you have not finished putting out. If you do not have water, stir in dirt and stay until there is no glow and no warmth.
""".strip(),
    ),
    (
        "Tinder, kindling, wood",
        """
Gather all of it before you light anything. A flame with nothing ready to feed it is a wasted match.

Tinder takes the spark or the match. It must be fine and dry: dry grass, the inner bark of dead cedar or birch, fluff from a cattail, shavings you carve so thin they curl, or a nest the size of a fist made of threads. If it does not light from a match held at the edge, it is too coarse or too damp. Split dead wood and take the dry wood from the inside.

Kindling is pencil-thick to thumb-thick, dry, and a pile as big as your hat before you start. Dead twigs still on the tree, under a branch, are drier than twigs on the ground.

Fuel is wrist-thick and larger. Dead standing wood is better than a log lying in the moss. If it bends without snapping, it is too green or too wet for the first fire. Use it later, after you have coals.

Stack the wood where sparks will not land in it, close enough that you can feed the fire without getting up and hunting in the dark.
""".strip(),
    ),
    (
        "Lighting and feeding",
        """
Match or lighter: shield the flame with your body. Touch it to the downwind edge of the tinder so the flame burns into the nest, not away from it. Nurse it. Do not drop a log on a new flame.

Spark from a ferro rod: scrape sparks down into the tinder nest, then lift the nest and blow gently at the base of the glow until it flames. Blowing hard scatters it.

Lens: a round lens from a headlamp, binoculars, or glasses that are magnifying, not just flat. Aim a bright dot at dark tinder. Hold still until it smokes, then blow it the way you would a spark.

Once the tinder is a flame, add kindling in a small cone or a lean-to of sticks over the flame, with a gap for air on the windward side. Fire needs air. A solid pile smothers it. When the kindling is burning on its own, add fuel one stick at a time.

If everything outside is wet, look for pitch wood, the fat-rich wood in a dead conifer stump, and split dry centers out of dead branches. Feather-stick the split face: cut shavings and leave them attached so one stick becomes its own tinder.

Keep a small store of dry tinder in a pocket for the morning. The night's dew will wet what you leave in the open.
""".strip(),
    ),
]

KNOT_WHICH = """
Use the knot that matches the job. A pretty knot in the wrong job slips or jams.

Join two ropes of similar size, and you may need to untie them: sheet bend.
Join two ropes you will not need to untie, or close a loop of cord: double fisherman's knot.
Join flat webbing or a strap: water knot. Do not use a water knot on round rope.

A loop at the end of a rope that must not slip: figure-eight loop. A bowline is faster to untie after a load and is fine for a haul line or a ridge that you can watch. Do not trust a bowline as the only thing holding a person if the loop can flap loose. A bowline that is not loaded can shake undone. Leave a tail a hand long, and stop the tail if the knot will shake.

Tie onto a post, ring, or tree when the load matters: round turn and two half hitches.
A quick tie you will watch: clove hitch, then a half hitch if it starts to roll.
Pull along a pole, or grab a tight rope with a smaller cord: rolling hitch.

Tighten a guy line you will adjust: taut-line hitch.
Pull a ridge line very tight: trucker's hitch.
A loop in the middle of a rope, so you can still pull either end: alpine butterfly.

Bind a bundle or the two ends of the same cloth: square knot. Do not use a square knot to join two climbing ropes. It can capsize and spill.

Every knot below is unfinished until you dress it. Remove slack and twists until it looks like the description, then pull it hard with the load it will actually take. A tail shorter than your palm is a knot asking to untie itself.
""".strip()

KNOTS_MAIN = [
    ("Which knot", KNOT_WHICH),
    (
        "Square knot",
        """
Use: bind a bundle, tie the two ends of the same bandage or cord, close a sack.
Do not use: to join two different ropes, or any line that will hold a person. It spills if the ropes differ or if one end is pulled sideways.

Names: each loose end is a working end. The rest of that rope is its standing part.

1. Cross the right working end over the left. Tuck it under. Pull snug. You have one half-knot.

2. Cross the end that is now on the left over the end that is now on the right. Tuck it under. Pull snug.

3. Look at it. Each working end should leave the knot on the same side as its own standing part. The knot is two loops sitting against each other, flat.

        standing     standing
            \\         //
             \\_______//
             /       \\
            /    X    \\
            \\_______/
            /         \\
        working       working

4. If the ends come out sideways, at right angles to their standing parts, you tied a granny. It will slip. Untie it and do step 2 again, the other way over.

5. Pull both standing parts and both ends to set it. Leave ends at least a hand long.
""".strip(),
    ),
    (
        "Sheet bend",
        """
Use: join two ropes, including ropes of different thickness. The thicker rope makes the bight.
Do not use: as a loop around a person. For slippery line, or a large difference in size, use the double sheet bend in step 6.

1. Fold the thicker rope back on itself so you have a bight, a narrow U. Hold the two legs of the U together.

2. Pass the thinner rope up through that U, from underneath.

3. Take the thinner rope around behind both legs of the U.

4. Tuck the thinner rope under itself, right where it first came up through the U. Do not tuck it under both legs. Tuck it under its own standing part only.

5. Pull the standing part of each rope. The thin rope's tail and the thick rope's tail should lie on the same side. If they lie on opposite sides, you tied it backward. It is weaker. Retie it.

        thick bight
          __|__
         /     \\
        |   ____|____  thin rope comes up,
         \\  \\       then around both legs,
          \\__\\___   then under itself

6. Double sheet bend: at step 3, wrap the thin rope around the bight twice, then tuck under itself as in step 4. Use this for wet line, smooth line, or a thin cord on a thick rope.

7. Set it with a hard pull. Leave a hand of tail on both ropes.
""".strip(),
    ),
    (
        "Bowline",
        """
Use: a fixed loop at the end of a rope. Throwing a line over a branch and making a loop you can haul on. A loop around a pack.
Limit: if the loop flaps with no load, a bowline can work loose. Leave a long tail. For a loop you cannot afford to have slip, use the figure-eight loop.

The story that matches the steps: the standing part is the tree. A small loop in it is the hole. The working end is the rabbit.

1. Form a small loop in the standing part, a short distance from the end. The working end comes up out of this hole. Lay the loop so the working end is under the standing part as it enters the hole. If you make this loop backward you will finish with a slip knot.

2. Pass the working end up through the hole. The rabbit comes out of the hole.

3. Take the working end around behind the standing part. The rabbit goes around the tree.

4. Pass the working end back down through the hole, beside itself. The rabbit goes back into the hole.

5. Pull the standing part with one hand and the working end with the other. The small hole should close up into the knot. The big loop is the useful one. It should not shrink when you pull the standing part.

        tree (standing part)
              |
          ____|____
         /    |    \\
        |     O     |   O is the hole that closed
         \\____|____/
              |
           [ loop you use ]

6. Test it. Pull the loop and the standing part hard. Then shake the loop loose on purpose. If the knot capsizes into a simple sliding noose, cut it off and retie it. The working end must finish inside the loop, next to the leg it went in on.

Tail: at least a hand long. Longer if the rope is stiff.
""".strip(),
    ),
    (
        "Figure-eight loop",
        """
Use: a loop at the end of a rope that must not slip and must be easy to check by eye. A ridge line you will load. A haul loop. Prefer this over a bowline when you cannot stand there and watch the knot.

You are tying a figure-eight, passing the end around the anchor, then tracing the first knot backward.

1. Leave a long working end, several feet if the rope is thick. You need enough to trace the whole knot and still have a tail.

2. Tie a loose figure-eight in the standing part:
   Make a loop. Pass the working end around behind the standing part and back through the loop. Stop. You should see a figure eight. Do not pull it tight.

3. Pass that working end around the tree, post, or whatever the loop is for. If the loop is only a handhold and has no anchor, skip this and use the rewoven form on a bight if you already know it. The follow-through below is the one to learn.

4. Trace backward. Feed the working end into the figure-eight right beside the standing part, and follow the rope that is already there, in the opposite direction, all the way through. Where the first rope goes over, the working end goes over. Where it goes under, the working end goes under. Two strands, side by side, the whole way around.

5. When you finish, the working end exits beside the standing part. Look at every crossing. If one strand skips a bend, you left the path. Untie the trace and follow it again. Do not "fix" a missed crossing by adding a half hitch.

6. Dress it. Work the slack out from the anchor toward the tail until the two strands sit parallel and the knot is a compact stack of turns. Pull it hard.

7. The tail should be at least a hand long. This knot is hard to untie after a heavy load. That is the point.
""".strip(),
    ),
    (
        "Clove hitch",
        """
Use: a fast hitch to a post, carabiner, or branch when you will see it and the load is steady. Hanging a light line. Starting a lashing.
Do not use: as the only hitch for a load that will jerk, or on a smooth pole. It rolls. Add a half hitch, or use a round turn and two half hitches instead.

1. Pass the working end around the post.

2. Cross it over its own standing part, making an X in front of the post.

3. Pass it around the post a second time, below the first wrap if the pull is upward, above it if the pull is downward. The second wrap goes on the side the load will pull toward.

4. Tuck the working end under the cross of the X.

5. Pull both the standing part and the working end. The cross sits between the two wraps, clamped.

        ||  post
       _||_
      | || |
       \\||/     the cross is under the working end
        ||

6. If you can roll the hitch around the post with your thumb, it is not safe for that load. Add a half hitch around the standing part, or retie as a round turn and two half hitches.
""".strip(),
    ),
    (
        "Round turn and two half hitches",
        """
Use: tie a rope to a post, ring, tree, or pack frame when the load actually matters. The round turn does the holding. The hitches only keep the turn from unwinding.

1. Pass the working end around the anchor. Then pass it around a second time. Two full turns. The standing part now has friction on the anchor before you tie anything.

2. Bring the working end in front of the standing part and tuck it around the standing part and back through, making a half hitch snug against the turns.

3. Make a second half hitch, further out on the standing part, and slide it down against the first.

4. Pull the standing part hard, then pull the working end. The two hitches should sit tight against the round turn, not wander up the rope.

You should be able to let go of the working end after the round turn, before the hitches, and the load should already be mostly held. If it is not, add nothing magical. Take another turn around the anchor, then put the two half hitches on.

Tail: a hand long. This knot is easier to untie than a figure-eight after a heavy pull.
""".strip(),
    ),
    (
        "Taut-line hitch",
        """
Use: a guy line you need to tighten and later loosen. Tent corners. A tarp edge. A clothesline that sags.

The hitch slides when you push it and holds when the guy line pulls it.

1. Pass the working end around the stake or tree and back toward the standing part, so the rope forms the loop that will be your guy line.

2. Wrap the working end twice around the standing part, inside that loop. Wrap toward the anchor, coil beside coil, not on top of each other in a tangle.

3. Now outside the loop, tie one half hitch around the standing part, on the side away from the anchor.

4. Dress the two inside wraps so they sit neat. Slide the whole hitch toward the anchor to tighten the guy. Slide it away to loosen.

5. Test it. Pull the guy as the wind will pull it. The hitch should jam and hold. If it slips under that pull, you wrapped away from the load instead of toward it. Untie and wrap the other direction.

Retie it if the rope dries or stretches a lot. A taut-line on stiff cold rope can creep. Check guy lines before sleep.
""".strip(),
    ),
]

KNOTS_MORE = [
    (
        "Trucker's hitch",
        """
Use: pull a ridge line, a lashing, or a tarp much tighter than your arms alone can pull. You get a rough 2-to-1 pull.

1. A short distance from the far anchor, put a small fixed loop in the standing part. Use an alpine butterfly, or a figure-eight on a bight if you have slack to fold the rope. This loop is the pulley. It must not slip.

2. Pass the working end around the anchor you are pulling toward, and back to that loop.

3. Feed the working end through the loop.

4. Pull the working end back toward the anchor, away from the loop. You are pulling against the loop the way you would pull a bowstring. The section between anchor and loop shortens hard.

5. While you hold that tension, pinch the rope where it leaves the loop. Tie two half hitches around the standing part, close to the loop, without letting the tension go.

6. Set the half hitches. Ease your pinch. The load should stay.

Do not stand inside the V of rope while you haul. If the anchor or the loop fails, the line comes through that space. Haul from the side.

To release: untie the two half hitches while keeping your weight out of the V, then let the end slip back through the loop.
""".strip(),
    ),
    (
        "Alpine butterfly",
        """
Use: a loop in the middle of a rope when you need both ends free. A middle attachment on a ridge line. An anchor point that can be pulled in any of the three directions.

1. Make a loop in the bight. You are not using the ends.

2. Twist that loop once, so the ropes cross and you have a smaller hole above a larger hole.

3. Twist a second time in the same direction. You want a figure-eight shape, with a clear hole in the upper part.

4. Fold the top bend down and push it through the lower hole.

5. Pull that bend through and dress the knot. The useful loop stands out of a compact barrel of rope. The two standing parts leave opposite sides.

Pull each standing part, then pull the loop. It should not collapse. If it collapses into a slip knot, you only twisted once. Untie and put the second twist in.

This loop is strong enough to be the pulley loop in a trucker's hitch.
""".strip(),
    ),
    (
        "Rolling hitch",
        """
Use: pull along a spar, or attach a small cord to a larger rope that is already tight, when the pull is almost parallel to that rope or spar.

1. Lay the working end along the spar, pointing against the direction you will pull.

2. Wrap it around the spar, crossing over itself, and wrap a second turn on the side toward the pull. The two turns sit side by side. The pull will jam them together.

3. Take the working end past those turns and tie a half hitch around the spar on the far side, away from the direction of pull.

4. Pull the standing part. The hitch should grip and not walk along the spar. Push the wraps the other way and it should slide so you can reset it.

If it slips toward the load, the second turn is on the wrong side. The extra turn belongs on the side the pull comes from.
""".strip(),
    ),
    (
        "Timber hitch",
        """
Use: drag a log, start a lashing around a pole, or tow a bundle when the pull will stay steady.

1. Pass the working end around the log.

2. Bring it across the standing part and around the standing part once.

3. Tuck the working end back through the space between that wrap and the log, then twist the working end around itself three or four more times, following the wrap, so the twists lie against the log. You are not tying half hitches out on the standing part. The twists are on the working end, dogged around itself.

4. Pull the standing part. The twists should jam between the standing part and the log. More pull, more jam.

5. If the log needs to be steered, add one half hitch around the log closer to the front, then lead the standing part from that hitch.

A timber hitch with no load will fall off. That is normal. Put the load on it before you trust it, and look at it when the pull changes direction.
""".strip(),
    ),
    (
        "Double fisherman's knot",
        """
Use: join two ropes of similar size when the join must not slip and you can accept a knot that is miserable to untie. Also the knot that closes a prusik loop.

1. Overlap the two ends, pointing opposite directions, overlap about two hands long.

2. With the first working end, wrap twice around both ropes, back toward its own standing part. Pass the end through those two wraps. You have a double overhand knot strangling the other rope. Pull it snug, not yet crushed.

3. With the other working end, do the same in the opposite direction. Two wraps around both ropes, end through the wraps.

4. Pull the two standing parts. The two barrels slide together and should seat against each other, wraps matching, tails sticking out opposite ends.

5. Tails at least a hand long. If a barrel has only one wrap, you tied a single fisherman's. Wet or slick cord will creep. Retie with two wraps.

Do not use this where you must untie in a hurry. Cut it if you have to.
""".strip(),
    ),
    (
        "Water knot",
        """
Use: join two pieces of flat webbing or a seatbelt strap.
Do not use: on round rope. Use a sheet bend or a double fisherman's knot for rope.

1. Tie a loose overhand knot in one end of the webbing. Do not tighten it. An overhand is the simple knot you tie in one strand before it becomes a granny: end through a loop in itself.

2. Take the other end and feed it into that overhand so it follows the first strap backward, in contact with it the whole way. It enters where the first tail exits, follows every bend, and exits beside the first standing part.

3. You now have two straps tracing one overhand, tails leaving opposite sides. Pull all four directions: both standing parts and both tails. The knot should lie flat, not bunched on one edge.

4. Tails at least three fingers long. Webbing is slippery when wet. Short tails pull through.

5. Look at both faces. If one strap skipped a bend, the knot is only an overhand with a strap lying next to it. It will pull out. Retie it.
""".strip(),
    ),
    (
        "Prusik",
        """
Use: a cord that grips a thicker rope when loaded and slides when you hold the load off it. Hang a pack from a ridge line. Inch a load along a tight line. The cord must be thinner than the rope it grips, or it will not grab.

1. Join the cord into a loop with a double fisherman's knot. The loop wants to be big enough to wrap the main rope and still give you a tail to hold, typically an arm's length of cord before you join it. Test and adjust.

2. Pass the loop around the main rope and back through itself. That is one wrap. Dress it.

3. Pass the loop around the main rope and through itself again. Two wraps. On icy, muddy, or slick rope, add a third wrap.

4. The wraps must sit next to each other, neat, not crossed over each other in a pile. A crossed prusik slips.

5. Pull the loop. The wraps should clamp and hold. Take the load off and push the barrel of wraps with your hand. It should slide.

6. Do not shock-load it. Sit your weight on slowly the first time. If it slips, add a wrap or use a thinner cord. If the cord is as thick as the rope, no number of wraps will save it.

This hitch holds a load on a rope. It is not a substitute for a belay you do not know how to build. Use it for camp loads you can afford to have drop a short distance while you test it.
""".strip(),
    ),
]

FOOD = """
Cook meat, fish, and shellfish all the way through. If you would not eat the center as it sits, cook it longer. Boil dried meat if you are not sure of it.

Boil water and milk you did not treat. Soup is a way to get the water and the food in one pot.

Throw food out when the can bulges, hisses, or spurts, when the lid is loose, or when the food smells sour, tastes fizzy, or foams. Heating bad canned food does not make it safe. Do not taste it to decide.

A hard frost does not make spoiled meat safe. Drying does not make already rotten meat safe.

To dry food you trust: slice it thin, hang it in sun and moving air, off the ground and under cloth so insects cannot lay in it. Bring it in at night. It is ready when a piece bends and does not weep moisture. Keep it covered and dry. If it smells rotten rather than smoky or plain, discard it.

Salt, sugar, oil, and hard cheese keep longer than fresh meat. Eat the fresh food first.

Do not eat wild mushrooms. Do not eat a plant you cannot already name with certainty. "Looks like" is how people poison themselves when they are hungry. Hunger is not a reason to run the experiment. If a plant is in the medical archive or the travel guide under a name you are sure of, read that entry before you eat it.

Store food and garbage away from where you sleep, hung if animals are around. A bear or a dog in the shelter at night is a worse problem than a cold walk to the hang.
""".strip()

SANITATION = """
Wash your hands with soap and treated or boiled water before you cook, before you eat, and after the latrine. Rinsing in the creek you drink from moves the problem into the creek. Carry wash water away from the source. Dig a small hole for wash water, or fling it wide on the ground well away from camp and water.

Put the latrine at least 30 metres from water, and downhill from camp so rain does not run from it through your kitchen. Dig a hole. Bury waste. Do not latrine upstream of the place you draw water, even if 30 metres seems far. Upstream is the wrong direction at any distance you are likely to walk.

Keep drinking water in a closed container. Do not scoop from the clean pot with a cup you just used for something else. Pour.

Boots, cups, and hands that handle waste do not handle food until they are washed.

Clean a fresh wound with the cleanest water you have. Pick out dirt you can see. Then look the injury up in Medicine: wound, bleeding, burn, or whatever the true word is. This sheet does not give drug doses and it does not tell you how to close a wound.

Diarrhea wastes water. Look up dehydration and diarrhea in Medicine, keep sipping treated water, and be stricter about the latrine and the handwashing than you were the day before. The usual cause in a camp is hands and water, not bad luck.
""".strip()

NAVIGATION = """
The sun rises in the east and sets in the west. At midday in the northern hemisphere it stands to the south of you. In the southern hemisphere it stands to the north of you. You do not need a precise fix to stop walking in circles. Pick a far object that lies on your heading and walk to it, then pick another.

At night in the northern hemisphere, find the Big Dipper. The two stars at the outer edge of the cup point to the North Star. It sits over the end of the Little Dipper's handle and it does not travel around the sky the way the other stars do. Face it and you are facing north.

Shadow stick, when you have fifteen quiet minutes and sun:
1. Push a straight stick into flat ground.
2. Mark the tip of its shadow with a pebble. That mark is west, roughly, in the middle of the day.
3. Wait until the shadow has moved a clear distance. Mark the tip again.
4. The line from the first mark to the second runs west to east. The first mark is west. Put your left foot on the first mark and your right foot on the second. You are facing north in the northern hemisphere.

This is a heading, not a map. Repeat it if you are unsure. Do not trust one reading taken when a cloud is about to cover the sun and the shadow is fuzzy.

Streams run downhill. People, roads, and the sea are more likely downstream than upstream. Do not use the streambed as your trail if the sky upstream is storming, or if the bed is full of tumbled logs and fresh gravel. That is a flood path. Walk the bench beside it.

If you are lost, sit down. Drink, eat a little if you have it, and build the shelter while you still have light and heat. Walking until dark to "find the trail" is how a short error becomes a night in the open. A search looks for the last place you were supposed to be. Staying put is a plan. Leaving a note of your direction, if you must move, is part of that plan.

Look up the place name in Places if you know a town, a park, a river, or a country. The travel guide is on this Pi.
""".strip()

SIGNALING = """
Three of anything is the standard call for help. Three whistle blasts, three shouts, three smokes, three rock piles, three flashes. Pause, then repeat. A single shout is a person talking. Three is a person asking.

A whistle carries farther than your voice and costs less breath. One short blast can mean "here" to your own group if you agreed that before you split up. Do not waste the voice on a long yell into wind.

A mirror or any shiny flat thing: catch the sun and sweep the horizon. When you see a flash land on a vehicle or a hillside, hold that aim and flash in threes. Do not flash an aircraft in a way that blinds the person flying it at close range. A short flash is a signal. A held beam into a cockpit is a hazard.

Smoke: a small hot fire, then green leaves or damp grass tossed on for a white puff. Three puffs if you can manage the timing. Build this only where the fire cannot spread, on the mineral soil you already cleared. Smoke on a windy dry day in brush is how you start a wildfire. If you cannot keep the fire, do not light it.

Ground signals, in an open place seen from above: straight lines and right angles. Nature does not make a large X, a V, or the letters HELP, out of rocks or stamped snow. Make them large, several body-lengths, and make the contrast strong. Rocks on snow. Dark logs on pale ground. Stamp the snow so the shadow of the trench shows at a low sun.

At night a fire is the signal. Three fires in a triangle if you have the fuel and the clear ground. One fire you actually keep lit is better than three you abandon.

Tell the group, before anyone walks away, where you will wait and what the signal is. A plan you invent after you are separated is a wish.
""".strip()

CLOTHING = """
You dress for sweat as much as for cold. Sweat wets the layer next to your skin. When you stop, that wet layer cools you. Take a layer off before you sweat on a climb. Put it back on the moment you stop, before you feel cold. Waiting until you shiver means you are already behind.

Cotton holds water and spends your heat drying it. Wool, fleece, and synthetic pile still insulate when they are damp. If you have a choice of what to wear against the skin on a wet day, do not choose cotton.

Layers, from the skin out: a dry base, an insulating layer, a shell that stops wind and rain. The shell also stops sweat from leaving if you work hard in it. Open it while you move. Close it when you stop.

Wet feet rot and they chill you. Dry socks in a dry pocket are a real piece of gear. Change into them when you get into the shelter. Put the wet pair against your body or hang them in dry air. Do not lay them on the ground.

In heat, cover skin against the sun, drink treated water before you are thirsty, and work in the cooler part of the day. A headache, stopping sweating, and confusion are reasons to stop, get into shade, and look up heat illness in Medicine. Do not wait to "finish the mile."

In cold, cover your head and neck. Loose clothing traps more air than tight clothing. A belt cinched over a soaked shirt makes a cold ring. Mittens beat gloves if you are not tying knots at that moment. When you are tying knots, put the mittens back on the moment you finish.

Look up hypothermia, frostbite, trench foot, dehydration, and heat stroke in Medicine for the signs. The encyclopedia is the medical text. This page is only the clothing.
""".strip()


def home():
    print()
    print(bright(BANNER))
    print(green("DOOMSDAY GUIDE"))
    print(dim("On this Pi. Enter moves forward. q goes back. No Page Up or Page Down."))
    print()
    print(green("1  Shelter"))
    print(green("2  Medicine"))
    print(green("3  Water"))
    print(green("4  Fire"))
    print(green("5  Knots"))
    print(green("6  Food"))
    print(green("7  Sanitation"))
    print(green("8  Navigation"))
    print(green("9  More"))
    print(green("q  Leave"))


def more_menu():
    submenu(
        "MORE",
        "Signaling, clothing, places, and the full search.",
        [
            ("Signaling", SIGNALING),
            ("Clothing and weather", CLOTHING),
            ("Places, open the travel guide", "Type s on the next screen and enter a town, region, river, or country."),
        ],
    )


def open_places_note():
    print()
    print(bright("PLACES"))
    print(green("Offline travel guide on this Pi."))
    print(green("Type a town, region, river, or country."))
    run_search(VOY)


def main():
    while True:
        home()
        choice = input(green("field> ")).strip().lower()
        if choice in ("q", "quit", "exit"):
            print(green("Guide closed. Type field to open it again."))
            return
        if choice == "1":
            submenu("SHELTER", "Build small, get off the ground, stay out of the wind.", SHELTER)
        elif choice == "2":
            print()
            print(bright("MEDICINE"))
            print(green("Offline medical encyclopedia on this Pi."))
            print(green("Look up a condition or a symptom: hypothermia, burn, bleeding,"))
            print(green("fracture, dehydration, diarrhea, wound, infection, frostbite."))
            print(green("This guide does not give drug doses."))
            run_search(MED)
        elif choice == "3":
            submenu("WATER", "Settle, then boil when you can.", WATER, MED)
        elif choice == "4":
            submenu("FIRE", "Small fire, bare soil, cold ashes before you leave.", FIRE)
        elif choice == "5":
            submenu("KNOTS", "Dress every knot. Leave a tail a hand long.", KNOTS_MAIN + [("More knots", None)])
        elif choice == "6":
            show_sheet("FOOD", FOOD)
            print(dim("s searches the medical archive. Enter returns."))
            if input(green("field> ")).strip().lower() == "s":
                run_search(MED)
        elif choice == "7":
            show_sheet("SANITATION", SANITATION)
            print(dim("s searches the medical archive. Enter returns."))
            if input(green("field> ")).strip().lower() == "s":
                run_search(MED)
        elif choice == "8":
            show_sheet("NAVIGATION", NAVIGATION)
        elif choice == "9":
            while True:
                print()
                print(bright("MORE"))
                print(green("1  Signaling"))
                print(green("2  Clothing and weather"))
                print(green("3  Places"))
                print(green("4  Search all archives"))
                print(green("q  Back"))
                sub = input(green("field> ")).strip().lower()
                if sub in ("q", "b", ""):
                    break
                if sub == "1":
                    show_sheet("SIGNALING", SIGNALING)
                elif sub == "2":
                    show_sheet("CLOTHING AND WEATHER", CLOTHING)
                elif sub == "3":
                    open_places_note()
                elif sub == "4":
                    run_search("")
                else:
                    print(green("Type a number from the list, then Enter."))
        else:
            print(green("Type a number from the list, then Enter."))


def patched_main():
    """Knots item 9 opens the second knot list instead of a blank sheet."""
    while True:
        home()
        choice = input(green("field> ")).strip().lower()
        if choice in ("q", "quit", "exit"):
            print(green("Guide closed. Type field to open it again."))
            return
        if choice == "1":
            submenu("SHELTER", "Build small, get off the ground, stay out of the wind.", SHELTER)
        elif choice == "2":
            print()
            print(bright("MEDICINE"))
            print(green("Offline medical encyclopedia on this Pi."))
            print(green("Look up a condition or a symptom: hypothermia, burn, bleeding,"))
            print(green("fracture, dehydration, diarrhea, wound, infection, frostbite."))
            print(green("This guide does not give drug doses."))
            run_search(MED)
        elif choice == "3":
            submenu("WATER", "Settle, then boil when you can.", WATER, MED)
        elif choice == "4":
            submenu("FIRE", "Small fire, bare soil, cold ashes before you leave.", FIRE)
        elif choice == "5":
            while True:
                print()
                print(bright("KNOTS"))
                print(green("Dress every knot. Leave a tail a hand long."))
                print()
                for number, (name, _body) in enumerate(KNOTS_MAIN, start=1):
                    print(green(f"{number}  {name}"))
                print(green("9  More knots"))
                print(green("q  Back"))
                print(dim("Type the number, then Enter."))
                picked = input(green("field> ")).strip().lower()
                if picked in ("q", "b", ""):
                    break
                if picked == "9":
                    submenu("MORE KNOTS", "Joins, mid-rope loops, and hitches that grip.", KNOTS_MORE)
                    continue
                if picked.isdigit() and 1 <= int(picked) <= len(KNOTS_MAIN):
                    name, body = KNOTS_MAIN[int(picked) - 1]
                    show_sheet(name.upper(), body)
                    continue
                print(green("Type a number from the list, then Enter."))
        elif choice == "6":
            show_sheet("FOOD", FOOD)
            print(dim("s then Enter searches the medical archive. Enter alone returns."))
            if input(green("field> ")).strip().lower() == "s":
                run_search(MED)
        elif choice == "7":
            show_sheet("SANITATION", SANITATION)
            print(dim("s then Enter searches the medical archive. Enter alone returns."))
            if input(green("field> ")).strip().lower() == "s":
                run_search(MED)
        elif choice == "8":
            show_sheet("NAVIGATION", NAVIGATION)
        elif choice == "9":
            while True:
                print()
                print(bright("MORE"))
                print(green("1  Signaling"))
                print(green("2  Clothing and weather"))
                print(green("3  Places"))
                print(green("4  Search all archives"))
                print(green("q  Back"))
                sub = input(green("field> ")).strip().lower()
                if sub in ("q", "b", ""):
                    break
                if sub == "1":
                    show_sheet("SIGNALING", SIGNALING)
                elif sub == "2":
                    show_sheet("CLOTHING AND WEATHER", CLOTHING)
                elif sub == "3":
                    open_places_note()
                elif sub == "4":
                    run_search("")
                else:
                    print(green("Type a number from the list, then Enter."))
        else:
            print(green("Type a number from the list, then Enter."))


if __name__ == "__main__":
    try:
        patched_main()
    except KeyboardInterrupt:
        print()
        print(green("Guide closed. Type field to open it again."))
