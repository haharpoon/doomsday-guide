"""Step diagrams for the knot, hitch, bend, loop and lashing cards.

Run from the repo root:
    python3 tools/gen_knots2.py              # every picture, into content/img/
    python3 tools/gen_knots2.py clove sq     # only names containing these words
    python3 tools/gen_knots2.py --out /tmp/k --sheet --debug
        --out    write somewhere else
        --sheet  also write /tmp/knot_sheets/*.png contact sheets (4 per sheet)
        --debug  number every crossing (to check the over/under letters)

Every picture is 480x284, green on black. Ropes are drawn with tools/rope.py:
z is height towards you, so at a crossing the higher strand is on top and the
lower one shows a black gap. Most knots are planned flat with tools/knot2d.py,
which takes an over/under letter per crossing and works out the heights.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rope import Diagram, arc, bight, helix, join, line, offset, reverse, smooth, tf  # noqa: E402
from knot2d import Knot, cap, pair  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "content", "img")
DIAGRAMS = {}
DEBUG = False
F, B = 2.0, -2.0  # base heights: in front of a post, behind it


def diagram(name):
    def wrap(fn):
        DIAGRAMS[name] = fn
        return fn

    return wrap


def knot(paths, spec="", kinds=None, name="", **kw):
    k = Knot(paths, kinds=kinds, spec=spec, **kw)
    k.report(name)
    return k


def post(p, x, w, y0=-80, y1=300):
    """A vertical post or tree, w wide, centred on x."""
    return p._add([(x, y0, 0), (x, y1, 0)], w * p.scale, "post")


def bar(p, y, w, x0=-80, x1=300):
    """A horizontal rail, pole or branch, w thick, centred on y."""
    return p._add([(x0, y, 0), (x1, y, 0)], w * p.scale, "post")


def show(p, k, i=0, upto=None, frm=None, debug=False, **kw):
    st = p.rope(k.path(i, upto, frm), **kw)
    if DEBUG and debug:
        k.debug(p)
    return st


def at(k, i, x, y, extra=0.0):
    """Arc length on rope i nearest (x, y), plus extra."""
    return k.nearest(i, x, y) + extra


def trefoil(cx, cy, s, t0=335, t1=25, step=-5, rot=0.0, zs=1.0):
    """An overhand knot as a trefoil cut open at one lobe (z alternates)."""
    pts = []
    t = t0
    while (t >= t1) if step < 0 else (t <= t1):
        r = math.radians(t)
        x = math.sin(r) + 2 * math.sin(2 * r)
        y = -(math.cos(r) - 2 * math.cos(2 * r))
        pts.append((x, y, -math.sin(3 * r) * zs * 2))
        t += step
    return tf(pts, cx, cy, s, rot)


def leads(k, left=-12, right=102, reach=10, drop=0.0):
    """Give a knot body two ends that leave sideways."""
    (x0, y0, z0), (x1, y1, _z1) = k[0], k[1]
    n = math.hypot(x1 - x0, y1 - y0) or 1
    a = (x0 - (x1 - x0) / n * reach, y0 - (y1 - y0) / n * reach, z0)
    (xa, ya, za), (xb, yb, _zb) = k[-1], k[-2]
    n = math.hypot(xa - xb, ya - yb) or 1
    b = (xa + (xa - xb) / n * reach, ya + (ya - yb) / n * reach, za)
    return join([(left, a[1] + drop, z0), a], k, [b, (right, b[1] + drop, za)])


# ================================================================ stoppers

# loose overhand, standing part from the top: C1 end over, C2 under, C3 over
OVERHAND = [(45, -10), (45, 10), (45, 45), (47, 68), (56, 86), (72, 88), (84, 74), (82, 52), (66, 40),
            (45, 43), (28, 48), (16, 64), (20, 84), (34, 96), (48, 86), (60, 70), (72, 62), (86, 64),
            (98, 76), (104, 96), (106, 118)]


@diagram("knot_overhand")
def overhand():
    d = Diagram("OVERHAND KNOT", 3)
    k = knot([OVERHAND], spec="ouo", name="overhand")
    box = (4, -4, 110, 118)
    p = d.panel("Make a loop: end over the standing part", box)
    show(p, k, 0, at(k, 0, 24, 52), arrow=True, start="standing", start_at=(66, 4))
    p = d.panel("Round, then up through the loop", box)
    show(p, k, 0, at(k, 0, 66, 64), arrow=True, start="standing", start_at=(66, 4))
    p = d.panel("Pull both. Leave a tail", box)
    show(p, k, 0, start="standing", end="end", start_at=(66, 4), end_at=(90, 112), debug=True)
    return d


# loose figure-eight, standing part from the top
FIG8 = [
    (50, -8, 0), (50, 12, 0), (50, 26, 1), (50, 48, -1), (50, 62, 0), (53, 73, 0), (62, 80, 1),
    (75, 79, 0), (84, 66, 0), (82, 52, 0), (72, 47, 0), (66, 47, -1), (50, 48, 1), (36, 49, 0),
    (25, 40, 0), (27, 27, 0), (38, 23, 0), (50, 26, -1), (63, 26, 0), (71, 33, 0), (66, 47, 1),
    (63, 62, 0), (62, 80, -1), (62, 96, 0), (61, 120, 0),
]


@diagram("knot_fig8_stopper")
def fig8_stopper():
    d = Diagram("FIGURE-EIGHT STOPPER", 3)
    box = (14, -4, 96, 112)
    k = knot([FIG8], name="fig8")
    p = d.panel("Loop: the end crosses on top", box)
    show(p, k, 0, at(k, 0, 36, 49), arrow=True, start="standing", start_at=(66, 4))
    p = d.panel("Round behind the standing part", box)
    show(p, k, 0, at(k, 0, 70, 32), arrow=True, start="standing", start_at=(66, 4))
    p = d.panel("Down through the first loop", box)
    show(p, k, 0, start="standing", end="end", start_at=(66, 4), end_at=(76, 106), debug=True)
    return d


# like the overhand, but the end goes up through the loop twice
DOUBLE_OH = [(40, -14), (40, 10), (40, 40), (41, 76), (50, 98), (70, 104), (88, 92), (93, 66), (80, 44),
             (58, 37), (40, 40), (22, 44), (8, 62), (12, 88), (26, 104), (42, 108), (54, 96), (64, 80),
             (76, 64), (88, 54), (102, 52), (112, 64), (112, 90), (100, 110), (80, 120), (66, 114), (66, 100),
             (74, 86), (86, 76), (98, 74), (110, 78), (122, 86), (130, 96)]


@diagram("knot_double_overhand")
def double_overhand():
    d = Diagram("DOUBLE OVERHAND STOPPER", 3)
    k = knot([DOUBLE_OH], spec="ouo" + "uoo", name="double_overhand")
    box = (2, -4, 130, 124)
    p = d.panel("An overhand knot, but do not pull", box)
    show(p, k, 0, at(k, 0, 108, 56), arrow=True, start="standing", start_at=(62, 4))
    p = d.panel("Round again, up through the loop again", box)
    show(p, k, 0, at(k, 0, 80, 82), arrow=True, start="standing", start_at=(62, 4))
    p = d.panel("Pull both: the turns roll together", box)
    show(p, k, 0, start="standing", end="end", start_at=(62, 4), end_at=(116, 110), debug=True)
    return d


# ================================================================ hitches

def clove_path(C, R, a, b, t0, t1, tail=50):
    """Clove hitch on a vertical post: two front bands at y=a and y=b, a diagonal from
    the top left (t0) to the bottom right (t1) over both."""
    return [(-40, a, F), (10, a, F), (C, a, F), (C + R - 3, a + 1, F), (C + R + 4, a + 5, 0), (C + R - 3, a + 9, B),
            (C, a + 8, B), (C - R + 3, t0 + 2, B), (C - R - 4, t0 - 2, 0), (C - R + 1, t0 - 5, F),
            (C - R + 6, t0 - 1, F), (C, (t0 + t1) / 2, F), (C + R - 6, t1 + 1, F), (C + R - 1, t1 + 3, F),
            (C + R + 4, t1, 0), (C + R - 3, t1 - 4, B), (C, b + 3, B), (C - R + 3, b - 1, B),
            (C - R - 4, b - 1, 0), (C - R + 2, b + 1, F), (C, b, F), (C + R, b, F), (C + R + 20, b, F),
            (C + R + tail, b, F)]


@diagram("knot_clove")
def clove():
    d = Diagram("CLOVE HITCH", 3, rope_w=10)
    C, R = 55, 17
    a, b, t0, t1 = 52, 96, 34, 112
    k = knot([clove_path(C, R, a, b, t0, t1)], spec="ou", name="clove")
    box = (0, 10, 110, 140)
    caps = ["End over the post, round behind", "Cross over its own line, round again",
            "Tuck under the cross. Pull both"]
    cuts = [at(k, 0, C - R + 2, t0 - 3), at(k, 0, C - 6, b), None]
    for i, c in enumerate(caps):
        p = d.panel(c, box)
        post(p, C, 2 * R)
        show(p, k, 0, cuts[i], arrow=i < 2, start="standing", start_at=(24, a - 12),
             end="end" if i == 2 else None, end_at=(100, b + 12), debug=i == 2)
    return d


def bar_turns(Y, hw, fronts, out=None):
    """Turns round a horizontal bar centred on y=Y, hw half its thickness.

    fronts: (x_bottom, x_top) for each pass up the front. Between passes the rope
    goes over the top and down the back. out: x where it leaves under the bar,
    behind, after the last pass."""
    pts = []
    for i, (xb, xt) in enumerate(fronts):
        pts += [(xb, Y + hw + 6, F if i == 0 else 0), (xb + (xt - xb) * 0.1, Y + hw - 3, F),
                (xt - (xt - xb) * 0.1, Y - hw + 3, F), (xt + 3, Y - hw - 5, 0)]
        nxt = fronts[i + 1][0] if i + 1 < len(fronts) else out
        if nxt is None:
            break
        pts += [(xt + 6, Y - hw + 3, B), (nxt - 6, Y + hw - 3, B)]
        if i + 1 < len(fronts):
            pts += [(nxt - 3, Y + hw + 5, 0)]
    return pts


def half_hitch_down(core_x, y, x_in, x_out, w=13, h=8):
    """A half hitch round a vertical core line at core_x, working downward.

    Arrives from above at x_in (right of the core), goes behind the core,
    round, over it, under itself, and leaves down at x_out. Letters: u o u."""
    return [(x_in + 1, y - h - 4), (x_in - 3, y + h - 2), (core_x, y + h + 1), (core_x - w + 2, y + h - 1),
            (core_x - w, y), (core_x - w + 4, y - h + 2), (core_x, y - h + 2), (x_in + 2, y - h + 3),
            (x_out, y - 1), (x_out + 3, y + h + 8)]


@diagram("knot_half_hitches")
def half_hitches():
    d = Diagram("TWO HALF HITCHES", 3)
    Y, hw, cx = 24, 10, 36
    path = join([(cx, 150, 0), (cx, 70, 0), (cx, Y + hw + 9, 0)], bar_turns(Y, hw, [(cx, cx + 4)], out=54),
                [(55, Y + hw + 8, B), (56, 46, 0)],
                half_hitch_down(cx, 62, 56, 62), half_hitch_down(cx, 92, 64, 70)[1:],
                [(76, 118, 0), (80, 132, 0)])
    k = knot([path], spec="uou" + "uou", name="half_hitches")
    box = (0, 0, 100, 140)
    caps = ["Round the bar. End down beside the line", "Behind the line, over it, under itself",
            "Again below, the same way. Snug up"]
    cuts = [at(k, 0, 56, 50), at(k, 0, 64, 64), None]
    for i, c in enumerate(caps):
        p = d.panel(c, box)
        bar(p, Y, 2 * hw)
        show(p, k, 0, cuts[i], arrow=i < 2, start="standing", start_at=(cx - 18, 124),
             end="end" if i == 2 else None, end_at=(90, 120), debug=i == 2)
    return d


@diagram("knot_round_turn")
def round_turn():
    d = Diagram("ROUND TURN AND TWO HALF HITCHES", 3, title_size=15)
    Y, hw, cx = 24, 10, 30
    path = join([(cx, 150, 0), (cx, 70, 0), (cx, Y + hw + 9, 0)], bar_turns(Y, hw, [(cx, cx + 4), (cx + 12, cx + 16)], out=60),
                [(61, Y + hw + 8, B), (62, 46, 0)],
                half_hitch_down(cx, 64, 62, 68), half_hitch_down(cx, 94, 70, 76)[1:],
                [(82, 120, 0), (86, 134, 0)])
    k = knot([path], spec="uou" + "uou", name="round_turn")
    box = (0, 0, 100, 140)
    caps = ["Two full turns round the bar", "Half hitch round the standing part",
            "A second the same way. Snug up"]
    cuts = [at(k, 0, 62, 50), at(k, 0, 70, 66), None]
    for i, c in enumerate(caps):
        p = d.panel(c, box)
        bar(p, Y, 2 * hw)
        show(p, k, 0, cuts[i], arrow=i < 2, start="standing", start_at=(cx - 14, 124),
             end="end" if i == 2 else None, end_at=(92, 122), debug=i == 2)
    return d


def half_hitch_up(core_x, y, x_in, x_out, w=13, h=8):
    """Mirror of half_hitch_down: arrives from below at x_in, leaves up at x_out."""
    return [(x, 2 * y - yy) for x, yy in half_hitch_down(core_x, y, x_in, x_out, w, h)]


@diagram("knot_buntline")
def buntline():
    d = Diagram("BUNTLINE HITCH", 3)
    Y, hw, cx = 24, 10, 36
    down = [(60, Y + hw + 8, B), (62, 70, 0), (62, 112, 0), (56, 124, 0), (48, 122, 0)]
    path = join([(cx, 150, 0), (cx, 70, 0), (cx, Y + hw + 9, 0)], bar_turns(Y, hw, [(cx, cx + 4)], out=58), down,
                half_hitch_up(cx, 106, 48, 50), half_hitch_up(cx, 76, 50, 52)[1:],
                [(52, 52, 0), (51, 44, 0)])
    k = knot([path], spec="uou" + "uou", name="buntline")
    box = (0, 0, 100, 140)
    caps = ["Round the bar, end down past the line", "Half hitch round the line, working up",
            "Second hitch nearer the bar. Pull hard"]
    cuts = [at(k, 0, 48, 122), at(k, 0, 50, 96), None]
    for i, c in enumerate(caps):
        p = d.panel(c, box)
        bar(p, Y, 2 * hw)
        show(p, k, 0, cuts[i], arrow=i < 2, start="standing", start_at=(cx - 18, 134),
             end="end" if i == 2 else None, end_at=(70, 48), debug=i == 2)
    return d


@diagram("knot_cow")
def cow():
    d = Diagram("COW HITCH (GIRTH HITCH)", 3)
    Y, hw = 30, 11
    L, Rt, oL, oR = 36, 64, 22, 78
    path = [(L, 150, 0), (L, 80, 0), (L, Y + hw + 6, F), (L, Y - hw + 3, F), (L + 3, Y - hw - 5, 0),
            (L + 6, Y - hw + 3, B), (oL + 4, Y + hw - 3, B), (oL - 1, Y + hw + 5, 0), (oL, Y + hw - 4, F),
            (oL + 6, Y + 1, F), (L, Y + 2, F), ((L + Rt) / 2, Y + 2, F), (Rt, Y + 2, F), (oR - 6, Y + 1, F),
            (oR, Y + hw - 4, F), (oR + 1, Y + hw + 5, 0), (oR - 4, Y + hw - 3, B), (Rt - 6, Y - hw + 3, B),
            (Rt - 3, Y - hw - 5, 0), (Rt, Y - hw + 3, F), (Rt, Y + hw + 6, F), (Rt, 80, 0), (Rt, 150, 0)]
    k = knot([path], spec="ou", name="cow")
    box = (0, 0, 100, 140)
    caps = ["Up the front, over, round the bar", "Across the front, over the line, round",
            "Down the front, under the cross"]
    cuts = [at(k, 0, oL + 6, Y + 1), at(k, 0, Rt - 3, Y - hw - 5), None]
    for i, c in enumerate(caps):
        p = d.panel(c, box)
        bar(p, Y, 2 * hw)
        show(p, k, 0, cuts[i], arrow=i < 2, start="standing", start_at=(L - 20, 120),
             end="end" if i == 2 else None, end_at=(Rt + 14, 120), debug=i == 2)
    return d


@diagram("knot_constrictor")
def constrictor():
    d = Diagram("CONSTRICTOR KNOT", 3, rope_w=10)
    C, R = 55, 17
    a, b, t0, t1 = 52, 96, 34, 112
    base = clove_path(C, R, a, b, t0, t1)[:-5]
    tuck = [(C - R - 4, b - 1, 0), (C - R + 2, b + 1, F), (C - 6, b - 6, F), (C + 6, a - 4, F), (C + R - 2, a - 16, F),
            (C + R + 16, a - 30, F), (C + R + 40, a - 40, F)]
    k = knot([join(base, tuck)], spec="ouu", name="constrictor")
    box = (0, 0, 110, 140)
    caps = ["Start a clove hitch: round, cross over", "Round again. Tuck under the cross...",
            "...and under the first turn too. Pull"]
    cuts = [at(k, 0, C - R - 3, t0 - 2), at(k, 0, C - 6, b - 6), None]
    for i, c in enumerate(caps):
        p = d.panel(c, box)
        post(p, C, 2 * R)
        show(p, k, 0, cuts[i], arrow=i < 2, start="standing", start_at=(24, a - 12),
             end="end" if i == 2 else None, end_at=(96, a - 22), debug=i == 2)
    return d


def twist(p, q, turns, amp, side=1, z=None):
    """Points of an end twisted round the straight strand p->q (zig-zag across it).

    With z (the strand's height) the end is raised over and dropped under the
    strand at alternate crossings, so no letters are needed."""
    out = []
    dx, dy = q[0] - p[0], q[1] - p[1]
    n = math.hypot(dx, dy)
    nx, ny = -dy / n, dx / n
    steps = int(turns * 8)
    for i in range(steps + 1):
        t = i / steps
        th = 2 * math.pi * turns * t + math.pi / 2
        o = side * amp * math.sin(th)
        pt = (p[0] + dx * t + nx * o, p[1] + dy * t + ny * o)
        out.append(pt if z is None else pt + (z + 1.6 * math.cos(th),))
    return out


@diagram("knot_rolling")
def rolling():
    d = Diagram("ROLLING HITCH", 3)
    Y, hw = 44, 12
    top, bot = Y - hw - 5, Y + hw + 5
    path = [(-20, 96, 0), (6, 72, 0), (16, Y + hw + 4, 0), (24, Y + hw - 3, F), (50, Y, F), (70, Y - hw + 3, F), (74, top, 0), (77, Y - hw + 3, B),
            (64, Y + hw - 3, B), (62, bot, 0), (60, Y + hw - 2, F), (54, Y - hw + 2, F), (52, top, 0),
            (50, Y - hw + 3, B), (42, Y + hw - 3, B), (40, bot, 0), (38, Y + hw - 2, F), (32, Y - hw + 2, F),
            (30, top, 0), (33, Y - hw + 3, B), (60, Y, B), (85, Y + hw - 3, B), (88, bot, 0), (90, Y + hw - 2, F),
            (95, Y - hw + 2, F), (97, top, 0), (100, Y - hw + 3, B), (104, Y + hw - 3, B), (107, bot, 0),
            (104, Y + hw - 1, F), (92, Y - 2, F), (84, Y - hw - 2, F), (78, 16, F), (72, 6, F)]
    k = knot([path], spec="oou", name="rolling")
    box = (8, 4, 112, 88)
    caps = ["Round the pole, over the line", "Round again, beside it, over the line",
            "Then round on the far side, tuck under"]
    cuts = [at(k, 0, 40, bot), at(k, 0, 88, bot), None]
    for i, c in enumerate(caps):
        p = d.panel(c, box)
        bar(p, Y, 2 * hw)
        show(p, k, 0, cuts[i], arrow=i < 2, start="pull", start_at=(24, 86),
             end="end" if i == 2 else None, end_at=(86, 8), debug=i == 2)
    return d


@diagram("knot_taut_line")
def taut_line():
    d = Diagram("TAUT-LINE HITCH", 3)
    S = 40
    path = [(S, -20), (S, 60), (S, 112), (S + 1, 122, 0), (S + 6, 130, B), (S + 24, 130, B), (S + 29, 122, 0),
            (S + 30, 100), (S + 30, 50), (S + 26, 40), (S + 14, 36), (S, 38), (S - 12, 42), (S - 14, 48),
            (S - 10, 52), (S, 54), (S + 10, 56), (S + 12, 62), (S + 6, 66), (S, 68), (S - 12, 70), (S - 14, 76),
            (S - 10, 80), (S, 82), (S + 12, 84), (S + 18, 78), (S + 19, 60), (S + 19, 34), (S + 14, 18), (S, 16),
            (S - 12, 18), (S - 14, 24), (S - 10, 28), (S, 30), (S + 12, 31), (S + 22, 32), (S + 36, 38),
            (S + 48, 50), (S + 52, 66)]
    k = knot([path], spec="ouou" + "o" + "ouu", name="taut_line")
    box = (0, -24, 100, 140)
    caps = ["Round the stake. Two turns inside the loop", "Cross up over them, one turn outside",
            "Tuck under itself. Slide to tighten"]
    cuts = [at(k, 0, S + 12, 84), at(k, 0, S + 12, 31, -8), None]
    for i, c in enumerate(caps):
        p = d.panel(c, box)
        p._add([(S + 15, 116, 0), (S + 15, 150, 0)], 12 * p.scale, "post")
        show(p, k, 0, cuts[i], arrow=i < 2, start="to tent", start_at=(S - 18, -14),
             end="end" if i == 2 else None, end_at=(S + 50, 76), debug=i == 2)
        p.label(S + 36, 140, "stake")
    return d


@diagram("knot_timber")
def timber():
    d = Diagram("TIMBER HITCH", 3)
    Y, hw = 70, 14
    tw = twist((82, 52), (52, 86), 3, 8, z=F)
    path = join([(130, 6, 0), (90, 28, 0), (52, 50, 0), (45, Y - hw - 3, 0), (46, Y - hw + 3, B), (50, Y + hw - 3, B),
                 (52, Y + hw + 5, 0), (56, Y + hw - 3, F), (70, Y - 4, F), (80, 54, F), (86, 36, F), (88, 28, F),
                 (94, 22, F), (90, 14, F), (80, 18, F), (74, 30, F), (76, 46, F)], tw,
                [(46, 92, F), (40, 100, F)])
    k = knot([path], spec="uo", name="timber")
    box = (0, 0, 120, 120)
    caps = ["Round the log, then round the line", "Twist the end round its own turn",
            "Three twists or more. Pull the line"]
    cuts = [at(k, 0, 76, 46), at(k, 0, *tw[10]), None]
    for i, c in enumerate(caps):
        p = d.panel(c, box)
        bar(p, Y, 2 * hw)
        show(p, k, 0, cuts[i], arrow=i < 2, start="pull", start_at=(110, 4),
             end="end" if i == 2 else None, end_at=(30, 104), debug=i == 2)
    return d


@diagram("knot_munter")
def munter():
    d = Diagram("MUNTER HITCH", 3)
    Y, hw = 70, 6
    cx = 52
    top, bot = Y - hw - 5, Y + hw + 5
    path = [(cx - 10, 150, 0), (cx - 10, 110, 0), (cx - 10, bot + 2, F), (cx - 9, Y - hw + 1, F), (cx - 7, top, 0),
            (cx - 4, Y - hw + 1, B), (cx - 6, Y + hw - 1, B), (cx - 8, bot + 4, 0), (cx - 22, bot + 10, 0),
            (cx - 26, bot + 2, F), (cx - 16, Y + 4, F), (cx + 2, Y - 2, F), (cx + 8, Y - hw + 1, F),
            (cx + 10, top, 0), (cx + 13, Y - hw + 1, B), (cx + 14, Y + hw - 1, B), (cx + 15, bot + 6, B),
            (cx + 16, 110, B), (cx + 16, 150, B)]
    k = knot([path], spec="o", name="munter")
    box = (6, 26, 100, 140)
    caps = ["Clip the rope through the locking biner", "Bring the brake side across the load side",
            "Clip it in again. Lock the gate"]
    cuts = [at(k, 0, cx - 6, Y + hw - 1), at(k, 0, cx + 2, Y - 2), None]
    for i, c in enumerate(caps):
        p = d.panel(c, box)
        p.ring(cx + 2, 22, 32, w=7, tilt=1.5)
        show(p, k, 0, cuts[i], arrow=i < 2, start="load", start_at=(cx - 24, 128),
             end="brake" if i == 2 else None, end_at=(cx + 34, 128), debug=i == 2)
        p.label(cx + 2, 34, "locking biner")
    return d


# ================================================================ bends and loops (first set)

def _ss(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def reef_rope(cx=50, cy=60, mirror=False, x0=-6, tip=78, narrow=5.0, wide=15.0):
    """One rope of a flat reef knot: a bight with a narrow neck and wide head.

    Runs from the lower lead, round its head at x=tip, back out along the upper
    lead. The other rope is the same, mirrored about cx, with z flipped."""
    def w(x):
        return narrow + (wide - narrow) * _ss((x - 32) / 34) + 6 * _ss((14 - x) / 16)

    def z(x):
        return -math.cos(2 * math.pi * (x - 28) / 44)

    low = [(x, cy + w(x), z(x)) for x in range(x0, 69, 4)]
    head = [(70 + 8 * math.sin(math.radians(a)), cy + (wide + 1) * math.cos(math.radians(a)), -1)
            for a in range(30, 160, 25)]
    up = [(x, cy - w(x), z(x)) for x in range(68, x0 - 1, -4)]
    pts = low + head + up
    if mirror:
        pts = [(2 * cx - x, y, -zz) for x, y, zz in pts]
    return pts


@diagram("knot_square")
def square():
    d = Diagram("SQUARE (REEF) KNOT", 3)
    box = (0, 0, 100, 134)
    # first half knot: right end over the left, then under it
    L1 = [(22, 146, 0), (32, 112, 0), (50, 98, -1), (62, 86, 0), (50, 74, 1), (38, 64, 0.3)]
    R1 = [(78, 146, 0), (68, 112, 0), (50, 98, 1), (38, 86, 0), (50, 74, -1), (62, 64, -0.3)]
    p = d.panel("Right end over left, and under", box)
    p.rope(L1 + [(30, 46, 0)], start="left", start_at=(14, 126))
    p.rope(R1 + [(70, 46, 0)], start="right", start_at=(88, 126))
    # second half knot: now the left end goes over the right, and under
    L2 = L1 + [(50, 52, 1), (62, 42, 0), (50, 30, -1), (38, 22, 0), (34, 8, 0)]
    R2 = R1 + [(50, 52, -1), (38, 42, 0), (50, 30, 1), (62, 22, 0), (66, 8, 0)]
    p = d.panel("Left end over right, and under", box)
    p.rope(L2, start="left", start_at=(14, 126))
    p.rope(R2, start="right", start_at=(88, 126))
    p = d.panel("Pull flat. Ends lie side by side", box)
    A = [(50 + (x - 50) * 0.82, 66 + (y - 66) * 1.6, z) for x, y, z in reef_rope(cy=66)]
    B = [(50 + (x - 50) * 0.82, 66 + (y - 66) * 1.6, z) for x, y, z in reef_rope(cy=66, mirror=True)]
    p.rope(A, start="standing", end="end", start_at=(16, 104), end_at=(16, 28))
    p.rope(B, start="standing", end="end", start_at=(84, 104), end_at=(84, 28))
    return d


def sheet_paths(double=False, cy=60, X=60, h=15):
    """Thick bight opening left; thin rope up through it, round, tucked under itself."""
    up_y, lo_y = cy - h, cy + h
    thick = [(-10, lo_y, 0), (40, lo_y, 0), (X + 10, lo_y, 0), (X + 20, lo_y - 4, 0), (X + 24, cy, 0),
             (X + 20, up_y + 4, 0), (X + 10, up_y, 0), (40, up_y, 0), (-4, up_y, 0)]
    # thin: from below, under the lower leg, up over the upper leg
    lead = [(X + 2, 150, -0.3), (X, lo_y + 18, -0.6), (X, lo_y, -1), (X, cy, 0), (X, up_y, 1),
            (X - 3, up_y - 12, 0.6)]
    wrap1 = [(X - 11, up_y - 17, 0.2), (X - 20, up_y - 7, -0.6), (X - 21, up_y, -1), (X - 21, lo_y, -1),
             (X - 20, lo_y + 9, -0.6), (X - 14, lo_y + 16, 0.1), (X - 9, lo_y + 8, 0.6), (X - 8, lo_y, 1)]
    tuck1 = [(X - 5, cy + 6, 0.8), (X, cy + 1, -0.6), (X + 6, cy - 5, 0.4)]
    out1 = [(X + 11, up_y + 5, 0.9), (X + 14, up_y, 1.1), (X + 19, up_y - 13, 0.6), (X + 26, up_y - 30, 0.3)]
    if not double:
        return thick, lead, wrap1, tuck1, out1
    over = [(X + 10, up_y + 5, 0.9), (X + 11, up_y, 1.1), (X + 6, up_y - 15, 0.8)]
    wrap2 = [(X - 12, up_y - 25, 0.5), (X - 29, up_y - 10, -0.6), (X - 30, up_y, -1), (X - 30, lo_y, -1),
             (X - 29, lo_y + 12, -0.6), (X - 21, lo_y + 23, 0.1), (X - 15, lo_y + 11, 0.6), (X - 14, lo_y, 1),
             (X - 7, cy - 3, 0.9), (X, cy - 7, -0.6), (X + 6, cy - 10, 0.4)]
    out2 = [(X + 9, up_y - 1, 1.4), (X + 13, up_y - 15, 0.8), (X + 18, up_y - 32, 0.3)]
    return thick, lead, wrap1, tuck1, over + wrap2, out2


@diagram("knot_sheet_bend")
def sheet_bend():
    d = Diagram("SHEET BEND", 3)
    box = (8, 6, 96, 124)
    thick, lead, wrap1, tuck1, out1 = sheet_paths(cy=70)
    p = d.panel("Bight in the thick rope", box)
    p.rope(thick, start="thick", end="end", width=d.rope_w + 4, start_at=(16, 100), end_at=(16, 42))
    p.rope([(62, 150, -0.3), (60, 112, 0)], start="thin", start_at=(76, 124))
    p.arrow([(60, 112, 0), (60, 96, -0.6), (60, 83, -1), (60, 70, 0), (60, 57, 1), (58, 44, 1)], z=None)
    p = d.panel("Thin end up through, round behind", box)
    p.rope(thick, width=d.rope_w + 4)
    p.rope(lead + wrap1, start="thin", start_at=(76, 124))
    p.arrow(wrap1[-1:] + tuck1 + [(66, 61, 0.6)], z=None)
    p = d.panel("Under itself only. Tails same side", box)
    p.rope(thick, width=d.rope_w + 4, end="end", end_at=(16, 42))
    p.rope(lead + wrap1 + tuck1 + out1, start="thin", end="end", start_at=(76, 124))
    return d


# ---------------------------------------------------------------- loops

def bowline_paths(C=(56, 54), k=1.0):
    """Bowline in a vertical rope. Returns (body, up, collar, down).

    body: standing part from the top, the hole (end side on top at C) and the
    big loop, rising as the working end. up: through the hole from below.
    collar: round behind the standing part. down: back down the hole."""
    cx, cy = C

    def q(pts):
        return [(cx + (x - cx) * k, cy + (y - cy) * k, z) for x, y, z in pts]

    body = [(cx + 8, -14, 0), (cx + 7, 8, 0), (cx + 4, cy - 10, -0.4), (cx, cy, -1), (cx - 5, cy + 7, -0.3),
            (cx - 13, cy + 9, 0), (cx - 21, cy + 2, 0), (cx - 22, cy - 9, 0), (cx - 15, cy - 16, 0),
            (cx - 6, cy - 12, 0.4), (cx, cy, 1), (cx + 4, cy + 12, 0.3), (cx + 7, cy + 34, 0),
            (cx + 6, cy + 60, 0), (cx - 4, cy + 76, 0), (cx - 20, cy + 76, 0), (cx - 28, cy + 58, 0),
            (cx - 27, cy + 34, 0)]
    up = [(cx - 22, cy + 22, -0.3), (cx - 16, cy + 9, -1), (cx - 12, cy - 2, 0), (cx - 10, cy - 15, 1),
          (cx - 6, cy - 26, 0.5)]
    collar = [(cx + 1, cy - 32, -0.3), (cx + 7, cy - 32, -1), (cx + 14, cy - 27, -0.4), (cx + 12, cy - 19, 0.4),
              (cx + 5, cy - 16, 1.2)]
    down = [(cx - 3, cy - 13, 1.4), (cx - 7, cy - 4, 0.2), (cx - 9, cy + 9, -1), (cx - 12, cy + 22, -0.4),
            (cx - 13, cy + 34, -0.2)]
    return q(body), q(up), q(collar), q(down)


@diagram("knot_bowline")
def bowline():
    d = Diagram("BOWLINE 1-3", 3)
    box = (4, 0, 96, 134)
    body, up, collar, down = bowline_paths(C=(58, 66), k=1.45)
    p = d.panel("Small loop. End side on top", box)
    p.rope(body, start="standing", end="end", start_at=(84, 8), end_at=(16, 110))
    p.label(20, 42, "hole")
    p.arrow([body[-1], up[0], up[1], up[2], up[3]], z=None)
    p = d.panel("End up through the hole", box)
    p.rope(body + up, start="standing", start_at=(84, 8))
    p.arrow(up[-1:] + collar[:3], z=None)
    p = d.panel("Round behind the standing part", box)
    p.rope(body + up + collar, start="standing", start_at=(84, 8))
    p.arrow(collar[-1:] + down[:3], z=None)
    return d


@diagram("knot_bowline_2")
def bowline_2():
    d = Diagram("BOWLINE 4-5", 2)
    box = (-6, 0, 106, 134)
    body, up, collar, down = bowline_paths(C=(58, 66), k=1.45)
    p = d.panel("Back down the hole, beside itself", box)
    p.rope(body + up + collar + down, start="standing", end="end", start_at=(84, 6), end_at=(26, 104))
    p = d.panel("Pull tight. Tail ends inside the loop", box)
    body, up, collar, down = bowline_paths(C=(56, 54), k=1.0)
    p.rope(body + up + collar + down, start="standing", end="tail", start_at=(80, 4), end_at=(30, 84))
    p.label(46, 104, "loop")
    return d


def bight_open(points, d, loop, zl=None):
    """Fold a path into a doubled rope that opens into a round loop.

    points: centre line from the standing end to where the loop starts.
    loop: centre-line points of the loop's far side (round the bottom), as
    (x, y, z), listed from the left strand's side to the right's."""
    s = smooth(points, 1.0)
    left = offset(s, d)
    right = offset(s, -d)
    return join(left, loop, reverse(right))


def fig8_open(n=None, tail=None, d=3.6, loop=None):
    pts = FIG8[:n] if n else FIG8[:-3]
    if n:
        return bight(pts, d)
    return bight_open(pts, d, loop)


LOOP8 = [(55, 102, 0), (46, 114, 0), (46, 128, 0), (58, 136, 0), (72, 128, 0), (72, 112, 0), (69, 100, 0)]
LOOP8_RING = [(55, 102, 0), (49, 112, 0.3), (47, 123, 1), (48, 133, -1), (52, 142, -0.8), (58, 145, -0.8),
              (65, 142, -0.8), (70, 133, -1), (70, 123, 1), (70, 112, 0.3), (69, 100, 0)]


@diagram("knot_fig8_loop")
def fig8_loop():
    d = Diagram("FIGURE-EIGHT ON A BIGHT", 3, rope_w=7)
    box = (14, -2, 96, 138)
    p = d.panel("Bight. Loop it, bight on top", box)
    p.rope(fig8_open(15), start="standing", start_at=(68, 4))
    p.arrow(FIG8[14:18], z=None)
    p = d.panel("Round behind both legs", box)
    p.rope(fig8_open(20), start="standing", start_at=(68, 4))
    p.arrow(FIG8[19:23], z=None)
    p = d.panel("Down through. Pairs lie flat", box)
    p.rope(fig8_open(loop=LOOP8), start="standing", start_at=(68, 4))
    p.label(59, 120, "loop")
    return d


@diagram("knot_fig8_follow")
def fig8_follow():
    d = Diagram("FIGURE-EIGHT FOLLOW-THROUGH", 3)
    box = (12, -2, 98, 150)
    single = FIG8[:-3] + [(68, 104, 0), (70, 112, 0.3), (70, 123, 1)]
    p = d.panel("Loose figure-eight. Long end", box)
    p.ring(58, 128, 17)
    p.rope(single[:-1], start="standing", end="end", start_at=(68, 4), end_at=(86, 100))
    p.arrow(single[-2:] + [(70, 133, -1), (65, 142, -0.8), (58, 145, -0.8), (50, 140, -0.8)], z=None)
    p.label(30, 140, "anchor")
    p = d.panel("Through the anchor, back up", box)
    p.ring(58, 128, 17)
    full = fig8_open(loop=LOOP8_RING, d=3.8)
    k = len(smooth(FIG8[:-3], 1.0))
    back = full[: k + len(LOOP8_RING) + 14]
    p.rope(back, start="standing", start_at=(68, 4))
    p.arrow(back[-1:] + [(50, 92, 0), (50, 82, -1)], z=None)
    p = d.panel("Follow the first path out", box)
    p.ring(58, 128, 17)
    p.rope(full, start="standing", end="end", start_at=(68, 4), end_at=(34, 4))
    return d


# ---------------------------------------------------------------- belay and quick-release hitches


# ================================================================ more hitches

def _pile_parts(C=55, R=12):
    s1 = [(-20, 58, 0), (10, 59, 0), (28, 60, 1.0), (C - R - 2, 61, 0.6), (C - R + 3, 62, B), (C + R - 3, 68, B),
          (C + R + 4, 76, 0), (C + R - 3, 84, F), (C, 87, F), (C - R + 4, 88, F), (C - R - 3, 86, F)]
    up = [(C - R - 8, 78, -1.5), (C - R - 8, 62, -1.5), (C - R - 6, 50, 0)]
    ring = [(C - R + 3, 44, F), (C, 42, F), (C + R - 3, 41, F), (C + R + 4, 38, 0), (C + R - 3, 34, B),
            (C, 34, B), (C - R + 3, 35, B), (C - R - 4, 40, 0)]
    down = [(C - R - 15, 52, -1.5), (C - R - 17, 70, -1.5), (C - R - 14, 92, 0)]
    s2 = [(C - R - 6, 99, F), (C - R + 3, 100, F), (C, 100, F), (C + R - 3, 98, F), (C + R + 4, 92, 0),
          (C + R - 3, 84, B), (C - R + 3, 77, B), (C - R - 2, 76, 0.6), (28, 75, 1.0), (10, 75, 0), (-20, 75, 0)]
    return s1, up, ring, down, s2


@diagram("knot_pile")
def pile():
    d = Diagram("PILE HITCH", 3)
    C, R = 55, 12
    s1, up, ring, down, s2 = _pile_parts(C, R)
    box = (8, 20, 92, 112)
    lab = dict(start="standing", start_at=(20, 51), end="end", end_at=(16, 84))
    p = d.panel("Bight round behind the post, back to the front", box)
    post(p, C, 2 * R, y0=28)
    p.rope(join(s1, [(C - R - 11, 94, F)], s2), **lab)
    p.arrow([(C - R - 11, 94, F), (C - R - 12, 80, -1.5), (C - R - 12, 62, -1.5), (C - R - 10, 48, 0), (C - R - 6, 40, 0)], z=None)
    p = d.panel("Up under both parts", box)
    post(p, C, 2 * R, y0=28)
    p.rope(join(s1, up, [(C - R - 11, 45, 0)], down, s2), **lab)
    p.arrow([(C - R - 10, 42, 0), (C - 8, 22, 2), (C + 8, 22, 2), (C + R + 6, 34, 2)])
    p = d.panel("Over the top of the post. Pull", box)
    post(p, C, 2 * R, y0=28)
    k = knot([join(s1, up, ring, down, s2)], name="pile")
    show(p, k, 0, debug=True, **lab)
    return d

@diagram("knot_siberian")
def siberian():
    """Plan of the finished hitch: a slipped figure-eight tied with the end round the standing part."""
    d = Diagram("SIBERIAN HITCH", 1, rope_w=9)
    f = tf(FIG8, 0, 0, 1.5, -90)
    f = [(x - f[0][0], y - f[0][1], z) for x, y, z in f]
    body, tuck = f[:20], f[20:23]
    back = [(132, -25, -1), (105, -26, 0), (84, -30, 1), (62, -38, 0)]
    tip = [(148, -18, 0), (154, -22, 0), (148, -26, 0)]
    tail = [(48, -46, 0), (34, -54, 0)]
    TX, Y, TR = -22, -20, 14
    sp = [(200, Y - 20, 0), (150, Y - 20, 0), (131, Y - 20, -1.6), (108, Y - 20, 0), (84, Y - 20, 1.6), (60, Y - 20, 0),
          (30, Y - 18, 0)] + [(TX + (TR + 4) * math.cos(math.radians(a)), Y + (TR + 4) * math.sin(math.radians(a)), 0)
                              for a in range(-60, -300, -20)]
    box = (-44, -60, 186, 40)
    p = d.panel("Round the tree. A figure-eight in the end, round the standing part. Last tuck a bight: pull the end to free it", box)
    p._add([(TX, Y, -3), (TX + 0.01, Y, -3)], 2 * TR * p.scale, "post")
    k = knot([join(sp, body, tuck, tip, back, tail)], spec="o", name="siberian")
    show(p, k, 0, start="to tarp", start_at=(176, Y - 30), end="end", end_at=(28, -56), debug=True)
    p.label(TX, Y, "tree")
    p.label(160, -8, "bight", anchor="mm")
    return d

@diagram("knot_highwayman")
def highwayman():
    d = Diagram("HIGHWAYMAN'S HITCH", 3, rope_w=8)
    Y, hw = 52, 7
    top = Y - hw - 5
    L1, R1, L2, R2, L3, R3 = 18, 82, 33, 67, 44, 56
    # bight 1: over the bar, hanging in front
    b1 = [(L1, top + 2, 0), (L1, Y, F), (L1, 92, F), (26, 110, F), (50, 116, F), (74, 110, F), (R1, 92, F), (R1, Y, F),
          (R1, top + 2, 0)]
    over_l = [(L1 - 2, Y + hw + 6, B), (L1, Y - hw + 2, B), (L1, top, 0)]
    over_r = [(R1, top, 0), (R1 + 2, Y - hw + 2, B), (R1 + 4, Y + hw + 6, B)]
    load1 = [(4, 150, 0), (8, 112, B), (L1 - 3, 80, B)]
    end1 = [(R1 + 6, 80, B), (92, 112, 0), (96, 150, 0)]
    # bight 2: a bight of the load side pulled up through bight 1, in front of the bar
    b2 = [(4, 150, 0), (12, 134, B), (L2, 126, B), (L2, 106, -3), (L2, Y + hw + 4, F), (L2, Y, F + 1), (L2, 24, F),
          (40, 10, F), (50, 7, F), (60, 10, F), (R2, 24, F), (R2, Y, F + 1), (R2, Y + hw + 4, F), (R2, 106, -3),
          (R2 - 2, 124, B), (50, 132, B), (20, 126, B), (12, 106, B), (L1 - 3, 80, B)]
    # bight 3: a bight of the end pulled up through bight 2
    b3 = [(R1 + 6, 80, B), (R2 - 2, 76, -4), (R3, 68, -4), (R3, Y, B), (R3, 28, 0), (R3, 14, F + 2), (R3, 0, F + 1),
          (50, -14, F + 1), (L3, 0, F + 1), (L3, 14, F + 2), (L3, 28, 0), (L3, Y, B), (L3, 72, -4), (R2, 96, -4),
          (90, 116, 0), (96, 150, 0)]
    box = (0, -22, 100, 146)
    lab = dict(start="load", start_at=(12, 144), end="end", end_at=(88, 144))
    p = d.panel("Bight up behind the bar, down the front", box)
    bar(p, Y, 2 * hw)
    p.rope(join(load1, over_l, b1, over_r, end1), **lab)
    p.arrow([(L2 + 4, 128, -3), (L2 + 4, 106, -3), (L2 + 4, Y + hw + 4, F), (L2 + 4, Y, F + 1), (L2 + 4, 20, F)], z=None)
    p = d.panel("Pull a bight of the load side up through", box)
    bar(p, Y, 2 * hw)
    p.rope(join(b2, over_l, b1, over_r, end1), **lab)
    p.arrow([(R2 + 6, 86, -4), (R3, 70, -4), (50, Y, B), (50, 28, 0), (50, 14, F + 2), (50, 0, F + 2)], z=None)
    p = d.panel("A bight of the end through that. Pull load", box)
    bar(p, Y, 2 * hw)
    p.rope(join(b2, over_l, b1, over_r, b3), **lab)
    return d

@diagram("knot_marlinspike")
def marlinspike():
    d = Diagram("MARLINSPIKE HITCH", 3)
    X = 50
    # panel 1: a loop to the side of the line
    side = [(X, -10, 0), (X, 30, 0), (X + 2, 44, 0.6), (X + 10, 52, 0.8), (X + 24, 52, 0.6), (X + 30, 42, 0),
            (X + 26, 30, 0), (X + 14, 28, 0), (X + 4, 34, -0.6), (X, 44, -1.2), (X, 70, 0), (X, 150, 0)]
    # panel 2: the loop folded down over the line: the line runs behind its middle
    folded = [(X, -10, 0), (X, 24, 0), (X + 4, 32, 1), (X + 16, 40, 1.2), (X + 20, 60, 1.2), (X + 14, 82, 1.2),
              (X, 88, 1.2), (X - 14, 82, 1.2), (X - 20, 60, 1.2), (X - 16, 40, 1.2), (X - 4, 32, 1),
              (X, 40, -1.2), (X, 60, -1.2), (X, 80, -1.2), (X, 100, -0.5), (X, 150, 0)]
    stick = [(-10, 60, 3), (X - 28, 60, 3), (X - 20, 60, 3), (X - 10, 60, 0), (X, 60, -3), (X + 10, 60, 0),
             (X + 20, 60, 3), (X + 40, 60, 3), (110, 60, 3)]
    box = (0, -4, 100, 140)
    p = d.panel("Twist a small loop in the line", box)
    p.rope(side, start="load", start_at=(X - 18, 4), end="pull", end_at=(X - 16, 132))
    p.arrow([(X + 32, 48, 5), (X + 30, 70, 5), (X + 16, 92, 5)])
    p = d.panel("Fold it down over the line", box)
    p.rope(folded, start="load", start_at=(X - 18, 4), end="pull", end_at=(X - 16, 132))
    p.arrow([(-4, 60, 3), (X - 28, 60, 3), (X - 20, 60, 3), (X - 10, 60, 0), (X, 60, -3), (X + 10, 60, 0),
             (X + 20, 60, 3), (X + 34, 60, 3)], z=None)
    p = d.panel("Stick over, under the line, over. Pull", box)
    p.rope(folded, start="load", start_at=(X - 18, 4), end="pull", end_at=(X - 16, 132))
    p._add(stick, 10 * p.scale, "post")
    p.label(14, 72, "stick")
    return d

# ================================================================ grip and haul

def wraps_v(cx, y0, turns, pitch, r=11, a0=-90, zr=2.4, d=0.0):
    """Turns round a vertical rope or pole at cx, starting at the left edge (a0=-90),
    front first, moving down by pitch per turn. d shifts the whole wrap down (a pair)."""
    return helix(cx, y0 + d, r, a0, a0 + 360 * turns, pitch, axis="v", zr=zr)


def wraps_h(cy, x0, turns, pitch, r=10, a0=-90, zr=2.4):
    """Turns round a horizontal pole at cy, starting at the top edge (a0=-90), front first."""
    return helix(x0, cy, r, a0, a0 + 360 * turns, pitch, axis="h", zr=zr)


def core(p, x, y0=-30, y1=170, w=None):
    """A thick vertical rope (the main line) for friction hitches."""
    return p.rope([(x, y0, 0), (x, y1, 0)], width=w or p.d.rope_w + 5)


@diagram("knot_prusik")
def prusik():
    d = Diagram("PRUSIK", 2, rope_w=7)
    X, r = 50, 11
    box = (8, 14, 92, 126)

    def rope_core(p):
        core(p, X, w=d.rope_w + 9)

    p = d.panel("Loop behind the rope. A round the front, through B", box)
    rope_core(p)
    p.rope(arc(X, 62, 34, 0, 360, z=-2, ry=9, steps=48))
    p.arrow([(X - 34, 56, -2), (X - 20, 46, 4), (X + 10, 46, 4), (X + 26, 54, 4)])
    p.label(X - 32, 80, "end A")
    p.label(X + 32, 80, "end B")
    p = d.panel("3 times, each inside the last. Dress neat. Load", box)
    rope_core(p)
    a = wraps_v(X, 34, 3, 13, r=r)
    b2 = [(x, y + 5, z) for x, y, z in a]
    loop = [(X - 2, 74, -2), (X - 2, 92, -2), (X + 6, 116, 0), (X + 14, 124, 0), (X + 22, 116, 0), (X + 8, 92, -2),
            (X + 3, 80, -2)]
    p.rope(join([(X - 2, 34, -2)], a, [(X - 4, 70, -2)], loop, reverse(b2), [(X - 2, 38, -2)]))
    p.label(X + 30, 122, "load")
    return d


@diagram("knot_klemheist")
def klemheist():
    d = Diagram("KLEMHEIST", 2, rope_w=7)
    X, r, g = 50, 11, 5
    box = (4, -2, 104, 140)
    a = wraps_v(X, 30, 4, 12, r=r)
    b = [(x, y + g, z) for x, y, z in a]
    # the short end's eye sticks out at the top right
    eye = [(X + r + 2, 30 + g, -2), (X + 18, 28, 0), (X + 26, 20, 0), (X + 34, 10, 0), (X + 38, 14, 0), (X + 30, 28, 0), (X + r + 2, 30, -2)]
    p = d.panel("Loop behind the rope. Wrap the long end down 4 times", box)
    core(p, X, w=d.rope_w + 9)
    tail = [(X - r - 2, 79, 0), (X - 20, 98, 0), (X - 16, 120, 0), (X - 10, 124, 0), (X - 8, 104, 0), (X - r + 1, 84, 0)]
    p.rope(join(reverse(eye), a, tail, reverse(b)))
    p.label(X + 38, 8, "eye")
    p.label(X - 30, 128, "long end")
    p.arrow([(X - 22, 108, 4), (X - 28, 60, 4), (X - 20, 20, 4), (X + 4, 6, 4), (X + 24, 12, 4)])
    p = d.panel("Up through the eye. Load it downward only", box)
    core(p, X, w=d.rope_w + 9)
    up1 = [(X - r - 2, 79, 0), (X - 8, 72, 4), (X - 2, 50, 4), (X + 6, 26, 4), (X + 16, 14, 4), (X + 28, 10, -1),
           (X + 38, 18, 4), (X + 38, 60, 4), (X + 34, 110, 4), (X + 28, 124, 4)]
    up2 = [(X + 22, 118, 4), (X + 30, 64, 4), (X + 31, 26, 4), (X + 26, 18, -1), (X + 14, 22, 4), (X + 4, 40, 4),
           (X - 3, 66, 4), (X - r + 1, 84, 0)]
    p.rope(join(reverse(eye), a, up1, up2, reverse(b)))
    p.label(X + 34, 134, "load")
    return d


@diagram("knot_icicle")
def icicle():
    d = Diagram("ICICLE HITCH", 3, rope_w=7)
    Y, r, S, E, T = 46, 8, 42, 29, 14
    box = (-6, 10, 104, 132)
    w = helix(S, Y, r, 90, 90 - 360 * 4.5, -9, axis="h", zr=2.4)   # front first, working right
    sp = [(S, 150, 0), (S, 90, 0), (S, Y + r + 4, 0)]
    after = [(w[-1][0] + 3, Y, -3), (w[-1][0] + 2, Y + r + 6, -3)]

    def pole(p, pull=False):
        p._add([(4, Y, 0), (130, Y, 0)], 2 * r * p.scale, "post")
        p.label(0, Y + 18, "pole", anchor="lm")
        p.label(0, Y + 27, "end", anchor="lm")
        if pull:
            p.arrow([(S - 4, Y - r - 9, 5), (8, Y - r - 9, 5)])
            p.label(24, Y - r - 18, "pull")

    p = d.panel("4 or 5 turns, away from the pole end", box)
    pole(p)
    p.rope(join(sp, w), start="standing", start_at=(S + 14, 124))
    hang = [(80, 98, -3), (56, 104, -3), (36, 96, -3), (E, 70, -3), (E, Y, -3), (E, Y - r - 3, 0), (E, Y, 3),
            (E - 1, Y + r + 4, 3), (E - 3, 90, 0), (E - 5, 150, 0)]
    p = d.panel("End over, beside the standing part", box)
    pole(p)
    p.rope(join(sp, w, after, hang), start="standing", start_at=(S + 14, 124), end="end", end_at=(E - 16, 124))
    p.label(64, 112, "bight behind")
    fin = [(80, 66, -3), (64, 72, 3), (44, 74, 3), (T + 6, 74, 3), (T - 2, 66, 3), (T - 2, Y + r + 2, 3), (T - 2, Y, 3),
           (T - 2, Y - r - 3, 0), (T, Y, -3), (T, Y + r + 6, -3), (T + 4, 80, -3), (E - 6, 80, -3), (E - 2, 70, -3),
           (E, Y, -3), (E, Y - r - 3, 0), (E, Y, 3), (E - 1, Y + r + 4, 3), (E - 3, 90, 0), (E - 5, 150, 0)]
    p = d.panel("Bight over both ends and the pole end", box)
    pole(p, pull=True)
    p.rope(join(sp, w, after, fin), start="standing", start_at=(S + 14, 124), end="end", end_at=(E - 16, 124))
    return d

@diagram("knot_truckers")
def truckers():
    d = Diagram("TRUCKER'S HITCH", 2, rope_w=8, layout="rows")
    PX, PR = 100, 6
    box = (-2, 30, 112, 82)
    stand = [(-30, 40, 0), (20, 40, 0), (34, 40, 0), (40, 42, 0.8), (44, 52, 0.8), (46, 66, 0.4), (52, 74, 0), (58, 66, -0.4),
             (60, 52, -0.8), (56, 44, -0.8), (48, 42, 0), (44, 40, 1.2), (52, 38, 0.6), (64, 38, 0)]
    to_post = [(80, 38, 0), (PX - PR - 3, 38, 0), (PX, 38, F), (PX + PR + 3, 42, 0), (PX + 2, 50, B), (PX - PR - 3, 54, 0),
               (80, 56, 0)]
    through = [(66, 57, 0), (60, 58, 1.5), (52, 60, 1.5), (49, 62, -1.5), (50, 68, -1.5), (58, 66, -1.5), (64, 68, 0)]

    def anchor(p):
        p.post(PX, 0, 120, w=2 * PR)
        p.label(PX + 8, 72, "anchor", anchor="lm")
        p.label(22, 64, "fixed loop")

    p = d.panel("Fixed loop. End round the anchor and back through the loop", box)
    anchor(p)
    p.rope(join(stand, to_post, through, [(74, 72, 0)]), start="from tree", start_at=(10, 32))
    p.arrow([(76, 73, 5), (90, 76, 5)])
    p = d.panel("Pull the end to the anchor. Pinch, then two half hitches round both legs", box)
    anchor(p)
    tw = twist((72, 47), (86, 47), 2, 13, z=0)
    p.rope(join(stand, to_post, through, [(70, 66, 0)], tw, [(90, 66, 0), (92, 76, 0)]), start="from tree",
           start_at=(10, 32), end="end", end_at=(84, 79))
    return d

# ================================================================ loops (second set)

def doubled(samples, d=3.4):
    """A bight along a sampled centre line: out on one side, round the tip, back on the other."""
    return bight([tuple(p) for p in samples], d)


@diagram("knot_overhand_loop")
def overhand_loop():
    d = Diagram("OVERHAND LOOP", 3, rope_w=6)
    k = knot([OVERHAND + [(108, 132), (108, 146)]], spec="ouo", name="overhand_loop")
    box = (0, -6, 116, 152)
    caps = ["Fold a bight", "Overhand knot with the doubled rope", "Pull the loop and both strands"]
    cuts = [at(k, 0, 45, 30), at(k, 0, 66, 64), None]
    for i, c in enumerate(caps):
        p = d.panel(c, box)
        pts = k.path(0, cuts[i])
        p.rope(doubled(pts), start="standing", start_at=(66, 0), end="loop" if i == 2 else None, end_at=(96, 146))
        if i < 2:
            nxt = k.path(0, cuts[i + 1] if cuts[i + 1] else None)[len(pts) - 1:len(pts) + 40:6]
            p.arrow(nxt, z=None)
    return d


@diagram("knot_slip")
def slip():
    d = Diagram("SLIP KNOT", 3)
    k = knot([OVERHAND], spec="ouo", name="slip")
    box = (4, -6, 116, 130)
    s = k.path(0)
    i0 = int(at(k, 0, 60, 70))            # the end starts to tuck here
    L = len(s)
    p = d.panel("Loop: the end crosses over", box)
    show(p, k, 0, at(k, 0, 24, 52), start="standing", start_at=(66, 4))
    p.arrow(s[int(at(k, 0, 24, 52)):int(at(k, 0, 40, 92)):6], z=None)
    p = d.panel("Fold a bight in the end. Push it up through", box)
    tuck = s[i0 - 30:L - 40]
    pre = s[:i0 - 30]
    bt = doubled(tuck, 3.6)
    half = len(bt) // 2
    x0, y0 = s[i0 - 30][0], s[i0 - 30][1]
    tail = [(x0 - 2, y0 + 12, 0), (x0 - 4, y0 + 40, 0)]
    p.rope(join(pre[:-1], [(s[i0 - 40][0] + 4, s[i0 - 40][1] + 18, 0)], [(70, 110, 0), (84, 120, 0)]), start="standing",
           start_at=(66, 4), end="end", end_at=(92, 122))
    p.arrow(tuck[::8], z=None)
    p = d.panel("Pull the bight and the standing part", box)
    p.rope(join(pre, bt[:half], bt[half:], tail), start="standing", start_at=(66, 4), end="end", end_at=(78, 118))
    p.label(112, 98, "bight")
    return d


@diagram("knot_running_bowline")
def running_bowline():
    d = Diagram("RUNNING BOWLINE", 2)
    cx, cy, kk = 60, 34, 1.25
    body, up, collar, down = bowline_paths(C=(cx, cy), k=kk)
    Y = cy + 58 * kk
    line_ = [(-40, Y, 0), (cx - 46, Y, 0), (cx - 34, Y, 1.8), (cx - 10, Y, 0), (cx + 9, Y, -1.8), (cx + 24, Y, 0)]
    noose = [(cx + 40, Y + 6, 0), (cx + 70, Y + 2, 0), (cx + 84, cy + 20, 0), (cx + 78, -20, 0), (cx + 50, -36, 0),
             (cx + 20, -34, 0), (cx + 10, -24, 0)]
    box = (-20, -44, 150, 140)
    p = d.panel("End round the standing part: a big loop", box)
    p.rope(join(line_, noose, [(cx + 8, -14, 0), (cx + 7, 8, 0), (cx + 2, 30, 0), (cx - 16, 44, 0)]), start="standing",
           start_at=(-6, Y - 10), end="end", end_at=(cx - 26, 54))
    p.label(cx + 96, cy + 20, "noose", anchor="mm")
    p = d.panel("Tie a small bowline round the standing part", box)
    p.rope(join(line_, noose, body, up, collar, down), start="standing", start_at=(-6, Y - 10), end="end",
           end_at=(cx - 34, cy + 40))
    p.arrow([(14, Y + 14, 4), (-12, Y + 14, 4)])
    p.label(10, Y + 26, "pull to close")
    return d


@diagram("knot_alpine_butterfly")
def alpine_butterfly():
    d = Diagram("ALPINE BUTTERFLY", 3, rope_w=8)
    twistp = [(-10, 120), (16, 112), (36, 96), (50, 76), (62, 62), (56, 52), (44, 46), (36, 34), (34, 18), (42, 6), (50, 4),
              (58, 6), (66, 18), (64, 34), (56, 46), (44, 52), (38, 62), (50, 76), (64, 96), (84, 112), (110, 120)]
    k = knot([twistp], spec="ou", name="butterfly_twist")
    box = (-4, -8, 104, 132)
    p = d.panel("Bight. Twist it twice the same way", box)
    show(p, k, 0, start="end", start_at=(4, 106), end="end", end_at=(96, 106), debug=True)
    p.label(50, 60, "eye")
    p.label(50, 22, "loop")
    s = k.path(0)
    i2 = int(at(k, 0, 56, 46))
    j2 = int(at(k, 0, 44, 46))
    lo, hi = s[:i2], s[j2:]
    fold = [(64, 48, -2.5), (68, 80, -2.5), (62, 112, -2.5), (50, 118, -2.5), (38, 112, -2.5), (32, 80, -2.5),
            (36, 48, -2.5)]
    p = d.panel("Fold the loop down behind", box)
    p.rope(join(lo, fold, hi), start="end", start_at=(4, 106), end="end", end_at=(96, 106))
    p.arrow([(50, 122, -2), (50, 90, -2.5), (50, 64, -2.5), (50, 52, 3), (50, 30, 3)], z=None)
    up = [(64, 48, -2.5), (70, 80, -2.5), (66, 108, -2.5), (58, 112, -2.5), (55, 96, -2.5), (55, 68, -2.5), (55, 58, 0),
          (56, 44, 3), (58, 20, 3), (54, 4, 3), (46, 4, 3), (42, 20, 3), (44, 44, 3), (45, 58, 0), (45, 68, -2.5),
          (45, 96, -2.5), (42, 112, -2.5), (34, 108, -2.5), (30, 80, -2.5), (36, 48, -2.5)]
    p = d.panel("Up through the eye. Pull loop, then ends", box)
    p.rope(join(lo, up, hi), start="end", start_at=(4, 106), end="end", end_at=(96, 106))
    p.label(50, -4, "loop")
    return d

@diagram("knot_bowline_bight")
def bowline_bight():
    d = Diagram("BOWLINE ON A BIGHT", 2, rope_w=6)
    body, up, collar, down = bowline_paths(C=(58, 52), k=1.35)
    box = (-6, -16, 110, 160)
    centre = smooth(join(body, up), 1.0)
    p = d.panel("Small loop in the doubled rope. Bight up through it", box)
    p.rope(bight([tuple(q) for q in centre], 3.4), start="standing parts", start_at=(90, -8))
    p.label(40, 150, "loops")
    tip = centre[-1]
    p = d.panel("Open the bight. Down round both loops, up behind the knot", box)
    p.rope(bight([tuple(q) for q in centre], 3.4), start="standing parts", start_at=(90, -8))
    p.arrow([(tip[0], tip[1] - 2, 4), (tip[0] - 26, tip[1] + 10, 4), (-2, 110, 4), (20, 162, 4), (70, 162, 4),
             (96, 110, -4), (80, 40, -4), (66, 10, -4)])
    p.label(40, 150, "loops")
    return d

# ================================================================ bends (second set)

def dsb_paths():
    """Double sheet bend, flat: thick bight opening left; thin rope from below."""
    thick = join([(-12, 96), (20, 96), (56, 96)], arc(56, 68, 28, 90, -90, steps=16), [(20, 40), (-12, 40)])
    lead = [(46, 140), (46, 118), (46, 96), (46, 68), (46, 40), (46, 28), (42, 18), (32, 14), (25, 22), (24, 40),
            (24, 68), (24, 96), (24, 106), (28, 112), (34, 108), (35, 96), (36, 86), (40, 80), (46, 78), (56, 74)]
    out1 = [(62, 60), (64, 40), (66, 24), (60, 8), (40, 1), (18, 3), (10, 16), (10, 40), (10, 68), (10, 96),
            (10, 110), (14, 117), (19, 112), (19, 96), (20, 76), (26, 64), (46, 62), (60, 62), (68, 58)]
    out2 = [(76, 46), (82, 34), (90, 22)]
    return thick, lead, out1, out2


@diagram("knot_double_sheet_bend")
def double_sheet_bend():
    d = Diagram("DOUBLE SHEET BEND", 2, rope_w=8)
    thick, lead, out1, out2 = dsb_paths()
    k = knot([thick, join(lead, out1, out2)], spec="uouuouo" + "uuoouuo", name="double_sheet_bend")
    box = (-14, -4, 100, 136)
    tw = d.rope_w + 6
    lab_thick = dict(width=tw, start="thick", start_at=(-7, 84), end="end", end_at=(-2, 28))
    p = d.panel("A sheet bend: up through, behind both legs, under itself", box)
    show(p, k, 0, **lab_thick)
    show(p, k, 1, at(k, 1, 56, 74, 6), start="thin", start_at=(60, 132))
    p.arrow([(62, 62, 5), (64, 42, 5), (66, 26, 5), (60, 10, 5), (42, 3, 5), (22, 5, 5)])
    p = d.panel("Round behind again, beside the first. Under itself again", box)
    show(p, k, 0, **lab_thick)
    show(p, k, 1, start="thin", start_at=(60, 132), end="end", end_at=(94, 14), debug=True)
    return d


ZC = (50, 62)


def zep_rope(r, z=1.0, zt=2.5):
    """One rope of the zeppelin bend, drawn as rope A (the 6, on top).

    Returns (shape, tail): the 6 itself, and the tail's path down round both
    ropes and up through the middle. Rope B is this turned half round, z negated."""
    cx, cy = ZC

    def P(a, zz):
        return (cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)), zz)

    stem = [(62, -14, z), (56, 8, z), (46, 26, z), P(232, z)]
    loop = [P(a, z) for a in range(220, -116, -15)]
    cross = [P(-114, z), (36, 38, z + 1.5), (24, 36, z + 1.2)]
    tail = [(12, 44, 0), (7, 58, -zt), (9, 72, -zt), (15, 80, -zt), (23, 81, -zt), (30, 74, -zt), (38, 66, -zt),
            (46, 58, 0), (55, 49, zt), (64, 40, zt), (72, 31, zt)]
    return stem + loop + cross, tail


def zep_b(pts):
    return [(2 * ZC[0] - x, 2 * ZC[1] - y, -z) for x, y, z in pts]


@diagram("knot_zeppelin")
def zeppelin():
    d = Diagram("ZEPPELIN BEND", 3, rope_w=7, caption_lines=3)
    a6, at_ = zep_rope(22)
    b6, bt = zep_rope(15)
    b9, bt = zep_b(b6), zep_b(bt)
    box = (-2, -12, 102, 136)
    la = dict(start="A", start_at=(70, -8))
    lb = dict(start="B", start_at=(30, 132))
    p = d.panel("A: a 6, end on top. B: a 9, end under", box)
    p.rope(tf(a6 + at_[:1], 2, 4, 0.6), start="A", start_at=(46, -6))
    p.rope(tf(b9 + bt[:1], 38, 54, 0.6), start="B", start_at=(54, 132))
    p = d.panel("Lay the 6 on the 9, holes lined up, ends outside", box)
    p.rope(a6 + at_[:1], **la)
    p.rope(b9 + bt[:1], **lb)
    p.arrow([(q[0], q[1], 6) for q in at_[1:6]])
    p.arrow([(q[0], q[1], 6) for q in bt[1:6]])
    p = d.panel("A: round both, up through. B: round, down through", box)
    p.rope(a6 + at_, end="end", end_at=(80, 22), **la)
    p.rope(b9 + bt, end="end", end_at=(20, 102), **lb)
    return d


def alternating(paths, name="", invert=False, **kw):
    """A Knot whose crossings alternate over, under, over... along each rope's walk.

    Rope 0 starts over at its first crossing (under with invert)."""
    k0 = Knot(paths, spec="", **kw)
    order = []
    for n, (early, late, _o, _xy, _auto) in enumerate(k0.crossings):
        order.append((early[0], early[1], n, "early"))
        order.append((late[0], late[1], n, "late"))
    order.sort()
    over = {}
    for r in range(len(paths)):
        seq = [o for o in order if o[0] == r]
        flip = 0
        for i, (_r, _s, n, which) in enumerate(seq):
            other = "late" if which == "early" else "early"
            if (n, other) in over:
                flip = (i % 2) ^ (0 if over[(n, other)] else 1) ^ 1
                break
        for i, (_r, _s, n, which) in enumerate(seq):
            if (n, which) not in over:
                over[(n, which)] = (i + flip) % 2 == 0
    spec = "".join("o" if over[(n, "late")] != invert else "u" for n in range(len(k0.crossings)))
    bad = [n for n in range(len(k0.crossings)) if over[(n, "late")] == over[(n, "early")]]
    if bad:
        print(f"  {name}: not alternating at crossings {bad}")
    return knot(paths, spec=spec, name=name, **kw)


CARRICK_A = [(-16, 104), (4, 92), (22, 78), (36, 60), (48, 40), (64, 30), (82, 34), (92, 50), (88, 68),
             (72, 80), (52, 82), (32, 74), (16, 60), (-2, 50), (-18, 46)]


@diagram("knot_carrick")
def carrick():
    d = Diagram("CARRICK BEND", 3, rope_w=8, caption_lines=3)
    C = (44, 60)
    A = CARRICK_A
    Bp = [(2 * C[0] - x, 2 * C[1] - y) for x, y in A]
    k = alternating([A, Bp], name="carrick", invert=True)
    box = (-20, 18, 108, 104)
    la = dict(start="A", start_at=(-12, 100), end="end", end_at=(-14, 36))
    lb = dict(start="B", start_at=(100, 22))
    p = d.panel("Loop in A, its end under its standing part", box)
    ka = knot([A], spec="u", name="carrick_a")
    show(p, ka, 0, **la)
    p.rope(Bp[:2], **lb)
    p.arrow(k.path(1, 52)[8::4], z=None)
    p = d.panel("B under the loop, over A, under A's end", box)
    show(p, k, 0, **la)
    show(p, k, 1, at(k, 1, 3, 46, 8), **lb)
    c = at(k, 1, 3, 46, 8)
    p.arrow(k.path(1, c + 34, c - 1)[::4], z=None)
    p = d.panel("Back across: over, under itself, over. Pull slowly", box)
    show(p, k, 0, **la)
    show(p, k, 1, end="end", end_at=(102, 84), debug=True, **lb)
    return d


# ================================================================ fishing and snare knots

def overhand_round(x1, x2, ya=40, yb=68, yt=56, top=20, lead=-24, tail=18, xe=None):
    """Rope A along y=ya from the left, its end tied in an overhand knot round a
    line at y=yb: down over the line at x1, up under it at x2, over the top,
    down over A's own standing part at xe, then through the loop beside the line."""
    xe = x1 - 10 if xe is None else xe
    return [(lead, ya), (xe - 10, ya), (x1 - 6, ya + 1), (x1 - 1, ya + 8), (x1, yb), (x1 + 2, yb + 10), (x1 + 8, yb + 15),
            (x2 - 6, yb + 15), (x2, yb + 8), (x2, yb - 6), (x2, ya), (x2 - 3, top + 6), (x2 - 12, top), (xe + 6, top),
            (xe, top + 8), (xe, ya), (xe, yt - 6), (xe + 5, yt), (x1 + 8, yt), (x2 + 8, yt), (x2 + tail, yt)]


def rot_about(pts, c):
    return [(2 * c[0] - p[0], 2 * c[1] - p[1]) + tuple(p[2:]) for p in pts]


@diagram("knot_fisherman")
def fisherman():
    d = Diagram("SINGLE FISHERMAN'S KNOT", 2, rope_w=8)
    C = (50, 54)
    A = overhand_round(66, 88)
    Bk = rot_about(A, C)
    Bs = [(124, 68), (60, 68), (0, 68), (-24, 68)]
    box = (-26, 10, 126, 98)
    k1 = knot([A, Bs], spec="ouo" + "ou", name="fisherman_1")
    p = d.panel("Ends side by side. End A: an overhand knot round B", box)
    show(p, k1, 0, start="A", start_at=(-14, 32))
    show(p, k1, 1, start="B", start_at=(114, 76), end="end", end_at=(-14, 76))
    k = knot([A, Bk], spec="ouo" + "ouou" + "ouo", name="fisherman")
    p = d.panel("End B: an overhand round A. Pull: the knots slide together", box)
    show(p, k, 0, start="A", start_at=(-14, 32), end="end", end_at=(116, 48))
    show(p, k, 1, start="B", start_at=(114, 76), end="end", end_at=(-16, 60), debug=True)
    p.arrow([(-4, 20, 5), (-24, 20, 5)])
    p.arrow([(104, 90, 5), (124, 90, 5)])
    return d


def eye_ring(p, cx, cy, r=11, w=4.5, hook=True):
    """A hook eye seen edge-on: a tall ellipse, its right side in front. With hook,
    the shank runs up from the eye to a bend."""
    pts = [(cx + 0.36 * r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)), 3 * math.cos(math.radians(a)))
           for a in range(0, 361, 10)]
    p._add(pts, w * p.scale, "post")
    if hook:
        shank = join([(cx, cy - r, 0), (cx, cy - r - 22, 0)], arc(cx + 9, cy - r - 22, 9, 180, 360, steps=10),
                     [(cx + 18, cy - r - 14, 0)])
        p._add(shank, w * p.scale, "post")
        p.label(cx - 12, cy - r - 30, "hook")


