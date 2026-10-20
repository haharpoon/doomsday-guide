"""Diagrams for batch 7: the exhaustive Fire, Shelter, Water, Food and Navigation
sub-menus, plus Clothing, Weather, Power, Tools, Emergency and Sanitation additions.
Run from the repo root: python3 tools/gen_guide7.py [prefix ...]

480x284 PNG, bold #1AFF80 lines on black. The helpers (new, t, L, C, E, dot, arrow,
dashed, divider, box, lines, circle_arrow, save, hatch, dots, flame, cross) come from
gen_guide6.py, which loads gen_guide5.py's helpers; only the helper sections run.
Give one or more name prefixes (fire_, sh_, wt_ ...) to redraw only those pictures.
"""
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "gen_guide6.py"), encoding="utf-8") as _handle:
    _src = _handle.read()
exec(_src.split("# ======================= FIRST AID")[0])  # noqa: S102  helpers only

ONLY = tuple(sys.argv[1:])
_save = save


def save(im, name):  # noqa: F811  filter by prefix
    if not ONLY or name.startswith(ONLY):
        _save(im, name)


def ground(d, y, x0=8, x1=472, w=3):
    L(d, [(x0, y), (x1, y)], w)
    for x in range(x0 + 6, x1, 26):
        L(d, [(x, y + 3), (x - 8, y + 11)], 2)


