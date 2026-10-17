"""Draw the bowline as two big two-step pictures (steps 1-2 and 3-4).

Run from the repo root: python3 tools/gen_bowline.py
Each rope point is (x, y, layer). A segment takes the layer of its first point;
higher layers are drawn later, on top, with a black gap so crossings read as over/under.
"""
import math
from PIL import Image, ImageDraw, ImageFont

G = (0x1A, 0xFF, 0x80)
K = (0, 0, 0)
W, H = 480, 284
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
ROPE, HALO = 9, 23


def font(size):
    return ImageFont.truetype(FONT, size)


def spline(p, n=14):
    if len(p) < 3:
        return list(p)
    P = [p[0]] + list(p) + [p[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n
            out.append(tuple(0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * t
                                    + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t * t
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t ** 3) for j in (0, 1)))
    out.append(tuple(p[-1][:2]))
    return out


def pieces(path, n=14):
    pts = [(x, y) for x, y, _ in path]
    layers = [lay for _, _, lay in path]
    sp = spline(pts, n)
    out = []
    for i, q in enumerate(sp):
        lay = layers[min(i // n, len(layers) - 1)]
        if out and out[-1][0] == lay:
            out[-1][1].append(q)
        else:
            prev = out[-1][1][-1] if out else q
            out.append((lay, [prev, q]))
    return out, sp


def arrow(d, a, b):
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    s = 20
    tip = (b[0] + 12 * math.cos(ang), b[1] + 12 * math.sin(ang))
    d.polygon([tip,
               (tip[0] - s * math.cos(ang - 0.5), tip[1] - s * math.sin(ang - 0.5)),
               (tip[0] - s * math.cos(ang + 0.5), tip[1] - s * math.sin(ang + 0.5))], fill=G)


def panel(d, x0, num, label, path, show_arrow, tags=()):
    pw = W // 2
    if x0:
        d.line([(x0, 34), (x0, 278)], fill=G, width=2)
    items, sp = pieces([(x0 + 125 + (x - 125) * 1.5, y, lay) for x, y, lay in path])
    for k, (lay, geo) in enumerate(sorted(items, key=lambda t: t[0])):
        d.line(geo, fill=K, width=HALO, joint="curve")
        d.line(geo, fill=G, width=ROPE, joint="curve")
    if show_arrow:
        arrow(d, sp[-4], sp[-1])
    d.ellipse([x0 + 6, 36, x0 + 36, 66], fill=K, outline=G, width=3)
    d.text((x0 + 21, 51), str(num), fill=G, font=font(20), anchor="mm")
    for text, (tx, ty) in tags:
        d.text((x0 + tx, ty), text, fill=G, font=font(13))
    for j, line in enumerate(label):
        d.text((x0 + 8, 236 + j * 21), line, fill=G, font=font(17))


# Standing part comes down from the anchor; the small loop ("hole") sits to its right.
STAND = [(118, 40, 0), (118, 72, 0), (118, 104, 0), (121, 128, 0), (136, 144, 0),
         (158, 144, 0), (174, 124, 0), (172, 96, 0), (154, 78, 0), (134, 80, 2),
         (118, 92, 2), (100, 112, 2), (90, 145, 2)]
TAIL = [(86, 180, 2), (100, 206, 2), (136, 214, 2), (166, 198, 2), (174, 174, 2)]
# Up through the hole from underneath: under the near edge, over the far edge.
UP = [(166, 158, -1), (158, 144, -1), (154, 128, 3), (150, 104, 3), (146, 82, 3), (142, 62, 3)]
# Round behind the standing part.
ROUND = [(132, 50, -1), (118, 47, -1), (102, 50, 3), (94, 62, 3)]
# Back down the hole beside itself: over the far edge, under the near edge.
DOWN = [(104, 72, 3), (128, 80, 3), (136, 100, 3), (140, 124, -1), (140, 146, -1), (138, 168, -1)]

steps = [
    ("Make a small loop. The", "end side lies ON TOP.", STAND + TAIL, True,
     [("standing", (134, 36)), ("hole", (196, 56)), ("end", (200, 150))]),
    ("End comes UP through", "the hole from below.", STAND + TAIL + UP, True,
     [("standing", (168, 36))]),
    ("Round BEHIND the", "standing part.", STAND + TAIL + UP + ROUND, True,
     [("standing", (168, 36))]),
    ("Back DOWN the hole.", "Pull standing + end.", STAND + TAIL + UP + ROUND + DOWN, True,
     [("standing", (168, 36))]),
]

for name, pair in (("knot_bowline", steps[:2]), ("knot_bowline_2", steps[2:])):
    im = Image.new("RGB", (W, H), K)
    d = ImageDraw.Draw(im)
    first = 1 if name == "knot_bowline" else 3
    d.text((44, 4), f"BOWLINE  steps {first}-{first + 1}", fill=G, font=font(20))
    for i, (l1, l2, path, show, tags) in enumerate(pair):
        panel(d, i * (W // 2), first + i, (l1, l2), path, show, tags)
    im.save(f"content/img/{name}.png")
