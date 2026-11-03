"""Best-case VL53L5CX + 2x SG90 pan/tilt room sweep, simulated.

Writes sweep.txt: the serial stream a realistic firmware would send
(`A pan tilt` then one `F m0..m63` median-of-4 frame per position).
Geometry is the cavemap.py sensor frame: origin at the sensor, +Y up,
+Z forward at pan 90 / tilt 90, +X right. Units metres.

    python3 sim/sim_sweep.py [step_deg] [out_path]

step_deg defaults to 2. A coarser step (for example 90) is only for a
smoke check. The picture renderer is sim/render_sim.py.
"""

import math
import os
import sys
import time
import warnings

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import cavemap as cm

RNG = np.random.default_rng(7)
FOV = cm.FOV_RAD                    # the app's own 45 deg model
SUB = 4                             # 4x4 rays per zone cone
FRAMES_PER_POS = 4
MAX_MM = 4000
LEVER = np.array([0.0, 0.030, 0.012])   # sensor sits ~3 cm above / 1.2 cm ahead of the tilt axis

# ---- room (boxes, axis aligned: xmin,xmax, ymin,ymax, zmin,zmax, reflectance) ----
F, C = -0.9, 1.5                    # floor / ceiling relative to sensor (0.9 m high, 2.4 m room)
X0, X1, Z0, Z1 = -2.0, 2.0, -1.15, 2.35   # 4.0 x 3.5 m room, scanner 0.6 m back of centre
T = 0.1
XH = 3.3                            # hallway behind the doorway in the right wall
BOXES = [
    # shell
    (X0 - T, XH + T, F - T, F, Z0 - T, Z1 + T, 0.35),      # floor
    (X0 - T, XH + T, C, C + T, Z0 - T, Z1 + T, 0.80),      # ceiling
    (X0 - T, XH + T, F, C, Z0 - T, Z0, 0.75),              # back wall
    (X0 - T, XH + T, F, C, Z1, Z1 + T, 0.75),              # front wall
    (X0 - T, X0, F, C, Z0, Z1, 0.75),                      # left wall
    (X1, X1 + T, F, C, Z0, 0.6, 0.75),                     # right wall, before door
    (X1, X1 + T, F, C, 1.5, Z1, 0.75),                     # right wall, after door
    (X1, X1 + T, 1.1, C, 0.6, 1.5, 0.75),                  # lintel (door 0.9 x 2.0 m)
    (XH, XH + T, F, C, Z0, Z1, 0.75),                      # hallway far wall
    # sofa against the front wall
    (-1.3, 0.5, F, -0.48, 1.50, Z1, 0.25),
    (-1.3, 0.5, -0.48, -0.05, 2.10, Z1, 0.25),
    (-1.3, -1.1, -0.48, -0.30, 1.50, 2.10, 0.25),
    (0.3, 0.5, -0.48, -0.30, 1.50, 2.10, 0.25),
    # coffee table
    (-0.8, 0.2, F, -0.48, 0.55, 1.05, 0.45),
    # chair (seat + back), right of the scanner
    (1.00, 1.45, F, -0.45, -0.05, 0.40, 0.40),
    (1.38, 1.46, -0.45, 0.00, -0.05, 0.40, 0.40),
    # bookshelf on the left wall
    (-2.0, -1.68, F, 1.0, 0.0, 1.2, 0.30),
]
B = np.array(BOXES, dtype=np.float64)
LO = B[:, [0, 2, 4]]
HI = B[:, [1, 3, 5]]
REFL = B[:, 6]


def rot(v, pan, tilt):
    """Exactly frame_to_points' rotation: tilt about X, then pan about Y."""
    x, y, z = v[..., 0], v[..., 1], v[..., 2]
    phi = np.radians(90.0 - tilt)
    y2 = y * np.cos(phi) - z * np.sin(phi)
    z2 = y * np.sin(phi) + z * np.cos(phi)
    psi = np.radians(pan - 90.0)
    x3 = x * np.cos(psi) + z2 * np.sin(psi)
    z3 = -x * np.sin(psi) + z2 * np.cos(psi)
    return np.stack([x3, y2, z3], axis=-1)


def local_dirs():
    """Sub-ray directions per zone, sensor frame, same angle model as the app."""
    half = FOV / 2
    pitch = FOV / 8                 # cone per zone (5.6 deg)
    offs = (np.arange(SUB) + 0.5) / SUB - 0.5
    rows, cols = np.mgrid[0:8, 0:8]
    out = np.zeros((64, SUB * SUB, 3))
    for k, (r, c) in enumerate(zip(rows.ravel(), cols.ravel())):
        ax0 = (c - 3.5) / 3.5 * half
        ay0 = (3.5 - r) / 3.5 * half
        j = 0
        for oy in offs:
            for ox in offs:
                ax, ay = ax0 + ox * pitch, ay0 - oy * pitch
                out[k, j] = [math.sin(ax) * math.cos(ay), math.sin(ay), math.cos(ax) * math.cos(ay)]
                j += 1
    return out


