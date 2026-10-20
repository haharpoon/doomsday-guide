"""Diagrams for the Childbirth, Mental health and Growing food cards. Run from the repo root.

480x284 PNG, bold #1AFF80 lines on black, like the other guide pictures.
Text is kept large because the touch guide shows pictures scaled down on a card.
"""
import math
from PIL import Image, ImageDraw, ImageFont

G = (0x1A, 0xFF, 0x80)
K = (0, 0, 0)
W, H = 480, 284
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def f(size):
    return ImageFont.truetype(FONT, size)


def new(title):
    im = Image.new("RGB", (W, H), K)
    d = ImageDraw.Draw(im)
    d.text((8, 4), title, fill=G, font=f(19))
    return im, d


def t(d, xy, s, size=15, anchor="la"):
    d.text(xy, s, fill=G, font=f(size), anchor=anchor)


def L(d, pts, w=4):
    d.line(pts, fill=G, width=w, joint="curve")


def C(d, c, r, w=4, fill=None):
    d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], outline=G, width=w, fill=fill)


def E(d, box, w=4, fill=None):
    d.ellipse(box, outline=G, width=w, fill=fill)


def dot(d, c, r=4):
    d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=G)


def arrow(d, a, b, w=3, s=12):
    L(d, [a, b], w)
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    d.polygon([b, (b[0] - s * math.cos(ang - 0.45), b[1] - s * math.sin(ang - 0.45)),
               (b[0] - s * math.cos(ang + 0.45), b[1] - s * math.sin(ang + 0.45))], fill=G)


def dashed(d, a, b, w=2, on=8, off=6):
    length = math.dist(a, b)
    ux, uy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
    pos = 0.0
    while pos < length:
        end = min(pos + on, length)
        L(d, [(a[0] + ux * pos, a[1] + uy * pos), (a[0] + ux * end, a[1] + uy * end)], w)
        pos += on + off


def divider(d, x, top=34, bottom=276):
    L(d, [(x, top), (x, bottom)], 2)


def save(im, name):
    im.save(f"content/img/{name}.png")


def box(d, xy, label, size=15, w=3):
    d.rounded_rectangle(xy, 8, outline=G, width=w)
    lines = label.split("\n")
    cx, cy = (xy[0] + xy[2]) / 2, (xy[1] + xy[3]) / 2
    for k, s in enumerate(lines):
        t(d, (cx, cy + (k - (len(lines) - 1) / 2) * (size + 3)), s, size, "mm")


def lines(d, x, y, rows, size=15, gap=5, anchor="la"):
    for k, s in enumerate(rows):
        t(d, (x, y + k * (size + gap)), s, size, anchor)


def circle_arrow(d, c, r, start=200, end=520, w=4):
    """Open circular arrow, clockwise from start to end degrees."""
    d.arc([c[0] - r, c[1] - r, c[0] + r, c[1] + r], start, end, fill=G, width=w)
    a = math.radians(end)
    tip = (c[0] + r * math.cos(a), c[1] + r * math.sin(a))
    tang = a + math.pi / 2
    s = 12
    d.polygon([(tip[0] + s * math.cos(tang), tip[1] + s * math.sin(tang)),
               (tip[0] + s * 0.6 * math.cos(a), tip[1] + s * 0.6 * math.sin(a)),
               (tip[0] - s * 0.6 * math.cos(a), tip[1] - s * 0.6 * math.sin(a))], fill=G)


# ---------------- Childbirth ----------------
im, d = new("BABY'S POSITION")
divider(d, 240)
for cx, breech in ((120, False), (360, True)):
    E(d, [cx - 70, 44, cx + 70, 214], 5)               # womb
    L(d, [(cx - 16, 214), (cx - 10, 232)], 4); L(d, [(cx + 16, 214), (cx + 10, 232)], 4)  # birth canal
    if not breech:
        C(d, (cx, 178), 28, 4)                           # head low
        E(d, [cx - 40, 64, cx + 40, 152], 4)             # body
        arrow(d, (cx, 196), (cx, 228), 3, 10)
    else:
        C(d, (cx, 86), 28, 4)                            # head high
        E(d, [cx - 40, 112, cx + 40, 200], 4)            # body, bottom down
        arrow(d, (cx, 196), (cx, 228), 3, 10)