def clinch_parts(turns=5):
    Y = 54
    line_in = [(116, Y), (100, Y), (40, Y), (20, Y + 2), (10, Y + 5), (4, Y + 6), (-4, Y + 9), (-9, Y + 16), (-4, Y + 24),
               (6, Y + 24), (16, Y + 21), (24, Y + 16)]
    tw = twist((30, Y), (92, Y), turns, 8, z=0)
    back = [(98, Y + 18), (94, Y + 30), (80, Y + 34), (40, Y + 34), (16, Y + 34), (8, Y + 28), (10, Y + 18)]
    tuck = [(14, Y + 9), (22, Y + 8), (34, Y + 14), (50, Y + 22), (64, Y + 26)]
    return line_in, tw, back, tuck


@diagram("knot_clinch")
def clinch():
    d = Diagram("IMPROVED CLINCH KNOT", 2, rope_w=6)
    line_in, tw, back, tuck = clinch_parts()
    path = join(line_in, tw, back, tuck)
    k = knot([path], spec="uo", name="clinch", sigma=3.0)
    box = (-14, 10, 114, 98)
    lab = dict(start="line", start_at=(122, 46))
    for i, (cap_, cut) in enumerate([("Through the eye, 5 to 7 wraps round the line, end back to the eye", at(k, 0, 10, 72)),
                                     ("Through the small loop by the eye, then back through the big loop", None)]):
        p = d.panel(cap_, box)
        eye_ring(p, 6, 60)
        show(p, k, 0, cut, start="line", start_at=(106, 44), end="end" if cut is None else None, end_at=(74, 84),
             debug=cut is None)
        if i == 0:
            p.arrow([(10, 70, 5), (14, 63, 5), (26, 63, 5), (40, 70, 5), (54, 77, 5)])
        else:
            p.label(52, 96, "big loop")
    return d


