"""Diagrams for the Shelter, Fire and Food cards. Run from the repo root.

480x284 PNG, bold #1AFF80 lines on black, like the other guide pictures.
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
    d.text((8, 4), title, fill=G, font=f(18))
    return im, d


def t(d, xy, s, size=13, anchor="la"):
    d.text(xy, s, fill=G, font=f(size), anchor=anchor)


def L(d, pts, w=4):
    d.line(pts, fill=G, width=w, joint="curve")


def C(d, c, r, w=4, fill=None):
    d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], outline=G, width=w, fill=fill)


def arrow(d, a, b, w=3):
    L(d, [a, b], w)
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    s = 12
    d.polygon([b, (b[0] - s * math.cos(ang - 0.45), b[1] - s * math.sin(ang - 0.45)),
               (b[0] - s * math.cos(ang + 0.45), b[1] - s * math.sin(ang + 0.45))], fill=G)


def flame(d, cx, base, h=30, w=16):
    L(d, [(cx - w, base), (cx - w // 2, base - h // 2), (cx, base - h), (cx + w // 2, base - h // 2), (cx + w, base)], 3)
    L(d, [(cx - w // 2, base), (cx, base - h // 2), (cx + w // 2, base)], 3)


def ground(d, y=230, x0=10, x1=470):
    L(d, [(x0, y), (x1, y)], 3)


def divider(d, x, bottom=276):
    L(d, [(x, 34), (x, bottom)], 2)


def save(im, name):
    im.save(f"content/img/{name}.png")


# ---------------- Shelter ----------------
im, d = new("DEBRIS HUT")
ground(d, 222)
L(d, [(60, 120), (420, 214)], 6)                 # ridge pole sloping to ground
L(d, [(70, 222), (60, 118), (50, 222)], 5)       # bipod at high end
for i in range(9):                               # ribs
    x = 85 + i * 38
    y = 120 + (x - 60) * 94 / 360
    L(d, [(x, y), (x - 26, 222)], 3)
    L(d, [(x, y), (x + 20, 222)], 2)
L(d, [(40, 100), (150, 70), (300, 120), (440, 205)], 3)   # leaf pile outline
t(d, (190, 46), "leaves: an arm's length thick")
arrow(d, (250, 64), (250, 100), 2)
d.rectangle([66, 180, 96, 222], outline=G, width=3)
t(d, (8, 236), "door: crawl size, plug it", 13)
t(d, (250, 236), "ridge: hip high at head end", 13)
t(d, (8, 256), "Bed of leaves inside, as thick as the roof is not", 12)
save(im, "shelter_debris_hut")

im, d = new("LEAN-TO WITH FIRE (end view)")
ground(d, 222)
L(d, [(130, 222), (130, 90)], 6)                 # upright / tree
C(d, (130, 96), 9, 4, fill=K)                    # ridge pole end-on
L(d, [(130, 96), (20, 222)], 7)                  # roof, back to the wind
for k in range(1, 4):
    L(d, [(130 - k * 22, 96 + k * 25), (130 - k * 22 + 8, 96 + k * 25 + 4)], 0)
t(d, (140, 74), "ridge pole", 12)
arrow(d, (10, 70), (70, 120), 3); t(d, (8, 46), "wind", 13)
C(d, (56, 212), 7); L(d, [(64, 213), (122, 213)], 7)
t(d, (40, 230), "you + thick bed", 12)
flame(d, 250, 220, 40, 20)
L(d, [(225, 220), (275, 220)], 5)
t(d, (220, 230), "small fire", 12)
for y in (218, 204, 190, 176):
    L(d, [(330, y), (380, y)], 7)
L(d, [(326, 222), (326, 166)], 4); L(d, [(384, 222), (384, 166)], 4)
t(d, (318, 230), "log wall", 12)
arrow(d, (320, 186), (285, 186), 2); arrow(d, (215, 186), (170, 186), 2)
t(d, (190, 140), "heat bounces back to you", 12)
t(d, (8, 256), "Open side faces the fire. Body-length gap.", 13)
save(im, "shelter_lean_to")

im, d = new("A-FRAME SHELTER")
ground(d, 222)
L(d, [(60, 222), (110, 110), (160, 222)], 6)     # front A
L(d, [(330, 222), (380, 140), (430, 222)], 6)    # back A (smaller, further)
L(d, [(110, 110), (380, 140)], 6)                # ridge
for i in range(1, 8):
    x = 110 + i * 34
    y = 110 + (x - 110) * 30 / 270
    L(d, [(x, y), (x - 40, 222)], 3)
    L(d, [(x, y), (x + 40, 222)], 2)
t(d, (120, 80), "ridge pole lashed to two A-frames")
t(d, (8, 236), "1 Two A-frames  2 Ridge  3 Ribs both sides", 13)
t(d, (8, 256), "4 Cover 30 cm+  5 Close the windward end", 13)
save(im, "shelter_aframe")

im, d = new("TARP PITCHES (side view)")
pw = 160
for i, name in enumerate(["A-FRAME", "PLOW POINT", "DIAMOND"]):
    x0 = i * pw
    if i:
        divider(d, x0, 256)
    t(d, (x0 + pw // 2, 44), name, 14, "ma")
    L(d, [(x0 + 8, 214), (x0 + pw - 8, 214)], 3)
    if i == 0:
        L(d, [(x0 + 12, 110), (x0 + pw - 12, 110)], 2)       # ridge line
        L(d, [(x0 + 30, 214), (x0 + 80, 110), (x0 + 130, 214)], 5)
        L(d, [(x0 + 12, 214), (x0 + 12, 90)], 4); L(d, [(x0 + pw - 12, 214), (x0 + pw - 12, 90)], 4)
        t(d, (x0 + 8, 226), "line between trees", 11)
        t(d, (x0 + 8, 242), "both edges pegged", 11)
    elif i == 1:
        L(d, [(x0 + 20, 214), (x0 + 20, 80)], 4)            # tree
        L(d, [(x0 + 20, 100), (x0 + 140, 210)], 5)           # tarp ridge from high corner to low
        L(d, [(x0 + 20, 100), (x0 + 60, 212)], 3)
        L(d, [(x0 + 20, 100), (x0 + 95, 212)], 3)
        arrow(d, (x0 + 155, 140), (x0 + 128, 160), 2)
        t(d, (x0 + 118, 120), "wind", 11)
        t(d, (x0 + 8, 226), "1 corner high on tree", 11)
        t(d, (x0 + 8, 242), "low corner into wind", 11)
    else:
        L(d, [(x0 + 20, 214), (x0 + 20, 80)], 4)
        L(d, [(x0 + 20, 96), (x0 + 75, 150), (x0 + 140, 210)], 5)
        L(d, [(x0 + 20, 96), (x0 + 70, 120), (x0 + 140, 210)], 3)
        L(d, [(x0 + 75, 150), (x0 + 75, 214)], 3)            # side stick
        t(d, (x0 + 8, 226), "high and low corner", 11)
        t(d, (x0 + 8, 242), "sides on short sticks", 11)
t(d, (8, 262), "Drip string on the ridge line stops rain running in.", 12)
save(im, "shelter_tarps")

im, d = new("SNOW TRENCH          QUINZHEE")
divider(d, 230)
# trench (cross-section)
L(d, [(10, 120), (60, 120), (60, 200), (170, 200), (170, 120), (220, 120)], 4)
L(d, [(40, 110), (190, 110)], 6)                       # branches across
L(d, [(40, 98), (115, 80), (190, 98)], 4)              # snow roof
t(d, (60, 56), "branches + snow roof", 12)
L(d, [(66, 192), (164, 192)], 6); t(d, (70, 204), "bough floor", 12)
t(d, (8, 236), "1 m deep, body long", 12)
t(d, (8, 254), "floor matters most", 12)
# quinzhee
d.arc([250, 70, 470, 290], 180, 360, fill=G, width=6)
d.arc([280, 100, 440, 260], 180, 360, fill=G, width=3)
L(d, [(250, 180), (470, 180)], 3)
for a in (200, 240, 270, 300, 340):
    r1, r2 = 110, 80
    ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
    L(d, [(360 + r1 * ca, 180 + r1 * sa), (360 + r2 * ca, 180 + r2 * sa)], 3)
L(d, [(360, 70), (360, 100)], 2); L(d, [(352, 68), (352, 100)], 2)
t(d, (372, 50), "vent", 12)
d.rectangle([380, 150, 432, 180], outline=G, width=3); t(d, (384, 156), "bench", 11)
d.rectangle([290, 162, 318, 180], outline=K, fill=K); L(d, [(290, 165), (318, 165)], 2)
t(d, (250, 196), "low door", 12)
t(d, (330, 196), "sticks = 30 cm walls", 12)
t(d, (240, 236), "Pile, wait 1-2 h, dig out.", 12)
t(d, (240, 254), "No flame without a vent.", 12)
save(im, "shelter_snow")

# ---------------- Fire ----------------
im, d = new("FIRE TRIANGLE")
A, B, Cc = (240, 54), (110, 214), (370, 214)
L(d, [A, B, Cc, A], 7)
t(d, (240, 40), "", 1)
t(d, (130, 110), "HEAT", 22, "ra")
t(d, (350, 110), "AIR", 22)
t(d, (240, 224), "FUEL", 22, "ma")
flame(d, 240, 190, 60, 26)
t(d, (8, 256), "Take one away and the fire dies.", 14)
save(im, "fire_triangle")

im, d = new("FIRE LAYS")
for i, name in enumerate(["TEEPEE", "LOG CABIN", "LEAN-TO"]):
    x0 = i * 160
    if i:
        divider(d, x0)
    t(d, (x0 + 80, 44), name, 14, "ma")
    L(d, [(x0 + 10, 210), (x0 + 150, 210)], 3)
    cx = x0 + 80
    if i == 0:
        for dx in (-50, -30, -10, 10, 30, 50):
            L(d, [(cx + dx, 210), (cx, 80)], 4)
        t(d, (x0 + 8, 222), "cone over tinder,", 11)
        t(d, (x0 + 8, 238), "door to the wind", 11)
    elif i == 1:
        for k in range(5):
            y = 205 - k * 22
            if k % 2 == 0:
                L(d, [(cx - 50 + k * 4, y), (cx + 50 - k * 4, y)], 7)
            else:
                C(d, (cx - 42 + k * 4, y), 7, 3); C(d, (cx + 42 - k * 4, y), 7, 3)
        L(d, [(cx - 10, 200), (cx, 180), (cx + 10, 200)], 3)
        t(d, (x0 + 8, 222), "stacked square,", 11)
        t(d, (x0 + 8, 238), "teepee inside", 11)
    else:
        L(d, [(x0 + 20, 210), (x0 + 145, 100)], 6)
        for k in range(4):
            xa = x0 + 60 + k * 18
            L(d, [(xa, 210), (xa + 12, 210 - (xa + 12 - x0 - 20) * 110 / 125)], 3)
        C(d, (x0 + 75, 202), 8, 3)
        arrow(d, (x0 + 150, 70), (x0 + 120, 70), 2)
        t(d, (x0 + 100, 54), "wind", 11)
        t(d, (x0 + 8, 222), "stick at 30 deg", 11)
        t(d, (x0 + 8, 238), "into wind, tinder under", 11)
t(d, (8, 260), "Light from the upwind side.", 12)
save(im, "fire_lays")

im, d = new("DAKOTA FIRE HOLE (cut-away)")
for seg in ([(10, 90), (120, 90)], [(200, 90), (290, 90)], [(330, 90), (470, 90)]):
    L(d, seg, 4)
L(d, [(120, 90), (120, 210), (200, 210)], 4)     # fire hole
L(d, [(200, 90), (200, 178)], 4)
L(d, [(290, 90), (290, 150), (200, 178)], 4)     # air hole + tunnel top
L(d, [(330, 90), (330, 176), (200, 210)], 4)     # air hole + tunnel bottom
flame(d, 160, 205, 70, 26)
arrow(d, (310, 50), (310, 150), 3)
arrow(d, (300, 172), (215, 196), 3)
t(d, (120, 44), "fire hole", 13); t(d, (110, 60), "~30 cm wide, deep", 12)
t(d, (300, 36), "air hole, upwind", 13)
t(d, (220, 220), "air tunnel to the bottom", 12)
L(d, [(110, 98), (210, 98)], 5); t(d, (8, 100), "green sticks", 11); t(d, (8, 114), "hold a pot", 11)
t(d, (8, 250), "Drown it, then fill both holes.", 13)
save(im, "fire_dakota")

im, d = new("FERRO ROD")
L(d, [(40, 200), (440, 200)], 3)
d.ellipse([150, 170, 290, 210], outline=G, width=4); t(d, (160, 214), "tinder nest", 12)
L(d, [(220, 190), (300, 60)], 12)                 # rod
d.rectangle([292, 40, 316, 72], outline=G, width=3)
t(d, (322, 44), "rod: tip in tinder,", 12); t(d, (322, 60), "held firm", 12)
L(d, [(240, 110), (300, 150)], 6)                 # striker at ~90 deg
t(d, (306, 140), "striker at 90 deg", 12)
arrow(d, (310, 100), (250, 175), 3)
t(d, (340, 100), "push down", 12)
for k in range(6):
    a = math.radians(200 + k * 25)
    L(d, [(225, 182), (225 + 30 * math.cos(a), 182 + 18 * math.sin(a) + 10)], 2)
t(d, (8, 236), "Stop before the striker hits the tinder.", 13)
t(d, (8, 256), "Or hold the striker still and pull the rod back.", 13)
save(im, "fire_ferro")

im, d = new("BOW DRILL")
L(d, [(20, 220), (460, 220)], 3)
d.rectangle([140, 196, 400, 212], outline=G, width=4)        # fireboard
t(d, (300, 176), "fireboard", 12)
d.polygon([(210, 196), (196, 212), (224, 212)], fill=K, outline=G)
d.rectangle([170, 212, 250, 220], outline=G, width=2); t(d, (110, 228), "bark catches the coal", 12)
L(d, [(210, 196), (210, 82)], 9)                              # spindle
d.ellipse([186, 62, 234, 84], outline=G, width=4); t(d, (240, 58), "socket (stone)", 12)
L(d, [(40, 150), (120, 110), (330, 120)], 6)                  # bow
L(d, [(40, 150), (205, 128), (215, 136), (330, 120)], 2)      # string loop
t(d, (236, 128), "bow: 1 turn round spindle", 12)
arrow(d, (60, 190), (130, 190), 2); arrow(d, (130, 190), (60, 190), 2)
t(d, (60, 196), "long strokes", 11)
t(d, (222, 92), "spindle", 12)
t(d, (330, 228), "V notch", 12); arrow(d, (340, 228), (222, 206), 2)
t(d, (8, 252), "Press down. Smoke + dark dust = coal.", 13)
save(im, "fire_bow_drill")

# ---------------- Food ----------------
im, d = new("WILD GARLIC  vs  LILY OF THE VALLEY")
divider(d, 240)
# garlic: separate leaves from ground, star flower ball
L(d, [(20, 220), (220, 220)], 3)
for x, tip in ((60, (30, 90)), (90, (100, 70)), (150, (190, 90))):
    L(d, [(x, 220), tip], 4)
    d.polygon([(x, 220), (tip[0] - 10, tip[1] + 40), tip, (tip[0] + 10, tip[1] + 40)], outline=G)
L(d, [(120, 220), (120, 80)], 3)
for k in range(8):
    a = k * math.pi / 4
    x, y = 120 + 20 * math.cos(a), 70 + 20 * math.sin(a)
    t(d, (x, y), "*", 16, "mm")
t(d, (10, 228), "1 leaf per stalk, from ground", 12)
t(d, (10, 244), "white stars in a ball", 12)
t(d, (10, 260), "smells of garlic", 12)
# lily
L(d, [(260, 220), (460, 220)], 3)
L(d, [(350, 220), (350, 70)], 3)
d.polygon([(350, 220), (310, 140), (330, 80), (352, 140)], outline=G, width=3)
d.polygon([(350, 220), (395, 140), (380, 80), (352, 140)], outline=G, width=3)
L(d, [(350, 70), (410, 60)], 3)
for k in range(4):
    x = 362 + k * 13
    L(d, [(x, 63 - k * 2), (x, 74)], 2)
    d.arc([x - 6, 70, x + 6, 84], 180, 360, fill=G, width=3)
t(d, (250, 228), "2-3 leaves wrap 1 stem", 12)
t(d, (250, 244), "hanging white bells", 12)
t(d, (250, 260), "POISONOUS, no garlic smell", 12)
save(im, "food_garlic_lily")

im, d = new("DEADLY: HEMLOCK, WATER DROPWORT")
divider(d, 240, 262)
L(d, [(110, 230), (110, 80)], 10)
for y in (110, 140, 175, 205):
    d.ellipse([104, y, 116, y + 10], fill=K, outline=K)
    d.ellipse([106, y + 2, 114, y + 8], fill=G)
for k in range(7):
    a = math.radians(200 + k * 23)
    L(d, [(110, 80), (110 + 50 * math.cos(a), 80 + 30 * math.sin(a))], 2)
    C(d, (110 + 50 * math.cos(a), 80 + 30 * math.sin(a)), 4, 2)
L(d, [(110, 150), (180, 120)], 3)
for k in range(5):
    x = 120 + k * 13
    L(d, [(x, 150 - k * 5), (x + 6, 136 - k * 5)], 2); L(d, [(x, 150 - k * 5), (x + 8, 156 - k * 5)], 2)
t(d, (10, 236), "hemlock: smooth stem,", 12)
t(d, (10, 252), "purple blotches, mousy smell", 12)
# dropwort roots
L(d, [(260, 120), (460, 120)], 3); t(d, (262, 100), "bank / water", 12)
L(d, [(360, 120), (360, 60)], 5)
for dx in (-50, -25, 0, 25, 50):
    L(d, [(360, 125), (360 + dx * 1.2, 150), (360 + dx * 1.5, 205)], 10)
t(d, (250, 236), "water dropwort: roots", 12)
t(d, (250, 252), "like pale fingers. DEADLY", 12)
t(d, (8, 270), "Do not eat ANY wild carrot-family plant.", 12)
save(im, "food_hemlock")

im, d = new("SMOKING RACK")
L(d, [(20, 230), (460, 230)], 3)
L(d, [(120, 230), (120, 80)], 5); L(d, [(360, 230), (360, 80)], 5)
L(d, [(110, 90), (370, 90)], 5); L(d, [(110, 120), (370, 120)], 4)
for x in range(150, 340, 30):
    L(d, [(x, 120), (x, 160)], 6)
t(d, (380, 128), "thin strips,", 12); t(d, (380, 144), "no fat", 12)
for x in range(160, 330, 25):
    d.ellipse([x - 8, 216, x + 8, 230], outline=G, width=3)
t(d, (180, 238), "coals + green hardwood chips", 12)
for x in (190, 240, 290):
    L(d, [(x, 210), (x - 8, 190), (x + 6, 176), (x - 4, 165)], 2)
t(d, (130, 194), "", 1)
L(d, [(100, 70), (100, 232)], 2); L(d, [(380, 70), (380, 120)], 2)
t(d, (8, 60), "cloth wall holds smoke", 12)
t(d, (380, 180), "~60 cm", 12); arrow(d, (440, 200), (440, 125), 2)
t(d, (8, 258), "Smoke, not flame. No pine, yew or holly.", 13)
save(im, "food_smoke_rack")

im, d = new("STONE BOILING")
L(d, [(10, 160), (470, 160)], 3)
flame(d, 90, 156, 50, 30)
for cx in (70, 100, 120):
    C(d, (cx, 150), 9, 3)
t(d, (40, 168), "dry stones", 12); t(d, (40, 184), "in fire 30 min", 12)
L(d, [(150, 100), (200, 140)], 3); L(d, [(155, 95), (205, 136)], 3)
arrow(d, (150, 70), (290, 110), 3)
t(d, (170, 54), "lift with 2 sticks", 12)
d.arc([260, 120, 440, 250], 0, 180, fill=G, width=5)
L(d, [(270, 170), (430, 170)], 2)
for cx in (320, 360):
    C(d, (cx, 215), 9, 3)
t(d, (300, 176), "water + food", 12)
t(d, (290, 120), "lined pit / bark tray", 12)
t(d, (8, 230), "NEVER river stones:", 13)
t(d, (8, 248), "they can burst", 13)
save(im, "food_stone_boil")
