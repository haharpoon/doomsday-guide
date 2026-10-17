"""Diagrams for the Power and Emergency cards. Run from the repo root.

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


def star(d, c, r=6):
    x, y = c
    pts = []
    for k in range(10):
        rr = r if k % 2 == 0 else r * 0.45
        a = -math.pi / 2 + k * math.pi / 5
        pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
    d.polygon(pts, fill=G)


def divider(d, x, top=34, bottom=276):
    L(d, [(x, top), (x, bottom)], 2)


def save(im, name):
    im.save(f"content/img/{name}.png")


def box(d, xy, label, size=13, w=3):
    d.rounded_rectangle(xy, 8, outline=G, width=w)
    lines = label.split("\n")
    cx, cy = (xy[0] + xy[2]) / 2, (xy[1] + xy[3]) / 2
    for k, s in enumerate(lines):
        t(d, (cx, cy + (k - (len(lines) - 1) / 2) * (size + 3)), s, size, "mm")


# ---------------- Power ----------------
im, d = new("WATTS = VOLTS x AMPS")
d.polygon([(130, 44), (30, 220), (230, 220)], outline=G, width=4)
L(d, [(72, 146), (188, 146)], 3); L(d, [(130, 146), (130, 220)], 3)
t(d, (130, 108), "W", 32, "mm"); t(d, (94, 186), "V", 30, "mm"); t(d, (166, 186), "A", 30, "mm")
t(d, (130, 236), "cover the one you want", 12, "ma")
X = 262
t(d, (X, 48), "W = V x A", 18)
t(d, (X, 74), "A = W / V", 18)
t(d, (X, 100), "Wh = W x hours", 18)
t(d, (X, 126), "Wh = Ah x V", 18)
divider(d, 252, 154, 154)
L(d, [(X, 156), (472, 156)], 2)
t(d, (X, 166), "12 V lamp, 0.5 A = 6 W", 13)
t(d, (X, 186), "6 W for 5 h = 30 Wh", 13)
t(d, (X, 206), "12 V 100 Ah = 1200 Wh", 13)
t(d, (X, 226), "(use about half if lead-acid)", 12)
t(d, (8, 258), "Low volts = more amps = thicker wire.", 13)
save(im, "power_watts")

im, d = new("SMALL SOLAR SETUP")
# panel
d.polygon([(20, 110), (60, 50), (130, 50), (90, 110)], outline=G, width=4)
for k in (1, 2):
    L(d, [(20 + 70 * k / 3 + 0, 110), (60 + 70 * k / 3, 50)], 2)
L(d, [(40, 80), (110, 80)], 2)
t(d, (75, 118), "PANEL", 13, "ma")
box(d, (160, 56, 270, 106), "CHARGE\nCONTROLLER", 12)
box(d, (160, 170, 270, 230), "BATTERY\n12 V", 14)
arrow(d, (110, 80), (158, 80), 3)
L(d, [(200, 108), (200, 168)], 3); L(d, [(230, 108), (230, 168)], 3)
d.rectangle([192, 128, 208, 146], outline=G, width=2); t(d, (186, 137), "fuse", 11, "rm")
t(d, (236, 137), "-", 14, "lm")
# loads
arrow(d, (272, 186), (330, 160), 3); arrow(d, (272, 210), (330, 220), 3)
box(d, (334, 136, 466, 184), "12 V / USB\nPi, lights, radio", 12)
box(d, (334, 198, 466, 246), "INVERTER\n230 V if needed", 12)
d.rectangle([292, 160, 306, 176], outline=G, width=2)
t(d, (8, 258), "Wire battery to controller first, then panel.", 13)
save(im, "power_solar")

im, d = new("FUSE NEAR THE BATTERY")
box(d, (20, 120, 130, 200), "BATTERY", 14, 4)
t(d, (40, 112), "+", 18, "mb"); t(d, (110, 112), "-", 18, "mb")
L(d, [(40, 120), (40, 70), (110, 70)], 4)
d.rectangle([110, 60, 150, 80], outline=G, width=3); t(d, (130, 56), "MAIN", 11, "mb")
t(d, (80, 92), "< 20 cm", 11, "mm")
L(d, [(150, 70), (200, 70)], 4)
d.rectangle([200, 50, 230, 190], outline=G, width=3); t(d, (215, 198), "fuse\nblock", 11, "ma")
for k, (y, lab) in enumerate(((70, "5 A  Pi"), (110, "3 A  lights"), (150, "2 A  radio"))):
    d.rectangle([236, y - 8, 262, y + 8], outline=G, width=2)
    L(d, [(230, y), (236, y)], 3); L(d, [(262, y), (300, y)], 3)
    t(d, (306, y), lab, 13, "lm")
L(d, [(110, 200), (110, 236), (420, 236)], 4)
d.rectangle([420, 226, 470, 246], outline=G, width=3); t(d, (445, 222), "- bar", 11, "mb")
for y in (70, 110, 150):
    dashed(d, (400, y), (440, y), 2); L(d, [(440, y), (440, 226)], 1)
t(d, (8, 258), "Fuse protects the wire. Each branch its own fuse.", 13)
save(im, "power_fuse")

im, d = new("POWERING THE PI")
box(d, (10, 90, 100, 160), "12 V\nBATTERY", 13, 4)
L(d, [(100, 125), (130, 125)], 4)
d.rectangle([130, 115, 160, 135], outline=G, width=3); t(d, (145, 140), "5 A", 12, "ma")
L(d, [(160, 125), (190, 125)], 4)
box(d, (190, 90, 290, 160), "12 V > 5 V\nBUCK\n3 A or more", 12, 4)
arrow(d, (290, 125), (330, 125), 4)
d.rounded_rectangle([334, 80, 470, 170], 10, outline=G, width=4)
t(d, (402, 112), "Pi", 22, "mm"); t(d, (402, 142), "USB-C 5 V", 12, "mm")
t(d, (20, 194), "Pi 4: 5 V 3 A     Pi 5: 5 V 5 A (3 A limits USB)", 13)
t(d, (20, 216), "Screen: add 0.5-1 A.  Bolt icon = too little power.", 13)
t(d, (20, 238), "Or: power bank, 5 V 3 A USB-C.", 13)
t(d, (8, 260), "Shut down from the menu before cutting power.", 13)
save(im, "power_pi")

im, d = new("CARBON MONOXIDE: GENERATORS OUTSIDE")
# house
L(d, [(20, 120), (110, 50), (200, 120)], 4)
d.rectangle([30, 120, 190, 240], outline=G, width=4)
d.rectangle([50, 140, 90, 180], outline=G, width=3)
d.rectangle([130, 170, 165, 240], outline=G, width=3)
box(d, (44, 190, 120, 230), "CO\nalarm", 11, 2)
# distance
dashed(d, (200, 220), (340, 220), 2)
arrow(d, (270, 220), (200, 220), 2); arrow(d, (270, 220), (340, 220), 2)
t(d, (270, 208), "6 m or more", 13, "mb")
# generator
box(d, (344, 190, 430, 240), "GEN", 15, 4)
L(d, [(430, 200), (450, 200)], 4)
for k in range(3):
    C(d, (458 + k * 6, 186 - k * 14), 5 + k * 2, 2)
t(d, (330, 60), "NEVER indoors,", 14)
t(d, (330, 80), "garage, shed,", 14)
t(d, (330, 100), "tent or porch.", 14)
t(d, (330, 130), "Exhaust away", 13); t(d, (330, 148), "from the house.", 13)
t(d, (8, 258), "Headache, dizzy, sick? Get out into fresh air. 999.", 13)
save(im, "power_co")

# ---------------- Emergency ----------------
im, d = new("GRAB BAG")
d.rounded_rectangle([20, 70, 160, 240], 24, outline=G, width=5)
d.rounded_rectangle([50, 40, 130, 80], 14, outline=G, width=4)
d.rounded_rectangle([40, 140, 140, 210], 10, outline=G, width=3)
L(d, [(40, 160), (140, 160)], 2)
items = ["Water and snacks", "Torch, radio, batteries", "Power bank and cable", "First aid kit",
         "Medicines + dose list", "ID, documents, plan", "Cash in small notes", "Warm layer, waterproof",
         "Whistle, multi-tool", "Keys, glasses, masks"]
for k, s in enumerate(items):
    y = 44 + k * 20
    d.rectangle([186, y, 198, y + 12], outline=G, width=2)
    t(d, (206, y - 2), s, 14)
t(d, (8, 258), "One per person. By the door. Check every 6 months.", 13)
save(im, "em_grab_bag")

im, d = new("EVACUATE")
steps = [("1", "Grab bags, meds, phone"), ("2", "Gas, power, water off if told"), ("3", "Lock up, take pets"),
         ("4", "Text your contact"), ("5", "Use the route given")]
for k, (n, s) in enumerate(steps):
    y = 44 + k * 38
    C(d, (30, y + 12), 13, 3); t(d, (30, y + 12), n, 14, "mm")
    t(d, (54, y + 3), s, 14)
    if k < len(steps) - 1:
        L(d, [(30, y + 26), (30, y + 36)], 2)
# flood warning
X = 330
for k in range(3):
    y = 120 + k * 10
    d.arc([X + 0 + k * 4, y, X + 40 + k * 4, y + 20], 200, 340, fill=G, width=3)
    d.arc([X + 40 + k * 4, y, X + 80 + k * 4, y + 20], 200, 340, fill=G, width=3)
    d.arc([X + 80 + k * 4, y, X + 120 + k * 4, y + 20], 200, 340, fill=G, width=3)
C(d, (390, 90), 44, 4); L(d, [(359, 59), (421, 121)], 5)
t(d, (390, 176), "No walking or", 13, "ma"); t(d, (390, 194), "driving in", 13, "ma"); t(d, (390, 212), "floodwater", 13, "ma")
t(d, (8, 258), "15 cm can knock you down. 30 cm floats a car.", 13)
save(im, "em_evacuate")

im, d = new("SHUT OFF GAS, WATER, POWER")
divider(d, 160); divider(d, 320)
# gas
t(d, (80, 40), "GAS (meter)", 14, "ma")
for y, ang, lab in ((90, 0, "ON: along pipe"), (180, 90, "OFF: across")):
    L(d, [(20, y), (140, y)], 8)
    if ang == 0:
        L(d, [(56, y - 4), (104, y - 4)], 8)
    else:
        L(d, [(80, y - 26), (80, y + 26)], 8)
    dot(d, (80, y), 7)
    t(d, (80, y + 32), lab, 12, "ma")
# water
t(d, (240, 40), "WATER (stopcock)", 14, "ma")
L(d, [(170, 150), (310, 150)], 10)
d.rectangle([224, 134, 256, 166], outline=G, width=3)
L(d, [(240, 134), (240, 100)], 5); C(d, (240, 88), 18, 4)
d.arc([206, 54, 274, 122], 200, 330, fill=G, width=3)
arrow(d, (262, 60), (274, 72), 3, 10)
t(d, (240, 182), "clockwise", 13, "ma"); t(d, (240, 200), "= off", 13, "ma")
t(d, (240, 222), "under kitchen sink", 11, "ma")
# electric
t(d, (400, 40), "POWER (fuse box)", 14, "ma")
d.rectangle([346, 70, 454, 200], outline=G, width=4)
d.rectangle([380, 96, 420, 170], outline=G, width=3)
d.rectangle([386, 140, 414, 164], fill=G)
arrow(d, (436, 110), (436, 160), 3)
t(d, (400, 206), "main switch", 12, "ma"); t(d, (400, 222), "down = off", 12, "ma")
t(d, (8, 258), "Smell gas? No switches or flames. Out. 0800 111 999.", 13)
save(im, "em_utilities")