def flat_eye(p, cx, cy, r=9, shank=24, w=4.5, side=1):
    """A hook eye seen from the side (a flat ellipse, front half nearer) with the
    shank running off to the right (side=-1: left) and the bend of the hook."""
    pts = [(cx + r * math.cos(math.radians(a)), cy + 0.34 * r * math.sin(math.radians(a)),
            3 * math.sin(math.radians(a))) for a in range(0, 361, 10)]
    p._add(pts, w * p.scale, "post")
    body = join([(cx + r, cy, 0), (cx + r + shank, cy, 0)], arc(cx + r + shank, cy + 10, 10, -90, 90, steps=10),
                [(cx + r + shank - 8, cy + 20, 0), (cx + r + shank - 12, cy + 13, 0)])
    if side < 0:
        body = [(2 * cx - x, y, z) for x, y, z in body]
    p._add(body, w * p.scale, "post")
    p.label(cx + side * (r + shank + 2), cy - 10, "hook")


PALOMAR = [(40, -12), (40, 8), (40, 30), (41, 50), (48, 66), (62, 70), (72, 60), (70, 44), (56, 36), (40, 38), (26, 44),
           (18, 58), (24, 74), (38, 82), (50, 74), (58, 62), (66, 56), (76, 58), (84, 68), (86, 84), (86, 100),
           (86, 116), (86, 148)]


