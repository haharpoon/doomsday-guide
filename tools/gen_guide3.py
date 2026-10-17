"""Diagrams for the Navigation, Sanitation, Clothing and Weather cards. Run from the repo root.

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


# ---------------- Navigation ----------------
im, d = new("SIX-FIGURE GRID REFERENCE")
x0, y0, s = 60, 44, 180                       # square 1844, bottom-left at (x0, y0+s)
d.rectangle([x0, y0, x0 + s, y0 + s], outline=G, width=4)
for k in range(1, 10):
    L(d, [(x0 + k * s / 10, y0 + s), (x0 + k * s / 10, y0 + s - 8)], 2)
    L(d, [(x0, y0 + s - k * s / 10), (x0 + 8, y0 + s - k * s / 10)], 2)
px, py = x0 + 7 * s / 10, y0 + s - 8 * s / 10
dashed(d, (x0, py), (px, py)); dashed(d, (px, y0 + s), (px, py))
C(d, (px, py), 8, 4)
t(d, (x0, y0 + s + 6), "18", 15, "ma"); t(d, (x0 + s, y0 + s + 6), "19", 15, "ma")
t(d, (x0 - 6, y0 + s), "44", 15, "rm"); t(d, (x0 - 6, y0), "45", 15, "rm")
t(d, (px, y0 + s + 6), "7", 13, "ma"); t(d, (x0 + 12, py), "8", 13, "lm")
X = 270
t(d, (X, 46), "1 Along the corridor:", 14)
t(d, (X, 64), "  line 18, 7 tenths = 187", 13)
t(d, (X, 88), "2 Up the stairs:", 14)
t(d, (X, 106), "  line 44, 8 tenths = 448", 13)
t(d, (X, 134), "187448", 26)
t(d, (X, 168), "4 figures = 1 km square", 13)
t(d, (X, 186), "6 figures = 100 m", 13)
t(d, (X, 204), "Add the letters: SU 187 448", 13)
t(d, (8, 258), "Eastings first, northings second. Bottom-left corner.", 13)
save(im, "nav_grid_ref")

im, d = new("CONTOURS")
# side view: gentle slope on the left, steep on the right
prof = [(20, 120), (70, 116), (120, 98), (170, 70), (200, 52), (222, 60), (238, 92), (250, 118), (330, 120), (440, 120)]
L(d, prof, 4)
for hy, lab in ((110, "10"), (90, "20"), (70, "30")):
    dashed(d, (20, hy), (440, hy), 1, 4, 6)
    t(d, (446, hy), lab, 11, "lm")
t(d, (90, 70), "gentle", 12); t(d, (240, 40), "steep", 12)
t(d, (300, 96), "side view", 12)
# plan view: rings far apart on the left, crowded on the right
for rx, ry, cx in ((110, 44, 160), (74, 32, 182), (38, 20, 204)):
    d.ellipse([cx - rx, 186 - ry, 224 + (110 - rx) * 0.12, 186 + ry], outline=G, width=3)
dot(d, (212, 186), 4)
t(d, (8, 236), "far apart = gentle", 11)
t(d, (150, 236), "close = steep", 11)
# valley: V tip points uphill; spur: V tip points downhill
t(d, (300, 136), "VALLEY", 12); t(d, (392, 136), "SPUR", 12)
L(d, [(296, 196), (322, 160), (348, 196)], 3); L(d, [(296, 222), (322, 180), (348, 222)], 3)
L(d, [(322, 186), (322, 232)], 2); t(d, (326, 226), "stream", 10)
L(d, [(384, 160), (410, 196), (436, 160)], 3); L(d, [(384, 180), (410, 222), (436, 180)], 3)
arrow(d, (462, 224), (462, 156), 2, 9); t(d, (458, 236), "uphill", 10, "ma")
t(d, (8, 258), "V points uphill = valley. V points downhill = spur.", 13)
save(im, "nav_contours")

im, d = new("BASEPLATE COMPASS")
bx0, by0, bx1, by1 = 150, 34, 300, 254
d.rounded_rectangle([bx0, by0, bx1, by1], 14, outline=G, width=4)
arrow(d, (225, 110), (225, 42), 5, 16)                         # direction of travel
cc = (225, 180); C(d, cc, 62, 5); C(d, cc, 50, 2)
for a in range(0, 360, 30):
    ca, sa = math.cos(math.radians(a - 90)), math.sin(math.radians(a - 90))
    L(d, [(cc[0] + 50 * ca, cc[1] + 50 * sa), (cc[0] + 62 * ca, cc[1] + 62 * sa)], 2)
t(d, (cc[0], cc[1] - 47), "N", 12, "ma")
for dx in (-24, 0, 24):
    L(d, [(cc[0] + dx, cc[1] - 38), (cc[0] + dx, cc[1] + 38)], 1)
d.polygon([(cc[0] - 9, cc[1] - 18), (cc[0] + 9, cc[1] - 18), (cc[0], cc[1] - 36)], outline=G, width=2)   # orienting arrow
d.polygon([(cc[0] - 6, cc[1]), (cc[0] + 6, cc[1]), (cc[0], cc[1] - 32)], fill=G)                        # needle N
d.polygon([(cc[0] - 6, cc[1]), (cc[0] + 6, cc[1]), (cc[0], cc[1] + 32)], outline=G, width=2)          # needle S
L(d, [(cc[0], cc[1] - 66), (cc[0], cc[1] - 80)], 4)            # index line
for k in range(6):
    L(d, [(bx0 + 4, 60 + k * 14), (bx0 + 14, 60 + k * 14)], 2)  # scale
# labels
def lab(y, x_end, text, side="l"):
    if side == "l":
        L(d, [(146, y), (x_end, y)], 2); t(d, (8, y), text, 12, "lm")
    else:
        L(d, [(x_end, y), (304, y)], 2); t(d, (310, y), text, 12, "lm")
lab(56, 218, "direction of travel"); lab(98, 225, "index line")
lab(70, 164, "scale / romer")
lab(140, 213, "orienting arrow"); lab(206, 201, "orienting lines")
lab(150, 230, "red needle: N", "r"); lab(210, 287, "housing 0-360", "r")
lab(244, 290, "baseplate edge", "r")
t(d, (8, 262), "Red in the shed.", 13)
save(im, "nav_compass")

im, d = new("HANDRAIL, AIMING OFF, CATCHING")
river = [(20, 84), (120, 70), (220, 82), (330, 66), (470, 76)]
L(d, river, 6); t(d, (300, 36), "river = catching feature", 12)
bxm = 200; L(d, [(bxm - 10, 62), (bxm - 10, 96)], 4); L(d, [(bxm + 10, 62), (bxm + 10, 96)], 4)
t(d, (bxm - 24, 40), "bridge", 12)
st = (290, 236); C(d, st, 7, 3); t(d, (300, 240), "you", 12)
arrow(d, st, (250, 90), 3); t(d, (276, 150), "aim off right", 12)
arrow(d, (242, 90), (218, 86), 3); t(d, (214, 102), "turn left", 11)
for k in range(10):
    x = 30 + k * 14
    d.rectangle([x, 150 + k * 8, x + 10, 156 + k * 8], outline=G, width=2)
t(d, (16, 128), "wall = handrail", 12)
t(d, (8, 246), "walk beside it", 11)
d.rectangle([370, 130, 460, 210], outline=G, width=2); t(d, (376, 136), "wood", 11)
L(d, [(370, 210), (370, 226)], 4); L(d, [(370, 226), (450, 226)], 4)
t(d, (350, 232), "wall corner =", 11); t(d, (350, 246), "attack point", 11)
t(d, (8, 266), "Hit the river right of the bridge; you know to turn left.", 12)
save(im, "nav_handrails")

im, d = new("SHADOW STICK (from above)")
stick = (240, 226); dot(d, stick, 7); t(d, (252, 222), "stick", 12)
w1, e1 = (130, 130), (350, 130)
L(d, [stick, w1], 3); L(d, [stick, (322, 140)], 3)
C(d, w1, 9, 4); dot(d, e1, 9)
L(d, [w1, e1], 4)
t(d, (100, 150), "1st mark", 12); t(d, (318, 150), "2nd mark", 12)
t(d, (88, 118), "W", 22); t(d, (368, 118), "E", 22)
arrow(d, (240, 128), (240, 50), 4)
t(d, (252, 44), "N", 22)
t(d, (130, 190), "shadow", 11); t(d, (300, 190), "15+ min later", 11)
t(d, (8, 244), "First mark is always west, anywhere on Earth.", 13)
t(d, (8, 262), "Left foot on 1st, right foot on 2nd: you face north.", 13)
save(im, "nav_shadow_stick")

im, d = new("NORTH STAR          SOUTHERN CROSS")
divider(d, 240)
plough = [(30, 220), (62, 200), (92, 196), (122, 204), (130, 236), (180, 238), (186, 204)]
for p in plough:
    star(d, p, 7)
L(d, plough[:4], 1); L(d, [plough[3], plough[4], plough[5], plough[6], plough[3]], 1)
ns = (210, 68)
dashed(d, (186, 204), ns, 2)
star(d, ns, 9); t(d, (140, 40), "North Star", 13)
t(d, (194, 214), "Pointers", 11)
t(d, (10, 248), "Plough: 5x the gap", 12)
dashed(d, ns, (210, 268), 1, 3, 5); t(d, (216, 254), "N", 14)
top, foot, left, right = (350, 50), (350, 84), (334, 66), (368, 62)
for p in (top, foot, left, right):
    star(d, p, 7)
L(d, [top, foot], 1); L(d, [left, right], 1)
pole = (350, 228)
dashed(d, foot, pole, 2)
pa, pb = (423, 151), (441, 173)
star(d, pa, 7); star(d, pb, 7); t(d, (400, 182), "Pointers", 11)
mid = ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2)
dashed(d, mid, pole, 2)
C(d, pole, 6, 2)
t(d, (290, 220), "pole", 12)
L(d, [(350, 236), (350, 266)], 2); t(d, (358, 254), "S", 14)
t(d, (378, 54), "Cross", 11)
t(d, (250, 110), "long axis", 11); t(d, (250, 124), "x4.5 to 5", 11)
t(d, (250, 266), "not to scale", 10)
save(im, "nav_stars")

# ---------------- Sanitation ----------------
im, d = new("CAT HOLE")
L(d, [(10, 150), (160, 150)], 3); L(d, [(220, 150), (470, 150)], 3)
L(d, [(160, 150), (166, 210), (214, 210), (220, 150)], 4)
for k in range(5):
    dot(d, (176 + k * 9, 202 - (k % 2) * 6), 3)
arrow(d, (240, 152), (240, 208), 2, 8); arrow(d, (240, 208), (240, 152), 2, 8)
t(d, (250, 170), "15-20 cm deep", 14)
t(d, (166, 120), "15 cm", 12)
L(d, [(170, 132), (210, 132)], 2)
# distance arrows to water
L(d, [(330, 150), (360, 140), (400, 146), (440, 138)], 2)
t(d, (330, 110), "water", 13)
arrow(d, (230, 96), (320, 96), 2); arrow(d, (230, 96), (180, 96), 2)
t(d, (190, 70), "60 m+ (70 steps)", 13)
t(d, (8, 40), "Downhill from your water. Away from camp and paths.", 12)
t(d, (8, 228), "Fill, tread down, mark with a stone.", 14)
t(d, (8, 250), "Bag pads and nappies. Wash hands.", 14)
save(im, "san_cat_hole")

im, d = new("TRENCH LATRINE")
# plan view of trench with soil pile, screen, handwash
d.rectangle([60, 90, 280, 120], outline=G, width=4)
t(d, (64, 66), "trench 20-30 cm wide", 12)
d.ellipse([60, 128, 280, 160], outline=G, width=3); t(d, (110, 136), "soil pile + scoop", 12)
L(d, [(250, 150), (290, 170)], 3)
L(d, [(40, 60), (40, 190), (300, 190), (300, 60)], 2)
t(d, (44, 194), "screen", 12)
L(d, [(30, 52), (310, 52)], 2); t(d, (316, 40), "ditch on", 12); t(d, (316, 54), "uphill side", 12)
# handwash
d.rectangle([330, 150, 360, 180], outline=G, width=3); t(d, (316, 186), "wash hands", 12)
arrow(d, (300, 170), (326, 168), 2, 8)
# water distance
L(d, [(420, 80), (440, 110), (430, 150), (450, 180)], 3); t(d, (392, 64), "well", 12)
arrow(d, (370, 120), (414, 120), 2, 8); t(d, (370, 96), "30 m+", 12)
t(d, (8, 216), "Cover each use with soil, 10 cm more each day.", 13)
t(d, (8, 236), "Full to 30 cm from top: fill, mound, mark.", 13)
t(d, (8, 256), "Downhill of water. Bottom 1.5 m above water table.", 13)
save(im, "san_trench")

im, d = new("TIPPY TAP")
L(d, [(80, 250), (80, 60)], 6); L(d, [(380, 250), (380, 60)], 6)
L(d, [(70, 64), (390, 64)], 6)
# jug
L(d, [(170, 64), (170, 84)], 3)
d.rounded_rectangle([140, 84, 220, 170], 10, outline=G, width=4)
d.rectangle([200, 74, 216, 86], outline=G, width=3)  # cap
t(d, (226, 88), "cap", 12)
dot(d, (210, 100), 4)
L(d, [(214, 100), (232, 118), (240, 150)], 2)
L(d, [(236, 120), (246, 150)], 2)
t(d, (232, 154), "water from hole", 11)
# cord from cap to pedal
L(d, [(208, 86), (300, 230)], 2)
L(d, [(270, 236), (360, 228)], 5); t(d, (282, 242), "foot pedal stick", 12)
# soap
L(d, [(110, 64), (110, 120)], 2); d.rounded_rectangle([96, 120, 124, 140], 6, outline=G, width=3)
t(d, (86, 144), "soap", 12)
for k in range(9):
    C(d, (120 + k * 18, 262), 5, 2)
t(d, (126, 238), "gravel", 12)
t(d, (8, 36), "Press pedal: jug tips, hands stay off it.", 13)
save(im, "san_tippy_tap")

im, d = new("SOAP FROM ASH AND FAT")
divider(d, 240)
# leach
d.polygon([(40, 60), (200, 60), (170, 180), (70, 180)], outline=G, width=4)
for k in range(5):
    L(d, [(50 + k * 8, 80 + k * 18), (190 - k * 8, 80 + k * 18)], 1)
t(d, (60, 86), "hardwood ash", 12)
L(d, [(76, 166), (164, 166)], 3); t(d, (80, 148), "straw / gravel", 11)
arrow(d, (120, 30), (120, 56), 3); t(d, (130, 32), "rainwater", 12)
L(d, [(120, 180), (120, 210)], 2); dot(d, (120, 214), 3); dot(d, (120, 226), 3)
d.rectangle([90, 230, 150, 262], outline=G, width=3); t(d, (156, 238), "lye", 13)
# pot
t(d, (250, 40), "2 parts fat : 1 part lye", 13)
d.rounded_rectangle([280, 120, 420, 200], 12, outline=G, width=4)
for k in range(3):
    L(d, [(300 + k * 40, 110), (310 + k * 40, 96), (300 + k * 40, 82)], 2)
L(d, [(350, 120), (380, 60)], 4); t(d, (386, 62), "wood spoon", 11)
for k in range(5):
    x = 300 + k * 24
    L(d, [(x, 230), (x + 6, 214), (x + 12, 230)], 3)
t(d, (250, 238), "boil until thick", 13)
t(d, (250, 258), "no aluminium. guard eyes.", 12)
save(im, "san_ash_lye")

# ---------------- Clothing ----------------
im, d = new("LAYERS (cut through)")
bands = [(40, 100, "SKIN"), (100, 190, "BASE"), (190, 300, "MID"), (300, 360, "SHELL")]
for x0, x1, name in bands:
    d.rectangle([x0, 60, x1, 220], outline=G, width=3)
    t(d, ((x0 + x1) // 2, 40), name, 13, "ma")
for k in range(4):
    for j in range(3):
        C(d, (212 + j * 34, 84 + k * 38), 9, 2)
t(d, (110, 228), "moves sweat", 11); t(d, (198, 228), "traps air", 11); t(d, (300, 228), "stops", 11); t(d, (300, 242), "wind, rain", 11)
arrow(d, (60, 130), (150, 130), 2, 9); t(d, (54, 136), "sweat", 10)
for y in (80, 140, 200):
    arrow(d, (460, y), (370, y), 3)
t(d, (400, 56), "wind", 12); t(d, (400, 166), "rain", 12)
t(d, (8, 260), "Shed before you sweat. Add before you chill.", 14)
save(im, "cloth_layers")

im, d = new("SEWING STITCHES")
for i, name in enumerate(["RUNNING", "BACKSTITCH", "WHIP"]):
    y = 60 + i * 70
    t(d, (8, y), name, 14)
    L(d, [(150, y + 28), (470, y + 28)], 1)
    if i == 0:
        for k in range(8):
            L(d, [(160 + k * 38, y + 28), (184 + k * 38, y + 28)], 5)
        t(d, (150, y + 38), "in and out. quick: hems, patches", 11)
    elif i == 1:
        for k in range(10):
            L(d, [(160 + k * 30, y + 28), (188 + k * 30, y + 28)], 5)
            dot(d, (160 + k * 30, y + 28), 3)
        t(d, (150, y + 38), "each stitch goes back to the last: strong seams", 11)
    else:
        L(d, [(150, y + 22), (470, y + 22)], 3)
        for k in range(10):
            x = 160 + k * 30
            L(d, [(x, y + 36), (x + 18, y + 10)], 4)
        t(d, (150, y + 40), "over the edge: tears, frayed ends", 11)
t(d, (8, 262), "Knot the end. Finish with 3 small stitches.", 13)
save(im, "cloth_stitches")

im, d = new("IMPROVISED CLOTHING")
divider(d, 160); divider(d, 320)
# bin bag poncho
d.polygon([(80, 50), (130, 90), (150, 240), (10, 240), (30, 90)], outline=G, width=4)
d.ellipse([66, 70, 94, 92], outline=G, width=3)
t(d, (8, 246), "bin bag: face hole", 11); t(d, (8, 262), "hood stays up", 11)
# blanket cloak
C(d, (240, 70), 16, 3)
d.polygon([(214, 88), (266, 88), (300, 236), (180, 236)], outline=G, width=4)
L(d, [(190, 160), (290, 160)], 4); t(d, (184, 166), "cord", 11, "ra")
t(d, (170, 246), "blanket cloak,", 11); t(d, (170, 262), "tied at waist", 11)
# slit goggles
d.rounded_rectangle([336, 120, 470, 160], 16, outline=G, width=4)
L(d, [(356, 140), (392, 140)], 3); L(d, [(414, 140), (450, 140)], 3)
L(d, [(336, 140), (326, 130)], 2); L(d, [(470, 140), (478, 130)], 2)
t(d, (330, 246), "slit goggles", 11); t(d, (330, 262), "stop snow blindness", 11)
save(im, "cloth_improvised")

# ---------------- Weather ----------------
im, d = new("CLOUD LEVELS (UK)")
for y in (100, 178):
    dashed(d, (10, y), (470, y), 1, 4, 6)
t(d, (10, 32), "HIGH above 6,000 m", 11); t(d, (10, 104), "MIDDLE 2,000-6,000 m", 11); t(d, (10, 182), "LOW below 2,000 m", 11)
# cirrus wisps
for k in range(3):
    x = 80 + k * 36
    d.arc([x, 50, x + 60, 90], 200, 320, fill=G, width=3)
t(d, (80, 86), "cirrus", 11)
L(d, [(220, 70), (330, 70)], 3); L(d, [(226, 78), (324, 78)], 2); C(d, (275, 60), 12, 2); t(d, (226, 84), "cirrostratus", 11)
# middle
for k in range(5):
    d.ellipse([90 + k * 22, 130, 108 + k * 22, 144], outline=G, width=2)
t(d, (86, 150), "altocumulus", 11)
d.rectangle([230, 124, 340, 140], outline=G, width=3); t(d, (232, 146), "altostratus", 11)
# low
L(d, [(110, 250), (110, 230)], 0)
d.arc([90, 214, 130, 250], 180, 360, fill=G, width=3); d.arc([116, 204, 160, 250], 180, 360, fill=G, width=3)
L(d, [(90, 248), (160, 248)], 3); t(d, (90, 254), "cumulus", 11)
d.rectangle([190, 220, 290, 236], outline=G, width=3); t(d, (196, 242), "stratus", 11)
# cumulonimbus tower with anvil
d.polygon([(350, 250), (360, 150), (340, 120), (330, 60), (470, 60), (440, 120), (430, 150), (440, 250)], outline=G, width=4)
for k in range(4):
    L(d, [(370 + k * 16, 252), (364 + k * 16, 276)], 2)
t(d, (372, 196), "Cb", 16)
t(d, (338, 40), "anvil = storm", 12)
save(im, "wx_clouds")

im, d = new("WARM FRONT coming towards you")
L(d, [(10, 250), (470, 250)], 3)
L(d, [(460, 250), (40, 70)], 4)                       # frontal surface, sloping up ahead of the front
t(d, (330, 60), "warm air rises", 13); t(d, (330, 76), "over cold air", 13)
t(d, (60, 200), "cold air", 13)
for k in range(3):
    d.arc([50 + k * 24, 36, 100 + k * 24, 66], 200, 320, fill=G, width=3)
t(d, (160, 40), "1 cirrus", 11)
L(d, [(140, 92), (220, 92)], 3); C(d, (180, 82), 9, 2); t(d, (226, 84), "2 halo", 11)
d.rectangle([210, 116, 300, 130], outline=G, width=3); t(d, (306, 116), "3 altostratus", 11)
d.rectangle([300, 148, 440, 176], outline=G, width=4)
t(d, (312, 155), "4 nimbostratus", 11)
for k in range(7):
    L(d, [(310 + k * 20, 180), (302 + k * 20, 244)], 2)
C(d, (30, 236), 6, 3); t(d, (20, 216), "you", 11)
t(d, (8, 260), "1 to 4 often takes 12 to 24 hours. Halo = plan now.", 12)
save(im, "wx_warm_front")

im, d = new("LIGHTNING: CAUGHT OUTSIDE")
divider(d, 250)
L(d, [(10, 240), (240, 240)], 3)
# crouch figure
C(d, (124, 150), 14, 4)
L(d, [(124, 164), (150, 196)], 5)       # back
L(d, [(150, 196), (110, 206), (120, 238)], 5)    # thigh, shin
L(d, [(150, 196), (140, 232)], 5)
L(d, [(132, 172), (112, 204)], 4)        # arms to knees
t(d, (10, 48), "squat, feet together,", 12); t(d, (10, 64), "hands on knees,", 12); t(d, (10, 80), "head down.", 12)
t(d, (10, 250), "Do not lie flat.", 12)
# right: no tree, no summit, flash to bang
L(d, [(300, 240), (300, 170)], 5); C(d, (300, 150), 26, 3)
L(d, [(270, 120), (330, 240)], 4); L(d, [(330, 120), (270, 240)], 4)
t(d, (262, 248), "no lone tree", 11)
L(d, [(360, 240), (410, 160), (460, 240)], 3)
L(d, [(386, 140), (434, 200)], 4); L(d, [(434, 140), (386, 200)], 4)
t(d, (370, 248), "no summit", 11)
L(d, [(420, 40), (404, 74), (420, 74), (400, 110)], 3)
t(d, (262, 40), "flash to bang:", 12); t(d, (262, 56), "3 s = 1 km", 12)
t(d, (262, 72), "<30 s: shelter", 12)
t(d, (262, 266), "Wait 30 min after last thunder.", 11)
save(im, "wx_lightning")