t(d, (120, 238), "HEAD DOWN", 17, "ma")
t(d, (120, 258), "usual, best", 15, "ma")
t(d, (360, 238), "BREECH", 17, "ma")
t(d, (360, 258), "bottom first: hands off", 15, "ma")
save(im, "cb_positions")

im, d = new("CROWNING: SLOW AND GENTLE")
# side view: the opening, the head coming out, one flat hand resting on it
L(d, [(30, 70), (130, 116)], 5)                          # upper edge of opening
L(d, [(30, 232), (130, 186)], 5)                         # lower edge
C(d, (156, 151), 44, 5)                                  # head
d.arc([120, 115, 192, 187], 300, 60, fill=G, width=2)    # hair line
# hand: palm and thumb, flat on the head
d.rounded_rectangle([206, 112, 236, 190], 14, outline=G, width=4)
L(d, [(222, 112), (238, 82)], 5)
t(d, (222, 202), "light hand", 14, "ma")
X = 262
lines(d, X, 44, ["1. She stops", "   pushing, pants.", "2. Rest a hand", "   on the head.", "3. DO NOT PULL.", "4. Head out: feel", "   for the cord."], 16, 6)
t(d, (8, 256), "Shoulders and body come with the next push.", 15)
save(im, "cb_crowning")

im, d = new("CORD ROUND THE NECK")
divider(d, 240)
for cx, tight in ((120, False), (360, True)):
    C(d, (cx, 108), 44, 5)                               # head
    L(d, [(cx - 22, 150), (cx - 30, 200)], 5); L(d, [(cx + 22, 150), (cx + 30, 200)], 5)  # neck/shoulders
    if tight:
        d.arc([cx - 30, 140, cx + 30, 170], 0, 360, fill=G, width=5)
        L(d, [(cx + 30, 156), (cx + 80, 210)], 5)
    else:
        d.arc([cx - 40, 140, cx + 40, 182], 0, 360, fill=G, width=5)
        L(d, [(cx + 38, 166), (cx + 86, 214)], 5)
        # arrow lifting the loop over the head
        d.arc([cx - 70, 40, cx + 70, 200], 200, 340, fill=G, width=3)
        arrow(d, (cx + 62, 70), (cx + 66, 84), 3, 12)
t(d, (120, 222), "LOOSE:", 17, "ma")
t(d, (120, 244), "slip it over the head", 15, "ma")
t(d, (360, 222), "TIGHT:", 17, "ma")
t(d, (360, 244), "leave it, unwind after", 15, "ma")
save(im, "cb_cord_neck")

im, d = new("BABY NOT BREATHING")
# baby on its back, side view, head level, folded cloth under the shoulders
d.rounded_rectangle([30, 150, 180, 190], 18, outline=G, width=4)    # body
C(d, (204, 166), 26, 4)                                             # head
d.rounded_rectangle([140, 192, 196, 206], 6, outline=G, width=3)    # folded cloth
L(d, [(16, 210), (270, 210)], 3)                                    # firm surface
d.arc([214, 138, 262, 190], 270, 90, fill=G, width=5)               # rescuer's mouth over mouth and nose
t(d, (30, 56), "Cover mouth", 16); t(d, (30, 76), "AND nose", 16)
arrow(d, (130, 94), (232, 140), 3)
t(d, (16, 218), "Head level. Cloth under shoulders.", 14)
X = 290
lines(d, X, 44, ["1. Dry, rub, warm", "2. 5 slow breaths,", "   2-3 s each", "3. Chest rises?", "   30 breaths/min", "4. No life after", "   30 s: 3 pushes", "   to 1 breath"], 15, 4)
t(d, (8, 256), "Two thumbs on lower breastbone, 1/3 deep.", 15)
save(im, "cb_newborn_breaths")

im, d = new("TIE AND CUT THE CORD")
# belly on the left
d.arc([-60, 60, 80, 240], 270, 90, fill=G, width=5)
t(d, (8, 140), "baby", 15)
# cord
d.line([(80, 150), (200, 146), (300, 154), (400, 148), (460, 150)], fill=G, width=8, joint="curve")
for x, lab in ((128, "2 cm"), (212, "5 cm")):
    d.rectangle([x - 4, 134, x + 4, 164], fill=G)
    t(d, (x, 172), "TIE", 15, "ma")
    t(d, (x, 192), lab, 15, "ma")