@diagram("knot_palomar")
def palomar():
    d = Diagram("PALOMAR KNOT", 3, rope_w=5, caption_lines=3)
    EX, EY = 86, 104
    box = (6, -14, 136, 156)
    p = d.panel("Double the line. Push the bight through the eye", box)
    flat_eye(p, EX, EY)
    p.rope(bight([(EX, -12, 0), (EX, 40, 0), (EX, EY, 0), (EX, 136, 0)], 3.2), start="line + end", start_at=(64, -6))
    p.label(EX - 18, 140, "bight")
    k = knot([PALOMAR], spec="ouo", name="palomar")
    db = bight(k.path(0), 3.2)
    for i, cap_ in enumerate(["Loose overhand knot with the doubled line", "Hook through the bight. Wet, pull line and end"]):
        p = d.panel(cap_, box)
        flat_eye(p, EX, EY)
        p.rope(db, start="line + end", start_at=(70, -6))
        if i == 0:
            p.label(EX - 18, 152, "bight")
        else:
            p.arrow([(EX - 4, 152, 6), (EX - 22, 146, 6), (EX - 24, 116, 6), (EX - 6, 90, 6), (EX + 24, 86, 6),
                     (EX + 46, 100, 6), (EX + 40, 136, 6), (EX + 14, 152, 6)])
            p.arrow([(24, 20, 6), (24, -4, 6)])
    return d