def log_end(d, c, r, w=3):
    C(d, c, r, w)
    C(d, c, max(2, r // 2), 2)


def log_side(d, x0, y0, x1, y1, w=3):
    """A log seen from the side: a long rounded box with an end ring."""
    r = (y1 - y0) / 2
    d.rounded_rectangle([x0, y0, x1, y1], int(r), outline=G, width=w)
    C(d, (x0 + r, y0 + r), int(r * 0.45), 2)


def coals(d, x0, x1, y, n=None):
    n = n or max(3, int((x1 - x0) / 14))
    for k in range(n):
        x = x0 + (x1 - x0) * (k + 0.5) / n
        E(d, [x - 6, y - 6 - (k % 2) * 3, x + 6, y + 2], 2, fill=G)


def tinder(d, cx, cy, r=14):
    for k in range(9):
        a = k * math.pi / 9
        L(d, [(cx - r * math.cos(a), cy - r * 0.5 * math.sin(a)), (cx + r * math.cos(a), cy + r * 0.3 * math.sin(a))], 2)


def smoke(d, x, y, h=40):
    pts = [(x + 6 * math.sin(k / 2.0), y - k * h / 12) for k in range(13)]
    d.line(pts, fill=G, width=2)


def pot(d, cx, top, w=56, h=36):
    d.rectangle([cx - w / 2, top, cx + w / 2, top + h], outline=G, width=3)
    L(d, [(cx - w / 2 - 6, top), (cx + w / 2 + 6, top)], 3)


def person_lying(d, x, y, length=150):
    C(d, (x, y - 10), 11, 3)
    d.rounded_rectangle([x + 12, y - 20, x + length, y], 9, outline=G, width=3)


# ======================= FIRE =======================
im, d = new("MAKE CHAR CLOTH")
coals(d, 40, 220, 236, 12)
d.rectangle([70, 170, 190, 228], outline=G, width=4)            # tin
L(d, [(62, 170), (198, 170)], 5)                                 # lid
dot(d, (130, 170), 4)
for k in range(4):
    d.rectangle([84 + k * 24, 196, 102 + k * 24, 222], outline=G, width=2)   # cotton squares
smoke(d, 130, 160, 70)
t(d, (20, 60), "smoke and gas", 14); t(d, (20, 78), "from one hole", 14)
lines(d, 262, 44, ["1. Cotton squares,", "   loose in a tin", "2. One nail hole", "3. Into the coals", "4. Smoke stops:", "   lift out, plug", "5. Cool CLOSED,", "   then open"], 16, 4)
t(d, (130, 256), "black and bendy = good", 15, "ma")
save(im, "fire_char_tin")

im, d = new("HAND DRILL")
ground(d, 256)
d.polygon([(60, 240), (420, 240), (430, 254), (50, 254)], outline=G, width=3)   # hearth board
d.polygon([(232, 240), (250, 240), (241, 254)], fill=G)                         # notch
L(d, [(241, 238), (241, 46)], 6)                                                 # spindle
for y, lab in ((80, "start"), (176, "bottom")):
    d.rounded_rectangle([204, y - 16, 230, y + 16], 8, outline=G, width=3)
    d.rounded_rectangle([252, y - 16, 278, y + 16], 8, outline=G, width=3)
arrow(d, (190, 84), (190, 168), 3)
t(d, (178, 120), "rub and", 14, "ra"); t(d, (178, 138), "press down", 14, "ra")
arrow(d, (300, 172), (300, 86), 3)
t(d, (312, 112), "jump back", 14); t(d, (312, 130), "to the top", 14)
t(d, (130, 214), "foot here", 14, "ma"); t(d, (360, 214), "notch + bark", 14, "ma")
t(d, (241, 34), "60-80 cm dry stalk", 14, "ma")
save(im, "fire_hand_drill")

im, d = new("FIRE PLOUGH")
ground(d, 252)
d.polygon([(30, 150), (430, 236), (430, 250), (30, 166)], outline=G, width=4)    # board slope
dashed(d, (60, 160), (400, 232), 2, 10, 6)                                        # groove
L(d, [(170, 120), (282, 198)], 7)                                                  # plough stick
arrow(d, (150, 92), (228, 146), 3); arrow(d, (250, 138), (172, 84), 3)
t(d, (90, 64), "push hard up and down", 15)
E(d, [396, 222, 430, 240], 3, fill=G)                                             # dust pile
tinder(d, 452, 238, 16)
t(d, (408, 182), "dust and", 14, "ma"); t(d, (408, 200), "ember here", 14, "ma")
t(d, (60, 196), "soft board,", 14); t(d, (60, 214), "groove 20-30 cm", 14)
save(im, "fire_plough")

im, d = new("FIRE SAW (BAMBOO)")
ground(d, 252)
d.arc([90, 150, 390, 290], 180, 360, fill=G, width=6)                            # hearth: curved side up
L(d, [(240, 150), (240, 176)], 5)                                                 # slot
tinder(d, 240, 196, 30)
L(d, [(70, 140), (100, 210)], 4); L(d, [(410, 140), (380, 210)], 4)               # stakes
d.rectangle([228, 70, 252, 150], outline=G, width=4)                              # saw half, edge down
arrow(d, (210, 100), (150, 100), 3); arrow(d, (270, 100), (330, 100), 3)
t(d, (60, 120), "end view", 14)
t(d, (240, 54), "saw hard across the slot", 15, "ma")
t(d, (420, 186), "stakes", 14, "ma")
t(d, (240, 226), "shavings under the slot", 14, "ma")
save(im, "fire_saw")

im, d = new("PUMP DRILL")
L(d, [(170, 40), (170, 236)], 6)                                                   # spindle
L(d, [(80, 126), (260, 126)], 8)                                                   # crossbar
L(d, [(84, 126), (170, 44), (256, 126)], 2)                                        # cord
E(d, [118, 180, 222, 206], 4)                                                      # flywheel
d.polygon([(40, 236), (300, 236), (308, 250), (32, 250)], outline=G, width=3)
d.polygon([(162, 236), (178, 236), (170, 250)], fill=G)
ground(d, 254, 8, 320)
arrow(d, (94, 104), (94, 150), 3)
lines(d, 300, 50, ["1. Twist: the cord", "   winds round", "   and lifts the bar", "2. Push the bar", "   down smoothly", "3. Flywheel spins", "   on and rewinds", "4. Ease, push again"], 15, 4)
t(d, (14, 172), "heavy", 14); t(d, (14, 190), "flywheel", 14)
save(im, "fire_pump_drill")

im, d = new("FIRE PISTON")
for cx, glow in ((110, False), (330, True)):
    d.rectangle([cx - 22, 120, cx + 22, 250], outline=G, width=4)                  # tube
    L(d, [(cx, 40 if not glow else 220), (cx, 120 if not glow else 236)], 0)
if True:
    d.rectangle([98, 60, 122, 140], outline=G, width=3)                            # plunger out
    E(d, [80, 34, 140, 60], 4)                                                     # knob
    dot(d, (110, 142), 5)
    arrow(d, (170, 60), (170, 170), 4)
    t(d, (110, 262), "tinder in the tip", 14, "ma")
    t(d, (184, 100), "SLAM", 16)
    d.rectangle([318, 54, 342, 112], outline=G, width=3)                            # pulled out
    E(d, [300, 28, 360, 54], 4)
    C(d, (330, 118), 8, 3, fill=G)
    for a in range(0, 360, 45):
        r = math.radians(a)
        L(d, [(330 + 12 * math.cos(r), 118 + 12 * math.sin(r)), (330 + 20 * math.cos(r), 118 + 20 * math.sin(r))], 2)
    t(d, (330, 262), "pull out: glow", 14, "ma")
    arrow(d, (380, 150), (380, 70), 4)
lines(d, 396, 130, ["grease", "the seal", "lightly"], 14, 3)
save(im, "fire_piston")

im, d = new("SUN: LENS, BOTTLE, ICE")
C(d, (60, 70), 22, 4)
for a in range(0, 360, 45):
    r = math.radians(a)
    L(d, [(60 + 28 * math.cos(r), 70 + 28 * math.sin(r)), (60 + 38 * math.cos(r), 70 + 38 * math.sin(r))], 3)
E(d, [180, 60, 200, 180], 4)                                                       # lens edge-on
for y in (76, 100, 120, 140, 164):
    L(d, [(90, y), (190, y)], 2)
    L(d, [(190, y), (300, 210)], 2)
dot(d, (300, 210), 6)
tinder(d, 300, 222, 26)
t(d, (300, 244), "smallest, brightest dot", 14, "ma")
t(d, (300, 262), "on DARK tinder", 14, "ma")
lines(d, 352, 44, ["Also works:", "water-filled", "round bottle;", "clear bag of", "water; clear ice", "shaped thick in", "the middle"], 14, 3)
save(im, "fire_lens")

im, d = new("BATTERY AND STEEL WOOL")
d.rectangle([60, 100, 150, 200], outline=G, width=4)
t(d, (105, 150), "9 V", 22, "mm")
C(d, (82, 90), 9, 3); d.rectangle([118, 82, 136, 98], outline=G, width=3)
for k in range(10):
    a = k * 0.7
    E(d, [62 + 10 * math.cos(a) + k * 6, 52 + 6 * math.sin(a), 82 + 10 * math.cos(a) + k * 6, 70 + 6 * math.sin(a)], 2)
t(d, (148, 56), "steel", 14); t(d, (148, 72), "wool", 14)
t(d, (105, 214), "touch BOTH", 14, "ma"); t(d, (105, 232), "terminals", 14, "ma")
divider(d, 220, 40, 240)
d.rectangle([250, 70, 290, 150], outline=G, width=3); d.rectangle([250, 150, 290, 230], outline=G, width=3)
d.rectangle([262, 62, 278, 70], outline=G, width=2); d.rectangle([262, 142, 278, 150], outline=G, width=2)
L(d, [(270, 62), (320, 40), (360, 40)], 2); L(d, [(270, 232), (320, 250), (360, 250)], 2)
for k in range(8):
    E(d, [350 + k * 4, 36 + k * 26, 380 + k * 4, 58 + k * 26], 2)
t(d, (270, 44), "2 x AA", 14, "ma")
t(d, (240, 262), "Fine 0000 wool. Tinder ready: it burns seconds.", 14, "ma")
save(im, "fire_steel_wool")

im, d = new("FEATHER STICK")
d.polygon([(220, 40), (260, 40), (268, 250), (212, 250)], outline=G, width=4)      # stick
for k in range(6):
    y = 120 + k * 20
    d.arc([180 - k * 2, y - 30, 240, y + 10], 90, 200, fill=G, width=3)
L(d, [(140, 240), (340, 240)], 3)                                                   # log under
arrow(d, (300, 60), (300, 200), 4)
t(d, (310, 90), "long, thin,", 15); t(d, (310, 110), "even cuts", 15)
t(d, (310, 140), "stop before", 15); t(d, (310, 160), "the curl", 15); t(d, (310, 180), "breaks off", 15)
t(d, (20, 80), "curls stay", 15); t(d, (20, 100), "attached,", 15); t(d, (20, 120), "bunched at", 15); t(d, (20, 140), "the bottom", 15)
t(d, (240, 256), "make 3 to 5, thinnest last", 14, "ma")
save(im, "fire_feather")

im, d = new("BATONING")
d.rectangle([110, 190, 330, 260], outline=G, width=4)                              # stump
d.rectangle([170, 110, 270, 190], outline=G, width=4)                              # log on end
C(d, (220, 110), 6, 2)
L(d, [(120, 104), (320, 104)], 6)                                                  # blade
d.rounded_rectangle([60, 94, 124, 114], 6, outline=G, width=3)                    # handle
d.rounded_rectangle([300, 30, 420, 56], 10, outline=G, width=4)                   # baton
arrow(d, (318, 62), (318, 96), 4)
t(d, (330, 120), "strike the TIP", 15); t(d, (330, 140), "that sticks out", 15)
t(d, (40, 128), "fixed blade", 14); t(d, (40, 146), "only", 14)
t(d, (220, 222), "stump, not stones", 14, "ma")
save(im, "fire_baton")

im, d = new("STAR FIRE")
cx, cy = 240, 160
flame(d, cx, cy + 8, 40, 20)
for k in range(5):
    a = math.radians(-90 + k * 72)
    x0, y0 = cx + 30 * math.cos(a), cy + 30 * 0.6 * math.sin(a)
    x1, y1 = cx + 190 * math.cos(a), cy + 190 * 0.6 * math.sin(a)
    L(d, [(x0, y0), (x1, y1)], 12)
    L(d, [(x0, y0), (x1, y1)], 0)
    arrow(d, (cx + 150 * math.cos(a) + 18 * math.sin(a), cy + 150 * 0.6 * math.sin(a) - 18 * math.cos(a)),
          (cx + 100 * math.cos(a) + 18 * math.sin(a), cy + 100 * 0.6 * math.sin(a) - 18 * math.cos(a)), 2, 10)
t(d, (8, 250), "push logs in as the tips burn", 15)
save(im, "fire_star")

im, d = new("LONG FIRE")
log_side(d, 30, 60, 330, 84); log_side(d, 30, 120, 330, 144)
for x in range(50, 320, 34):
    flame(d, x, 116, 26, 10)
person_lying(d, 46, 210, 260)
t(d, (340, 200), "stride", 14); t(d, (340, 216), "away", 14)
L(d, [(30, 236), (330, 236)], 6)
t(d, (180, 250), "reflector or rock behind you", 14, "ma")
lines(d, 352, 52, ["logs as long", "as you", "", "fire in the gap", "", "eats wood:", "gather lots"], 14, 3)
save(im, "fire_long")

im, d = new("SWEDISH TORCH")
# side view: log with the cross cut showing as a slot
E(d, [30, 60, 150, 92], 4)                                                         # top
L(d, [(30, 76), (30, 238)], 4); L(d, [(150, 76), (150, 238)], 4)
d.arc([30, 222, 150, 254], 0, 180, fill=G, width=4)
L(d, [(40, 76), (140, 76)], 4); L(d, [(90, 62), (90, 90)], 4)                 # cross on top
d.rectangle([86, 92, 94, 180], outline=G, width=3)                               # cut slot
dashed(d, (30, 180), (150, 180), 2)
flame(d, 90, 74, 30, 14)
arrow(d, (166, 128), (166, 80), 2); arrow(d, (166, 132), (166, 178), 2)
t(d, (174, 120), "cut", 13); t(d, (174, 136), "2/3", 13)
t(d, (90, 262), "SIDE", 14, "ma")
# top view: cross cut, tinder in the centre
C(d, (272, 140), 52, 4); C(d, (272, 140), 18, 2)
L(d, [(222, 140), (322, 140)], 6); L(d, [(272, 90), (272, 190)], 6)
dot(d, (272, 140), 9)
t(d, (272, 210), "tinder in the", 13, "ma"); t(d, (272, 226), "centre", 13, "ma")
t(d, (272, 262), "TOP", 14, "ma")
t(d, (344, 62), "Dry log,", 13); t(d, (344, 78), "20-30 cm wide,", 13); t(d, (344, 94), "40-60 cm tall.", 13)
t(d, (344, 126), "Light at the", 13); t(d, (344, 142), "top. It burns", 13); t(d, (344, 158), "down inside.", 13)
t(d, (344, 190), "A pot can sit", 13); t(d, (344, 206), "on top.", 13)
save(im, "fire_swedish")

im, d = new("KEYHOLE FIRE (top view)")
for k in range(14):
    a = math.radians(40 + k * 20)
    C(d, (140 + 80 * math.cos(a), 150 + 80 * math.sin(a)), 9, 3)
for x in range(230, 400, 22):
    C(d, (x, 120), 9, 3); C(d, (x, 180), 9, 3)
flame(d, 140, 168, 44, 22)
coals(d, 236, 390, 156, 9)
pot(d, 310, 70, 56, 26)
arrow(d, (190, 150), (240, 150), 3)
t(d, (140, 246), "fire here", 15, "ma"); t(d, (320, 210), "rake coals here,", 15, "ma"); t(d, (320, 230), "cook over them", 15, "ma")
save(im, "fire_keyhole")

im, d = new("FIRE ON SNOW OR WET GROUND")
for x in range(80, 400, 9):
    dot(d, (x, 236 + (x % 3)), 1)
L(d, [(40, 230), (440, 230)], 3)
for k in range(7):
    log_end(d, (120 + k * 40, 210), 18)
log_side(d, 100, 172, 380, 190)
flame(d, 240, 170, 54, 32)
t(d, (60, 250), "snow", 14)
t(d, (330, 40), "2 layers of green", 14, "ma"); t(d, (330, 58), "logs, crossed", 14, "ma")
arrow(d, (330, 66), (340, 150), 2)
t(d, (110, 60), "no snowy branch", 14, "ma"); t(d, (110, 78), "overhead", 14, "ma")
save(im, "fire_platform")

im, d = new("REFLECTOR WALL")
ground(d, 240)
for k in range(4):
    log_end(d, (70, 222 - k * 26), 13)
L(d, [(52, 240), (52, 100)], 4); L(d, [(88, 240), (88, 100)], 4)
flame(d, 190, 238, 50, 24)
for y in (150, 180, 210):
    arrow(d, (160, y), (100, y - 6), 2, 10)
    arrow(d, (110, y + 6), (300, y + 6), 2, 10)
d.polygon([(330, 240), (420, 120), (460, 240)], outline=G, width=4)
t(d, (70, 70), "green logs", 14, "ma"); t(d, (70, 86), "between stakes", 14, "ma")
t(d, (190, 254), "about 1 m", 14, "ma")
t(d, (400, 100), "shelter", 14, "ma")
save(im, "fire_reflector")

im, d = new("CARRY FIRE: EMBER TIN")
d.rectangle([150, 90, 330, 220], outline=G, width=4)
L(d, [(140, 90), (340, 90)], 5)
for x in range(170, 320, 30):
    dot(d, (x, 90), 3); dot(d, (150, 120 + (x - 170) // 2), 3)
d.arc([150, 40, 330, 140], 200, 340, fill=G, width=3)
for x in range(166, 320, 16):
    d.arc([x, 180, x + 20, 214], 180, 360, fill=G, width=2)
C(d, (240, 170), 14, 3, fill=G)
t(d, (380, 140), "air holes", 14, "ma")
t(d, (240, 236), "coal in dry moss, punky wood", 14, "ma"); t(d, (240, 254), "or a cramp ball", 14, "ma")
t(d, (345, 46), "wire handle", 14)
save(im, "fire_ember_tin")

im, d = new("PUT IT OUT: DROWN, STIR, FEEL")
steps = [("1", "DROWN"), ("2", "STIR"), ("3", "DROWN"), ("4", "FEEL")]
for k, (n, s) in enumerate(steps):
    x0 = 12 + k * 117
    d.rounded_rectangle([x0, 40, x0 + 108, 230], 10, outline=G, width=3)
    C(d, (x0 + 18, 58), 12, 3, fill=G); d.text((x0 + 18, 58), n, fill=K, font=f(15), anchor="mm")
    t(d, (x0 + 54, 214), s, 15, "mm")
    coals(d, x0 + 18, x0 + 90, 190, 5)
    cx = x0 + 54
    if s == "DROWN":
        for j in range(5):
            L(d, [(cx - 20 + j * 10, 90), (cx - 24 + j * 10, 160)], 2)
    elif s == "STIR":
        L(d, [(cx + 30, 92), (cx - 10, 180)], 5); circle_arrow(d, (cx, 170), 22, 200, 500, 2)
    else:
        d.rounded_rectangle([cx - 22, 110, cx + 22, 150], 10, outline=G, width=3)
        t(d, (cx, 166), "near, then touch", 11, "ma")
t(d, (240, 258), "Cold everywhere. Never bury hot coals.", 15, "ma")
save(im, "fire_out")

im, d = new("FIRE IN WIND")
for k in range(5):
    arrow(d, (10, 70 + k * 30), (80, 70 + k * 30), 3)
t(d, (12, 40), "WIND", 16)
for k in range(4):
    E(d, [100, 210 - k * 34, 150, 244 - k * 34], 4)
flame(d, 210, 240, 40, 20)
L(d, [(170, 240), (250, 240)], 3)
for k in range(5):
    dot(d, (260 + k * 26, 200 - k * 10), 3)
t(d, (330, 132), "sparks go", 14, "ma"); t(d, (330, 148), "downwind", 14, "ma")
d.polygon([(380, 244), (420, 190), (460, 244)], outline=G, width=3)
t(d, (420, 260), "not here", 13, "ma")
t(d, (125, 260), "windbreak", 14, "ma")
lines(d, 200, 40, ["low lay, small fire,", "light it with your", "back to the wind"], 14, 3)
ground(d, 246, 90, 470)
save(im, "fire_wind")


# ======================= SHELTER =======================
def tree(d, x, base, h=150, w=3, crown=40):
    L(d, [(x, base), (x, base - h)], w + 2)
    E(d, [x - crown, base - h - crown, x + crown, base - h + crown * 0.8], w)


def conifer(d, x, base, h=150, w=3):
    L(d, [(x, base), (x, base - h)], w + 1)
    for k in range(4):
        y = base - h + 10 + k * h / 5
        half = 14 + k * 14
        L(d, [(x - half, y + 24), (x, y), (x + half, y + 24)], w)


im, d = new("SITE HAZARDS")
L(d, [(8, 120), (90, 120), (130, 250)], 4)                     # cliff and slope
for k in range(4):
    E(d, [100 + k * 12, 236 - k * 4, 112 + k * 12, 246 - k * 4], 2)
t(d, (16, 96), "rockfall", 14)
L(d, [(130, 250), (230, 250)], 4)
d.arc([150, 236, 210, 262], 0, 180, fill=G, width=3)          # dry stream bed
t(d, (180, 262), "dry bed: flood", 13, "ma")
L(d, [(230, 250), (470, 120)], 4)                              # hillside
tree(d, 300, 214, 110, 3, 36)
L(d, [(300, 120), (350, 84)], 4)
cross(d, (330, 110), 8, 3)
t(d, (350, 60), "dead limb", 14)
d.polygon([(380, 169), (420, 148), (392, 128)], outline=G, width=3)   # good tent on the slope
t(d, (420, 196), "partway up:", 14, "ma"); t(d, (420, 214), "best", 14, "ma")
t(d, (180, 168), "cold air pools", 13, "ma"); t(d, (180, 184), "in hollows", 13, "ma")
save(im, "sh_hazards")

im, d = new("RAISED BED")
ground(d, 250)
for x in (60, 400):
    L(d, [(x, 250), (x, 180)], 5); L(d, [(x - 12, 168), (x, 184), (x + 12, 168)], 4)
for y in (186,):
    L(d, [(40, y), (420, y)], 6)
for x in range(70, 400, 16):
    L(d, [(x, 182), (x + 2, 192)], 3)
for x in range(70, 390, 24):
    d.arc([x, 150, x + 40, 190], 200, 340, fill=G, width=3)
d.rounded_rectangle([70, 150, 390, 166], 6, outline=G, width=2)
t(d, (230, 120), "grass a hand thick on top", 15, "ma")
t(d, (230, 100), "springy boughs under it", 15, "ma")
t(d, (230, 214), "cross sticks on 2 poles", 15, "ma")
t(d, (440, 210), "20-40", 13, "ma"); t(d, (440, 226), "cm", 13, "ma")
save(im, "sh_raised_bed")

im, d = new("HEAVY RAIN")
L(d, [(30, 240), (470, 180)], 3)                               # sloping ground
L(d, [(90, 232), (240, 96), (390, 200)], 5)                   # tarp
L(d, [(240, 96), (240, 60)], 2); L(d, [(240, 60), (300, 50)], 2)
L(d, [(258, 58), (258, 80)], 2); t(d, (300, 70), "drip line", 14)
L(d, [(120, 226), (360, 196)], 6)                              # groundsheet inside
t(d, (240, 236), "groundsheet inside the edge", 14, "ma")
d.arc([400, 180, 440, 206], 0, 180, fill=G, width=3)
t(d, (430, 150), "ditch", 14, "ma"); t(d, (430, 166), "uphill", 14, "ma")
for k in range(6):
    L(d, [(30 + k * 20, 40 + k * 6), (24 + k * 20, 60 + k * 6)], 2)
t(d, (40, 120), "steep roof", 14)
save(im, "sh_rain")

im, d = new("WICKIUP / TIPI")
apex = (200, 44)
for x in range(70, 340, 26):
    L(d, [(apex[0] + (x - 200) * 0.05, apex[1] - 8), (x, 250)], 3)
L(d, [(176, 52), (224, 52)], 4); L(d, [(180, 60), (220, 60)], 4)    # lashing
for k in range(5):
    y = 230 - k * 34
    half = 130 * (y - 44) / 206
    L(d, [(200 - half, y), (200 + half, y)], 2)
d.polygon([(180, 250), (200, 196), (220, 250)], fill=K, outline=G, width=3)
lines(d, 340, 50, ["lashed tripod", "first", "", "lean poles in", "a circle", "", "cover from the", "bottom up", "", "door away", "from wind"], 14, 1)
ground(d, 252, 8, 330)
save(im, "sh_wickiup")

im, d = new("PONCHO LEAN-TO")
L(d, [(40, 250), (40, 80)], 6); L(d, [(420, 250), (420, 80)], 6)
L(d, [(40, 140), (420, 140)], 2)
d.polygon([(90, 140), (370, 140), (400, 236), (60, 236)], outline=G, width=4)
C(d, (230, 180), 14, 3); L(d, [(222, 172), (238, 188)], 3)
t(d, (230, 204), "hood tied shut", 14, "ma")
for x in (60, 400):
    L(d, [(x, 236), (x, 252)], 3)
ground(d, 252)
t(d, (230, 112), "line at waist height", 14, "ma")
for k in range(4):
    arrow(d, (460, 60 + k * 26), (440, 60 + k * 26), 2, 8)
t(d, (440, 46), "wind", 13, "ma")
t(d, (230, 262), "low edge pegged to windward", 13, "ma")
save(im, "sh_poncho")

im, d = new("HAMMOCK AND TARP")
L(d, [(40, 260), (40, 40)], 8); L(d, [(440, 260), (440, 40)], 8)
L(d, [(40, 90), (440, 90)], 2)
L(d, [(90, 126), (240, 90), (390, 126)], 4)                       # tarp over the ridge line
L(d, [(64, 90), (64, 106)], 2); t(d, (70, 66), "drip line", 13)
L(d, [(40, 120), (110, 160)], 3); L(d, [(440, 120), (370, 160)], 3)   # suspension at 30 degrees
d.arc([110, 110, 370, 230], 0, 180, fill=G, width=5)               # hammock
d.arc([150, 140, 330, 210], 20, 160, fill=G, width=2)               # mat
t(d, (88, 168), "30 deg", 13, "ma")
t(d, (240, 236), "mat or underquilt inside", 14, "ma")
t(d, (240, 254), "trees 4-5 m apart, wide straps", 14, "ma")
save(im, "sh_hammock")

im, d = new("FALLEN TREE / ROOT BALL")
ground(d, 250)
E(d, [30, 90, 110, 250], 4)                                         # root plate
for k in range(6):
    L(d, [(70, 170), (30 + k * 16, 92 + (k % 2) * 30)], 2)
log_side(d, 100, 214, 450, 248)
for x in range(170, 420, 26):
    L(d, [(x, 216), (x + 40, 150)], 3)
t(d, (290, 120), "poles on the lee side", 14, "ma")
cross(d, (130, 70), 10, 4)
t(d, (150, 60), "NEVER cut near the root plate:", 13); t(d, (150, 78), "it can swing back up", 13)
t(d, (70, 262), "root plate", 13, "ma")
save(im, "sh_root_ball")

im, d = new("DESERT SHADE: DOUBLE ROOF")
for k in range(6):
    a = math.radians(200 + k * 28)
L(d, [(8, 240), (472, 240)], 3)
d.arc([0, 160, 140, 320], 180, 270, fill=G, width=4)                 # sand mound
L(d, [(70, 162), (420, 200)], 5)                                     # lower sheet
L(d, [(70, 122), (420, 160)], 5)                                     # upper sheet
for x in (90, 410):
    pass
L(d, [(420, 160), (430, 240)], 3); L(d, [(420, 200), (426, 240)], 2)
arrow(d, (250, 162), (250, 180), 2, 8); arrow(d, (250, 162), (250, 145), 2, 8)
t(d, (262, 156), "30-45 cm air gap", 13)
person_lying(d, 160, 230, 180)
C(d, (420, 56), 18, 3)
for a in range(0, 360, 45):
    r = math.radians(a)
    L(d, [(420 + 24 * math.cos(r), 56 + 24 * math.sin(r)), (420 + 32 * math.cos(r), 56 + 32 * math.sin(r))], 2)
t(d, (40, 60), "can be 11-22 C cooler", 15)
t(d, (40, 80), "under it (US Army)", 15)
t(d, (40, 262), "sand mound or rock", 13)
save(im, "sh_desert")

im, d = new("JUNGLE RAISED PLATFORM")
ground(d, 256)
for x in (80, 400):
    L(d, [(x, 256), (x, 50)], 6)
L(d, [(80, 170), (400, 170)], 6)
for x in range(92, 392, 14):
    L(d, [(x, 164), (x, 176)], 3)
L(d, [(60, 120), (240, 40), (420, 120)], 5)
for k in range(5):
    y = 112 - k * 16
    half = 180 - k * 36
    L(d, [(240 - half, y), (240 + half, y)], 2)
t(d, (240, 190), "bed of poles at knee to waist height", 14, "ma")
t(d, (240, 136), "steep leaf thatch", 14, "ma")
save(im, "sh_jungle")

im, d = new("SWAMP BED")
for k in range(8):
    d.arc([10 + k * 58, 236, 70 + k * 58, 256], 180, 360, fill=G, width=2)
for x in (70, 410):
    L(d, [(x, 260), (x, 40)], 7)
dashed(d, (20, 190), (460, 190), 2)
t(d, (240, 196), "high-water line (debris marks)", 13, "ma")
L(d, [(60, 150), (420, 150)], 6)
for x in range(84, 400, 14):
    L(d, [(x, 144), (x, 156)], 3)
for x in range(90, 390, 28):
    d.arc([x, 120, x + 36, 156], 200, 340, fill=G, width=2)
d.rectangle([330, 130, 390, 142], outline=G, width=2, fill=G)
t(d, (360, 96), "fire pad", 13, "ma"); L(d, [(360, 112), (360, 128)], 2)
t(d, (240, 70), "frame lashed well above it", 14, "ma")
save(im, "sh_swamp")

im, d = new("TREE-PIT SNOW SHELTER")
L(d, [(8, 120), (150, 120)], 3); L(d, [(330, 120), (472, 120)], 3)
for x in range(10, 150, 12):
    dot(d, (x, 130), 1)
L(d, [(150, 120), (170, 250), (310, 250), (330, 120)], 4)
L(d, [(240, 250), (240, 30)], 4)
for y0, half in ((40, 40), (70, 80), (100, 125)):
    L(d, [(240 - half, y0 + 26), (240, y0), (240 + half, y0 + 26)], 4)
for x in range(180, 300, 20):
    L(d, [(x, 246), (x + 14, 238)], 3)
t(d, (80, 96), "snow", 14, "ma")
t(d, (400, 150), "dig round", 14, "ma"); t(d, (400, 168), "the trunk", 14, "ma")
t(d, (400, 196), "boughs on", 14, "ma"); t(d, (400, 214), "the floor", 14, "ma")
t(d, (60, 50), "low branches", 14, "ma"); t(d, (60, 68), "are the roof", 14, "ma")
save(im, "sh_tree_pit")

im, d = new("IGLOO")
L(d, [(8, 230), (472, 230)], 3)
d.arc([60, 50, 340, 410], 180, 360, fill=G, width=5)
for k in range(1, 6):
    y = 230 - k * 30
    half = math.sqrt(max(0, 140 ** 2 - (230 - y) ** 2 * 0.62))
    L(d, [(200 - half, y + 4 * k), (200 + half, y - 4 * k)], 2)
    for j in range(-3, 4):
        x = 200 + j * 40 + (k % 2) * 20
        if abs(x - 200) < half - 10:
            L(d, [(x, y - 26), (x, y)], 2)
d.rectangle([180, 50, 220, 64], outline=G, width=3)
t(d, (240, 34), "key block", 13)
L(d, [(60, 230), (20, 230)], 0)
d.rectangle([310, 236, 450, 262], outline=G, width=3)
d.rectangle([312, 230, 336, 240], fill=K)
t(d, (400, 212), "low tunnel", 13, "ma")
d.rectangle([90, 200, 230, 230], outline=G, width=2)
t(d, (160, 214), "bench", 13, "mm")
L(d, [(226, 58), (300, 80)], 2); t(d, (304, 72), "vent", 13)
lines(d, 352, 100, ["blocks rise", "in a spiral,", "each one", "leaning in"], 14, 3)
save(im, "sh_igloo")

im, d = new("WARM ONE ROOM")
d.rectangle([40, 40, 440, 250], outline=G, width=4)
d.rectangle([150, 40, 290, 60], outline=G, width=3, fill=G)
t(d, (220, 76), "blanket over the window", 14, "ma")
d.rectangle([40, 150, 56, 230], outline=G, width=3)
d.rounded_rectangle([56, 220, 96, 232], 5, outline=G, width=2, fill=G)
t(d, (64, 160), "towel at", 13); t(d, (64, 176), "the door", 13)
d.rounded_rectangle([140, 200, 420, 236], 8, outline=G, width=3)
t(d, (280, 218), "rug or cardboard on the floor", 13, "mm")
d.polygon([(250, 196), (330, 110), (410, 196)], outline=G, width=3)
t(d, (330, 176), "den", 14, "ma")
C(d, (180, 160), 10, 3); L(d, [(180, 170), (180, 196)], 4)
C(d, (210, 160), 10, 3); L(d, [(210, 170), (210, 196)], 4)
t(d, (108, 110), "everyone in", 14, "ma"); t(d, (108, 126), "one room", 14, "ma")
save(im, "sh_warm_room")

im, d = new("CAR AS SHELTER (SNOW)")
d.polygon([(60, 200), (90, 150), (150, 110), (300, 110), (350, 150), (420, 160), (420, 200)], outline=G, width=4)
C(d, (130, 206), 22, 4); C(d, (360, 206), 22, 4)
L(d, [(170, 116), (170, 150)], 2); L(d, [(260, 116), (260, 150)], 2)
L(d, [(300, 112), (300, 124)], 0)
dashed(d, (300, 118), (330, 150), 2, 4, 4)
t(d, (360, 66), "window open", 13); t(d, (360, 82), "a crack", 13)
L(d, [(420, 196), (446, 196)], 4)
t(d, (446, 222), "exhaust", 13, "ma"); t(d, (446, 238), "CLEAR", 13, "ma")
L(d, [(110, 150), (110, 60)], 2)
d.polygon([(110, 60), (150, 70), (110, 84)], fill=G)
t(d, (60, 40), "bright cloth on the aerial", 13)
for x in range(20, 470, 9):
    dot(d, (x, 236), 1)
t(d, (240, 254), "engine + heater 10 min each hour", 15, "ma")
save(im, "sh_car")

im, d = new("LOG CABIN CORNER")
d.rectangle([40, 220, 300, 260], outline=G, width=3)
for x in range(50, 300, 30):
    L(d, [(x, 222), (x + 14, 258)], 1)
t(d, (170, 270), "stone footing", 13, "ma")
for k in range(4):
    y = 200 - k * 44
    if k % 2 == 0:
        log_side(d, 60, y - 20, 300, y + 20)
    else:
        log_end(d, (90, y), 22)
        L(d, [(112, y - 20), (300, y - 20)], 3); L(d, [(112, y + 20), (300, y + 20)], 3)
        d.arc([66, y - 46, 114, y - 6], 20, 160, fill=G, width=2)
for k in range(3):
    dots(d, (120, 178 - k * 44, 290, 184 - k * 44), 10, 2)
lines(d, 320, 50, ["saddle notch:", "curved cut under", "the upper log", "sits over the", "one below", "", "chink gaps:", "moss, then clay"], 14, 3)
save(im, "sh_log_cabin")

im, d = new("WATTLE AND DAUB")
for x in range(60, 220, 30):
    L(d, [(x, 40), (x, 250)], 5)
for k in range(9):
    y = 50 + k * 22
    pts = [(50 + j * 15, y + (6 if (j + k) % 2 else -6)) for j in range(13)]
    d.line(pts, fill=G, width=3)
t(d, (140, 262), "wattle: rods woven", 13, "ma")
d.rectangle([270, 40, 330, 250], outline=G, width=3)
hatch(d, (270, 40, 330, 250), 12, 2)
for x in (285, 300, 315):
    L(d, [(x, 46), (x, 244)], 1)
lines(d, 340, 60, ["daub: clay,", "sand, straw", "", "press into", "BOTH sides", "", "dry slowly,", "limewash"], 14, 3)
arrow(d, (240, 140), (266, 140), 3)
save(im, "sh_wattle")

im, d = new("THATCHING")
L(d, [(40, 250), (240, 50), (440, 250)], 4)                      # rafters
for k in range(1, 9):
    x, y = 40 + k * 22, 250 - k * 22
    dot(d, (x + 3, y + 3), 3)                                   # battens
for k in range(8):
    f0, f1 = k / 8.0, min(1.0, k / 8.0 + 0.28)
    a = (40 + 200 * f0 - 10, 250 - 200 * f0 - 10)
    b = (40 + 200 * f1 - 10, 250 - 200 * f1 - 10)
    L(d, [(a[0] - 16, a[1] + 4), b], 7)
d.arc([200, 30, 280, 74], 180, 360, fill=G, width=6)
t(d, (290, 34), "ridge cap", 14)
lines(d, 330, 70, ["rows from the", "eaves UP; each", "covers the", "fixings below"], 14, 3)
t(d, (240, 200), "battens", 13, "ma")
t(d, (240, 262), "steep: 45-55 degrees, a forearm thick", 14, "ma")
save(im, "sh_thatch")

# ======================= WATER =======================
def bottle(d, x, y, w=30, h=70, fill_to=None):
    d.rounded_rectangle([x, y + 16, x + w, y + h], 6, outline=G, width=3)
    d.rectangle([x + w * 0.3, y, x + w * 0.7, y + 16], outline=G, width=3)
    if fill_to is not None:
        d.rectangle([x + 4, y + h - fill_to, x + w - 4, y + h - 4], fill=G)


im, d = new("WATER PER PERSON PER DAY")
for k in range(3):
    bottle(d, 40 + k * 44, 80, 34, 90, 70)
t(d, (102, 186), "3 litres", 18, "ma"); t(d, (102, 210), "to drink", 15, "ma"); t(d, (102, 228), "(survive)", 15, "ma")
divider(d, 210, 50, 240)
for k in range(10):
    bottle(d, 230 + (k % 5) * 46, 52 + (k // 5) * 74, 30, 64, 46)
t(d, (340, 206), "about 10 litres", 18, "ma"); t(d, (340, 230), "drink, cook, wash", 15, "ma")
t(d, (240, 258), "More in heat, work, illness. Pee pale straw.", 15, "ma")
save(im, "wt_needs")

im, d = new("WATER INSIDE A HOUSE")
d.polygon([(20, 260), (20, 110), (150, 40), (280, 110), (280, 260)], outline=G, width=4)
L(d, [(20, 180), (280, 180)], 3)
d.rounded_rectangle([40, 120, 80, 172], 10, outline=G, width=3)          # cylinder upstairs
L(d, [(60, 172), (60, 178)], 3)
t(d, (60, 106), "hot tank", 12, "ma")
d.rectangle([180, 140, 220, 160], outline=G, width=3); L(d, [(200, 160), (200, 176)], 3)   # cistern + toilet
t(d, (200, 124), "cistern", 12, "ma")
dot(d, (250, 130), 4); t(d, (250, 112), "top tap", 12, "ma")
dot(d, (60, 240), 4); t(d, (60, 222), "lowest tap", 12, "ma")
d.rectangle([200, 206, 260, 226], outline=G, width=2)
for x in range(206, 258, 10):
    L(d, [(x, 208), (x, 224)], 1)
cross(d, (230, 194), 8, 3); t(d, (230, 232), "radiator", 12, "ma")
lines(d, 296, 44, ["1. Boiler and", "   immersion OFF,", "   cool, drain tank", "2. Open top tap,", "   then run the", "   lowest tap", "3. Cistern, not", "   the bowl", "4. NEVER radiators", "Treat all of it."], 14, 3)
save(im, "wt_home")

im, d = new("SEEP AND BEACH WELL")
divider(d, 240)
d.arc([20, 60, 220, 220], 200, 340, fill=G, width=4)                    # river bend top view
d.arc([50, 90, 190, 200], 200, 340, fill=G, width=4)
C(d, (120, 54), 12, 4, fill=G)
t(d, (120, 120), "dig on the", 14, "ma"); t(d, (120, 138), "OUTSIDE of", 14, "ma"); t(d, (120, 156), "the bend", 14, "ma")
t(d, (120, 230), "dry stream bed", 14, "ma"); t(d, (120, 248), "(top view)", 13, "ma")
L(d, [(250, 220), (300, 220)], 3)
d.arc([290, 150, 380, 290], 180, 360, fill=G, width=4)                  # dune
L(d, [(380, 220), (400, 220), (410, 250), (430, 250), (440, 220), (470, 220)], 3)
dashed(d, (404, 236), (436, 236), 2, 4, 3)
for x in range(250, 300, 8):
    d.arc([x, 214, x + 8, 226], 180, 360, fill=G, width=2)
t(d, (270, 196), "sea", 14, "ma"); t(d, (335, 190), "1st dune", 13, "ma")
t(d, (420, 168), "dig behind", 13, "ma"); t(d, (420, 184), "it, ~1 m", 13, "ma")
t(d, (360, 262), "take only the top water", 13, "ma")
save(im, "wt_seep")

im, d = new("TRANSPIRATION BAG")
L(d, [(20, 60), (200, 90)], 6)                                          # branch
for k in range(7):
    x = 200 + k * 30
    E(d, [x - 10, 110 + (k % 2) * 14, x + 18, 128 + (k % 2) * 14], 3)
    L(d, [(200 + k * 22, 96 + k * 4), (x + 4, 118 + (k % 2) * 14)], 2)
L(d, [(200, 90), (380, 120)], 4)
d.polygon([(190, 70), (440, 100), (430, 220), (360, 250), (190, 110)], outline=G, width=3)
L(d, [(186, 72), (194, 108)], 5)
E(d, [356, 228, 380, 248], 3, fill=G)
for k in range(6):
    dot(d, (240 + k * 30, 170 + (k % 2) * 12), 3)
t(d, (90, 110), "tie it tight", 14, "ma"); t(d, (90, 128), "round the branch", 14, "ma")
t(d, (300, 262), "stone in the low corner: water collects", 13, "ma")
t(d, (60, 200), "full sun", 14, "ma"); t(d, (60, 218), "0.5-1 L/day", 14, "ma")
save(im, "wt_transpiration")

im, d = new("ROOF RAIN: FIRST FLUSH")
d.polygon([(20, 110), (140, 40), (260, 110)], outline=G, width=4)
L(d, [(240, 112), (300, 112)], 4)                                       # gutter
L(d, [(296, 112), (296, 150)], 5)                                       # downpipe
L(d, [(296, 150), (296, 250)], 5)                                       # diverter pipe down
d.rectangle([288, 250, 304, 258], fill=G)
t(d, (250, 270), "cap: empty after rain", 12, "ma")
L(d, [(296, 150), (360, 150), (360, 170)], 5)
d.rectangle([340, 170, 460, 260], outline=G, width=4)
L(d, [(336, 170), (464, 170)], 5)
t(d, (400, 214), "covered", 14, "ma"); t(d, (400, 232), "tank", 14, "ma")
t(d, (226, 186), "first, dirty", 13, "ra"); t(d, (226, 202), "rain fills", 13, "ra"); t(d, (226, 218), "this pipe", 13, "ra")
t(d, (400, 110), "then clean", 13, "ma"); t(d, (400, 126), "water flows on", 13, "ma")
t(d, (20, 150), "about 0.5 L per m2", 13); t(d, (20, 166), "of roof", 13)
t(d, (300, 70), "mesh", 13); L(d, [(298, 86), (298, 104)], 2)
save(im, "wt_first_flush")

im, d = new("CLOTH FILTER")
for k in range(5):
    L(d, [(60 + k * 4, 70 + k * 6), (200 - k * 4, 70 + k * 6)], 3)
t(d, (130, 46), "fold 4-8 layers", 15, "ma")
d.polygon([(260, 120), (420, 120), (410, 250), (270, 250)], outline=G, width=4)
d.arc([250, 100, 430, 150], 0, 180, fill=G, width=4)
L(d, [(256, 126), (424, 126)], 3)
L(d, [(250, 130), (270, 140)], 3); L(d, [(430, 130), (410, 140)], 3)
d.rectangle([276, 200, 404, 246], fill=G)
d.polygon([(300, 40), (370, 40), (380, 70), (330, 100)], outline=G, width=3)
for k in range(3):
    L(d, [(336 + k * 6, 100 + k * 2), (338 + k * 6, 116)], 2)
t(d, (130, 140), "tie over the", 14, "ma"); t(d, (130, 158), "container,", 14, "ma"); t(d, (130, 176), "pour slowly", 14, "ma")
t(d, (130, 214), "Then BOIL", 15, "ma"); t(d, (130, 234), "or treat it.", 15, "ma")
save(im, "wt_cloth")

im, d = new("BIOSAND FILTER")
d.rectangle([60, 40, 220, 260], outline=G, width=4)
layers = [(232, 260, "gravel 5 cm"), (212, 232, "coarse sand 5 cm"), (110, 212, "fine sand ~50 cm"), (90, 110, "water 5 cm")]
for y0, y1, lab in layers:
    L(d, [(60, y0), (220, y0)], 2)
dots(d, (64, 236, 216, 258), 10, 3)
dots(d, (64, 214, 216, 230), 8, 1)
dots(d, (64, 112, 216, 210), 14, 1)
d.rectangle([70, 70, 210, 80], outline=G, width=3)
for x in range(80, 205, 16):
    dot(d, (x, 75), 2)
L(d, [(140, 252), (240, 252), (240, 96), (280, 96)], 4)
d.polygon([(280, 92), (290, 100), (280, 108)], fill=G)
for (y0, y1, lab) in layers:
    t(d, (300, (y0 + y1) / 2 - 8), lab, 14)
t(d, (300, 60), "plate with holes", 14)
L(d, [(296, 68), (214, 74)], 1)
t(d, (250, 180), "outlet pipe", 14)
t(d, (232, 34), "still boil or chlorinate", 13)
save(im, "wt_biosand")

im, d = new("DISTIL WITH A POT")
coals(d, 80, 300, 252, 12)
d.rectangle([90, 120, 290, 240], outline=G, width=4)
for x in range(100, 290, 18):
    d.arc([x, 196, x + 18, 210], 180, 360, fill=G, width=2)
L(d, [(80, 120), (300, 120)], 0)
d.polygon([(80, 118), (190, 150), (300, 118)], outline=G, width=4)
L(d, [(190, 150), (190, 162)], 5)
d.rectangle([170, 170, 210, 196], outline=G, width=3)
for k in range(3):
    dot(d, (190, 160 + k * 4), 2)
for k in range(4):
    smoke(d, 120 + k * 46, 190, 40)
t(d, (310, 100), "lid upside down,", 14); t(d, (310, 118), "handle down", 14)
t(d, (310, 164), "cup catches", 14); t(d, (310, 182), "the drips", 14)
t(d, (310, 220), "bad or salty", 14); t(d, (310, 238), "water below", 14)
t(d, (40, 44), "cool the lid with snow or wet cloth", 14)
save(im, "wt_distil")

# ======================= FOOD =======================
def leaf(d, c, length=60, width=22, angle=0, w=3, vein=True):
    """Pointed oval leaf centred at c, rotated by angle degrees."""
    a = math.radians(angle)
    pts = []
    for k in range(25):
        u = -1 + 2 * k / 24
        v = math.sqrt(max(0.0, 1 - u * u)) * (1 - 0.35 * u)
        pts.append((u * length / 2, v * width / 2))
    pts += [(x, -y) for x, y in reversed(pts)]
    rot = [(c[0] + x * math.cos(a) - y * math.sin(a), c[1] + x * math.sin(a) + y * math.cos(a)) for x, y in pts]
    d.polygon(rot, outline=G, width=w)
    if vein:
        L(d, [(c[0] - length / 2 * math.cos(a), c[1] - length / 2 * math.sin(a)), (c[0] + length / 2 * math.cos(a), c[1] + length / 2 * math.sin(a))], 2)


def arrow_leaf(d, tip, h=110, half=40, sheath=False, spots=False):
    x, y = tip
    d.polygon([(x, y), (x + half, y + h * 0.7), (x + half * 0.9, y + h), (x + 8, y + h * 0.78),
               (x - 8, y + h * 0.78), (x - half * 0.9, y + h), (x - half, y + h * 0.7)], outline=G, width=3)
    L(d, [(x, y + 10), (x, y + h * 0.78)], 2)
    L(d, [(x, y + h * 0.78), (x, y + h + 50)], 4)
    if sheath:
        d.rectangle([x - 6, y + h + 8, x + 6, y + h + 30], outline=G, width=2)
    if spots:
        for k in range(5):
            dot(d, (x - 18 + k * 9, y + 50 + (k % 2) * 14), 3)


im, d = new("FORAGING YEAR (UK)")
C(d, (240, 154), 96, 4)
L(d, [(240, 58), (240, 250)], 3); L(d, [(144, 154), (336, 154)], 3)
t(d, (200, 110), "SPRING", 14, "ma"); t(d, (282, 110), "SUMMER", 14, "ma")
t(d, (282, 192), "AUTUMN", 14, "ma"); t(d, (200, 192), "WINTER", 14, "ma")
lines(d, 8, 44, ["Mar-May:", "nettle, wild", "garlic, cleavers,", "dandelion,", "sorrel, chickweed"], 13, 2)
lines(d, 348, 44, ["Jun-Aug:", "elderflower,", "samphire,", "bilberry, first", "blackberries"], 13, 2)
lines(d, 348, 178, ["Sep-Nov:", "berries, hips,", "haws, sloes,", "all the nuts,", "acorns, apples"], 13, 2)
lines(d, 8, 178, ["Dec-Feb:", "chickweed, sea", "beet, seaweed,", "mussels, roots,", "stored nuts"], 13, 2)
save(im, "fd_calendar")

im, d = new("YEW: ALL PARTS DEADLY")
L(d, [(30, 150), (450, 120)], 4)
for k in range(14):
    x = 50 + k * 28
    y = 150 - (x - 30) * 30 / 420
    L(d, [(x, y), (x - 6, y - 40)], 4)
    L(d, [(x, y), (x - 6, y + 40)], 4)
for cx in (170, 330):
    cy = 150 - (cx - 30) * 30 / 420 + 70
    C(d, (cx, cy), 18, 4)
    dot(d, (cx, cy), 7)
    L(d, [(cx, cy - 18), (cx, cy - 66)], 2)
t(d, (240, 40), "flat needles in two rows", 15, "ma")
t(d, (250, 250), "red cups with a dark, deadly seed", 15, "ma")
save(im, "fd_yew")

im, d = new("DEADLY NIGHTSHADE vs BILBERRY")
divider(d, 240)
C(d, (120, 120), 30, 5)
for k in range(5):
    a = math.radians(90 + k * 72)
    d.polygon([(120 + 18 * math.cos(a - 0.5), 120 + 18 * math.sin(a - 0.5)),
               (120 + 62 * math.cos(a), 120 + 62 * math.sin(a)),
               (120 + 18 * math.cos(a + 0.5), 120 + 18 * math.sin(a + 0.5))], outline=G, width=3)
C(d, (120, 120), 30, 5, fill=K); C(d, (120, 120), 30, 5)
d.arc([100, 100, 124, 124], 200, 280, fill=G, width=3)
t(d, (120, 196), "SHINY, alone in a", 14, "ma"); t(d, (120, 214), "green 5-point star", 14, "ma")
t(d, (120, 236), "soft plant to 1.5 m", 14, "ma"); t(d, (120, 258), "DEADLY", 16, "ma")
for k, (cx, cy) in enumerate(((330, 110), (380, 130))):
    C(d, (cx, cy), 18, 4)
    for j in range(5):
        a = math.radians(-90 + j * 72)
        dot(d, (cx + 6 * math.cos(a), cy - 10 + 4 * math.sin(a)), 2)
L(d, [(270, 170), (440, 150)], 3)
leaf(d, (300, 186), 30, 14, -10)
t(d, (360, 196), "dusty bloom, crown", 14, "ma"); t(d, (360, 214), "on top, purple inside", 14, "ma")
t(d, (360, 236), "low shrub on heath", 14, "ma"); t(d, (360, 258), "bilberry", 16, "ma")
save(im, "fd_nightshade")

im, d = new("LORDS-AND-LADIES (CUCKOO PINT)")
arrow_leaf(d, (90, 50), 110, 46, spots=True)
t(d, (90, 236), "glossy, spotted,", 13, "ma"); t(d, (90, 252), "arrow leaf", 13, "ma")
d.polygon([(240, 50), (276, 120), (262, 200), (240, 214), (218, 200), (204, 120)], outline=G, width=3)
E(d, [232, 96, 248, 170], 3, fill=G)
L(d, [(240, 214), (240, 230)], 3)
t(d, (240, 240), "hood + club", 13, "ma"); t(d, (240, 256), "April-May", 13, "ma")
L(d, [(390, 230), (390, 70)], 3)
for k in range(9):
    C(d, (380 + (k % 2) * 20, 80 + k * 12), 8, 3, fill=G if k % 3 == 0 else None)
t(d, (390, 240), "orange-red berry", 13, "ma"); t(d, (390, 256), "spike, late summer", 13, "ma")
save(im, "fd_arum")

im, d = new("SORREL vs LORDS-AND-LADIES")
divider(d, 240)
arrow_leaf(d, (120, 44), 100, 34, sheath=True)
L(d, [(86, 114), (70, 150)], 3); L(d, [(154, 114), (170, 150)], 3)
t(d, (120, 214), "lobes point back,", 13, "ma"); t(d, (120, 230), "papery sheath round", 13, "ma"); t(d, (120, 246), "the stem; meadows", 13, "ma")
t(d, (190, 170), "sheath", 13, "ma")
arrow_leaf(d, (360, 44), 110, 50, spots=True)
t(d, (360, 214), "glossy, often spotted,", 13, "ma"); t(d, (360, 230), "no sheath; shady", 13, "ma"); t(d, (360, 246), "hedges: POISON", 13, "ma")
save(im, "fd_sorrel")

im, d = new("CHICKWEED")
L(d, [(30, 200), (450, 160)], 4)
for k, x in enumerate((90, 200, 310, 410)):
    y = 200 - (x - 30) * 40 / 420
    leaf(d, (x, y - 26), 50, 22, -70, 3, False)
    leaf(d, (x, y + 26), 50, 22, 70, 3, False)
    seg = (x + 30, y - 3)
    for j in range(5):
        dot(d, (x + 12 + j * 9, y - 6 - j * 0.9 + (0 if k % 2 == 0 else 12)), 2)
cx, cy = 160, 76
for k in range(10):
    a = math.radians(k * 36)
    E(d, [cx + 22 * math.cos(a) - 8, cy + 22 * math.sin(a) - 4, cx + 22 * math.cos(a) + 8, cy + 22 * math.sin(a) + 4], 2)
C(d, (cx, cy), 7, 2, fill=G)
t(d, (200, 50), "5 petals, split to look like 10", 13)
t(d, (240, 236), "one line of hairs, swaps side at each leaf pair", 13, "ma")
t(d, (240, 256), "stem has a stretchy core when pulled", 13, "ma")
save(im, "fd_chickweed")

im, d = new("ELDER")
L(d, [(60, 260), (70, 140), (110, 60)], 6)
for y in range(150, 256, 18):
    L(d, [(58, y), (76, y + 4)], 2)
t(d, (24, 266), "corky bark", 12)
L(d, [(110, 120), (200, 120)], 3)
for k in range(3):
    leaf(d, (130 + k * 28, 100), 30, 12, -80, 2, False)
    leaf(d, (130 + k * 28, 140), 30, 12, 80, 2, False)
leaf(d, (214, 120), 30, 12, 0, 2, False)
t(d, (160, 164), "5-7 leaflets", 13, "ma")
d.arc([240, 40, 340, 90], 180, 360, fill=G, width=3)
dots(d, (250, 50, 330, 70), 9, 2)
t(d, (290, 98), "flat cream", 13, "ma"); t(d, (290, 114), "flowers, June", 13, "ma")
L(d, [(400, 50), (400, 80)], 3)
for k in range(12):
    dot(d, (380 + (k % 4) * 13, 92 + (k // 4) * 14 + (k % 4) * 3), 5)
t(d, (410, 150), "drooping berries", 13, "ma"); t(d, (410, 166), "COOK them", 13, "ma")
t(d, (330, 210), "a woody shrub,", 13, "ma"); t(d, (330, 226), "not a soft plant", 13, "ma")
save(im, "fd_elder")

im, d = new("SWEET CHESTNUT vs HORSE CHESTNUT")
divider(d, 240)
leaf(d, (60, 110), 120, 34, -60, 3)
for k in range(8):
    u = -0.4 + k * 0.12
    pass
C(d, (170, 90), 32, 3)
for k in range(24):
    a = math.radians(k * 15)
    L(d, [(170 + 32 * math.cos(a), 90 + 32 * math.sin(a)), (170 + 46 * math.cos(a), 90 + 46 * math.sin(a))], 2)
d.polygon([(150, 200), (170, 160), (190, 200)], outline=G, width=3)
L(d, [(170, 160), (170, 150)], 2); L(d, [(170, 150), (164, 144)], 1); L(d, [(170, 150), (176, 144)], 1)
t(d, (120, 214), "SWEET: eat", 15, "ma"); t(d, (120, 234), "long toothed leaf, spiny", 12, "ma"); t(d, (120, 250), "case, pointed nut + tassel", 12, "ma")
for k in range(6):
    a = math.radians(-150 + k * 24)
    leaf(d, (300 + 34 * math.cos(a), 100 + 34 * math.sin(a)), 54, 18, k * 24 - 150, 2, False)
C(d, (400, 90), 30, 3)
for a in range(0, 360, 60):
    r = math.radians(a)
    L(d, [(400 + 30 * math.cos(r), 90 + 30 * math.sin(r)), (400 + 40 * math.cos(r), 90 + 40 * math.sin(r))], 3)
C(d, (400, 180), 20, 4)
d.arc([386, 166, 414, 194], 200, 260, fill=G, width=2)
t(d, (360, 214), "HORSE: poison", 15, "ma"); t(d, (360, 234), "hand leaf, few spikes,", 12, "ma"); t(d, (360, 250), "round shiny conker", 12, "ma")
save(im, "fd_chestnuts")

im, d = new("ACORNS: LEACH OUT THE BITTER")
steps = [("1", "shell", "and crush"), ("2", "boil, pour", "off brown"), ("3", "repeat", "5-10 times"), ("4", "dry and", "grind")]
for k, (n, a1, a2) in enumerate(steps):
    x0 = 12 + k * 117
    d.rounded_rectangle([x0, 40, x0 + 108, 220], 10, outline=G, width=3)
    C(d, (x0 + 18, 58), 12, 3, fill=G); d.text((x0 + 18, 58), n, fill=K, font=f(15), anchor="mm")
    cx = x0 + 54
    if k == 0:
        E(d, [cx - 14, 86, cx + 14, 126], 3); d.arc([cx - 16, 78, cx + 16, 100], 180, 360, fill=G, width=4)
        for j in range(4):
            dot(d, (cx - 18 + j * 12, 146), 4)
    elif k in (1, 2):
        pot(d, cx, 100, 60, 40)
        for j in range(3):
            smoke(d, cx - 16 + j * 16, 96, 20)
        if k == 2:
            circle_arrow(d, (cx, 150), 18, 200, 500, 2)
    else:
        d.rectangle([cx - 30, 100, cx + 30, 130], outline=G, width=3)
        dots(d, (cx - 28, 102, cx + 28, 128), 8, 1)
    t(d, (cx, 176), a1, 13, "ma"); t(d, (cx, 194), a2, 13, "ma")
t(d, (240, 240), "Ready when a taste is bland, not bitter.", 15, "ma")
save(im, "fd_acorn")

im, d = new("MUSSELS: ALIVE, THEN OPEN")
def mussel(cx, cy, open_=False):
    if open_:
        E(d, [cx - 50, cy - 40, cx + 2, cy + 6], 3); E(d, [cx - 2, cy - 40, cx + 50, cy + 6], 3)
        dot(d, (cx - 22, cy - 18), 6); dot(d, (cx + 22, cy - 18), 6)
    else:
        E(d, [cx - 50, cy - 20, cx + 50, cy + 20], 4)
        L(d, [(cx - 44, cy), (cx + 44, cy)], 2)
divider(d, 240, 40, 240)
mussel(120, 80); t(d, (120, 112), "BEFORE: closed", 14, "ma"); t(d, (120, 130), "or shuts when tapped", 13, "ma")
mussel(120, 200, True); cross(d, (120, 186), 14, 4); t(d, (120, 226), "open before: bin", 13, "ma")
mussel(360, 80, True); t(d, (360, 112), "AFTER: open", 14, "ma"); t(d, (360, 130), "steam 3-5 min", 13, "ma")
mussel(360, 200); cross(d, (360, 200), 14, 4); t(d, (360, 226), "shut after: bin", 13, "ma")
t(d, (240, 258), "Cooking does not remove algae toxins.", 14, "ma")
save(im, "fd_mussels")

im, d = new("PUFFBALL: CUT EVERY ONE")
for k, (cx, lab1, lab2) in enumerate(((84, "pure white", "inside: OK"), (240, "mushroom shape", "inside: DEADLY"), (396, "dark inside:", "earthball, NO"))):
    C(d, (cx, 130), 62, 4)
    L(d, [(cx, 68), (cx, 192)], 0)
    if k == 1:
        E(d, [cx - 30, 92, cx + 30, 126], 3)
        L(d, [(cx - 8, 124), (cx - 8, 176)], 3); L(d, [(cx + 8, 124), (cx + 8, 176)], 3)
        for j in range(5):
            L(d, [(cx - 24 + j * 12, 118), (cx - 22 + j * 12, 124)], 1)
    if k == 2:
        for j in range(-4, 5):
            L(d, [(cx - 40 + abs(j) * 4, 130 + j * 9), (cx + 40 - abs(j) * 4, 130 + j * 9)], 3)
    t(d, (cx, 206), lab1, 14, "ma"); t(d, (cx, 224), lab2, 14, "ma")
    if k == 0:
        t(d, (cx, 130), "solid", 14, "mm")
    if k:
        cross(d, (cx + 46, 72), 9, 3)
t(d, (240, 254), "Slice top to bottom. Leave small ones.", 15, "ma")
save(im, "fd_puffball")

im, d = new("CHANTERELLE: RIDGES, NOT GILLS")
divider(d, 240)
for k, cx in enumerate((120, 360)):
    d.polygon([(cx - 80, 70), (cx + 80, 70), (cx + 16, 140), (cx + 16, 230), (cx - 16, 230), (cx - 16, 140)], outline=G, width=4)
    if k == 0:
        for j in range(-3, 4):
            d.line([(cx + j * 20, 76), (cx + j * 10, 110), (cx + j * 4, 150)], fill=G, width=2)
            d.line([(cx + j * 10, 110), (cx + j * 14, 140)], fill=G, width=1)
    else:
        for j in range(-12, 13):
            L(d, [(cx + j * 6, 74), (cx + j * 1.2, 138)], 1)
t(d, (120, 240), "blunt, forked ridges", 14, "ma"); t(d, (120, 258), "run down the stem", 14, "ma")
t(d, (360, 240), "thin crowded gills:", 14, "ma"); t(d, (360, 258), "webcap, false: NO", 14, "ma")
save(im, "fd_chanterelle")

# ======================= NAVIGATION =======================
def stick_person(d, x, base, h=60, w=3):
    head = h * 0.16
    C(d, (x, base - h + head), head, w)
    L(d, [(x, base - h + 2 * head), (x, base - h * 0.4)], w)
    L(d, [(x, base - h * 0.4), (x - h * 0.15, base)], w)
    L(d, [(x, base - h * 0.4), (x + h * 0.15, base)], w)
    L(d, [(x - h * 0.2, base - h * 0.62), (x + h * 0.2, base - h * 0.62)], w)


def sun(d, c, r=16, w=3):
    C(d, c, r, w)
    for k in range(8):
        a = math.radians(k * 45)
        L(d, [(c[0] + (r + 4) * math.cos(a), c[1] + (r + 4) * math.sin(a)), (c[0] + (r + 12) * math.cos(a), c[1] + (r + 12) * math.sin(a))], 2)


im, d = new("DIGITAL WATCH: DRAW THE CLOCK")
d.rounded_rectangle([16, 70, 140, 140], 10, outline=G, width=3)
t(d, (78, 105), "16:00", 30, "mm")
t(d, (78, 158), "BST summer", 14, "ma"); t(d, (78, 176), "(use 1 o'clock)", 13, "ma")
arrow(d, (148, 105), (196, 105), 3)
cx, cy, r = 320, 150, 100
C(d, (cx, cy), r, 3)
for h in range(12):
    a = math.radians(h * 30 - 90)
    L(d, [(cx + (r - 8) * math.cos(a), cy + (r - 8) * math.sin(a)), (cx + r * math.cos(a), cy + r * math.sin(a))], 3)
a4 = math.radians(4 * 30 - 90)
arrow(d, (cx, cy), (cx + 70 * math.cos(a4), cy + 70 * math.sin(a4)), 5, 14)
a1 = math.radians(1 * 30 - 90)
dashed(d, (cx, cy), (cx + 88 * math.cos(a1), cy + 88 * math.sin(a1)), 3)
t(d, (cx + 102 * math.cos(a1) + 4, cy + 102 * math.sin(a1)), "1", 15, "lm")
ah = math.radians(2.5 * 30 - 90)
arrow(d, (cx, cy), (cx + 96 * math.cos(ah), cy + 96 * math.sin(ah)), 4, 14)
t(d, (cx + 108 * math.cos(ah), cy + 108 * math.sin(ah) + 10), "S", 22, "lm")
sun(d, (cx + 136 * math.cos(a4), cy + 120 * math.sin(a4) + 20), 10)
t(d, (78, 214), "hour hand at sun,", 13, "ma"); t(d, (78, 232), "halfway to 1 is", 13, "ma"); t(d, (78, 250), "south", 13, "ma")
save(im, "nav_digital")

im, d = new("MOON: LIT SIDE FACES THE SUN")
divider(d, 240, 34, 196)
for x0 in (16, 256):
    ground(d, 166, x0, x0 + 208)
    t(d, (x0 + 4, 172), "E", 16); t(d, (x0 + 104, 172), "S", 16, "ma"); t(d, (x0 + 190, 172), "W", 16)
C(d, (120, 84), 30, 3); d.pieslice([90, 54, 150, 114], -90, 90, fill=G)
t(d, (120, 124), "evening, waxing:", 14, "ma"); t(d, (120, 142), "lit side west", 14, "ma")
C(d, (360, 84), 30, 3); d.pieslice([330, 54, 390, 114], 90, 270, fill=G)
t(d, (360, 124), "before dawn, waning:", 14, "ma"); t(d, (360, 142), "lit side east", 14, "ma")
t(d, (240, 200), "(facing south in the UK)", 13, "ma")
t(d, (240, 222), "Crescent: a line through the two tips, down", 14, "ma")
t(d, (240, 242), "to the horizon, is roughly south.", 14, "ma")
save(im, "nav_moon")

im, d = new("STARS: RISING = EAST, SINKING = WEST")
ground(d, 250)
L(d, [(70, 250), (70, 190)], 5); L(d, [(170, 250), (170, 170)], 5)
dashed(d, (40, 200), (460, 110), 2)
C(d, (60, 196), 8, 2)
t(d, (24, 150), "your eye", 13)
dot(d, (330, 138), 6)
arrow(d, (350, 124), (380, 90), 3); t(d, (360, 66), "up: EAST", 15)
arrow(d, (350, 150), (380, 186), 3); t(d, (360, 192), "down: WEST", 15)
arrow(d, (320, 156), (290, 186), 2)
t(d, (250, 210), "sideways: N or S", 13, "ma")
t(d, (190, 56), "two sticks as a gun sight", 14, "ma"); t(d, (190, 74), "wait 15-20 minutes", 14, "ma")
save(im, "nav_rise_set")

im, d = new("IMPROVISED COMPASS")
divider(d, 200)
L(d, [(24, 130), (176, 130)], 4); C(d, (24, 130), 4, 2)
t(d, (24, 140), "eye", 12); t(d, (150, 140), "point", 12)
d.rectangle([50, 92, 90, 126], outline=G, width=3); t(d, (70, 109), "M", 15, "mm")
arrow(d, (96, 100), (170, 100), 3, 10)
t(d, (100, 60), "magnet slides", 13, "ma"); t(d, (100, 76), "eye to point", 13, "ma")
t(d, (100, 180), "stroke ONE way,", 14, "ma"); t(d, (100, 198), "30-50 times,", 14, "ma"); t(d, (100, 216), "lift clear", 14, "ma")
E(d, [230, 120, 450, 200], 4)
E(d, [250, 132, 430, 188], 2)
leaf(d, (340, 160), 90, 34, 0, 3, False)
L(d, [(270, 160), (410, 160)], 4)
t(d, (414, 150), "N", 18); t(d, (252, 150), "S", 18)
t(d, (340, 60), "float on a leaf in still water,", 14, "ma")
t(d, (340, 80), "out of the wind", 14, "ma")
t(d, (340, 220), "check which end is north", 14, "ma"); t(d, (340, 238), "with the sun or stars", 14, "ma")
save(im, "nav_needle")

im, d = new("RESECTION: CROSS THE BEARINGS")
d.rectangle([12, 36, 468, 276], outline=G, width=2)
for x in range(12, 468, 76):
    L(d, [(x, 36), (x, 276)], 1)
for y in range(36, 276, 60):
    L(d, [(12, y), (468, y)], 1)
d.polygon([(60, 90), (80, 56), (100, 90)], outline=G, width=3); t(d, (40, 96), "summit", 13)
L(d, [(410, 50), (410, 100)], 3); L(d, [(398, 100), (410, 50), (422, 100)], 2); t(d, (380, 104), "mast", 13)
d.rectangle([400, 220, 430, 250], outline=G, width=3); L(d, [(415, 220), (415, 200)], 3); L(d, [(408, 208), (422, 208)], 3); t(d, (380, 254), "church", 13)
P = (230, 180)
for a in ((80, 80), (410, 82), (415, 232)):
    ux, uy = P[0] - a[0], P[1] - a[1]
    L(d, [a, (a[0] + ux * 1.18, a[1] + uy * 1.18)], 3)
d.polygon([(222, 174), (240, 176), (228, 190)], outline=G, width=2)
t(d, (180, 214), "you: inside the", 14, "ma"); t(d, (180, 232), "small triangle", 14, "ma")
save(im, "nav_resection")

im, d = new("ROUTE CARD (NAISMITH)")
cols = [12, 70, 150, 230, 300, 380, 468]
heads = ["leg", "bearing", "km", "climb", "min", "reach"]
rows = [["1", "045", "1.5", "50 m", "23", "wall"], ["2", "110", "2.0", "200 m", "44", "top"], ["3", "200", "2.5", "0", "30", "road"]]
for k, hd in enumerate(heads):
    t(d, ((cols[k] + cols[k + 1]) / 2, 54), hd, 14, "ma")
for r, row in enumerate(rows):
    y = 80 + r * 36
    for k, v in enumerate(row):
        t(d, ((cols[k] + cols[k + 1]) / 2, y + 8), v, 15, "ma")
for x in cols:
    L(d, [(x, 46), (x, 188)], 2)
for y in (46, 76, 112, 148, 188):
    L(d, [(12, y), (468, y)], 2)
t(d, (240, 202), "12 min per km + 1 min per 10 m climbed", 15, "ma")
t(d, (240, 224), "e.g. 2 km = 24, + 200 m = 20, total 44 min", 14, "ma")
t(d, (240, 248), "Add stops. Note escape routes.", 14, "ma")
save(im, "nav_route_card")

im, d = new("DAYLIGHT LEFT: FINGERS TO SUN")
ground(d, 230)
t(d, (24, 238), "horizon", 13)
sun(d, (300, 70), 16)
for k in range(4):
    d.rounded_rectangle([250, 96 + k * 33, 350, 126 + k * 33], 12, outline=G, width=3)
d.rounded_rectangle([340, 90, 380, 226], 10, outline=G, width=3)
L(d, [(380, 150), (466, 140)], 5)
t(d, (130, 110), "1 finger", 15, "ma"); t(d, (130, 128), "about 15 min", 15, "ma")
t(d, (130, 160), "4 fingers", 15, "ma"); t(d, (130, 178), "about 1 hour", 15, "ma")
t(d, (420, 112), "arm", 13, "ma"); t(d, (420, 126), "straight", 13, "ma")
t(d, (240, 252), "In Britain often longer. Count on it as the least.", 13, "ma")
save(im, "nav_hand_sun")

im, d = new("JUDGING DISTANCE: A PERSON AT...")
L(d, [(8, 210), (472, 210)], 3)
for k, (x, h, lab) in enumerate(((50, 120, "200 m"), (140, 96, "300 m"), (230, 76, "400 m"), (320, 60, "500 m"), (410, 46, "600 m"))):
    if k <= 1:
        stick_person(d, x, 210, h, 4 if k == 0 else 3)
    elif k == 2:
        E(d, [x - 8, 210 - h, x + 8, 210 - h + 14], 3)
        d.polygon([(x - 12, 210 - h + 16), (x + 12, 210 - h + 16), (x + 8, 210), (x - 8, 210)], outline=G, width=3)
    elif k == 3:
        dot(d, (x, 210 - h + 4), 4)
        d.polygon([(x - 10, 210 - h + 10), (x + 10, 210 - h + 10), (x + 3, 210), (x - 3, 210)], outline=G, width=3)
    else:
        d.polygon([(x - 8, 210 - h), (x + 8, 210 - h), (x, 210)], outline=G, width=3)
    t(d, (x, 218), lab, 14, "ma")
lines(d, 240, 238, ["kit clear | face blur | outline | head unclear | wedge"], 12, 2, "ma")
t(d, (240, 258), "Football pitch = about 100 m. Thunder: 3 s per km.", 13, "ma")
save(im, "nav_distance")

im, d = new("FOG: LEAPFROG ON A BEARING")
for k in range(10):
    y = 40 + k * 7
    dashed(d, (0, y), (480, y), 1, 20, 18)
stick_person(d, 80, 230, 70)
stick_person(d, 380, 170, 54)
dashed(d, (100, 214), (360, 160), 3)
t(d, (110, 236), "you: compass", 14); t(d, (110, 252), "on the bearing", 14)
t(d, (380, 180), "leader at the", 14, "ma"); t(d, (380, 196), "edge of sight", 14, "ma")
arrow(d, (318, 136), (356, 136), 3); arrow(d, (442, 136), (404, 136), 3)
t(d, (380, 104), "waved left/right", 14, "ma")
t(d, (240, 266), "", 13)
t(d, (250, 236), "then walk to them;", 14); t(d, (250, 252), "count paces; repeat", 14)
save(im, "nav_fog")

im, d = new("RULE OF TWELFTHS (LOW TO HIGH)")
parts = [1, 2, 3, 3, 2, 1]
total = 0
for k, p in enumerate(parts):
    x0 = 60 + k * 62
    total += p
    top = 214 - total * 12
    d.rectangle([x0, top, x0 + 44, 214], outline=G, width=3)
    d.rectangle([x0 + 3, top + 3, x0 + 41, top + p * 12 - 1], fill=G)
    t(d, (x0 + 22, 220), f"hr {k + 1}", 13, "ma")
    t(d, (x0 + 22, top - 18), f"+{p}/12", 13, "ma")
L(d, [(40, 214), (440, 214)], 3)
t(d, (240, 242), "Hours 3 and 4 rise fastest: half the range.", 14, "ma")
t(d, (240, 262), "High water comes about 50 min later each day.", 13, "ma")
save(im, "nav_tides")

im, d = new("MARK YOUR WAY")
divider(d, 240)
for k in range(7):
    C(d, (40 + k * 20, 140 - abs(k - 6) * 0 + 0), 8, 3)
for k, (dx, dy) in enumerate(((140, 120), (140, 160))):
    pass
C(d, (150, 124), 8, 3); C(d, (162, 110), 8, 3); C(d, (150, 156), 8, 3); C(d, (162, 170), 8, 3)
t(d, (110, 190), "arrow of stones", 14, "ma"); t(d, (110, 208), "the way you went", 14, "ma")
t(d, (110, 234), "+ note: time, plan", 14, "ma")
for k, (w, y) in enumerate(((70, 210), (56, 186), (44, 164), (30, 146), (18, 132))):
    E(d, [360 - w / 2, y - 12, 360 + w / 2, y + 12], 3)
ground(d, 222, 280, 450)
t(d, (360, 234), "cairn only at key", 14, "ma"); t(d, (360, 252), "turns; remove later", 14, "ma")
L(d, [(300, 60), (300, 110)], 4); L(d, [(300, 80), (330, 70)], 3); L(d, [(330, 70), (344, 82)], 3)
t(d, (380, 56), "bent twig", 13, "ma"); t(d, (380, 72), "points the way", 13, "ma")
save(im, "nav_marks")

im, d = new("SKETCH MAP FROM MEMORY")
arrow(d, (440, 110), (440, 52), 4, 14); t(d, (440, 114), "N", 16, "ma")
d.line([(20, 260), (90, 210), (130, 150), (200, 120), (260, 60), (300, 36)], fill=G, width=6, joint="curve")
t(d, (20, 176), "river", 13)
L(d, [(20, 120), (460, 180)], 3); L(d, [(20, 130), (460, 190)], 3)
t(d, (330, 194), "road", 13)
d.polygon([(330, 80), (370, 40), (410, 80)], outline=G, width=3); t(d, (340, 86), "hill", 13)
d.polygon([(200, 230), (220, 206), (240, 230)], outline=G, width=3); t(d, (196, 236), "camp", 13)
C(d, (150, 230), 8, 3); t(d, (110, 244), "spring", 13)
cross(d, (160, 70), 10, 4); t(d, (110, 84), "cliff!", 13)
t(d, (330, 232), "town: 2 h walk", 13)
arrow(d, (240, 216), (330, 224), 2, 8)
save(im, "nav_sketch")

# ======================= EMERGENCY / SANITATION =======================
def house(d, x0, y0, x1, y1, w=3, roof=None):
    mid = (x0 + x1) / 2
    d.rectangle([x0, y0, x1, y1], outline=G, width=w)
    rh = roof if roof is not None else min((x1 - x0) * 0.35, y0 - 40)
    L(d, [(x0 - 10, y0), (mid, y0 - rh), (x1 + 10, y0)], w)


def bucket(d, x, y, w=60, h=70, lid=True):
    d.polygon([(x - w / 2, y), (x + w / 2, y), (x + w * 0.4, y + h), (x - w * 0.4, y + h)], outline=G, width=3)
    if lid:
        d.rectangle([x - w / 2 - 4, y - 8, x + w / 2 + 4, y], outline=G, width=3)


im, d = new("FIRE AT HOME: GET OUT, STAY OUT")
for k in range(3):
    dashed(d, (10, 44 + k * 10), (300, 44 + k * 10), 2, 14, 10)
t(d, (160, 76), "smoke", 13, "ma")
d.rectangle([30, 100, 90, 230], outline=G, width=3); C(d, (80, 170), 4, 2)
L(d, [(100, 160), (130, 160)], 4); E(d, [94, 150, 108, 170], 3)
t(d, (60, 236), "feel door with", 13, "ma"); t(d, (60, 252), "back of hand", 13, "ma")
C(d, (170, 200), 10, 3); L(d, [(180, 204), (240, 214)], 4); L(d, [(196, 208), (190, 228)], 3); L(d, [(236, 214), (250, 230)], 3); L(d, [(220, 212), (214, 230)], 3)
L(d, [(140, 232), (290, 232)], 2)
t(d, (210, 240), "crawl low", 13, "ma"); t(d, (210, 256), "close doors", 13, "ma")
divider(d, 312)
d.rectangle([330, 60, 460, 150], outline=G, width=3); L(d, [(395, 60), (395, 150)], 2)
t(d, (395, 158), "TRAPPED:", 14, "ma")
lines(d, 330, 178, ["bedding at", "door gap,", "shout, call", "999"], 13, 2)
d.rectangle([420, 214, 470, 232], outline=G, width=2); t(d, (445, 238), "door", 12, "ma")
save(im, "em_fire")

im, d = new("FLOOD AT HOME")
house(d, 30, 100, 330, 248)
L(d, [(30, 170), (330, 170)], 3)
d.rectangle([280, 118, 310, 160], outline=G, width=2)
d.rectangle([60, 120, 120, 160], outline=G, width=2); t(d, (90, 128), "papers", 12, "ma"); t(d, (90, 142), "meds", 12, "ma")
stick_person(d, 200, 168, 44); stick_person(d, 240, 168, 36)
d.rectangle([150, 190, 200, 250], outline=G, width=3)
d.rectangle([146, 220, 204, 252], outline=G, width=4, fill=G)
t(d, (175, 258), "board", 12, "ma")
d.rectangle([250, 226, 268, 238], outline=G, width=3, fill=G); t(d, (276, 212), "air", 12); t(d, (276, 226), "brick", 12)
d.rectangle([60, 186, 90, 222], outline=G, width=2); L(d, [(70, 214), (80, 194)], 3)
t(d, (75, 226), "mains", 12, "ma")
for x in range(8, 470, 28):
    d.arc([x, 252, x + 28, 268], 180, 360, fill=G, width=2)
lines(d, 346, 70, ["1 things", "  upstairs", "2 boards on", "3 mains off", "4 go up", "  or leave"], 14, 3)
save(im, "em_flood")

im, d = new("POWER CUT")
d.rounded_rectangle([20, 50, 120, 110], 10, outline=G, width=3); t(d, (70, 80), "105", 30, "mm")
t(d, (70, 118), "free call", 13, "ma")
d.rectangle([160, 46, 230, 220], outline=G, width=3); L(d, [(160, 110), (230, 110)], 3)
t(d, (195, 74), "freezer", 12, "ma")
t(d, (195, 150), "fridge", 12, "ma"); t(d, (195, 168), "4 h", 18, "ma")
t(d, (195, 228), "keep shut", 13, "ma")
t(d, (250, 52), "full freezer 48 h", 15); t(d, (250, 72), "half full 24 h", 15)
d.rectangle([260, 120, 300, 150], outline=G, width=3); d.polygon([(300, 125), (330, 112), (330, 158), (300, 145)], outline=G, width=3)
for k in range(3):
    L(d, [(338, 120 + k * 15), (370, 112 + k * 23)], 2)
t(d, (300, 166), "torch, not", 13, "ma"); t(d, (300, 182), "candle", 13, "ma")
C(d, (424, 120), 18, 3); L(d, [(416, 140), (432, 140)], 3)
t(d, (424, 166), "leave one", 13, "ma"); t(d, (424, 182), "light on", 13, "ma")
t(d, (240, 250), "Over 4 C for 2 h? Bin it. No stoves indoors.", 14, "ma")
save(im, "em_power_cut")

im, d = new("EARTHQUAKE: DROP, COVER, HOLD ON")
for k, lab in enumerate(("DROP", "COVER", "HOLD ON")):
    x0 = 12 + k * 156
    d.rounded_rectangle([x0, 40, x0 + 144, 230], 10, outline=G, width=2)
    t(d, (x0 + 72, 50), lab, 16, "ma")
    gx = x0 + 72
    if k == 0:
        C(d, (gx - 20, 130), 12, 3); L(d, [(gx - 10, 138), (gx + 30, 150)], 4)
        L(d, [(gx - 6, 140), (gx - 10, 190)], 3); L(d, [(gx + 30, 150), (gx + 30, 190)], 3); L(d, [(gx + 18, 150), (gx + 10, 190)], 3)
    else:
        d.rectangle([gx - 60, 110, gx + 60, 120], outline=G, width=3, fill=G)
        L(d, [(gx - 54, 120), (gx - 54, 190)], 4); L(d, [(gx + 54, 120), (gx + 54, 190)], 4)
        C(d, (gx - 20, 150), 12, 3); L(d, [(gx - 10, 156), (gx + 30, 166)], 4)
        L(d, [(gx - 30, 140), (gx - 10, 136)], 3)
        L(d, [(gx + 30, 166), (gx + 30, 190)], 3)
        if k == 2:
            L(d, [(gx + 16, 162), (gx + 52, 150)], 3)
    L(d, [(x0 + 8, 190), (x0 + 136, 190)], 3)
lines(d, 240, 238, ["Stay inside until it stops. Then watch for aftershocks."], 14, 2, "ma")
t(d, (240, 258), "Near the coast after strong shaking: go to high ground.", 13, "ma")
save(im, "em_quake")

im, d = new("RADIATION: GO IN, STAY IN, TUNE IN")
house(d, 40, 110, 280, 250)
L(d, [(40, 180), (280, 180)], 2); L(d, [(160, 110), (160, 250)], 2)
d.rectangle([120, 186, 200, 246], outline=G, width=3)
stick_person(d, 160, 244, 46)
t(d, (160, 76), "middle of a brick", 13, "ma"); t(d, (160, 92), "building or basement", 13, "ma")
lines(d, 300, 52, ["1 get inside now", "2 middle room", "3 outer clothes", "  in a sealed bag", "4 wash: soap,", "  shampoo, no", "  conditioner", "5 radio on,", "  24 h at least"], 13, 3)
save(im, "em_radiation")

im, d = new("WINTER AT HOME")
house(d, 40, 100, 300, 250)
L(d, [(170, 100), (170, 250)], 2)
d.rectangle([60, 120, 130, 170], outline=G, width=2)
for x in range(64, 130, 8):
    L(d, [(x, 120), (x, 170)], 1)
t(d, (95, 176), "curtains", 12, "ma")
t(d, (235, 130), "18 C", 22, "ma")
d.rectangle([190, 190, 280, 246], outline=G, width=2); t(d, (235, 198), "one warm", 12, "ma"); t(d, (235, 212), "room", 12, "ma")
d.rounded_rectangle([60, 238, 160, 250], 5, outline=G, width=3, fill=G)
t(d, (110, 220), "draught stop", 12, "ma")
L(d, [(320, 90), (320, 250)], 6); L(d, [(320, 160), (440, 160)], 6)
for y in range(96, 250, 10):
    L(d, [(312, y), (328, y)], 2)
for x in range(326, 440, 10):
    L(d, [(x, 152), (x, 168)], 2)
t(d, (384, 176), "lagged pipes", 13, "ma")
C(d, (410, 80), 16, 3); t(d, (410, 80), "CO", 12, "mm"); t(d, (410, 102), "alarm", 12, "ma")
t(d, (384, 210), "know your", 13, "ma"); t(d, (384, 226), "stopcock", 13, "ma")
save(im, "em_winter")

im, d = new("BUCKET TOILET")
bucket(d, 110, 90, 110, 140)
L(d, [(66, 120), (154, 120)], 2)
dots(d, (72, 196, 148, 222), 9, 2)
t(d, (110, 150), "bag-lined", 13, "ma")
t(d, (110, 204), "", 12)
t(d, (110, 238), "poo + cover", 14, "ma")
bucket(d, 250, 130, 70, 100)
t(d, (250, 238), "wee", 14, "ma")
d.rectangle([310, 160, 370, 230], outline=G, width=3); dots(d, (314, 166, 366, 226), 10, 2)
L(d, [(370, 150), (390, 120)], 3); d.arc([380, 104, 410, 130], 0, 360, fill=G, width=3)
t(d, (340, 238), "sawdust, soil,", 13, "ma"); t(d, (340, 254), "ash + scoop", 13, "ma")
t(d, (420, 60), "wash", 14, "ma"); t(d, (420, 76), "hands", 14, "ma")
bottle(d, 420, 100, 26, 56)
t(d, (110, 42), "cover every time,", 13, "ma"); t(d, (110, 58), "lid on", 13, "ma")
save(im, "san_bucket")

im, d = new("COMPOSTING TOILET: STORE 2 YEARS")
d.rectangle([30, 120, 210, 240], outline=G, width=3); d.rectangle([250, 120, 430, 240], outline=G, width=3)
d.rectangle([80, 90, 160, 120], outline=G, width=3); E(d, [96, 92, 144, 108], 3)
t(d, (120, 70), "seat: in use", 14, "ma")
dots(d, (40, 190, 200, 234), 10, 3)
d.rectangle([250, 100, 430, 120], outline=G, width=4, fill=G)
t(d, (340, 70), "closed, dated", 14, "ma")
dots(d, (260, 150, 420, 234), 10, 3)
d.rounded_rectangle([290, 160, 390, 200], 6, outline=G, width=3, fill=K); t(d, (340, 180), "MAY 2026", 14, "mm")
L(d, [(110, 108), (40, 160)], 0)
t(d, (120, 250), "cover each use", 13, "ma"); t(d, (340, 250), "1.5-2 years untouched", 13, "ma")
bottle(d, 450, 170, 22, 50); t(d, (450, 236), "wee", 12, "ma")
L(d, [(160, 102), (450, 170)], 0)
save(im, "san_compost")

im, d = new("GREYWATER SOAK PIT")
ground(d, 120)
d.polygon([(200, 120), (360, 120), (340, 250), (220, 250)], outline=G, width=3)
for y in range(132, 250, 16):
    for x in range(212 + (y // 16 % 2) * 8, 350, 18):
        if 200 + (y - 120) * 20 / 130 < x < 360 - (y - 120) * 20 / 130:
            C(d, (x, y), 6, 2)
d.rectangle([190, 108, 370, 118], outline=G, width=3)
t(d, (280, 90), "cover", 13, "ma")
bucket(d, 90, 40, 60, 36, False)
L(d, [(64, 40), (116, 40)], 3)
for k in range(5):
    L(d, [(66 + k * 12, 36), (66 + k * 12, 46)], 1)
t(d, (90, 82), "strain out", 13, "ma"); t(d, (90, 98), "food, grease", 13, "ma")
arrow(d, (130, 56), (200, 100), 3)
t(d, (380, 170), "stones or", 13); t(d, (380, 186), "gravel, 1 m", 13)
t(d, (410, 60), "30 m from", 13, "ma"); t(d, (410, 76), "any water", 13, "ma")
t(d, (100, 190), "use the", 13, "ma"); t(d, (100, 206), "same day", 13, "ma")
save(im, "san_greywater")

# ======================= CLOTHING / WEATHER =======================
def mitten_shape(d, x, y, s=1.0, w=3, dashed_line=False):
    pts = [(x, y + 150 * s), (x, y + 50 * s), (x + 8 * s, y + 10 * s), (x + 40 * s, y), (x + 72 * s, y + 10 * s),
           (x + 80 * s, y + 50 * s), (x + 80 * s, y + 80 * s), (x + 104 * s, y + 56 * s), (x + 114 * s, y + 66 * s),
           (x + 86 * s, y + 118 * s), (x + 80 * s, y + 150 * s)]
    if dashed_line:
        for a, b in zip(pts, pts[1:]):
            dashed(d, a, b, 2, 6, 5)
    else:
        d.line(pts, fill=G, width=w, joint="curve")


im, d = new("BLANKET MITTENS")
mitten_shape(d, 40, 50, 1.2, 3, True)
mitten_shape(d, 58, 74, 0.9, 3)
t(d, (110, 250), "trace hand + 3 cm,", 13, "ma"); t(d, (110, 266), "cut two, sew round", 13, "ma")
mitten_shape(d, 256, 80, 0.85, 4)
mitten_shape(d, 366, 80, 0.85, 4)
L(d, [(290, 208), (290, 228), (400, 228), (400, 208)], 3)
t(d, (362, 246), "cord joins the pair", 13, "ma")
save(im, "cloth_mitten")

im, d = new("STUFF CLOTHES WITH DRY LEAVES")
d.polygon([(140, 50), (340, 50), (380, 110), (350, 120), (340, 100), (340, 250), (140, 250), (140, 100), (130, 120), (100, 110)], outline=G, width=4)
d.polygon([(160, 64), (320, 64), (320, 236), (160, 236)], outline=G, width=2)
for k in range(16):
    x = 170 + (k % 4) * 38
    y = 80 + (k // 4) * 40
    leaf(d, (x + 14, y + 12), 26, 10, 30 + k * 40, 2, False)
L(d, [(100, 110), (130, 120)], 6); L(d, [(350, 120), (380, 110)], 6)
t(d, (60, 136), "cuffs", 13, "ma"); t(d, (60, 152), "tied", 13, "ma")
t(d, (420, 136), "loose,", 13, "ma"); t(d, (420, 152), "2-5 cm", 13, "ma")
t(d, (240, 256), "between two layers; refill when damp", 13, "ma")
save(im, "cloth_stuffing")

im, d = new("MEND OR MAKE FOOTWEAR")
divider(d, 240)
d.polygon([(30, 190), (30, 80), (90, 80), (100, 150), (200, 170), (210, 200), (30, 200)], outline=G, width=4)
L(d, [(30, 210), (215, 210)], 3)
for x in (70, 140):
    d.rectangle([x, 150, x + 26, 216], outline=G, width=3)
t(d, (120, 226), "tape or inner tube", 13, "ma"); t(d, (120, 242), "round a loose sole", 13, "ma")
E(d, [300, 50, 400, 230], 4)
for c in ((345, 78), (318, 196), (382, 196)):
    C(d, c, 6, 3)
L(d, [(345, 78), (318, 196)], 2); L(d, [(345, 78), (382, 196)], 2); L(d, [(318, 196), (382, 196)], 2)
t(d, (350, 240), "tyre sole, 3 holes", 13, "ma"); t(d, (350, 256), "cord to the ankle", 13, "ma")
save(im, "cloth_footwear")

im, d = new("WAX COTTON")
d.rectangle([30, 120, 450, 220], outline=G, width=3)
for x in range(40, 450, 14):
    L(d, [(x, 124), (x, 216)], 1)
d.rectangle([60, 80, 150, 120], outline=G, width=4); t(d, (105, 100), "wax", 14, "mm")
arrow(d, (160, 96), (230, 96), 3)
t(d, (110, 56), "rub in", 14, "ma")
for x in (260, 290, 320):
    smoke(d, x, 110, 30)
t(d, (290, 56), "warm it in", 14, "ma")
for c in ((380, 156), (410, 176), (360, 192)):
    E(d, [c[0] - 10, c[1] - 8, c[0] + 10, c[1] + 8], 3)
t(d, (400, 230), "water beads", 14, "ma")
t(d, (150, 232), "cotton canvas,", 13, "ma"); t(d, (150, 248), "not breathable coats", 13, "ma")
save(im, "cloth_wax")

im, d = new("PUTTEES: SPIRAL UP, OVERLAP HALF")
d.polygon([(150, 200), (150, 250), (290, 250), (290, 228), (210, 210), (210, 200)], outline=G, width=4)
L(d, [(150, 60), (150, 200)], 3); L(d, [(210, 60), (210, 200)], 3)
for k in range(7):
    y = 196 - k * 20
    d.polygon([(146, y), (214, y - 12), (214, y - 2), (146, y + 10)], outline=G, width=3)
L(d, [(214, 66), (240, 50)], 3); L(d, [(214, 72), (244, 56)], 3)
t(d, (250, 40), "tie off below", 13); t(d, (250, 56), "the knee", 13)
arrow(d, (110, 200), (110, 80), 3)
t(d, (66, 210), "start at", 13, "ma"); t(d, (66, 226), "the boot", 13, "ma")
t(d, (360, 120), "cloth strip", 14, "ma"); t(d, (360, 138), "10 cm x 1.5-2 m", 14, "ma")
t(d, (360, 170), "not tight", 14, "ma")
save(im, "cloth_puttee")

im, d = new("BAROMETER: CHANGE IN 3 HOURS")
rows = [("steady", "under 0.1", "no change"), ("slowly", "0.1-1.5", "slow change"), ("falling", "1.6-3.5", "unsettled"),
        ("quickly", "3.6-6", "strong wind"), ("very fast", "over 6", "gale likely")]
for k, (a, b, c) in enumerate(rows):
    y = 48 + k * 40
    t(d, (16, y + 10), a, 15)
    t(d, (130, y + 10), b + " hPa", 15)
    w = [4, 24, 54, 90, 120][k]
    d.rectangle([260, y + 8, 260 + w, y + 28], outline=G, width=2, fill=G if k >= 3 else None)
    t(d, (470, y + 10), c, 13, "ra")
t(d, (240, 252), "Read at the same height. 8 m climb = about 1 hPa drop.", 13, "ma")
save(im, "wx_barometer")

im, d = new("WIND BY EYE (BEAUFORT)")
for k, (force, mph, bend) in enumerate(((3, "8-12", 0), (5, "19-24", 10), (7, "32-38", 24), (9, "47-54", 36))):
    x = 60 + k * 112
    cx, cy = x + bend, 120 + bend * 0.3
    r = 34 - k * 2
    L(d, [(x, 220), (cx - bend * 0.2, cy + r)], 5)
    C(d, (cx, cy), r, 3)
    if k == 0:
        for j in range(4):
            L(d, [(cx - 30 + j * 18, 82), (cx - 26 + j * 18, 74)], 2)
    for j in range(k):
        arrow(d, (x - 50, 70 + j * 14), (x - 20, 70 + j * 14), 2, 8)
    if k == 3:
        L(d, [(cx - 4, 196), (cx + 26, 206)], 3); L(d, [(cx + 10, 200), (cx + 16, 192)], 2)
        t(d, (cx + 16, 170), "branches", 11, "ma")
    ground(d, 220, x - 50, x + 50)
    t(d, (x, 232), f"force {force}", 15, "ma"); t(d, (x, 250), f"{mph} mph", 13, "ma")
save(im, "wx_beaufort")

im, d = new("HILL WEATHER")
d.polygon([(20, 250), (250, 70), (460, 250)], outline=G, width=4)
for k in range(4):
    E(d, [150 + k * 46, 66, 206 + k * 46, 96], 2)
t(d, (40, 60), "cloud on", 13); t(d, (40, 76), "the tops", 13)
t(d, (330, 44), "summit 5 C", 15)
for j in range(3):
    arrow(d, (330, 80 + j * 14), (400, 80 + j * 14), 3, 10)
t(d, (408, 86), "windier", 13)
for k in range(3):
    y = 140 + k * 36
    dashed(d, (250 - (y - 70) * 230 / 180 + 10, y), (250 + (y - 70) * 210 / 180 - 10, y), 1, 6, 10)
t(d, (250, 160), "about -1 C", 14, "ma"); t(d, (250, 178), "per 150 m", 14, "ma")
t(d, (24, 256), "valley 12 C", 15)
save(im, "wx_hill")

im, d = new("SIGNS FROM PLANTS AND ANIMALS")
for k in range(8):
    a = math.radians(k * 45)
    L(d, [(90, 120), (90 + 60 * math.cos(a), 120 + 60 * math.sin(a))], 2)
for r in (20, 36, 52):
    C(d, (90, 120), r, 1)
for k in range(10):
    a = math.radians(k * 36 + 10)
    dot(d, (90 + 40 * math.cos(a), 120 + 40 * math.sin(a)), 3)
t(d, (90, 196), "heavy dew after a", 13, "ma"); t(d, (90, 212), "clear night: fine", 13, "ma")
for k, (x, y) in enumerate(((210, 180), (260, 196), (300, 176))):
    L(d, [(x - 18, y - 6), (x, y), (x + 18, y - 6)], 3)
ground(d, 214, 180, 330)
t(d, (256, 60), "swallows low:", 13, "ma"); t(d, (256, 76), "humid, rain", 13, "ma"); t(d, (256, 92), "may follow", 13, "ma")
E(d, [380, 90, 430, 180], 3)
for k in range(5):
    L(d, [(384, 104 + k * 16), (426, 112 + k * 16)], 2)
t(d, (405, 196), "cone shut:", 13, "ma"); t(d, (405, 212), "damp air", 13, "ma")
t(d, (240, 250), "Clues for the next few hours only.", 14, "ma")
save(im, "wx_signs")

# ======================= POWER / TOOLS =======================
im, d = new("BIKE GENERATOR: SAFE CHAIN")
C(d, (50, 120), 40, 4); C(d, (50, 120), 6, 3)
C(d, (100, 156), 13, 3); t(d, (100, 174), "gen", 12, "ma")
chain = [("diode", 160), ("charge\ncontrol", 240), ("fuse", 320), ("12 V\nbattery", 404)]
prev = (113, 156)
for lab, x in chain:
    arrow(d, prev, (x - 34, 156), 3, 8)
    box(d, (x - 34, 134, x + 34, 178), lab, 13)
    prev = (x + 34, 156)
L(d, [(404, 178), (404, 210)], 3)
box(d, (350, 210, 440, 250), "12 V to 5 V", 13)
arrow(d, (440, 230), (462, 230), 3, 8); t(d, (472, 238), "Pi", 13, "ra")
t(d, (110, 52), "never straight into the Pi", 14)
t(d, (110, 72), "fuse within 20 cm of battery +", 14)
t(d, (180, 214), "50-100 W", 15, "ma"); t(d, (180, 232), "pedalling", 13, "ma")
save(im, "pw_bike")

im, d = new("SMALL WIND TURBINE")
L(d, [(120, 250), (120, 86)], 5)
for a in (90, 210, 330):
    r = math.radians(a)
    L(d, [(120, 82), (120 + 36 * math.cos(r), 82 - 36 * math.sin(r))], 5)
d.rectangle([110, 74, 140, 90], outline=G, width=3); L(d, [(140, 82), (170, 82)], 3); d.polygon([(170, 70), (190, 82), (170, 94)], outline=G, width=3)
L(d, [(120, 120), (40, 250)], 2); L(d, [(120, 120), (200, 250)], 2)
ground(d, 250, 8, 230)
t(d, (24, 204), "guys", 12)
box(d, (270, 60, 370, 104), "wind\ncontroller", 13)
box(d, (390, 60, 470, 104), "dump\nload", 13)
L(d, [(370, 82), (390, 82)], 3)
box(d, (270, 150, 370, 194), "12 V\nbattery", 13)
L(d, [(320, 104), (320, 150)], 3)
box(d, (390, 150, 470, 194), "stop\nswitch", 13)
L(d, [(120, 160), (250, 160), (250, 82), (270, 82)], 2)
L(d, [(430, 194), (430, 204), (250, 204), (250, 160)], 2)
t(d, (360, 216), "average 5 m/s or more,", 13, "ma"); t(d, (360, 234), "blades well above trees", 13, "ma"); t(d, (360, 252), "and roofs nearby", 13, "ma")
save(im, "pw_wind")

im, d = new("SUN FOR HEAT")
sun(d, (50, 60), 16)
for k in range(3):
    arrow(d, (70 + k * 8, 80 + k * 14), (190 + k * 8, 160 + k * 14), 2, 10)
house(d, 160, 100, 440, 250, 3, 40)
d.rectangle([160, 130, 180, 200], outline=G, width=3)
t(d, (150, 210), "south", 12, "ra"); t(d, (150, 224), "window", 12, "ra")
for k in range(3):
    d.rectangle([220 + k * 40, 200, 250 + k * 40, 248], outline=G, width=3, fill=G)
t(d, (280, 160), "dark water", 13, "ma"); t(d, (280, 176), "tanks soak heat", 13, "ma")
for x in range(380, 430, 8):
    L(d, [(x, 120), (x, 200)], 1)
t(d, (405, 206), "curtains", 12, "ma"); t(d, (405, 220), "shut at", 12, "ma"); t(d, (405, 234), "dusk", 12, "ma")
save(im, "pw_solar_heat")

im, d = new("BONE AWL AND NEEDLE")
E(d, [20, 60, 60, 90], 3); E(d, [190, 60, 230, 90], 3); d.rectangle([40, 66, 210, 84], outline=G, width=3)
dashed(d, (40, 75), (210, 75), 2)
t(d, (125, 98), "score + split", 13, "ma")
d.rectangle([240, 50, 460, 90], outline=G, width=3)
for x in range(250, 460, 20):
    dot(d, (x, 60), 2); dot(d, (x + 10, 78), 2)
L(d, [(300, 46), (380, 30)], 4)
t(d, (350, 98), "grind on wet sandstone", 13, "ma")
d.polygon([(30, 170), (60, 150), (90, 165), (200, 172), (90, 180), (60, 192)], outline=G, width=3)
t(d, (110, 200), "awl: fat butt,", 13, "ma"); t(d, (110, 216), "5 cm point", 13, "ma")
L(d, [(260, 170), (450, 170)], 4); E(d, [266, 165, 282, 175], 2)
d.polygon([(440, 166), (460, 170), (440, 174)], fill=G)
t(d, (360, 190), "needle: drill the eye", 13, "ma"); t(d, (360, 206), "from both sides", 13, "ma")
t(d, (240, 250), "Raw or dried bone. Cooked bone splinters.", 14, "ma")
save(im, "tl_bone")

im, d = new("MALLET AND WEDGES")
d.rectangle([30, 50, 90, 120], outline=G, width=3)
d.rectangle([48, 120, 72, 220], outline=G, width=3)
t(d, (60, 230), "mallet", 13, "ma"); t(d, (60, 246), "40 cm", 13, "ma")
d.polygon([(130, 60), (160, 60), (150, 150), (140, 150)], outline=G, width=3)
t(d, (145, 160), "wedge", 13, "ma"); t(d, (145, 176), "long taper", 13, "ma")
d.rectangle([200, 140, 460, 210], outline=G, width=3)
E(d, [190, 140, 210, 210], 3)
d.line([(210, 175), (260, 170), (320, 178), (380, 172), (460, 176)], fill=G, width=2)
for x in (270, 360):
    d.polygon([(x - 12, 118), (x + 12, 118), (x + 2, 176), (x - 2, 176)], outline=G, width=3, fill=K)
arrow(d, (270, 70), (270, 110), 3); arrow(d, (360, 70), (360, 110), 3)
t(d, (330, 222), "drive the next wedge into the", 13, "ma"); t(d, (330, 238), "crack; swap as each loosens", 13, "ma")
save(im, "tl_mallet")

im, d = new("BIRCH BARK BOX")
d.rectangle([20, 60, 200, 170], outline=G, width=3)
dashed(d, (70, 60), (70, 170), 2); dashed(d, (150, 60), (150, 170), 2)
dashed(d, (20, 95), (200, 95), 2); dashed(d, (20, 135), (200, 135), 2)
t(d, (110, 108), "base", 13, "ma")
t(d, (110, 180), "score the base", 13, "ma"); t(d, (110, 196), "on the inside", 13, "ma")
arrow(d, (210, 115), (250, 115), 3)
d.polygon([(270, 120), (380, 120), (400, 90), (290, 90)], outline=G, width=3)
d.polygon([(270, 120), (270, 200), (380, 200), (380, 120)], outline=G, width=3)
d.polygon([(380, 120), (400, 90), (400, 170), (380, 200)], outline=G, width=3)
L(d, [(270, 120), (300, 160), (270, 200)], 2)
L(d, [(400, 80), (400, 110)], 4); L(d, [(392, 80), (392, 110)], 4)
t(d, (430, 60), "split-stick", 12, "ma"); t(d, (430, 74), "clip", 12, "ma")
t(d, (330, 214), "fold sides up,", 13, "ma"); t(d, (330, 230), "tuck corners", 13, "ma")
t(d, (240, 256), "Dead or fallen birch only. Never peel a living tree.", 13, "ma")
save(im, "tl_birch_box")

im, d = new("BOW SAW FRAME")
L(d, [(120, 50), (100, 230)], 6); L(d, [(360, 50), (380, 230)], 6)
L(d, [(110, 140), (370, 140)], 6)
L(d, [(100, 226), (380, 226)], 3)
for x in range(110, 372, 10):
    L(d, [(x, 226), (x + 5, 234)], 2)
d.line([(120, 56), (240, 64), (360, 56)], fill=G, width=2)
d.line([(120, 62), (240, 70), (360, 62)], fill=G, width=2)
L(d, [(240, 50), (240, 136)], 5)
t(d, (248, 90), "toggle: twist", 13); t(d, (248, 106), "to tighten", 13)
t(d, (240, 150), "cross bar", 13, "ma")
t(d, (240, 244), "blade pinned in slots", 13, "ma")
t(d, (30, 120), "arm", 13); t(d, (400, 120), "arm", 13)
save(im, "tl_bow_saw")

im, d = new("HAFT A STONE AXE")
L(d, [(240, 260), (240, 60)], 0)
d.rectangle([226, 60, 254, 260], outline=G, width=3)
d.polygon([(254, 100), (330, 80), (360, 120), (330, 160), (254, 140)], outline=G, width=4)
d.polygon([(226, 104), (200, 110), (200, 134), (226, 138)], outline=G, width=3)
for k in range(6):
    L(d, [(222, 70 + k * 6), (258, 76 + k * 6)], 2)
    L(d, [(222, 150 + k * 6), (258, 144 + k * 6)], 2)
L(d, [(222, 100), (258, 142)], 3); L(d, [(222, 142), (258, 100)], 3)
t(d, (100, 70), "binding above", 13, "ma")
t(d, (100, 160), "binding below", 13, "ma")
t(d, (100, 110), "pitch glue +", 13, "ma"); t(d, (100, 126), "cross wrap", 13, "ma")
t(d, (390, 170), "stone head in", 13, "ma"); t(d, (390, 186), "a split handle", 13, "ma")
t(d, (390, 230), "wet rawhide", 13, "ma"); t(d, (390, 246), "shrinks tight", 13, "ma")
save(im, "tl_haft")

print("batch 7 diagrams written")