# cut mark between
L(d, [(158, 112), (182, 184)], 3); L(d, [(182, 112), (158, 184)], 3)
t(d, (170, 208), "CUT", 16, "ma")
t(d, (170, 228), "between", 15, "ma")
t(d, (460, 172), "to placenta", 15, "ra")
t(d, (260, 44), "Wait until it stops", 15)
t(d, (260, 64), "pulsing: 2-4 min.", 15)
t(d, (8, 256), "Boiled ties and blade. Tight reef knots.", 15)
save(im, "cb_cord_ties")

im, d = new("BLEEDING: RUB THE WOMB")
# front view of her belly
L(d, [(30, 40), (30, 250)], 4); L(d, [(250, 40), (250, 250)], 4)
dot(d, (140, 60), 5); t(d, (128, 60), "belly button", 13, "rm")
E(d, [86, 96, 194, 240], 4)                              # womb, top just below the belly button
t(d, (140, 214), "womb", 15, "mm")
d.rounded_rectangle([110, 104, 170, 134], 14, outline=G, width=4)  # cupped hand on the top
circle_arrow(d, (140, 119), 40, 200, 500, 4)
X = 270
lines(d, X, 44, ["Find the top of", "the womb near the", "belly button.", "", "Soft? Rub firmly", "in circles until", "hard.", "", "Baby to breast.", "Help her pee."], 15, 4)
t(d, (8, 260), "Check every 15 min for 2 hours. Call 999.", 14)
save(im, "cb_fundal")

# ---------------- Mental health ----------------
im, d = new("LOOK  -  LISTEN  -  LINK")
cols = [(80, "LOOK", ["Safe here?", "Urgent needs?", "Who is very", "upset?"]),
        (240, "LISTEN", ["Go gently.", "Ask needs.", "Listen. Let", "them talk."]),
        (400, "LINK", ["Water, food,", "shelter.", "True info.", "Family, help."])]
for k, (cx, name, rows) in enumerate(cols):
    C(d, (cx, 84), 40, 5)
    if name == "LOOK":
        E(d, [cx - 26, 70, cx + 26, 98], 4); dot(d, (cx, 84), 8)
    elif name == "LISTEN":
        d.arc([cx - 18, 60, cx + 18, 104], 270, 110, fill=G, width=5)
        d.arc([cx - 8, 72, cx + 10, 94], 270, 90, fill=G, width=3)
    else:
        d.rounded_rectangle([cx - 28, 74, cx + 2, 94], 10, outline=G, width=4)
        d.rounded_rectangle([cx - 4, 74, cx + 26, 94], 10, outline=G, width=4)
    t(d, (cx, 132), name, 19, "ma")
    lines(d, cx, 162, rows, 15, 5, "ma")
    if k < 2:
        arrow(d, (cx + 46, 84), (cx + 112, 84), 3)
t(d, (240, 262), "Do not force anyone to talk.", 15, "ma")
save(im, "mh_look_listen_link")

im, d = new("BOX BREATHING")
x0, y0, s = 60, 60, 170
d.rectangle([x0, y0, x0 + s, y0 + s], outline=G, width=5)
arrow(d, (x0 + 20, y0 - 14), (x0 + s - 20, y0 - 14), 3)
arrow(d, (x0 + s + 14, y0 + 20), (x0 + s + 14, y0 + s - 20), 3)
arrow(d, (x0 + s - 20, y0 + s + 14), (x0 + 20, y0 + s + 14), 3)
arrow(d, (x0 - 14, y0 + s - 20), (x0 - 14, y0 + 20), 3)
t(d, (x0 + s / 2, y0 + 22), "IN 4", 18, "ma")
t(d, (x0 + s - 14, y0 + s / 2 - 22), "HOLD", 16, "rm"); t(d, (x0 + s - 14, y0 + s / 2), "4", 16, "rm")
t(d, (x0 + s / 2, y0 + s - 22), "OUT 4", 18, "md")
t(d, (x0 + 14, y0 + s / 2 - 22), "HOLD", 16, "lm"); t(d, (x0 + 14, y0 + s / 2), "4", 16, "lm")
X = 290
lines(d, X, 52, ["Count slowly.", "Belly, not chest.", "4 rounds or more."], 15, 6)
L(d, [(X, 130), (470, 130)], 2)
lines(d, X, 142, ["Or: in for 5,", "out for 5 or", "longer, for", "5 minutes."], 15, 6)
t(d, (8, 260), "Long out-breath = calm body.", 15)
save(im, "mh_box_breathing")

