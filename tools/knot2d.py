"""Plan knot drawings in 2D and let the crossings set the heights.

rope.py draws ropes in 3D (x, y, z) so it can show which strand is on top. Writing
z by hand for every control point is slow and easy to get wrong. Here you give
each rope as a flat path and say, crossing by crossing, whether the strand that
arrives later goes over ('o') or under ('u'). Heights are then made smooth bumps
round each crossing.

    k = Knot([post_path, rope_path], kinds=["post", "rope"], spec="oou")
    k.draw(panel, upto={1: 0.6}, labels=...)

Order of the spec: ropes are walked in list order, each from its start. A
crossing is decided when the later of its two strands reaches it: a later rope
in the list, or the same rope further along. Crossings where the base z (third
value of the control points) already differs by more than `thresh` decide
themselves and take no letter. Posts are never bumped.
"""
import math

import numpy as np

from rope import _pt, join, smooth  # noqa: F401


def _segments_cross(a, b, same):
    """Indices and params of crossings between polylines a and b (n,2), (m,2)."""
    p = a[:-1, None, :2]
    r = (a[1:, :2] - a[:-1, :2])[:, None, :]
    q = b[None, :-1, :2]
    s = (b[1:, :2] - b[:-1, :2])[None, :, :]
    rxs = r[..., 0] * s[..., 1] - r[..., 1] * s[..., 0]
    qp = q - p
    with np.errstate(divide="ignore", invalid="ignore"):
        t = (qp[..., 0] * s[..., 1] - qp[..., 1] * s[..., 0]) / rxs
        u = (qp[..., 0] * r[..., 1] - qp[..., 1] * r[..., 0]) / rxs
    ok = (np.abs(rxs) > 1e-9) & (t >= 0) & (t < 1) & (u >= 0) & (u < 1)
    if same:
        n = a.shape[0] - 1
        ii, jj = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
        ok &= jj > ii + 3
    ii, jj = np.nonzero(ok)
    return [(i, t[i, j], j, u[i, j]) for i, j in zip(ii, jj)]