def cast(orig, dirs):
    """Nearest hit of rays against box exteriors. Returns t, refl, cos(incidence)."""
    inv = 1.0 / np.where(np.abs(dirs) < 1e-12, 1e-12, dirs)
    t1 = (LO[None] - orig[:, None]) * inv[:, None]
    t2 = (HI[None] - orig[:, None]) * inv[:, None]
    tmin = np.minimum(t1, t2)
    tmax = np.maximum(t1, t2)
    tn = tmin.max(axis=2)
    axis = tmin.argmax(axis=2)
    tf = tmax.min(axis=2)
    ok = (tn <= tf) & (tn > 1e-4)
    tn = np.where(ok, tn, np.inf)
    best = tn.argmin(axis=1)
    idx = np.arange(len(dirs))
    t = tn[idx, best]
    ax = axis[idx, best]
    cosi = np.abs(dirs[idx, ax])
    return t, REFL[best], cosi


def zone_value(d, refl, cosi):
    """One zone from its sub-rays: dominant (strongest) target, edges blur, some mix."""
    good = np.isfinite(d)
    if good.sum() < 3:
        return 0.0
    d, refl, cosi = d[good], refl[good], cosi[good]
    sig = refl * np.maximum(cosi, 0.05) / np.maximum(d, 0.1) ** 2
    order = np.argsort(d)
    d, sig = d[order], sig[order]
    gaps = np.where(np.diff(d) > np.maximum(0.08, 0.04 * d[:-1]))[0]
    bounds = np.concatenate([[0], gaps + 1, [len(d)]])
    clusters = [(d[a:b], sig[a:b]) for a, b in zip(bounds[:-1], bounds[1:])]
    weights = np.array([s.sum() for _, s in clusters])
    k = int(weights.argmax())
    frac = weights[k] / weights.sum()
    dom = float(np.average(clusters[k][0], weights=clusters[k][1]))
    if len(clusters) > 1 and frac < 0.8 and RNG.random() < 0.3:
        # mixed pixel: a flying point between foreground and background
        top = np.argsort(weights)[-2:]
        meds = [float(np.median(clusters[i][0])) for i in top]
        w = weights[top] / weights[top].sum()
        return float(np.dot(w, meds))
    return dom


def measure(true_m, strength):
    """Per-frame range noise and dropouts on a zone value in metres."""
    if true_m <= 0:
        return 0
    sigma = true_m * (0.008 + 0.005 * true_m)          # ~1% near, ~3% at 4 m
    mm = (true_m + RNG.normal(0, sigma)) * 1000.0
    p_drop = 0.01 + 0.25 * max(0.0, (true_m - 2.8) / 1.2) ** 2 + (0.25 if strength < 0.02 else 0.0)
    if RNG.random() < p_drop or mm > MAX_MM or mm < 20:
        return 0
    return int(round(mm))


def main(out=None, step=2):
    if out is None:
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sweep.txt")
    t0 = time.time()
    loc = local_dirs()                                  # 64 x 16 x 3
    pans = np.arange(0, 181, step)
    tilts = np.arange(45, 136, step)
    lines, positions = ["READY"], 0
    zero = 0
    for ti, tilt in enumerate(tilts):
        row = pans if ti % 2 == 0 else pans[::-1]       # serpentine, like a sane firmware
        direction = 1 if ti % 2 == 0 else -1
        for pan in row:
            # SG90: ~+-1 deg jitter plus ~0.5 deg direction-dependent backlash
            ap = pan + np.clip(RNG.normal(0, 0.5), -1, 1) + 0.5 * direction
            at = tilt + np.clip(RNG.normal(0, 0.5), -1, 1)
            dirs = rot(loc.reshape(-1, 3), ap, at)
            orig = rot(LEVER, ap, at)
            t, refl, cosi = cast(np.broadcast_to(orig, dirs.shape), dirs)
            t = t.reshape(64, -1)
            refl = refl.reshape(64, -1)
            cosi = cosi.reshape(64, -1)
            frames = np.zeros((FRAMES_PER_POS, 64))
            for z in range(64):
                for f in range(FRAMES_PER_POS):
                    v = zone_value(t[z], refl[z], cosi[z])
                    strength = float(np.median(refl[z] * cosi[z])) / max(v, 0.1) ** 2 if v else 0
                    frames[f, z] = measure(v, strength)
            # firmware: per-zone median of the valid frames, need 2 of 4
            valid = frames > 0
            med = np.where(valid, frames, np.nan)
            with np.errstate(all="ignore"):
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    m = np.nanmedian(med, axis=0)
            m = np.where(valid.sum(axis=0) >= 2, m, 0)
            zero += int((m == 0).sum())
            lines.append(f"A {pan} {tilt}")
            lines.append("F " + " ".join(str(int(round(v))) for v in m))
            positions += 1
        print(f"tilt {tilt}: {positions} positions, {time.time() - t0:.0f}s", flush=True)
    os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    print(f"positions={positions} zones={positions * 64} no_return={zero} ({zero / (positions * 64):.1%})")
    print(f"wrote {out}")


if __name__ == "__main__":
    step = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    out = sys.argv[2] if len(sys.argv) > 2 else None
    main(out=out, step=step)