im, d = new("GROUNDING: 5-4-3-2-1")
rows = [("5", "things you SEE"), ("4", "things you TOUCH"), ("3", "things you HEAR"),
        ("2", "things you SMELL"), ("1", "thing you TASTE")]
for k, (n, s) in enumerate(rows):
    y = 58 + k * 42
    C(d, (52, y), 18, 4)
    t(d, (52, y), n, 20, "mm")
    t(d, (86, y), s, 19, "lm")
t(d, (460, 80), "Slowly.", 16, "ra")
t(d, (460, 104), "Out loud", 16, "ra")
t(d, (460, 128), "or in", 16, "ra")
t(d, (460, 152), "your head.", 16, "ra")
t(d, (8, 262), "Feet on the floor. You are here, now.", 15)
save(im, "mh_grounding")

# ---------------- Growing ----------------
im, d = new("SOWING DEPTH")
SOIL = 92
L(d, [(10, SOIL), (470, SOIL)], 4)
for x in range(20, 470, 26):
    dot(d, (x, SOIL + 8), 1)
items = [(70, 4, 22, "lettuce", "1 cm"), (170, 5, 22, "radish", "1 cm"),
         (280, 8, 55, "squash", "2.5 cm"), (400, 11, 110, "bean", "5 cm")]
for x, r, depth, name, lab in items:
    y = SOIL + depth
    E(d, [x - r * 1.4, y - r, x + r * 1.4, y + r], 3, fill=G)
    L(d, [(x + 30, SOIL), (x + 30, y)], 2)
    L(d, [(x + 24, SOIL), (x + 36, SOIL)], 2); L(d, [(x + 24, y), (x + 36, y)], 2)
    t(d, (x, SOIL - 30), name, 16, "ma")
    t(d, (x + 30, y + 6), lab, 15, "ma")
t(d, (8, 236), "Rule: 2 to 3 times the seed's size.", 16)
t(d, (8, 258), "Tiny seeds: just cover. Firm, then water.", 15)
save(im, "gr_sowing_depth")

im, d = new("SPROUTS IN A JAR")
# jar upside down at a slant in a bowl
cx, cy = 120, 140
ang = math.radians(35)


def rot(px, py):
    return (cx + px * math.cos(ang) - py * math.sin(ang), cy + px * math.sin(ang) + py * math.cos(ang))


jar = [rot(-40, -70), rot(40, -70), rot(40, 60), rot(-40, 60)]
d.polygon(jar, outline=G, width=5)
L(d, [rot(-44, 60), rot(44, 60)], 7)                  # mesh lid
for k in range(-30, 40, 12):
    dot(d, rot(k, 52), 3)
    dot(d, rot(k + 6, 44), 3)
d.arc([40, 200, 240, 280], 180, 360, fill=G, width=4)  # bowl
L(d, [(40, 240), (240, 240)], 4)
X = 262
steps = ["1 Soak 8-12 h", "2 Mesh lid, drain", "3 Rinse, drain", "  2x a day", "4 Upside down,", "  on a slant", "5 Eat in 2-5 days"]
lines(d, X, 44, steps, 16, 6)
t(d, (8, 262), "Cook till steaming hot to be safe.", 15)
save(im, "gr_jar_sprouts")

im, d = new("THREE SISTERS (from above)")
for k, cx in enumerate((120, 360)):
    cy = 140
    C(d, (cx, cy), 84, 3)                                # mound edge
    for a in range(0, 360, 90):                          # corn
        p = (cx + 20 * math.cos(math.radians(a + 45)), cy + 20 * math.sin(math.radians(a + 45)))
        d.rectangle([p[0] - 6, p[1] - 6, p[0] + 6, p[1] + 6], fill=G)
    for a in range(0, 360, 60):                          # beans
        p = (cx + 48 * math.cos(math.radians(a)), cy + 48 * math.sin(math.radians(a)))
        C(d, p, 6, 3)
    for a in (30, 210):                                  # squash
        p = (cx + 70 * math.cos(math.radians(a)), cy + 70 * math.sin(math.radians(a)))
        C(d, p, 13, 4)
        for b in range(0, 360, 72):
            L(d, [p, (p[0] + 13 * math.cos(math.radians(b)), p[1] + 13 * math.sin(math.radians(b)))], 2)