def uni_parts(turns=5, amp=18):
    Y = 50
    lead = [(124, Y), (60, Y), (20, Y + 1), (10, Y + 4), (2, Y + 7), (-6, Y + 12), (-4, Y + 20), (6, Y + 21), (20, Y + 14),
            (40, Y + 12), (70, Y + 12), (96, Y + 12)]
    loop = [(106, Y + 9), (110, Y), (106, Y - 9), (96, Y - 12), (60, Y - 12), (30, Y - 12), (20, Y - 10)]
    down = [(16, Y - 2), (17, Y + 10), (22, Y + amp - 2)]
    tw = twist((28, Y), (88, Y), turns, amp, z=0)
    tail = [(96, Y + amp + 8), (100, Y + amp + 16)]
    return lead, loop, down, tw, tail


@diagram("knot_uni")
def uni():
    d = Diagram("UNI KNOT", 3, rope_w=5, caption_lines=3)
    lead, loop, down, tw, tail = uni_parts()
    k = knot([join(lead, loop, down, tw, tail)], spec="ooo", name="uni")
    box = (6, 0, 100, 146)

    def R(pts):
        """The knot is planned lying left to right; draw it standing up, eye at the bottom."""
        return tf(pts, 0, 130, 1, -90)

    def rp(x, y):
        return R([(x, y)])[0][:2]

    def eye(p):
        flat_eye(p, 55, 124, side=-1)

    lab = dict(start="line", start_at=rp(124, 62))
    p = d.panel("Through the eye. Lay the end back along the line", box)
    eye(p)
    p.rope(R(k.path(0, at(k, 0, 96, 62))), **lab)
    p.arrow(R([(98, 62, 5), (108, 56, 5), (108, 42, 5), (96, 36, 5), (70, 36, 5)]))
    p = d.panel("Bend it back toward the eye: a loop over both lines", box)
    eye(p)
    p.rope(R(k.path(0, at(k, 0, 20, 40))), **lab)
    p.arrow(R([(18, 40, 5), (16, 52, 5), (22, 66, 5), (32, 60, 5), (36, 44, 5)]))
    p = d.panel("5 or 6 turns round both lines, through the loop. Wet, pull", box)
    eye(p)
    p.rope(R(k.path(0)), end="end", end_at=rp(104, 84), **lab)
    p.label(*rp(104, 24), "loop")
    if DEBUG:
        k.debug(p)
    return d


