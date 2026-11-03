"""Feed sweep.txt through cavemap's own parse_line / Session and render ROOM.

The cloud is built exactly as the app builds it (parse_line -> Session.apply_reading
-> frame_to_points, sensor-relative). Display-only steps, all derived from the
cloud itself, are applied afterwards so the room reads at 480x320:
  * lift by the mount height (0.9 m) so the floor sits at y=0 like the demo cave,
  * centre on the cloud's footprint and zoom (the ROOM camera is fixed at 6.5 m),
  * 4 cm voxel thinning so surfaces stay see-through like the demo,
  * drop the ceiling (dollhouse view),
  * colour: floor dim, wall planes (found from a histogram of high points) mid,
    everything else (furniture) bright by height.

    python3 sim/render_sim.py [sweep.txt]

SIM_OUT, SIM_CAP, SIM_VOXEL, SIM_ZOOM, SIM_LIFT, SIM_CEIL, SIM_YAW, SIM_PITCH,
SIM_DX, SIM_DZ, and SIM_GIF are the same knobs as before. sweep.txt is the
file sim/sim_sweep.py writes. It is generated output, not part of the repo.
"""

import math
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import numpy as np
import pygame
import cavemap as cm

HERE = os.path.dirname(os.path.abspath(__file__))
cm.CLOUD_CAP = int(os.environ.get("SIM_CAP", "300000"))   # default 6000 holds ~1.4% of one sweep
MOUNT_H = 0.9
VOXEL = float(os.environ.get("SIM_VOXEL", "0.04"))
ZOOM = float(os.environ.get("SIM_ZOOM", "0.65"))
LIFT = float(os.environ.get("SIM_LIFT", "0.1"))
CEIL_CUT = float(os.environ.get("SIM_CEIL", "2.25"))     # floor-relative metres
YAW = float(os.environ.get("SIM_YAW", "0.6"))
PITCH = float(os.environ.get("SIM_PITCH", "-0.65"))   # negative = camera above (app clamps to -0.45)


def build_session(path):
    session = cm.Session(demo=False, serial=None, link_name="SIM")
    n_a = n_f = 0
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            reading = cm.parse_line(line)
            if reading is None:
                continue
            n_a += reading.pan is not None
            n_f += reading.frame is not None
            session.apply_reading(reading)
    return session, n_a, n_f


def wall_planes(q, axis):
    """Coordinates along ``axis`` where many points stand above 1.6 m: walls."""
    high = q[q[:, 1] > 1.6, axis]
    if len(high) == 0:
        return []
    hist, edges = np.histogram(high, bins=np.arange(high.min() - 0.1, high.max() + 0.15, 0.05))
    thr = max(50, hist.max() * 0.25)
    return [0.5 * (edges[i] + edges[i + 1]) for i in range(len(hist))
            if hist[i] >= thr and hist[i] == hist[max(0, i - 2):i + 3].max()]


def display_cloud(raw):
    q = raw.astype(np.float64).copy()
    q[:, 1] += MOUNT_H
    planes = {axis: wall_planes(q, axis) for axis in (0, 2)}   # before any cut
    q = q[q[:, 1] < CEIL_CUT]
    k = np.floor(q / VOXEL).astype(np.int64)
    _, idx = np.unique(k, axis=0, return_index=True)
    q = q[np.sort(idx)]
    near_wall = np.zeros(len(q), bool)
    for axis, cs in planes.items():
        for c in cs:
            near_wall |= np.abs(q[:, axis] - c) < 0.09
    floor = q[:, 1] < 0.06
    h = q[:, 1].copy()
    fx, fz = q[floor, 0], q[floor, 2]
    cx = 0.5 * (np.percentile(fx, 1) + np.percentile(fx, 99))
    cz = 0.5 * (np.percentile(fz, 1) + np.percentile(fz, 99))
    q[:, 0] -= cx
    q[:, 2] -= cz
    q *= ZOOM
    q[:, 1] += LIFT
    q[:, 0] += float(os.environ.get("SIM_DX", "0.35"))
    q[:, 2] += float(os.environ.get("SIM_DZ", "0"))
    dim = np.array(cm.DIM, np.float32)
    mid = np.array(cm.MID, np.float32)
    green = np.array(cm.GREEN, np.float32)
    col = np.empty((len(q), 3), np.float32)
    unit = np.clip(h / 2.2, 0, 1)[:, None]
    col[:] = dim * 0.9 + (mid * 0.8 - dim * 0.9) * unit                # walls: dim at the floor, mid at the top
    furn = ~near_wall & ~floor
    fu = np.clip(h[furn] / 1.0, 0, 1)[:, None]
    col[furn] = green * (0.7 + 0.3 * fu)                                # furniture: bright
    col[floor] = dim * 0.7                                              # floor: dim
    return q.astype(np.float32), col.astype(np.uint8), int(furn.sum()), int(near_wall.sum()), int(floor.sum())