arrow(d, (240, 140), (276, 140), 2, 8); arrow(d, (240, 140), (204, 140), 2, 8)
t(d, (240, 118), "1 m", 15, "ma")
# key
d.rectangle([12, 248, 24, 260], fill=G); t(d, (30, 254), "corn", 15, "lm")
C(d, (100, 254), 6, 3); t(d, (112, 254), "beans", 15, "lm")
C(d, (186, 254), 10, 3); t(d, (202, 254), "squash", 15, "lm")
t(d, (472, 254), "mounds 30 cm high", 14, "rm")
save(im, "gr_three_sisters")

im, d = new("POTATOES")
divider(d, 240)
# earthing up: ridge with stems
t(d, (120, 40), "EARTH UP", 17, "ma")
GROUND = 220
L(d, [(10, GROUND), (230, GROUND)], 3)
d.polygon([(30, GROUND), (90, 160), (150, 160), (210, GROUND)], outline=G, width=4)
for x in (100, 140):
    L(d, [(x, 200), (x, 100)], 4)
    for y in (110, 126, 142):
        L(d, [(x, y), (x - 14, y - 8)], 3); L(d, [(x, y), (x + 14, y - 8)], 3)
E(d, [70, 196, 96, 214], 3, fill=G); E(d, [144, 200, 170, 216], 3, fill=G)
L(d, [(180, 100), (180, 160)], 2); L(d, [(174, 100), (186, 100)], 2); L(d, [(174, 160), (186, 160)], 2)
t(d, (190, 130), "10 cm", 14, "lm")
t(d, (120, 234), "at 23 cm tall,", 15, "ma")
t(d, (120, 254), "pile soil up", 15, "ma")
# sack
t(d, (360, 40), "IN A SACK", 17, "ma")
d.polygon([(300, 80), (420, 80), (430, 220), (290, 220)], outline=G, width=4)
for x in (310, 340, 380, 410):
    dot(d, (x, 214), 3)
dashed(d, (296, 150), (424, 150), 2)
L(d, [(360, 190), (360, 120)], 4)
for y in (128, 142):
    L(d, [(360, y), (346, y - 8)], 3); L(d, [(360, y), (374, y - 8)], 3)
E(d, [346, 182, 374, 200], 3, fill=G)
arrow(d, (452, 190), (452, 140), 3)
t(d, (360, 234), "add compost", 15, "ma")
t(d, (360, 254), "as it grows", 15, "ma")
save(im, "gr_potatoes")

im, d = new("NO-DIG BED")
# layered cross-section
L(d, [(30, 210), (450, 210)], 3)                             # old ground
for x in range(40, 450, 18):
    L(d, [(x, 210), (x - 4, 196)], 2); L(d, [(x + 6, 210), (x + 10, 198)], 2)   # flattened grass
L(d, [(30, 190), (390, 190)], 5); L(d, [(30, 184), (390, 184)], 5)              # cardboard
d.rectangle([30, 110, 390, 180], outline=G, width=4)                            # compost
for x in range(46, 380, 22):
    for y in (126, 146, 166):
        dot(d, (x + (y % 3) * 4, y), 2)
for x in (160, 260, 350):                                                       # seedlings
    L(d, [(x, 110), (x, 80)], 4)
    d.arc([x - 22, 62, x, 84], 270, 90, fill=G, width=3)
    d.arc([x, 62, x + 22, 84], 90, 270, fill=G, width=3)
L(d, [(404, 110), (404, 180)], 2); L(d, [(398, 110), (410, 110)], 2); L(d, [(398, 180), (410, 180)], 2)
t(d, (414, 136), "10-15", 14, "lm"); t(d, (414, 154), "cm", 14, "lm")
t(d, (30, 92), "compost", 15)
t(d, (8, 226), "cardboard x2 (wet), then cut grass", 15)
L(d, [(30, 56), (390, 56)], 2); L(d, [(30, 50), (30, 62)], 2); L(d, [(390, 50), (390, 62)], 2)
t(d, (472, 30), "1.2 m wide:", 14, "ra"); t(d, (472, 48), "reach the", 14, "ra"); t(d, (472, 66), "middle", 14, "ra")
t(d, (8, 254), "Sow straight into the compost.", 15)
save(im, "gr_no_dig")