@diagram("knot_surgeons")
def surgeons():
    d = Diagram("SURGEON'S KNOT (JOIN TWO LINES)", 3, rope_w=5, caption_lines=3, title_size=15)
    k = knot([DOUBLE_OH], spec="ouo" + "uoo", name="surgeons")
    box = (2, -6, 132, 126)
    dd = 3.2
    p = d.panel("Lay the lines side by side, opposite ways, a hand's overlap", box)
    p.rope([(58, -4), (58, 100)], start="A", start_at=(48, 0), end="A end", end_at=(44, 108))
    p.rope([(66, 122), (66, 18)], start="B", start_at=(78, 118), end="B end", end_at=(82, 12))
    p = d.panel("Treat them as one. Loop, then both ends through it twice", box)
    a, b = pair(k.path(0, at(k, 0, 108, 56)), dd)
    p.rope(a, start="A", start_at=(52, -2))
    p.rope(b, start="B end", start_at=(80, -2))
    p.arrow(k.path(0, at(k, 0, 80, 82), at(k, 0, 108, 56))[::6], z=None)
    p = d.panel("Wet it. Pull all four strands evenly", box)
    a, b = pair(k.path(0), dd)
    p.rope(a, start="A", start_at=(52, -2), end="A end", end_at=(108, 122))
    p.rope(b, start="B end", start_at=(80, -2), end="B", end_at=(132, 104))
    return d


PERF_STAND = [(50, -14, 0), (50, 0, 0), (50, 20, 0), (51, 32, 0), (58, 40, 0)]
PERF_LOOP1 = [(66, 50, 0), (66, 68, 0), (54, 78, 0), (40, 72, 0), (35, 56, 0), (41, 41, -0.6), (50, 27, -1.8),
              (58, 19, -1.2), (66, 17, 0.4)]
PERF_LOOP2 = [(74, 24, 2), (80, 42, 2), (81, 64, 2), (72, 86, 2), (52, 96, 2), (32, 88, 2), (22, 64, 2), (23, 40, 2),
              (31, 20, 2), (41, 8, 2.2), (50, 5, 2.4), (57, 7, 2), (61, 14, 1)]
PERF_END = [(60, 26, 1), (57, 44, 1), (56, 66, 1), (58, 90, 1), (62, 110, 1)]


@diagram("knot_perfection")
def perfection():
    d = Diagram("PERFECTION LOOP", 3, rope_w=6, caption_lines=3)
    box = (12, -16, 92, 118)
    lab = dict(start="line", start_at=(40, -10))
    p = d.panel("Loop: pass the end behind the line", box)
    p.rope(join(PERF_STAND, PERF_LOOP1), **lab)
    p.arrow([(70, 18, 5), (80, 30, 5), (84, 50, 5)])
    p = d.panel("Second loop round in front. End down between the loops", box)
    p.rope(join(PERF_STAND, PERF_LOOP1, PERF_LOOP2, PERF_END), end="end", end_at=(70, 112), **lab)
    p.label(18, 100, "2nd")
    p.label(45, 64, "1st")
    p = d.panel("Pull the 2nd loop through the 1st. Wet it, pull loop and line", box)
    neck = [(46, 40, 0), (46, 56, 0), (40, 76, 0), (32, 96, 0), (38, 112, 0), (50, 116, 0), (62, 112, 0), (68, 96, 0),
            (60, 76, 0), (54, 56, 0), (54, 40, 0)]
    wrap = helix(50, 36, 9, -90, 450, 12, axis="v", zr=2.4)
    p.rope(join([(50, -14, 0), (50, 10, 0), (50, 24, 0), (44, 30, -2), (46, 40, 0)], neck[1:-1],
                [(54, 40, 0), (58, 30, -2)], wrap, [(60, 50, 2.4), (72, 54, 2.4), (86, 54, 2.4)]),
           end="end", end_at=(88, 46), **lab)
    p.label(50, 92, "loop")
    return d


