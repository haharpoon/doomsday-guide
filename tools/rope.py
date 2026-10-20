"""Rope drawing helper for the knot diagrams.

A rope is a list of control points (x, y, z) in a panel's design box. The path
is smoothed with a centripetal Catmull-Rom spline and drawn as a thick band.
z is height towards the viewer: where two strands cross, the one with the
higher z at that spot is drawn on top and the lower one gets a black gap, so
every crossing shows which strand is over. Posts, poles and rings are strands
too, so a wrap that goes behind a post (z < 0) is hidden by it.

Rendering is a z-buffer at 3x size, then scaled down for smooth edges.

    from rope import Diagram, helix
    d = Diagram("CLOVE HITCH", 3)
    p = d.panel("Round the post", box=(100, 150))
    p.post(50, 0, 150)
    p.rope([(0, 20, 1), (50, 40, 1), ...], end="end", start="standing")
    d.save("content/img/knot_clove.png")

Run tools/gen_knots2.py to rebuild every knot picture.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFont

GREEN = (0x1A, 0xFF, 0x80)
EDGE = (0x0C, 0x8A, 0x45)
POST_FILL = (0x06, 0x30, 0x18)
BLACK = (0, 0, 0)
W, H = 480, 284
SS = 3
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def font(size, bold=True):
    return ImageFont.truetype(FONT if bold else FONT_REG, int(size * SS))


# ---------------------------------------------------------------- path helpers

def helix(cx, cy, r, a0, a1, pitch, axis="v", steps_per_turn=36, zr=1.0, z0=0.0):
    """Points of a wrap round an axis through (cx, cy).

    Angle 0 is the front (z = +zr). A positive angle moves to +x for a vertical
    axis ("v") or +y for a horizontal one ("h"). pitch is the advance along the
    axis per full turn (design units, sign gives the direction).
    """
    n = max(2, int(abs(a1 - a0) / 360 * steps_per_turn) + 1)
    out = []
    for i in range(n + 1):
        a = a0 + (a1 - a0) * i / n
        t = math.radians(a)
        along = pitch * (a - a0) / 360.0
        side = r * math.sin(t)
        z = z0 + zr * math.cos(t)
        if axis == "v":
            out.append((cx + side, cy + along, z))
        else:
            out.append((cx + along, cy + side, z))
    return out


def arc(cx, cy, r, a0, a1, z=0.0, z1=None, steps=None, ry=None):
    """Arc in the drawing plane. Angles in degrees, 0 = +x, 90 = +y (down)."""
    if steps is None:
        steps = max(3, int(abs(a1 - a0) / 12))
    ry = r if ry is None else ry
    z1 = z if z1 is None else z1
    out = []
    for i in range(steps + 1):
        f = i / steps
        a = math.radians(a0 + (a1 - a0) * f)
        out.append((cx + r * math.cos(a), cy + ry * math.sin(a), z + (z1 - z) * f))
    return out


def line(x0, y0, x1, y1, z=0.0, z1=None, steps=2):
    z1 = z if z1 is None else z1
    return [
        (x0 + (x1 - x0) * i / steps, y0 + (y1 - y0) * i / steps, z + (z1 - z) * i / steps)
        for i in range(steps + 1)
    ]


def _pt(p):
    if len(p) == 2:
        return (float(p[0]), float(p[1]), 0.0)
    return (float(p[0]), float(p[1]), float(p[2]))


def join(*parts):
    """Concatenate point lists, dropping a repeated joint point."""
    out = []
    for part in parts:
        for p in part:
            p = _pt(p)
            if out and abs(out[-1][0] - p[0]) < 1e-6 and abs(out[-1][1] - p[1]) < 1e-6:
                continue
            out.append(p)
    return out


def smooth(points, spacing):
    """Centripetal Catmull-Rom through points, resampled every `spacing` units."""
    pts = [np.array(_pt(p)) for p in points]
    clean = [pts[0]]
    for p in pts[1:]:
        if np.hypot(*(p[:2] - clean[-1][:2])) > 1e-6:
            clean.append(p)
    pts = clean
    if len(pts) == 1:
        return np.array(pts)
    ext = [2 * pts[0] - pts[1]] + pts + [2 * pts[-1] - pts[-2]]
    dense = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]

        def tj(ti, a, b):
            return ti + max(np.hypot(*(b[:2] - a[:2])), 1e-4) ** 0.5

        t0 = 0.0
        t1 = tj(t0, p0, p1)
        t2 = tj(t1, p1, p2)
        t3 = tj(t2, p2, p3)
        seg = max(2, int(np.hypot(*(p2[:2] - p1[:2])) / max(spacing, 1e-3) * 2) + 2)
        for k in range(seg):
            t = t1 + (t2 - t1) * k / seg
            a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
            a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
            a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
            b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
            b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
            dense.append((t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2)
    dense.append(pts[-1])
    dense = np.array(dense)
    d = np.hypot(np.diff(dense[:, 0]), np.diff(dense[:, 1]))
    s = np.concatenate([[0], np.cumsum(d)])
    total = s[-1]
    n = max(2, int(total / spacing) + 1)
    targets = np.linspace(0, total, n)
    out = np.stack([np.interp(targets, s, dense[:, j]) for j in range(3)], axis=1)
    return out


# ---------------------------------------------------------------- the diagram

class Strand:
    def __init__(self, samples, width, style, sid, clip=None):
        self.clip = clip
        self.samples = samples  # (n, 3) in final pixels + z
        self.width = width  # final pixels
        self.style = style
        self.sid = sid


class Panel:
    def __init__(self, diagram, rect, caption, box, number):
        self.d = diagram
        self.rect = rect  # x0, y0, x1, y1 in final pixels (drawing area)
        self.caption = caption
        self.number = number
        if len(box) == 2:
            box = (0, 0, box[0], box[1])
        bx, by, bx1, by1 = box
        bw, bh = bx1 - bx, by1 - by
        rw, rh = rect[2] - rect[0], rect[3] - rect[1]
        self.scale = min(rw / bw, rh / bh)
        self.ox = rect[0] + (rw - bw * self.scale) / 2 - bx * self.scale
        self.oy = rect[1] + (rh - bh * self.scale) / 2 - by * self.scale
        self.clip = None

    def xy(self, x, y):
        return (self.ox + x * self.scale, self.oy + y * self.scale)

    def _add(self, points, width, style):
        pts = [_pt(p) for p in points]
        px = [(*self.xy(x, y), z) for x, y, z in pts]
        samples = smooth(px, 0.45)
        st = self.d._strand(samples, width, style)
        st.clip = self.clip
        return st

    def rope(self, points, width=None, start=None, end=None, arrow=False, start_at=None,
             end_at=None, style="rope", ends=True):
        """A rope through control points. start/end label the two ends."""
        width = width or self.d.rope_w
        st = self._add(points, width, style)
        if arrow:
            self.d.heads.append((st.samples, width))
        if start:
            self._end_label(st.samples, 0, start, start_at)
        if end:
            self._end_label(st.samples, -1, end, end_at)
        return st

    def tape(self, points, width=None, **kw):
        """Flat webbing: a wider band with a dark centre line."""
        return self.rope(points, width=width or int(self.d.rope_w * 1.6), style="tape", **kw)

    def _end_label(self, s, idx, text, at):
        if at is not None:
            x, y = self.xy(*at)
            self.d.labels.append((x, y, text, "mm"))
            return
        x, y = s[idx][0], s[idx][1]
        j = 8 if idx == 0 else -9
        dx, dy = x - s[j][0], y - s[j][1]
        n = math.hypot(dx, dy) or 1
        dx, dy = dx / n, dy / n
        lx, ly = x + dx * 12, y + dy * 12
        anchor = ("l" if dx > 0.5 else "r" if dx < -0.5 else "m") + ("t" if dy > 0.5 else "b" if dy < -0.5 else "m")
        self.d.labels.append((lx, ly, text, anchor))

    def post(self, x, y0, y1, w=16, z=0.0):
        """Vertical post or tree, centred on x."""
        return self._add([(x, y0, z), (x, y1, z)], w * self.scale, "post")

    def pole(self, x0, y0, x1, y1, w=14, z=0.0):
        return self._add([(x0, y0, z), (x1, y1, z)], w * self.scale, "post")

    def ring(self, cx, cy, r, w=7, tilt=0.35, z=0.0):
        """A ring seen at a slant: top half behind (z-), bottom half in front."""
        pts = []
        for i in range(0, 361, 10):
            a = math.radians(i)
            pts.append((cx + r * math.cos(a), cy + r * tilt * math.sin(a), z + math.sin(a)))
        return self._add(pts, w * self.scale, "post")

    def arrow(self, points, z=50.0, lift=0.02):
        """A thin pointer showing where the end goes next.

        z=None keeps each point's own height, so the pointer dives under the
        strands the end will pass under."""
        if z is None:
            pts = [(_pt(p)[0], _pt(p)[1], _pt(p)[2] + lift) for p in points]
        else:
            pts = [(_pt(p)[0], _pt(p)[1], z) for p in points]
        st = self._add(pts, max(3, self.d.rope_w * 0.32), "arrow")
        self.d.heads.append((st.samples, None))
        return st

    def label(self, x, y, text, anchor="mm"):
        x, y = self.xy(x, y)
        self.d.labels.append((x, y, text, anchor))

    def mark(self, x, y, text):
        """A small numbered or lettered tag in a box."""
        x, y = self.xy(x, y)
        self.d.marks.append((x, y, text))


class Diagram:
    def __init__(self, title, panels=3, rope_w=None, caption_lines=2, widths=None, title_size=17,
                 layout="cols", cap_w=118):
        self.title = title
        self.n = panels
        self.layout = layout
        self.cap_w = cap_w
        if layout == "rows":
            rope_w = rope_w or {1: 12, 2: 11, 3: 9, 4: 8}.get(panels, 8)
            caption_lines = 4
        self.rope_w = rope_w or {1: 13, 2: 11, 3: 9, 4: 8}.get(panels, 8)
        self.halo = 3.2
        self.strands = []
        self.panels = []
        self.heads = []
        self.labels = []
        self.marks = []
        self.caption_lines = caption_lines
        self.title_size = title_size
        widths = widths or [1] * panels
        total = float(sum(widths))
        self.cols = []
        x = 0.0
        for wv in widths:
            self.cols.append((x, x + W * wv / total))
            x += W * wv / total
        self.cap_h = 6 + 14 * caption_lines
        self.top = 27

    def panel(self, caption, box=(100, 140)):
        """box is (w, h) from the origin, or a view (x0, y0, x1, y1) in design units."""
        i = len(self.panels)
        if self.layout == "rows":
            rh = (H - self.top - 2) / self.n
            y0 = self.top + 2 + i * rh
            rect = (self.cap_w + 6, y0 + 3, W - 6, y0 + rh - 3)
            p = Panel(self, rect, caption, box, i + 1)
            p.clip = (self.cap_w + 2, y0 + 2, W - 2, y0 + rh - 2)
            p.row = (y0, y0 + rh)
        else:
            x0, x1 = self.cols[i]
            rect = (x0 + 8, self.top + 6, x1 - 8, H - self.cap_h - 4)
            p = Panel(self, rect, caption, box, i + 1)
            p.clip = (x0 + 3, self.top + 2, x1 - 3, H - self.cap_h - 1)
        self.panels.append(p)
        return p

    def _strand(self, samples, width, style):
        st = Strand(samples, width, style, len(self.strands))
        self.strands.append(st)
        return st

    # -------------------------------------------------------------- render
    def render(self, warn=True):
        w, h = W * SS, H * SS
        zf = np.full((h, w), -np.inf)
        df = np.full((h, w), np.inf)
        idf = np.full((h, w), -1, dtype=np.int32)
        sf = np.zeros((h, w))
        col = np.zeros((h, w, 3), dtype=np.uint8)
        ties = []
        for st in self.strands:
            s = st.samples
            seg = np.hypot(np.diff(s[:, 0]), np.diff(s[:, 1]))
            arclen = np.concatenate([[0], np.cumsum(seg)]) * SS
            r = st.width * SS / 2.0
            local = (st.width + 2 * self.halo) * SS * 2.2
            pad = int(math.ceil(r + 2))
            cl = (0, 0, w, h) if st.clip is None else tuple(int(v * SS) for v in st.clip)
            for k in range(len(s)):
                cx, cy, z = s[k, 0] * SS, s[k, 1] * SS, s[k, 2]
                x0, x1 = max(cl[0], int(cx) - pad), min(cl[2], int(cx) + pad + 1)
                y0, y1 = max(cl[1], int(cy) - pad), min(cl[3], int(cy) + pad + 1)
                if x0 >= x1 or y0 >= y1:
                    continue
                yy, xx = np.mgrid[y0:y1, x0:x1]
                dist = np.hypot(xx - cx, yy - cy)
                inside = dist <= r
                if not inside.any():
                    continue
                zw = zf[y0:y1, x0:x1]
                dw = df[y0:y1, x0:x1]
                iw = idf[y0:y1, x0:x1]
                sw = sf[y0:y1, x0:x1]
                is_local = (iw == st.sid) & (np.abs(sw - arclen[k]) < local)
                other = inside & ~is_local & (iw >= 0)
                if warn and st.style != "arrow":
                    tie = other & (np.abs(zw - z) < 0.04)
                    if tie.any():
                        ties.append((cx / SS, cy / SS, st.sid))
                upd = inside & ((is_local & (dist < dw)) | (~is_local & (z > zw)))
                if not upd.any():
                    continue
                zw[upd] = z
                dw[upd] = dist[upd]
                iw[upd] = st.sid
                sw[upd] = arclen[k]
                c = self._colour(st.style, dist / r)
                cw = col[y0:y1, x0:x1]
                for j in range(3):
                    cj = cw[..., j]
                    cj[upd] = c[..., j][upd]
        black = np.zeros((h, w), dtype=bool)
        for st in self.strands:
            s = st.samples
            seg = np.hypot(np.diff(s[:, 0]), np.diff(s[:, 1]))
            arclen = np.concatenate([[0], np.cumsum(seg)]) * SS
            r = (st.width / 2.0 + self.halo) * SS
            local = (st.width + 2 * self.halo) * SS * 2.2
            pad = int(math.ceil(r + 2))
            cl = (0, 0, w, h) if st.clip is None else tuple(int(v * SS) for v in st.clip)
            for k in range(len(s)):
                cx, cy, z = s[k, 0] * SS, s[k, 1] * SS, s[k, 2]
                x0, x1 = max(cl[0], int(cx) - pad), min(cl[2], int(cx) + pad + 1)
                y0, y1 = max(cl[1], int(cy) - pad), min(cl[3], int(cy) + pad + 1)
                if x0 >= x1 or y0 >= y1:
                    continue
                yy, xx = np.mgrid[y0:y1, x0:x1]
                inside = np.hypot(xx - cx, yy - cy) <= r
                zw = zf[y0:y1, x0:x1]
                iw = idf[y0:y1, x0:x1]
                sw = sf[y0:y1, x0:x1]
                is_local = (iw == st.sid) & (np.abs(sw - arclen[k]) < local)
                cut = inside & (iw >= 0) & ~is_local & (zw < z - 0.04)
                black[y0:y1, x0:x1] |= cut
        col[black] = 0
        img = Image.fromarray(col, "RGB")
        self._overlay(img)
        self.ties = ties
        if warn and ties:
            seen = []
            for x, y, sid in ties:
                if all(math.hypot(x - a, y - b) > 10 for a, b in seen):
                    seen.append((x, y))
            self.tie_spots = seen
        else:
            self.tie_spots = []
        return img.resize((W, H), Image.LANCZOS)

    def _colour(self, style, f):
        out = np.zeros(f.shape + (3,), dtype=np.uint8)
        g = np.array(GREEN, dtype=np.uint8)
        e = np.array(EDGE, dtype=np.uint8)
        if style == "rope":
            out[:] = g
            out[f > 0.80] = e
        elif style == "tape":
            out[:] = g
            out[(f > 0.84)] = e
            out[(f < 0.16)] = e
        elif style == "post":
            out[:] = np.array(POST_FILL, dtype=np.uint8)
            out[f > 0.72] = g
        elif style == "arrow":
            out[:] = g
        return out

    def _overlay(self, img):
        d = ImageDraw.Draw(img)
        S = SS
        green = GREEN
        # arrow heads
        for s, width in self.heads:
            if len(s) < 6:
                continue
            tip = s[-1]
            back = s[max(0, len(s) - 14)]
            ang = math.atan2(tip[1] - back[1], tip[0] - back[0])
            size = 9 if width is None else max(10, width * 1.1)
            reach = 2 if width is None else width * 0.6
            bx, by = tip[0] + reach * math.cos(ang), tip[1] + reach * math.sin(ang)
            pts = [
                (bx + size * 0.55 * math.cos(ang), by + size * 0.55 * math.sin(ang)),
                (bx - size * math.cos(ang - 0.55), by - size * math.sin(ang - 0.55)),
                (bx - size * math.cos(ang + 0.55), by - size * math.sin(ang + 0.55)),
            ]
            d.polygon([(x * S, y * S) for x, y in pts], fill=green, outline=BLACK, width=S)
        f_lab = font(11)
        for x, y, text, anchor in self.labels:
            d.text((x * S, y * S), text, fill=green, font=f_lab, anchor=anchor,
                   stroke_width=3 * S, stroke_fill=BLACK)
        f_mark = font(11)
        for x, y, text in self.marks:
            d.rounded_rectangle([(x - 8) * S, (y - 8) * S, (x + 8) * S, (y + 8) * S], radius=4 * S,
                                fill=BLACK, outline=green, width=2 * S)
            d.text((x * S, y * S), text, fill=green, font=f_mark, anchor="mm")
        # title, separators, numbers, captions
        d.text((7 * S, 4 * S), self.title, fill=green, font=font(self.title_size))
        f_cap = font(11.5)
        if self.layout == "rows":
            for i, p in enumerate(self.panels):
                y0, y1 = p.row
                if i:
                    d.line([(4 * S, y0 * S), ((W - 4) * S, y0 * S)], fill=EDGE, width=2 * S)
                cx, cy = 15, y0 + 14
                d.ellipse([(cx - 10) * S, (cy - 10) * S, (cx + 10) * S, (cy + 10) * S], fill=BLACK,
                          outline=green, width=2 * S)
                d.text((cx * S, cy * S), str(p.number), fill=green, font=font(13), anchor="mm")
                lines = _wrap(p.caption, f_cap, (self.cap_w - 32) * S)
                n_l = len(lines)
                y = y0 + 6
                for j, ln in enumerate(lines):
                    xx = 30
                    d.text((xx * S, y * S), ln, fill=green, font=f_cap)
                    y += 14
                if y > y1 + 2:
                    raise ValueError(f"caption too long for {self.title} row {p.number}: {p.caption!r}")
            return
        for i, p in enumerate(self.panels):
            x0, x1 = self.cols[i]
            if i:
                d.line([(x0 * S, (self.top + 4) * S), (x0 * S, (H - 4) * S)], fill=EDGE, width=2 * S)
            if self.n > 1:
                cx, cy = x0 + 15, self.top + 13
                d.ellipse([(cx - 10) * S, (cy - 10) * S, (cx + 10) * S, (cy + 10) * S], fill=BLACK,
                          outline=green, width=2 * S)
                d.text((cx * S, cy * S), str(p.number), fill=green, font=font(13), anchor="mm")
            lines = _wrap(p.caption, f_cap, (x1 - x0 - 8) * S)
            y = H - self.cap_h + 2
            for ln in lines[: self.caption_lines]:
                d.text(((x0 + 5) * S, y * S), ln, fill=green, font=f_cap)
                y += 14
            if len(lines) > self.caption_lines:
                raise ValueError(f"caption too long for {self.title} panel {p.number}: {p.caption!r}")

    def save(self, path, warn=True):
        img = self.render(warn=warn)
        img.save(path)
        if warn and self.tie_spots:
            print(f"  {path}: equal-height crossings near {[(round(x), round(y)) for x, y in self.tie_spots]}")
        return img


def _wrap(text, f, width):
    words = text.split()
    lines = [""]
    for word in words:
        trial = (lines[-1] + " " + word).strip()
        if f.getlength(trial) > width and lines[-1]:
            lines.append(word)
        else:
            lines[-1] = trial
    return lines


# ---------------------------------------------------------------- shape helpers

def tf(points, dx=0.0, dy=0.0, s=1.0, rot=0.0, mirror=False, dz=0.0, zs=1.0):
    """Move, scale, rotate (degrees) and optionally mirror (x -> -x) a point list."""
    c, si = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    out = []
    for p in points:
        x, y, z = _pt(p)
        if mirror:
            x = -x
        x, y = x * s, y * s
        x, y = x * c - y * si, x * si + y * c
        out.append((x + dx, y + dy, z * zs + dz))
    return out


def offset(points, d, spacing=1.0):
    """A parallel copy of a smoothed path, d units to the left of travel."""
    s = smooth(points, spacing)
    out = []
    for i in range(len(s)):
        a = s[max(0, i - 2)]
        b = s[min(len(s) - 1, i + 2)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        n = math.hypot(tx, ty) or 1.0
        out.append((s[i][0] - ty / n * d * -1, s[i][1] + tx / n * d * -1, s[i][2]))
    return out


def reverse(points):
    return list(reversed([_pt(p) for p in points]))


def bight(points, d, dz=0.0):
    """Fold a path into a bight: out along one side, round the tip, back along the other.

    points run from the open legs to the tip of the bight. Returns one path.
    """
    s = smooth(points, 1.0)
    left = offset(s, d)
    right = offset(s, -d)
    tip = s[-1]
    a = s[-3]
    ang = math.degrees(math.atan2(tip[1] - a[1], tip[0] - a[0]))
    # half circle from the left side round the tip to the right side
    cap = []
    for i in range(1, 12):
        t = math.radians(ang + 90 - 180 * i / 12)
        cap.append((tip[0] + d * math.cos(t), tip[1] + d * math.sin(t), tip[2] + dz))
    return join(left, cap, reverse(right))


# ---------------------------------------------------------------- simple 3D

def ring3(cx, y, r, a0, a1, dy=0.0, cz=0.0, step=10):
    """Points round a vertical axis at x=cx, in real units: angle 0 is the front.

    dy is the drop along the axis over the whole sweep (like a helix)."""
    n = max(2, int(abs(a1 - a0) / step))
    out = []
    for i in range(n + 1):
        f = i / n
        a = math.radians(a0 + (a1 - a0) * f)
        out.append((cx + r * math.sin(a), y + dy * f, cz + r * math.cos(a)))
    return out


def view(points, tilt=25.0, cy=0.0, depth=0.12):
    """Look down on a real-unit 3D model by `tilt` degrees.

    Model: x right, y down, z towards you. Returns (x, y, z) for the renderer
    with z as depth (scaled by `depth`)."""
    t = math.radians(tilt)
    out = []
    for p in points:
        x, y, z = _pt(p)
        yy = cy + (y - cy) * math.cos(t) + z * math.sin(t)
        zz = -(y - cy) * math.sin(t) + z * math.cos(t)
        out.append((x, yy, zz * depth))
    return out