class Knot:
    def __init__(self, paths, kinds=None, spec="", h=1.0, sigma=5.0, thresh=0.5, spacing=1.0):
        self.kinds = kinds or ["rope"] * len(paths)
        self.samples = []
        self.arclen = []
        for pts in paths:
            sm = np.array(smooth([_pt(p) for p in pts], spacing), dtype=float)
            self.samples.append(sm)
            d = np.hypot(np.diff(sm[:, 0]), np.diff(sm[:, 1]))
            self.arclen.append(np.concatenate([[0], np.cumsum(d)]))
        base = [s[:, 2].copy() for s in self.samples]
        found = []
        for i in range(len(paths)):
            for j in range(i, len(paths)):
                if self.kinds[i] == "post" and self.kinds[j] == "post":
                    continue
                for ia, ta, jb, tb in _segments_cross(self.samples[i], self.samples[j], i == j):
                    sa = self.arclen[i][ia] + ta * (self.arclen[i][ia + 1] - self.arclen[i][ia])
                    sb = self.arclen[j][jb] + tb * (self.arclen[j][jb + 1] - self.arclen[j][jb])
                    za = base[i][ia] + ta * (base[i][ia + 1] - base[i][ia])
                    zb = base[j][jb] + tb * (base[j][jb + 1] - base[j][jb])
                    a = self.samples[i][ia, :2] + ta * (self.samples[i][ia + 1, :2] - self.samples[i][ia, :2])
                    # (earlier strand, later strand)
                    if i == j and sb < sa:
                        early, late = (j, sb, zb), (i, sa, za)
                    elif i == j:
                        early, late = (i, sa, za), (j, sb, zb)
                    else:
                        early, late = (i, sa, za), (j, sb, zb)
                    found.append((late[0], late[1], early, late, tuple(a)))
        found.sort(key=lambda c: (c[0], c[1]))
        letters = [c for c in spec if c in "ou"]
        self.crossings = []
        k = 0
        for _r, _s, early, late, xy in found:
            if abs(early[2] - late[2]) > thresh:
                over = "late" if late[2] > early[2] else "early"
                auto = True
            else:
                if k >= len(letters):
                    self.crossings.append((early, late, None, xy, False))
                    k += 1
                    continue
                over = "late" if letters[k] == "o" else "early"
                k += 1
                auto = False
            self.crossings.append((early, late, over, xy, auto))
        self.needed = k
        self.given = len(letters)
        z = [b.copy() for b in base]
        for early, late, over, _xy, auto in self.crossings:
            if over is None or auto:
                continue
            up, down = (late, early) if over == "late" else (early, late)
            for (ri, s0, _z0), sign in ((up, 1), (down, -1)):
                if self.kinds[ri] == "post":
                    continue
                z[ri] += sign * h * np.exp(-((self.arclen[ri] - s0) ** 2) / (2 * sigma ** 2))
        for ri, zz in enumerate(z):
            self.samples[ri][:, 2] = zz
        self.problems = []
        for n, (early, late, over, xy, auto) in enumerate(self.crossings):
            if over is None:
                self.problems.append((n, xy, "no letter"))
                continue
            ze = np.interp(early[1], self.arclen[early[0]], z[early[0]])
            zl = np.interp(late[1], self.arclen[late[0]], z[late[0]])
            gap = (zl - ze) if over == "late" else (ze - zl)
            if gap < 0.3:
                self.problems.append((n, xy, f"weak {gap:.2f}"))

    def report(self, name=""):
        if self.needed != self.given:
            print(f"  {name}: spec has {self.given} letters, needs {self.needed}")
        for n, xy, why in self.problems:
            print(f"  {name}: crossing {n} at ({xy[0]:.0f},{xy[1]:.0f}) {why}")

    def path(self, i, upto=None, start=None):
        """Samples of rope i, optionally cut: upto/start are a fraction (<=1) or a length."""
        s = self.samples[i]
        L = self.arclen[i][-1]

        def at(v):
            v = v * L if v <= 1.0 else v
            return int(np.searchsorted(self.arclen[i], v))

        a = 0 if start is None else at(start)
        b = len(s) if upto is None else max(a + 2, at(upto))
        return [tuple(p) for p in s[a:b]]

    def length(self, i):
        return float(self.arclen[i][-1])

    def nearest(self, i, x, y):
        """Arc length on rope i nearest to (x, y): handy for cut points."""
        s = self.samples[i]
        k = int(np.argmin(np.hypot(s[:, 0] - x, s[:, 1] - y)))
        return float(self.arclen[i][k])

    def debug(self, panel):
        for n, (_e, _l, _o, xy, auto) in enumerate(self.crossings):
            panel.mark(xy[0], xy[1], ("a" if auto else "") + str(n))


def pair(points, d):
    """Two parallel copies of a sampled path (a doubled rope), keeping z."""
    pts = [_pt(p) for p in points]
    left, right = [], []
    n = len(pts)
    for k in range(n):
        a = pts[max(0, k - 2)]
        b = pts[min(n - 1, k + 2)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        m = math.hypot(tx, ty) or 1.0
        nx, ny = -ty / m, tx / m
        x, y, z = pts[k]
        left.append((x + nx * d, y + ny * d, z))
        right.append((x - nx * d, y - ny * d, z))
    return left, right


def cap(left, right, end=True):
    """Join a doubled pair round a bight tip at the end (or start) into one path."""
    if end:
        a, b = left[-1], right[-1]
        pa = left[-3]
    else:
        a, b = right[0], left[0]
        pa = right[2]
    cx, cy = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    cz = (a[2] + b[2]) / 2
    r = math.hypot(a[0] - cx, a[1] - cy)
    ang0 = math.atan2(a[1] - cy, a[0] - cx)
    # direction of travel at the tip
    tx, ty = a[0] - pa[0], a[1] - pa[1]
    # sweep from a to b through the forward side
    best = None
    for sgn in (1, -1):
        mid = ang0 + sgn * math.pi / 2
        mx, my = cx + r * math.cos(mid), cy + r * math.sin(mid)
        score = (mx - cx) * tx + (my - cy) * ty
        if best is None or score > best[0]:
            best = (score, sgn)
    sgn = best[1]
    arc_pts = [(cx + r * math.cos(ang0 + sgn * math.pi * t / 10), cy + r * math.sin(ang0 + sgn * math.pi * t / 10), cz)
               for t in range(1, 10)]
    if end:
        return join(left, arc_pts, list(reversed(right)))
    return join(list(reversed(right)), arc_pts, left)