def snare_eye(dx, dy, s=0.5):
    """A small overhand loop (the fixed eye), lying left to right: the doubled
    rope comes in at the left, the eye opens at the right. Returns (path, eye centre).
    The path starts at the standing part and ends at the short tail."""
    k = knot([OVERHAND], spec="ouo", name="snare_eye")
    pts = k.path(0)
    ex, ey = 106, 132
    ring = [(ex - 3.6 + 1, 118, 0), (ex - 14, 130, 0), (ex - 13, 146, 0), (ex, 154, 0), (ex + 13, 146, 0),
            (ex + 14, 130, 0), (ex + 3.6 - 1, 118, 0)]
    path = bight_open(pts, 3.6, ring)
    out = tf(path, dx, dy, s, -90)
    c = tf([(ex, 138)], dx, dy, s, -90)[0][:2]
    return out, c


@diagram("knot_snare")
def snare():
    d = Diagram("SNARE NOOSE (SURVIVAL USE ONLY)", 2, rope_w=6, title_size=15)
    box = (-24, -4, 118, 122)
    eye, (ex, ey) = snare_eye(6, 94)
    stand = [(-14, 50, 0), (-8, 60, 0)]
    tail = [(-6, 82, 0)]
    p = d.panel("A small fixed eye in the end: an overhand loop", box)
    p.rope(join(stand, eye, tail), start="standing", start_at=(6, 42), end="end", end_at=(-8, 92))
    p.label(ex + 16, ey + 12, "eye")
    p = d.panel("Standing part through the eye. Loop slides shut and open", box)
    noose = [(ex + 40, -2, 0), (ex + 16, ey - 20, 0), (ex + 3, ey - 12, 0.5), (ex + 1, ey - 6, 2.5), (ex, ey, 0),
             (ex - 1, ey + 6, -2.5), (ex - 3, ey + 14, -1), (ex - 6, ey + 30, 0), (ex - 14, 100, 0), (40, 116, 0),
             (6, 112, 0), (-16, 98, 0), (-18, 80, 0), (-10, 70, 0)]
    p.rope(join(noose, eye, tail), start="to stake", start_at=(ex + 22, -2), end="end", end_at=(-8, 92))
    p.label(34, 100, "running loop")
    p.arrow([(ex + 28, 24, 5), (ex + 40, 6, 5)])
    return d


# ================================================================ lashings

def hbar(p, y, w, x0=-80, x1=300, z=1.0):
    """A horizontal pole in front of an upright (z=1)."""
    return p._add([(x0, y, z), (x1, y, z)], w * p.scale, "post")


SQ = dict(C=50, Y=60, R=8)


def square_wraps(n=3, C=50, Y=60, R=8):
    """Square lashing wraps: up over the crossbar on the right, behind the upright,
    down over the crossbar on the left, behind the upright. Each wrap further out
    on the crossbar, nearer the crossing on the upright."""
    pts = []
    for k in range(n):
        xl, xr = C - R - 5 - 5 * k, C + R + 5 + 5 * k
        yt, yb = Y - R - 5 - 5 * (n - 1 - k), Y + R + 5 + 5 * (n - 1 - k)
        pts += [(xr, yb, 1.5), (xr, Y + R + 1, 3), (xr, Y, 3), (xr, Y - R - 1, 3), (xr, yt + 2, 1.5),
                (xr - 4, yt, 0), (C + R + 1, yt, -2), (C, yt, -2), (C - R - 1, yt, -2), (xl + 4, yt, 0),
                (xl, yt + 2, 1.5), (xl, Y - R - 1, 3), (xl, Y, 3), (xl, Y + R + 1, 3), (xl, yb - 2, 1.5),
                (xl + 4, yb, 0), (C - R - 1, yb, -2), (C, yb, -2), (C + R + 1, yb, -2), (xr + 1 if k < n - 1 else xr - 4, yb, 0)]
    return pts


def frap_turns(C=50, Y=60, R=8, reach=24, n=2):
    """Frapping turns round the wraps, between the poles: across the upright in
    front, just above and below the crossbar, round the outside of the wraps."""
    pts = []
    for k in range(n):
        a, b = Y - R - 2 - 2.5 * k, Y + R + 2 + 2.5 * k
        pts += [(C + reach + 2, b - 6, -2), (C + reach, b, 4), (C + 12, b, 4), (C, b, 0.6), (C - 12, b, 4),
                (C - reach, b, 4), (C - reach - 3, Y + 4, -3), (C - reach - 3, Y - 4, -3), (C - reach, a, 4),
                (C - 12, a, 4), (C, a, 0.6), (C + 12, a, 4), (C + reach, a, 4), (C + reach + 3, Y - 4, -3),
                (C + reach + 3, Y + 4, -3)]
    return pts


def lash_cross(p, C=50, Y=60, R=8):
    post(p, C, 2 * R, y0=-20, y1=150)
    hbar(p, Y, 2 * R, x0=-20, x1=120)


def clove_knot(C, R, a, b, name="clove_small", tail=30):
    """A clove hitch on a vertical pole (centre C, radius R), bands at y=a and y=b."""
    return knot([clove_path(C, R, a, b, a - 6, b + 6, tail=tail)], spec="ou", name=name)


@diagram("lash_start")
def lash_start():
    d = Diagram("START AND FINISH A LASHING", 3, rope_w=6, caption_lines=3, title_size=15)
    C, Y, R = 50, 48, 11
    box = (12, 10, 112, 122)
    kc = clove_knot(C, R, 92, 110, tail=8)
    wr = square_wraps(3, C, Y, R)
    fr = frap_turns(C, Y, R, reach=29)
    lead = [(C + R + 12, 104, F), (C + R + 16, 94, 1.5)]
    kb = clove_knot(Y, R, 88, 102, name="lash_finish", tail=6)
    fin = [(y, x, z) for x, y, z in kb.path(0, start=at(kb, 0, Y - R - 10, 88))]
    first = kc.path(0, start=at(kc, 0, 26, 92))

    def cross(p):
        post(p, C, 2 * R, y0=-20, y1=150)
        hbar(p, Y, 2 * R, x0=-20, x1=130)

    p = d.panel("Clove hitch on one pole, tight by the crossing", box)
    cross(p)
    p.rope(join(first, lead[:1]), start="short end", start_at=(26, 82), end="long end", end_at=(86, 118))
    p.arrow([(C + R + 18, 100, 6), (C + R + 20, 84, 6)])
    p = d.panel("Wraps, each beside the last. 3 or 4", box)
    cross(p)
    p.rope(join(first, lead, wr[:-1]), start="short end", start_at=(26, 82))
    p = d.panel("Fraps between the poles. Clove hitch on the other pole", box)
    cross(p)
    p.rope(join(first, lead, wr, fr, [(C + 32, Y + 4, -2), (C + 36, Y - R - 6, -1)], fin), start="short end",
           start_at=(26, 82), end="end", end_at=(108, 74))
    p.label(C, 14, "fraps")
    return d


@diagram("lash_shear")
def lash_shear():
    d = Diagram("SHEAR LASHING", 3, rope_w=5, caption_lines=3)
    L, Rr, R = 34, 66, 9
    box = (8, -6, 92, 132)
    y0, turns, pitch = 42, 6, 6
    kc = clove_knot(L, R, 12, 24, name="shear_start", tail=0)
    hit = kc.path(0, start=at(kc, 0, L - R - 8, 12))[:-6]
    wraps = helix(50, y0, 28, 90, 90 + 360 * turns, pitch, axis="v", zr=3)
    fr = helix(49, y0 + 18, 22, 180, 180 + 720, 3, axis="h", zr=4)
    fr = [(x, y, z) for x, y, z in fr]
    kf = clove_knot(Rr, R, 100, 112, name="shear_finish", tail=10)
    fin = kf.path(0, start=at(kf, 0, Rr - R - 4, 100))

    def poles(p):
        post(p, L, 2 * R, y0=-20, y1=150)
        post(p, Rr, 2 * R, y0=-20, y1=150)

    lead = [(L + R + 4, 28, F), (L + R + 8, 34, 2)]
    p = d.panel("Poles side by side. Clove hitch, then 6 to 8 turns round both", box)
    poles(p)
    body = join(hit, lead, wraps)
    p.rope(body, start="short end", start_at=(16, 34))
    p = d.panel("2 frapping turns between the poles. Clove hitch", box)
    poles(p)
    p.rope(join(body, [(56, y0 + turns * pitch + 4, 3)], [(50, y0 + 46, 4)], fr[1:], [(54, 96, 2)], fin),
           start="short end", start_at=(16, 34), end="end", end_at=(86, 120))
    p = d.panel("Open the legs. The ridge pole sits in the fork", box)
    p.pole(62, 4, 24, 132, w=12)
    p.pole(38, 4, 76, 132, w=12)
    p.pole(-10, 20, 110, 20, w=10, z=6)
    hx = helix(50, 36, 15, 90, 90 + 360 * 4, 3.5, axis="v", zr=5)
    p.rope(hx)
    p.label(22, 8, "ridge pole")
    return d


def clove_round(cx, Y, R, a, b, name, tail=10):
    """A clove hitch round a horizontal bundle centred on y=Y (half thickness R),
    bands at x=a and x=b: the vertical-pole clove turned on its side."""
    k = clove_knot(Y, R, a, b, name=name, tail=tail)
    return k, [(y, x, z) for x, y, z in k.path(0)]


@diagram("lash_round")
def lash_round():
    d = Diagram("ROUND LASHING", 2, rope_w=5, caption_lines=2)
    Y1, Y2, R = 46, 64, 9
    Y, RR = 55, 18
    box = (-6, 14, 130, 100)

    def poles(p, a=(-30, 110), b=(14, 160)):
        bar(p, Y1, 2 * R, x0=a[0], x1=a[1])
        bar(p, Y2, 2 * R, x0=b[0], x1=b[1])

    k1, c1 = clove_round(0, Y, RR, 18, 30, "round_start", tail=4)
    c1 = c1[int(len(c1) * 0.18):-8]
    wr = helix(46, Y, RR + 2, 180, 180 + 360 * 7, 6.5, axis="h", zr=3)
    k2, c2 = clove_round(0, Y, RR, 104, 116, "round_finish", tail=6)
    c2 = c2[int(len(c2) * 0.2):]
    p = d.panel("Clove hitch round both, 8 to 10 tight turns, clove hitch. No fraps", box)
    poles(p)
    p.rope(join(c1, [(38, Y - RR - 4, 0)], wr, [(98, Y - RR - 4, 0)], c2), start="short end", start_at=(10, 26),
           end="end", end_at=(126, 96))
    p = d.panel("Two lashings on the overlap. Tap wedges under the wraps", box)
    poles(p, a=(-10, 96), b=(26, 140))
    for x0 in (30, 76):
        p.rope(helix(x0, Y, RR + 2, 180, 180 + 360 * 4, 5.5, axis="h", zr=3))
        for x in (x0 + 3, x0 + 14):
            p._add([(x, Y - RR - 6, 6), (x + 4, Y - RR + 2, 6)], 4 * p.scale, "post")
    p.label(58, 24, "wedges")
    p.label(58, 92, "overlap")
    return d


def floor_bight(yk, xin=52, xout=26, X=40, h=6, run=62):
    """Centre line of one floor-lashing bight, seen from above: out of the running
    cord inside the support pole, over the stick, under the pole, back over the
    stick outside. The stick lies across at y=yk."""
    return [(run, yk - h - 6, 0), (xin + 3, yk - h - 2, 1.5), (xin, yk - 2, 2.5), (xin, yk + h, 1), (xin - 6, yk + h + 2, -2),
            (X, yk + h + 2, -2.5), (xout + 6, yk + h + 2, -2), (xout, yk + h, 1), (xout, yk, 2.5), (xout - 1, yk - h - 2, 1.5)]


@diagram("lash_floor")
def lash_floor():
    d = Diagram("FLOOR LASHING", 3, rope_w=4, caption_lines=3)
    X, PR, RUN = 40, 7, 62
    sticks = [26, 50, 74, 98]
    box = (6, -6, 98, 122)

    def frame(p):
        post(p, X, 2 * PR, y0=-20, y1=150)
        for y in sticks:
            p._add([(14, y, 1), (140, y, 1)], 10 * p.scale, "post")
        p.label(X, 118, "support pole")

    hitch = [(X - PR - 6, -4, 3), (X - PR - 2, 0, 3), (X + PR + 3, 4, 3), (X + PR + 4, 7, -3), (X - PR - 4, 10, -3),
             (X - PR - 3, 13, 3), (X, 12, 3), (X + PR + 2, 10, 3), (RUN - 6, 10, 1), (RUN, 12, 0)]

    def cord(n):
        pts = list(hitch)
        for i, y in enumerate(sticks[:n]):
            bt = bight(floor_bight(y, run=RUN), 1.7)
            pts += [(RUN, y - 12, 0)] + bt[1:-1] + [(RUN, y - 12, 0), (RUN, y, -2), (RUN, y + 10, 0)]
        return pts

    p = d.panel("Clove hitch on the support pole by the first stick", box)
    frame(p)
    p.rope(join(hitch, [(RUN, 18, 0)]), start="short end", start_at=(14, 8), arrow=True)
    p.label(86, 38, "stick")
    p.label(76, 62, "inside")
    p.label(18, 62, "outside")
    p = d.panel("Bight over the stick inside, under the pole, over it outside", box)
    frame(p)
    p.rope(join(cord(1), [(RUN, 42, 0)]), start="short end", start_at=(14, 8), arrow=True)
    p = d.panel("Pull tight. Every stick the same. Two half hitches", box)
    frame(p)
    p.rope(join(cord(4), [(RUN, 116, 0)]), start="short end", start_at=(14, 8))
    return d


# ==== rope work

def whip_rope(p, Y, x0=-20, x1=96, R=10):
    """The rope being whipped, lying across, its cut end on the right."""
    p._add([(x0, Y, 0), (x1, Y, 0)], 2 * R * p.scale, "post")
    for dy in (-R * 0.6, 0, R * 0.6):
        p._add([(x1 + 1, Y + dy, 0.5), (x1 + 6, Y + dy * 1.4, 0.5)], 2.5 * p.scale, "arrow")