def frame(session, fonts, layout, yaw, pitch):
    session.yaw, session.pitch = yaw, pitch
    surf = pygame.Surface((cm.WIDTH, cm.HEIGHT))
    cm.render(surf, fonts, layout, session, 1, "SIMULATED SWEEP", clock="BEST CASE")
    view = layout.view
    tag = cm.GLYPHS.render(fonts["sm"], "SIMULATED", cm.BLACK)  # never claim live data
    box = pygame.Rect(view.left + 6, view.top + 6, tag.get_width() + 8, tag.get_height() + 2)
    pygame.draw.rect(surf, cm.GREEN, box)
    surf.blit(tag, (box.x + 4, box.y + 1))
    return surf


def _rgb_bytes(surface):
    if hasattr(pygame.image, "tobytes"):
        return pygame.image.tobytes(surface, "RGB")
    return pygame.image.tostring(surface, "RGB")


def main(sweep=None):
    path = sweep or os.path.join(HERE, "sweep.txt")
    pygame.display.init()
    pygame.font.init()
    pygame.display.set_mode((1, 1))
    fonts = cm.load_fonts()
    layout = cm.make_layout()
    session, n_a, n_f = build_session(path)
    raw_n = session.cloud_n
    print(f"A lines={n_a} F lines={n_f} app cloud points={raw_n} (cap {cm.CLOUD_CAP})")
    pts, col, nf, nw, nfl = display_cloud(session.cloud[:raw_n])
    print(f"display points={len(pts)} furniture={nf} wall={nw} floor={nfl}")
    session.cloud = pts
    session.cloud_n = len(pts)
    session.visible_cloud = lambda: (pts, col, 3.9, raw_n)    # HUD PTS shows the app's real count
    session.pan, session.tilt, session.sweep = 180.0, 135.0, 1.0
    out = os.environ.get("SIM_OUT", os.path.join(HERE, "room_best_case.png"))
    img = frame(session, fonts, layout, YAW, PITCH)
    os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
    pygame.image.save(img, out)
    pygame.image.save(pygame.transform.scale(img, (cm.WIDTH * 2, cm.HEIGHT * 2)), out.replace(".png", "_2x.png"))
    print("saved", out)
    if os.environ.get("SIM_GIF"):
        from PIL import Image
        frames, n = [], 60
        for i in range(n):
            angle = YAW + math.sin(i / n * math.tau) * 0.5
            shot = frame(session, fonts, layout, angle, PITCH)
            im = Image.frombytes("RGB", (cm.WIDTH, cm.HEIGHT), _rgb_bytes(shot))
            frames.append(im.resize((cm.WIDTH * 2, cm.HEIGHT * 2), Image.NEAREST).quantize(colors=48))
        gif = out.replace(".png", "_spin.gif")
        frames[0].save(gif, save_all=True, append_images=frames[1:], duration=83, loop=0, optimize=True)
        print("gif", gif, os.path.getsize(gif))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