@diagram("rope_whipping")
def rope_whipping():
    d = Diagram("COMMON WHIPPING", 3, rope_w=4, caption_lines=3)
    Y, R = 60, 14
    box = (-4, 22, 106, 104)
    a, b = 26, 70                                   # wraps run from a to b
    leg1 = [(-10, Y - 6, 1.5), (60, Y - 6, 1.5)]    # pull end (back of the bight)
    loop = arc(82, Y, 6, -90, 90, z=1.5)
    loop = [(x, y, z) for x, y, z in loop]
    bt = join(leg1, [(78, Y - 6, 1.5)], loop, [(78, Y + 6, 1.5)], [(a - 4, Y + 6, 1.5)])
    wr = helix(a, Y, R + 1, -90, -90 + 360 * 6.5, 6.6, axis="h", zr=3)
    p = d.panel("Lay a bight of twine along the rope, the loop to the end", box)
    whip_rope(p, Y, R=R)
    p.rope(join(bt, [(a - 6, Y + 14, 2)], [(a - 2, Y + 30, 2)]), start="pull end", start_at=(14, 36),
           end="working end", end_at=(30, 100))
    p.arrow([(a + 2, Y + 26), (a + 8, Y + 8), (a + 12, Y - 16)])
    p.label(92, 40, "loop")
    p.label(98, 94, "rope end")
    p = d.panel("Wrap tight toward the end. Working end through the loop", box)
    whip_rope(p, Y, R=R)
    end = wr[-1]
    p.rope(join(bt[:-1], [(a - 4, Y + 6, 1.5)], [(a - 4, Y - R - 2, 2)], wr,
                [(end[0] + 6, end[1] + 2, 3)], [(84, Y + 6, 2.5)], [(86, Y + 22, 2)]),
           start="pull end", start_at=(14, 36))
    p.arrow([(86, Y + 24), (84, Y + 6)], z=None)
    p = d.panel("Pull till the loop is halfway under. Trim both ends", box)
    whip_rope(p, Y, R=R)
    loop3 = [(x - 24, y, -0.5 if x - 24 < b + 2 else 1.5) for x, y, z in loop]
    p.rope(join([(a - 10, Y - 6, 1.5)], [(56, Y - 6, 1)], loop3, [(54, Y + 6, 1)]), ends=False)
    p.rope(wr)
    p.rope(join([wr[-1]], [(wr[-1][0] + 2, wr[-1][1] - 4, 3)]))
    p.arrow([(a - 12, Y - 14), (a - 30, Y - 14)])
    p.label(48, 92, "trim here")
    return d


def laid(points, r=3.0, pitch=16.0, n=3, phase=0.0, zr=2.0, z0=0.0, taper=None):
    """n strands twisted along a path: a laid rope. taper(s) can scale r along it."""
    s = smooth(points, 1.0)
    L = [0.0]
    for i in range(1, len(s)):
        L.append(L[-1] + math.hypot(s[i][0] - s[i - 1][0], s[i][1] - s[i - 1][1]))
    out = []
    for k in range(n):
        pts = []
        for i in range(len(s)):
            a = s[max(0, i - 2)]
            b = s[min(len(s) - 1, i + 2)]
            tx, ty = b[0] - a[0], b[1] - a[1]
            m = math.hypot(tx, ty) or 1.0
            nx, ny = -ty / m, tx / m
            rr = r * (taper(L[i] / L[-1]) if taper else 1.0)
            t = 2 * math.pi * (L[i] / pitch + k / n) + phase
            pts.append((s[i][0] + nx * rr * math.sin(t), s[i][1] + ny * rr * math.sin(t),
                        s[i][2] + z0 + zr * math.cos(t)))
        out.append(pts[::3] + [pts[-1]])
    return out


@diagram("rope_splice")
def rope_splice():
    d = Diagram("EYE SPLICE", 3, rope_w=4, caption_lines=3)
    box = (0, 24, 116, 104)
    Y = 80
    eye = arc(30, 60, 20, 90, 360, z=0)[1:]
    stand = join([(124, Y, 0), (40, Y, 0)], eye, [(56, 70, 1)], [(62, 72, 1)])
    U = (62, 72, 1)
    W = 9   # rope thickness
    SW = 5  # one strand

    def fat(p, pts):
        p.rope(pts, width=int(W * p.scale), ends=False)

    def strand(p, pts):
        p.rope(pts, width=int(SW * p.scale), ends=False)

    fan = [[(88, 44, 3)], [(98, 54, 3)], [(102, 66, 3)]]
    p = d.panel("Unlay a hand of strands, tape the ends. Bend the eye", box)
    fat(p, stand)
    for f in fan:
        strand(p, join([U, (70, 66, 3)], f))
    p.label(30, 60, "eye")
    p.label(104, 36, "3 strands")
    p.label(98, 96, "standing part")

    p = d.panel("Tuck each strand under a strand of the rope, against the twist", box)
    fat(p, stand)
    for i, x in enumerate((72, 82, 92)):
        strand(p, [U, (x - 6, Y - 8, 3), (x, Y - 5, 1.5), (x + 3, Y, -3), (x + 6, Y + 5, 1.5), (x + 10, Y + 10, 3),
                   (x + 13, Y + 20, 3)])
    p.label(32, 60, "eye")
    p.label(66, 104, "under one")

    p = d.panel("Over one, under one: 5 rounds (3 in natural rope). Roll and trim", box)
    fat(p, join([(124, Y, 0), (40, Y, 0)], eye, [(56, 74, 0)], [(70, Y - 1, 0)]))
    for k in range(3):
        h = helix(62, Y, 5.2, 120 * k, 120 * k + 360 * 2.6, 16, axis="h", zr=4)
        strand(p, h + [(h[-1][0] + 4, h[-1][1], 4)])
    p.label(30, 60, "eye")
    p.label(84, 100, "5 rounds")
    p.label(110, 62, "trim")
    return d


def coil_path(n=6, C=(55, 58), reach=46, spread=16, h=4.0):
    """Centre line of a butterfly coil seen from above: bights laid left, right,
    left ... from the middle. Each later bight lies on top."""
    cx, cy = C
    pts = [(cx, cy - 50, 0), (cx, cy - 20, 0.5)]
    tips = []
    for i in range(n):
        side = -1 if i % 2 == 0 else 1
        row = i // 2
        ty = cy + (row - (n // 2 - 1) / 2) * spread
        tx = cx + side * reach
        z = 1.0 + i
        pts += [(cx + side * 6, cy - 2, z), (cx + side * 0.55 * reach, (cy + ty) / 2 - h, z)]
        pts += [(tx - side * 4, ty - h, z), (tx, ty, z), (tx - side * 4, ty + h, z),
                (cx + side * 0.55 * reach, (cy + ty) / 2 + h, z), (cx - side * 4, cy + 2, z)]
        tips.append((tx, ty))
    return pts, tips


def doubled_rope(p, pts, d=1.8, **kw):
    for s in (offset(pts, d), offset(pts, -d)):
        p.rope(s, ends=False, **kw)


@diagram("rope_coil")
def rope_coil():
    d = Diagram("BUTTERFLY COIL", 3, rope_w=3, caption_lines=3)
    box = (2, 4, 108, 118)
    C = (55, 66)
    full, tips = coil_path(6, C, spread=20)
    part = full[:2 + 7 * 3]
    p = d.panel("Both ends together, 2 m tail. Bights left, right, left", box)
    doubled_rope(p, part)
    p.arrow([part[-1][:2], (68, C[1] + 4), (90, C[1] + 22)])
    p.label(76, 12, "2 m tail")
    p.label(55, 112, "doubled rope")

    TW = 6
    wr = helix(46, C[1], 13, -90, -90 + 360 * 3, 8, axis="h", zr=16)
    tail = join([(30, 4, 9), (40, C[1] - 18, 9)], wr)
    p = d.panel("Stop with 2 m left. Wrap the tails round the middle 3 or 4 times", box)
    doubled_rope(p, full[2:])
    p.rope(tail, width=int(TW * p.scale), start="tails", start_at=(22, 10))

    p = d.panel("Bight of the tails through the top, tails through that bight. Pull", box)
    doubled_rope(p, full[2:])
    e = wr[-1]
    up = [(e[0] + 2, C[1] + 6, 2), (58, C[1] - 4, 2), (52, C[1] - 18, 18), (46, C[1] - 36, 18), (56, C[1] - 52, 18),
          (66, C[1] - 36, 18), (62, C[1] - 18, 18), (70, C[1] - 12, 18), (90, C[1] - 18, 18), (96, C[1] - 34, 18)]
    p.rope(join(tail, up), width=int(TW * p.scale), start="tails", start_at=(22, 10))
    p.arrow([(96, C[1] - 38), (84, C[1] - 44), (66, C[1] - 40), (40, C[1] - 36)], z=None)
    p.label(30, 22, "bight")
    p.label(55, 112, "then over the shoulders")
    return d


@diagram("rope_ridgeline")
def rope_ridgeline():
    d = Diagram("RIDGE LINE FOR A TARP", 3, rope_w=5, caption_lines=3)
    # 1: round turn and two half hitches, the knot_round_turn path turned on its side
    Y, hw, cx = 24, 10, 30
    path = join([(cx, 150, 0), (cx, 70, 0), (cx, Y + hw + 9, 0)],
                bar_turns(Y, hw, [(cx, cx + 4), (cx + 12, cx + 16)], out=60),
                [(61, Y + hw + 8, B), (62, 46, 0)],
                half_hitch_down(cx, 64, 62, 68), half_hitch_down(cx, 94, 70, 76)[1:],
                [(79, 112, 0)])
    path = tf(path, dx=-4, dy=90, rot=-90)
    k = knot([path], spec="uou" + "uou", name="ridge_tree1")
    p = d.panel("Tree one: round turn and two half hitches", (2, 14, 116, 104))
    p.post(20, -20, 140, w=2 * hw)
    show(p, k, 0, None, start="to tree two", start_at=(96, 72), end="end", end_at=(104, 26))
    p.label(20, 100, "tree one")

    # 2: butterfly loop and trucker's hitch round tree two (as knot_truckers)
    PX, PR = 100, 6
    stand = [(-30, 40, 0), (20, 40, 0), (34, 40, 0), (40, 42, 0.8), (44, 52, 0.8), (46, 66, 0.4), (52, 74, 0),
             (58, 66, -0.4), (60, 52, -0.8), (56, 44, -0.8), (48, 42, 0), (44, 40, 1.2), (52, 38, 0.6), (64, 38, 0)]
    to_post = [(80, 38, 0), (PX - PR - 3, 38, 0), (PX, 38, F), (PX + PR + 3, 42, 0), (PX + 2, 50, B),
               (PX - PR - 3, 54, 0), (80, 56, 0)]
    through = [(66, 57, 0), (60, 58, 1.5), (52, 60, 1.5), (49, 62, -1.5), (50, 68, -1.5), (58, 66, -1.5), (64, 68, 0)]
    tw = twist((72, 47), (86, 47), 2, 13, z=0)
    p = d.panel("Butterfly an arm short of tree two. Round it, back through, pull, lock", (-2, 0, 112, 110))
    p.post(PX, -20, 140, w=2 * PR)
    p.rope(join(stand, to_post, through, [(70, 66, 0)], tw, [(90, 66, 0), (92, 76, 0)]), start="from tree one",
           start_at=(20, 28), end="end", end_at=(86, 84))
    p.label(30, 82, "butterfly loop")
    p.label(PX - 8, 10, "tree two", anchor="rm")
    p.arrow([(58, 100), (88, 100)])
    p.label(54, 100, "pull hard", anchor="rm")

    # 3: the whole thing with the tarp
    p = d.panel("Tarp on two Prusiks. Guy the corners with taut-line hitches", (0, 6, 110, 114))
    LY = 30
    p.post(4, -20, 140, w=8)
    p.post(106, -20, 140, w=8)
    p.rope([(4, LY, 0), (106, LY, 0)], ends=False)
    for x in (24, 86):
        p.rope(helix(x - 4, LY, 4, -90, -90 + 360 * 2, 4, axis="h", zr=3), width=3, ends=False)
        p.rope([(x, LY + 3, 3), (x, LY + 12, 3)], width=3, ends=False)
    tarp = [(28, LY + 12), (82, LY + 12), (94, LY + 62), (16, LY + 62), (28, LY + 12)]
    p._add([(x, y, 1) for x, y in tarp], 3 * p.scale, "post")
    p.rope([(24, LY + 12, 3), (28, LY + 12, 3)], width=3, ends=False)
    p.rope([(82, LY + 12, 3), (86, LY + 12, 3)], width=3, ends=False)
    for (x0, y0), (x1, y1) in (((16, LY + 62), (6, LY + 78)), ((94, LY + 62), (104, LY + 78))):
        p.rope([(x0, y0, 2), (x1, y1, 2)], width=3, ends=False)
        p.rope(helix(x0 + (x1 - x0) * 0.5, y0 + (y1 - y0) * 0.5, 3, -90, 270, 3, axis="v", zr=2), width=3, ends=False)
        p._add([(x1, y1 - 2, 3), (x1, y1 + 6, 3)], 3 * p.scale, "post")
    p.label(26, 20, "Prusik")
    p.label(55, 62, "tarp")
    p.label(55, 102, "taut-line hitches")
    return d


#@@NEW@@



def main(argv):
    global DEBUG
    out = OUT
    words = []
    sheet = False
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--sheet":
            sheet = True
        elif a == "--debug":
            DEBUG = True
        elif a == "--out":
            out = argv[i + 1]
            i += 1
        else:
            words.append(a)
        i += 1
    os.makedirs(out, exist_ok=True)
    done = []
    for name, fn in DIAGRAMS.items():
        if words and not any(w in name for w in words):
            continue
        path = os.path.join(out, name + ".png")
        fn().save(path)
        done.append(path)
        print(path)
    if sheet and done:
        from PIL import Image

        os.makedirs("/tmp/knot_sheets", exist_ok=True)
        for old in os.listdir("/tmp/knot_sheets"):
            os.remove(os.path.join("/tmp/knot_sheets", old))
        for k in range(0, len(done), 4):
            group = done[k:k + 4]
            img = Image.new("RGB", (960, 568), (40, 40, 40))
            for j, p in enumerate(group):
                img.paste(Image.open(p), ((j % 2) * 480, (j // 2) * 284))
            img.save(f"/tmp/knot_sheets/sheet_{os.getpid()}_{k // 4:02d}.png")
        print("sheets:", sorted(os.listdir("/tmp/knot_sheets")))


if __name__ == "__main__":
    main(sys.argv[1:])
