#!/usr/bin/env python3
"""Cave Mapper: Pip-Boy SCAN screen for the 480x320 Pi LCD.

Draws into an offscreen pygame surface and, on the device, copies RGB565
bytes to /dev/fb0. SDL2 pygame has no fbcon driver, so the framebuffer
path sets SDL_VIDEODRIVER=dummy. ``--window`` opens a normal desktop
window for preview off the Pi.

There is no range sensor wired yet. Built-in demo geometry runs until a
USB serial device shows up, and the picture is labelled DEMO DATA.

ESP32 link (115200 8N1, UTF-8, one record per line, LF or CRLF)
----------------------------------------------------------------
Blank lines and lines whose first non-space character is ``#`` are
ignored. Anything else that does not match is ignored, so a firmware
debug print cannot wedge the parser.

F m0 m1 ... m63
    One VL53L5CX frame. Sixty-four distances in millimetres, row-major.
    Index 0 is row 0, column 0 (the sensor's top-left). 0, or any value
    above 4000, means no return.

A pan tilt
    Servo angles in degrees. Decimal values are fine.
    Pan:  0 left, 90 forward, 180 right.
    Tilt: 0 down, 90 level, 180 up.

LEFT  RIGHT  UP  DOWN  PUSH  PULL  HOLD  BREACH
    A single word alone on the line.
    LEFT/RIGHT/UP/DOWN nudge the head.
    PUSH/PULL step a cave-log station in or back.
    BREACH trips the perimeter alarm. HOLD clears it.

Touch calibration is ``~/.touchcal.json``::

    {"cx": [a, b, c], "cy": [d, e, f]}

    screen_x = a*rawX + b*rawY + c
    screen_y = d*rawX + e*rawY + f

rawX and rawY are ABS_X / ABS_Y from the ADS7846 evdev device.
"""

from __future__ import annotations

import argparse
import glob
import json
import math
import os
import sys
import time
import warnings
from dataclasses import dataclass, field

# Same console/framebuffer clash as field_touch: silence pygame before import.
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
warnings.filterwarnings("ignore", category=RuntimeWarning, module="pygame")
warnings.filterwarnings("ignore", message=".*neon capable.*")
warnings.filterwarnings("ignore", message=".*avx2.*")

try:
    import numpy as np
    import pygame
except ImportError as err:
    sys.stderr.write(
        "cavemap needs python3-pygame and python3-numpy.\n"
        "On the Pi: sudo apt install python3-pygame python3-numpy "
        "python3-evdev python3-serial\n"
        f"({err})\n"
    )
    sys.exit(1)

WIDTH = 480
HEIGHT = 320
TARGET_FPS = 18

BLACK = (0, 0, 0)
GREEN = (0x1A, 0xFF, 0x80)
DIM = (0x0A, 0x5C, 0x2E)
# Mix used for secondary instrument ink. Still inside the same green.
MID = (0x12, 0xAE, 0x57)

TAB_Y = 2
TAB_H = 22
BTN_Y = 28
BTN_H = 26

SWEEP_PERIOD = 22.0
AUTO_YAW = 0.045  # rad/s, a slow turn when nobody is dragging
BREACH_PERIOD = 7.0
BREACH_AFTER = 4.7
FLASH_HZ = 8.0
CLOUD_CAP = 6000
FOV_RAD = math.radians(45.0)

EVENTS = frozenset({"LEFT", "RIGHT", "UP", "DOWN", "PUSH", "PULL", "HOLD", "BREACH"})

DEMO_STATIONS = (
    ("ENT", 0.0, 0.0),
    ("DRIP", 3.0, 5.0),
    ("CRAWL", 2.0, 11.0),
    ("JCT", 8.0, 14.0),
    ("POOL", 7.0, 21.0),
    ("HALL", 14.0, 24.0),
    ("END", 20.0, 22.0),
)

FONT_REGULAR = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    "/usr/share/fonts/truetype/freefont/FreeMono.ttf",
)
FONT_BOLD = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeMonoBold.ttf",
)

KDSETMODE = 0x4B3A
KD_TEXT = 0
KD_GRAPHICS = 1

# 8x8 index grid, built once.
_GRID_Y, _GRID_X = np.mgrid[0:8, 0:8].astype(np.float32)
_DEPTH_NOISE = np.random.default_rng(1).normal(0, 18.0, size=(8, 8)).astype(np.float32)


# --- protocol -----------------------------------------------------------------


@dataclass
class Reading:
    """One parsed line from the ESP32, or a piece of demo state."""

    frame: np.ndarray | None = None
    pan: float | None = None
    tilt: float | None = None
    event: str | None = None


def parse_line(line: str) -> Reading | None:
    """Parse one protocol line. Return None when the line is not a record."""

    text = line.strip()
    if not text or text.startswith("#"):
        return None
    parts = text.split()
    head = parts[0].upper()
    if head in EVENTS and len(parts) == 1:
        return Reading(event=head)
    if head == "A" and len(parts) == 3:
        try:
            pan = float(parts[1])
            tilt = float(parts[2])
        except ValueError:
            return None
        if not (math.isfinite(pan) and math.isfinite(tilt)):
            return None
        return Reading(pan=pan, tilt=tilt)
    if head == "F" and len(parts) == 65:
        try:
            values = np.array([float(part) for part in parts[1:]], dtype=np.float32)
        except ValueError:
            return None
        if not np.isfinite(values).all():
            return None
        return Reading(frame=values.reshape(8, 8))
    return None


def apply_cal(raw_x: float, raw_y: float, cx, cy) -> tuple[int, int]:
    """Map ADS7846 ABS_X/ABS_Y through the saved affine calibration."""

    screen_x = cx[0] * raw_x + cx[1] * raw_y + cx[2]
    screen_y = cy[0] * raw_x + cy[1] * raw_y + cy[2]
    return int(round(screen_x)), int(round(screen_y))


def touchcal_path() -> str:
    override = os.environ.get("CAVEMAP_TOUCHCAL")
    if override:
        return override
    # sudo leaves HOME=/root. The calibration the user saved lives in their home.
    if os.environ.get("HOME") == "/root" and os.environ.get("SUDO_USER"):
        try:
            import pwd

            home = pwd.getpwnam(os.environ["SUDO_USER"]).pw_dir
            return os.path.join(home, ".touchcal.json")
        except (KeyError, OSError):
            pass
    return os.path.join(os.path.expanduser("~"), ".touchcal.json")


def load_calibration(path: str | None = None):
    """Return (cx, cy). Fall back to a 0..4095 -> 480x320 map."""

    fallback = ([WIDTH / 4096.0, 0.0, 0.0], [0.0, HEIGHT / 4096.0, 0.0])
    filename = path or touchcal_path()
    try:
        with open(filename, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        cx = [float(value) for value in data["cx"]]
        cy = [float(value) for value in data["cy"]]
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return fallback
    if len(cx) != 3 or len(cy) != 3:
        return fallback
    if not all(math.isfinite(value) for value in cx + cy):
        return fallback
    return cx, cy


# --- geometry -----------------------------------------------------------------


def _lerp_colors(height: np.ndarray) -> np.ndarray:
    span = float(height.max() - height.min()) if len(height) else 1.0
    if span < 1e-4:
        mix = np.full((len(height), 1), 0.55, dtype=np.float32)
    else:
        # Keep the floor readable. Pure dim green disappears into the black.
        unit = ((height - float(height.min())) / span).astype(np.float32)
        mix = (0.2 + 0.8 * unit)[:, None]
    dim = np.array(DIM, dtype=np.float32)
    green = np.array(GREEN, dtype=np.float32)
    return (dim + (green - dim) * mix).astype(np.uint8)


def build_cloud(seed: int = 4):
    """Precompute a cave chamber. Returns points, sweep key, colors, range."""

    rng = np.random.default_rng(seed)
    chunks = []

    def add(array):
        chunks.append(np.asarray(array, dtype=np.float32))

    count = 900
    theta = rng.random(count) * math.tau
    radius = np.sqrt(rng.random(count))
    add(
        np.stack(
            [
                radius * np.cos(theta) * 2.5,
                rng.normal(0.0, 0.025, count),
                radius * np.sin(theta) * 3.3,
            ],
            axis=1,
        )
    )

    count = 700
    theta = rng.random(count) * math.tau
    radius = np.sqrt(rng.random(count))
    x = radius * np.cos(theta) * 2.3
    z = radius * np.sin(theta) * 3.05
    y = 2.25 + 0.28 * np.cos(x / 2.5 * math.pi) + rng.normal(0.0, 0.03, count)
    add(np.stack([x, y, z], axis=1))

    count = 2600
    theta = rng.random(count) * math.tau
    rx = 2.55 + 0.16 * np.sin(3.0 * theta)
    rz = 3.30 + 0.20 * np.sin(2.0 * theta + 0.5)
    add(
        np.stack(
            [
                np.cos(theta) * rx + rng.normal(0.0, 0.04, count),
                rng.random(count) * 2.35,
                np.sin(theta) * rz + rng.normal(0.0, 0.04, count),
            ],
            axis=1,
        )
    )

    for cx, cz, tall in ((-1.15, 0.7, 1.5), (0.95, -0.85, 1.25), (0.15, 1.55, 1.05)):
        count = 140
        ang = rng.random(count) * math.tau
        rad = rng.random(count) * 0.16
        add(
            np.stack(
                [
                    cx + np.cos(ang) * rad,
                    0.55 + rng.random(count) * tall,
                    cz + np.sin(ang) * rad,
                ],
                axis=1,
            )
        )

    count = 380
    add(
        np.stack(
            [
                rng.normal(-0.35, 0.32, count),
                np.abs(rng.normal(0.12, 0.1, count)),
                rng.normal(0.45, 0.32, count),
            ],
            axis=1,
        )
    )

    points = np.concatenate(chunks, axis=0)
    azimuth = (np.arctan2(points[:, 0], points[:, 2]) + math.pi) / math.tau
    colors = _lerp_colors(points[:, 1])
    sensor = np.array([0.0, 1.1, 0.0], dtype=np.float32)
    dists = np.linalg.norm(points - sensor, axis=1).astype(np.float32)
    return (
        points,
        azimuth.astype(np.float32),
        colors,
        dists,
    )


def demo_depth(t: float) -> np.ndarray:
    """8x8 millimetre frame: a passage (far center, near walls) plus a mover."""

    xx, yy = _GRID_X, _GRID_Y
    bowl = (xx - 3.5) ** 2 + (yy - 3.5) ** 2
    base = 2350.0 - 175.0 * bowl
    cx = 3.5 + 2.5 * math.sin(t * 0.65)
    cy = 3.5 + 1.5 * math.cos(t * 0.5)
    blob = np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / 2.6)
    frame = base - blob * 980.0 + _DEPTH_NOISE
    return np.clip(frame, 80.0, 3800.0).astype(np.float32)


def frame_to_points(frame: np.ndarray, pan: float, tilt: float) -> np.ndarray:
    """Project an 8x8 range frame along the current pan/tilt into cave space.

    Sensor frame is +Z forward, +X right, +Y up. Pan 90 / tilt 90 looks
    along +Z. Cells outside 30..4000 mm are no-returns and are dropped.
    """

    rows, cols = _GRID_Y, _GRID_X
    half = FOV_RAD * 0.5
    ax = (cols - 3.5) / 3.5 * half
    ay = (3.5 - rows) / 3.5 * half
    valid = (frame >= 30.0) & (frame <= 4000.0)
    dist = frame / 1000.0
    x = np.sin(ax) * np.cos(ay) * dist
    y = np.sin(ay) * dist
    z = np.cos(ax) * np.cos(ay) * dist

    phi = math.radians(90.0 - tilt)
    cph, sph = math.cos(phi), math.sin(phi)
    y2 = y * cph - z * sph
    z2 = y * sph + z * cph

    psi = math.radians(pan - 90.0)
    cps, sps = math.cos(psi), math.sin(psi)
    x3 = x * cps + z2 * sps
    z3 = -x * sps + z2 * cps
    stacked = np.stack([x3, y2, z3], axis=-1)
    return stacked[valid].astype(np.float32)


def project(points: np.ndarray, yaw: float, pitch: float, rect: pygame.Rect):
    """Perspective project y-up points. zz is depth, larger is farther."""

    cy, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    x = points[:, 0]
    y = points[:, 1]
    z = points[:, 2]
    xz = x * cy + z * sy
    zz = -x * sy + z * cy
    yy = y * cp - zz * sp
    zz = y * sp + zz * cp
    zz = zz + 6.5
    focal = rect.h * 1.65
    inv = focal / np.maximum(zz, 0.25)
    sx = rect.centerx + xz * inv
    sy = rect.centery - (yy - 0.9) * inv
    return sx, sy, zz


def breach_state(t: float) -> tuple[bool, bool]:
    """Demo tripwire. Returns (alarm, flash_on)."""

    alarm = (t % BREACH_PERIOD) >= BREACH_AFTER
    flash = alarm and (int(t * FLASH_HZ) % 2 == 0)
    return alarm, flash


def sweep_line(sweep: float) -> np.ndarray:
    """Vertical line on the chamber wall at this sweep fraction."""

    angle = sweep * math.tau - math.pi
    x = math.sin(angle) * 2.62
    z = math.cos(angle) * 3.38
    ys = np.linspace(0.04, 2.32, 28, dtype=np.float32)
    return np.stack(
        [np.full(28, x, dtype=np.float32), ys, np.full(28, z, dtype=np.float32)],
        axis=1,
    )


# --- session / sources --------------------------------------------------------


class SerialSource:
    """Non-blocking reader for the ESP32 link. ``ser`` is a pyserial port
    or any object with ``read(n) -> bytes`` and ``close()``."""

    def __init__(self, ser, name: str):
        self.ser = ser
        self.name = name
        self.buf = b""
        self.demo = False

    @classmethod
    def open(cls, port: str, baud: int = 115200) -> "SerialSource":
        import serial

        ser = serial.Serial(port, baudrate=baud, timeout=0)
        return cls(ser, port)

    def poll(self) -> list[Reading] | None:
        """Read whatever is waiting. None means the port died."""

        try:
            data = self.ser.read(8192) or b""
        except Exception:
            return None
        if data:
            self.buf += data
            if len(self.buf) > 65536:
                self.buf = self.buf[-32768:]
        readings = []
        while b"\n" in self.buf:
            raw, self.buf = self.buf.split(b"\n", 1)
            text = raw.decode("utf-8", "replace").strip("\r")
            reading = parse_line(text)
            if reading is not None:
                readings.append(reading)
        return readings

    def close(self):
        try:
            self.ser.close()
        except Exception:
            pass


def find_serial_port() -> str | None:
    """A user port, else a USB serial device. Never the Pi UART console."""

    chosen = os.environ.get("CAVEMAP_PORT", "").strip()
    if chosen:
        return chosen
    by_id = "/dev/serial/by-id"
    if os.path.isdir(by_id):
        entries = sorted(
            os.path.join(by_id, name)
            for name in os.listdir(by_id)
            if not name.startswith(".")
        )
        if entries:
            return entries[0]
    for pattern in ("/dev/ttyACM*", "/dev/ttyUSB*"):
        matches = sorted(glob.glob(pattern))
        if matches:
            return matches[0]
    return None


@dataclass
class Session:
    """What the screen draws. Demo and the serial link fill the same fields."""

    demo: bool = True
    serial: SerialSource | None = None
    t: float = 0.0
    yaw: float = 0.62
    pitch: float = 0.46
    pan: float = 90.0
    tilt: float = 90.0
    sweep: float = 0.0
    frame: np.ndarray = field(default_factory=lambda: np.full((8, 8), 2000.0, np.float32))
    points: np.ndarray | None = None
    keys: np.ndarray | None = None
    colors: np.ndarray | None = None
    dists: np.ndarray | None = None
    alarm_latched: bool = False
    last_event: str = ""
    stations: list = field(default_factory=lambda: [tuple(item) for item in DEMO_STATIONS])
    link_name: str = ""
    cloud: np.ndarray = field(default_factory=lambda: np.zeros((CLOUD_CAP, 3), np.float32))
    cloud_n: int = 0
    cloud_i: int = 0

    def __post_init__(self):
        if self.demo and self.points is None:
            self._load_demo_cloud()
        self._derive_demo()

    def _load_demo_cloud(self):
        self.points, self.keys, self.colors, self.dists = build_cloud()

    def engage_demo(self):
        self.demo = True
        self.alarm_latched = False
        self.stations = [tuple(item) for item in DEMO_STATIONS]
        self.cloud_n = 0
        self.cloud_i = 0
        if self.points is None or len(self.points) < 100:
            self._load_demo_cloud()
        if self.serial is not None:
            self.serial.close()
            self.serial = None
        self._derive_demo()

    def _derive_demo(self):
        if not self.demo:
            return
        self.sweep = (self.t % SWEEP_PERIOD) / SWEEP_PERIOD
        self.frame = demo_depth(self.t)
        self.pan = 90.0 + 70.0 * math.sin(self.sweep * math.tau)
        self.tilt = 90.0 + 12.0 * math.sin(self.t * 0.35)

    def place(self, t: float, yaw: float | None = None, pitch: float | None = None):
        self.t = float(t)
        if yaw is not None:
            self.yaw = float(yaw)
        if pitch is not None:
            self.pitch = float(pitch)
        self._derive_demo()

    def advance(self, dt: float, spin: bool = True, yaw_delta: float = 0.0, pitch_delta: float = 0.0):
        self.t += dt
        self.yaw += yaw_delta
        if self.demo and spin:
            self.yaw += dt * AUTO_YAW
        self.pitch = min(0.95, max(-0.45, self.pitch + pitch_delta))
        if self.demo:
            self._derive_demo()
            return
        self._poll_serial()

    def _poll_serial(self):
        if self.serial is None:
            self.engage_demo()
            return
        readings = self.serial.poll()
        if readings is None:
            sys.stderr.write("cavemap: serial link lost, using demo data\n")
            self.engage_demo()
            return
        for reading in readings:
            self.apply_reading(reading)
        self.sweep = min(1.0, max(0.0, self.pan / 180.0))

    def apply_reading(self, reading: Reading):
        if reading.pan is not None:
            self.pan = reading.pan
            self.tilt = reading.tilt if reading.tilt is not None else self.tilt
        if reading.frame is not None:
            self.frame = reading.frame
            self._absorb(frame_to_points(reading.frame, self.pan, self.tilt))
        if reading.event:
            self.last_event = reading.event
            self._apply_event(reading.event)

    def _absorb(self, pts: np.ndarray):
        count = len(pts)
        if count == 0:
            return
        if count >= CLOUD_CAP:
            self.cloud[:] = pts[-CLOUD_CAP:]
            self.cloud_n = CLOUD_CAP
            self.cloud_i = 0
            return
        end = self.cloud_i + count
        if end <= CLOUD_CAP:
            self.cloud[self.cloud_i : end] = pts
        else:
            first = CLOUD_CAP - self.cloud_i
            self.cloud[self.cloud_i :] = pts[:first]
            self.cloud[: count - first] = pts[first:]
        self.cloud_i = (self.cloud_i + count) % CLOUD_CAP
        self.cloud_n = min(CLOUD_CAP, self.cloud_n + count)

    def _apply_event(self, event: str):
        if event == "BREACH":
            self.alarm_latched = True
        elif event == "HOLD":
            self.alarm_latched = False
        elif event == "LEFT":
            self.yaw -= 0.08
        elif event == "RIGHT":
            self.yaw += 0.08
        elif event == "UP":
            self.pitch = min(0.95, self.pitch + 0.06)
        elif event == "DOWN":
            self.pitch = max(-0.45, self.pitch - 0.06)
        elif event == "PUSH":
            name, x, y = self.stations[-1]
            step = 4.0
            self.stations.append(
                (
                    f"P{len(self.stations)}",
                    x + math.sin(self.yaw) * step,
                    y + math.cos(self.yaw) * step,
                )
            )
        elif event == "PULL" and len(self.stations) > 1:
            self.stations.pop()

    def alarm(self) -> tuple[bool, bool]:
        if self.demo:
            return breach_state(self.t)
        flash = self.alarm_latched and (int(self.t * FLASH_HZ) % 2 == 0)
        return self.alarm_latched, flash

    def visible_cloud(self):
        """Points the room view should draw, already coloured, plus max range."""

        if self.demo:
            assert self.points is not None and self.keys is not None
            mask = self.keys <= (self.sweep + 1e-4)
            if not np.any(mask):
                empty = np.zeros((0, 3), np.float32)
                return empty, np.zeros((0, 3), np.uint8), 0.0, 0
            dists = self.dists[mask]
            return self.points[mask], self.colors[mask], float(dists.max()), int(mask.sum())
        if self.cloud_n <= 0:
            empty = np.zeros((0, 3), np.float32)
            return empty, np.zeros((0, 3), np.uint8), 0.0, 0
        pts = self.cloud[: self.cloud_n] if self.cloud_n < CLOUD_CAP else self.cloud
        colors = _lerp_colors(pts[:, 1])
        sensor = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        dists = np.linalg.norm(pts - sensor, axis=1)
        return pts, colors, float(dists.max()) if len(dists) else 0.0, int(len(pts))


def open_session(force_demo: bool = False, port: str | None = None) -> Session:
    """Serial when a device is present, otherwise the built-in demo."""

    if force_demo:
        return Session(demo=True)
    chosen = port if port is not None else find_serial_port()
    if not chosen:
        return Session(demo=True)
    try:
        source = SerialSource.open(chosen)
    except Exception as error:
        sys.stderr.write(f"cavemap: {chosen} not usable ({error}); demo data\n")
        return Session(demo=True)
    session = Session(demo=False, serial=source, link_name=chosen)
    session.points = None
    sys.stderr.write(f"cavemap: live link {chosen} at 115200\n")
    return session


# --- drawing ------------------------------------------------------------------


def _font_file(candidates) -> str | None:
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def load_fonts():
    regular = _font_file(FONT_REGULAR)
    bold = _font_file(FONT_BOLD) or regular

    def face(path, size, fallback_bold=False):
        if path:
            return pygame.font.Font(path, size)
        return pygame.font.SysFont("monospace", size, bold=fallback_bold)

    return {
        "sm": face(regular, 13),
        "md": face(regular, 15),
        "md_b": face(bold, 15, True),
        "lg": face(bold, 18, True),
        "xl": face(bold, 26, True),
    }


@dataclass
class Layout:
    tabs: list
    modes: list
    back: pygame.Rect
    badge: pygame.Rect
    view: pygame.Rect

    def mode_at(self, x, y):
        for number, _label, rect in self.modes:
            if rect.collidepoint(x, y):
                return number
        return None

    def tab_at(self, x, y):
        for name, rect in self.tabs:
            if rect.collidepoint(x, y):
                return name
        return None


def make_layout() -> Layout:
    labels = ("1 ROOM", "2 DEPTH", "3 LOG", "4 WIRE")
    gap = 4
    back_w = 70
    usable = WIDTH - 16 - back_w - gap
    width = (usable - gap * (len(labels) - 1)) // len(labels)
    modes = []
    x = 8
    for number, label in enumerate(labels, start=1):
        modes.append((number, label, pygame.Rect(x, BTN_Y, width, BTN_H)))
        x += width + gap
    return Layout(
        tabs=[
            ("SCAN", pygame.Rect(8, TAB_Y, 72, TAB_H)),
            ("DATA", pygame.Rect(84, TAB_Y, 72, TAB_H)),
            ("RADIO", pygame.Rect(160, TAB_Y, 80, TAB_H)),
        ],
        modes=modes,
        back=pygame.Rect(WIDTH - 8 - back_w, BTN_Y, back_w, BTN_H),
        badge=pygame.Rect(WIDTH - 8 - 128, TAB_Y, 128, TAB_H),
        view=pygame.Rect(8, 58, 464, 232),
    )


def blit_text(surface, font, text, xy, color):
    surface.blit(font.render(text, True, color), xy)


def blit_center(surface, font, text, rect, color):
    image = font.render(text, True, color)
    surface.blit(
        image,
        (
            rect.x + (rect.w - image.get_width()) // 2,
            rect.y + (rect.h - image.get_height()) // 2 - 1,
        ),
    )


def draw_corners(surface, rect, color, length=12):
    x, y, w, h = rect
    pairs = (
        ((x, y), (x + length, y), (x, y + length)),
        ((x + w - 1, y), (x + w - 1 - length, y), (x + w - 1, y + length)),
        ((x, y + h - 1), (x + length, y + h - 1), (x, y + h - 1 - length)),
        ((x + w - 1, y + h - 1), (x + w - 1 - length, y + h - 1), (x + w - 1, y + h - 1 - length)),
    )
    for corner, horizontal, vertical in pairs:
        pygame.draw.line(surface, color, corner, horizontal)
        pygame.draw.line(surface, color, corner, vertical)


def apply_scanlines(surface):
    """1px dark row every 3px, about 25% black over the picture."""

    pixels = pygame.surfarray.pixels3d(surface)
    try:
        band = pixels[:, 2::3, :]
        pixels[:, 2::3, :] = ((band.astype(np.uint16) * 3) // 4).astype(np.uint8)
    finally:
        del pixels


def paint_cloud(surface, points, colors, yaw, pitch, rect):
    if len(points) == 0:
        return
    sx, sy, zz = project(points, yaw, pitch, rect)
    mask = (
        (zz > 0.6)
        & (sx >= rect.left)
        & (sx < rect.right - 1)
        & (sy >= rect.top)
        & (sy < rect.bottom - 1)
    )
    if not np.any(mask):
        return
    order = np.argsort(zz[mask])[::-1]
    xi = sx[mask][order].astype(np.int32)
    yi = sy[mask][order].astype(np.int32)
    col = colors[mask][order]
    pixels = pygame.surfarray.pixels3d(surface)
    try:
        pixels[xi, yi] = col
        pixels[xi + 1, yi] = col
        pixels[xi, yi + 1] = col
    finally:
        del pixels


def draw_sweep(surface, sweep, yaw, pitch, rect):
    line = sweep_line(sweep)
    sx, sy, zz = project(line, yaw, pitch, rect)
    mask = (zz > 0.6) & (sx >= rect.left) & (sx < rect.right) & (sy >= rect.top) & (sy < rect.bottom)
    if int(mask.sum()) < 2:
        return
    pts = [(float(x), float(y)) for x, y in zip(sx[mask], sy[mask])]
    prev = surface.get_clip()
    surface.set_clip(rect)
    if len(pts) >= 2:
        pygame.draw.lines(surface, MID, False, pts, 3)
        pygame.draw.lines(surface, GREEN, False, pts, 1)
    surface.set_clip(prev)


def draw_height_legend(surface, font, rect):
    x = rect.right - 16
    top = rect.top + 8
    height = 52
    for i in range(height):
        mix = 1.0 - (i / max(1, height - 1))
        color = tuple(int(DIM[c] + (GREEN[c] - DIM[c]) * mix) for c in range(3))
        surface.fill(color, pygame.Rect(x, top + i, 6, 1))
    blit_text(surface, font, "HI", (x - 16, top - 2), DIM)
    blit_text(surface, font, "LO", (x - 16, top + height - 10), DIM)


def draw_room(surface, fonts, session: Session, rect: pygame.Rect):
    points, colors, range_m, count = session.visible_cloud()
    paint_cloud(surface, points, colors, session.yaw, session.pitch, rect)
    draw_sweep(surface, session.sweep, session.yaw, session.pitch, rect)
    cx, cy = rect.center
    pygame.draw.line(surface, DIM, (cx - 7, cy), (cx + 7, cy))
    pygame.draw.line(surface, DIM, (cx, cy - 7), (cx, cy + 7))

    hud = pygame.Rect(rect.left + 8, rect.bottom - 76, 118, 58)
    pygame.draw.rect(surface, BLACK, hud)
    pygame.draw.rect(surface, DIM, hud, 1)
    lines = (
        f"PTS {count:5d}",
        f"RNG {range_m:4.1f}m",
        f"PRG {int(session.sweep * 100):4d}%",
    )
    for index, line in enumerate(lines):
        blit_text(surface, fonts["sm"], line, (hud.x + 6, hud.y + 4 + index * 17), GREEN)
    draw_height_legend(surface, fonts["sm"], rect)

    bar = pygame.Rect(rect.left + 8, rect.bottom - 12, rect.w - 16, 5)
    pygame.draw.rect(surface, DIM, bar)
    fill = bar.copy()
    fill.w = max(1, int(bar.w * session.sweep)) if session.sweep > 0 else 0
    if fill.w:
        pygame.draw.rect(surface, GREEN, fill)

    if count == 0 and not session.demo:
        blit_center(surface, fonts["md"], "WAITING FOR FRAME", rect, GREEN)


def depth_colors(frame: np.ndarray) -> np.ndarray:
    """Near is bright green, far falls off toward black. No-returns stay dim."""

    near, far = 250.0, 2500.0
    mix = 1.0 - np.clip((frame - near) / (far - near), 0.0, 1.0)
    valid = (frame >= 30.0) & (frame <= 4000.0)
    dim = np.array(DIM, dtype=np.float32)
    green = np.array(GREEN, dtype=np.float32)
    color = dim * 0.35 + (green - dim * 0.35) * mix[..., None]
    dark = np.array((0, 18, 8), dtype=np.float32)
    color = np.where(valid[..., None], color, dark)
    return color.astype(np.uint8)


def draw_depth(surface, fonts, session: Session, rect: pygame.Rect):
    frame = session.frame
    colors = depth_colors(frame)
    small = pygame.Surface((8, 8))
    pixels = pygame.surfarray.pixels3d(small)
    try:
        pixels[:, :, :] = np.transpose(colors, (1, 0, 2))
    finally:
        del pixels
    inner = rect.inflate(-16, -36)
    inner.h = min(inner.h, 168)
    inner.y = rect.top + 8
    scaled = pygame.transform.smoothscale(small, (inner.w, inner.h))
    surface.blit(scaled, inner.topleft)
    prev = surface.get_clip()
    surface.set_clip(inner)
    for index in range(9):
        x = inner.left + int(round(index * inner.w / 8))
        y = inner.top + int(round(index * inner.h / 8))
        pygame.draw.line(surface, (0, 28, 12), (x, inner.top), (x, inner.bottom - 1))
        pygame.draw.line(surface, (0, 28, 12), (inner.left, y), (inner.right - 1, y))
    flat = frame.ravel()
    valid = flat[(flat >= 30.0) & (flat <= 4000.0)]
    if len(valid):
        nearest = int(np.argmin(np.where((frame >= 30.0) & (frame <= 4000.0), frame, 1e9)))
        row, col = divmod(nearest, 8)
        cell_w = inner.w / 8
        cell_h = inner.h / 8
        box = pygame.Rect(
            int(inner.left + col * cell_w),
            int(inner.top + row * cell_h),
            max(2, int(cell_w)),
            max(2, int(cell_h)),
        )
        pygame.draw.rect(surface, GREEN, box, 1)
    surface.set_clip(prev)

    if len(valid):
        near_mm = float(valid.min())
        far_mm = float(valid.max())
    else:
        near_mm = far_mm = 0.0
    caption = f"VL53 8x8    NEAR {near_mm:4.0f} mm    FAR {far_mm:4.0f} mm"
    blit_text(surface, fonts["sm"], caption, (rect.left + 10, inner.bottom + 8), GREEN)
    bar = pygame.Rect(rect.left + 10, inner.bottom + 28, rect.w - 20, 8)
    for i in range(bar.w):
        mix = 1.0 - i / max(1, bar.w - 1)
        color = tuple(int(DIM[c] * 0.35 + (GREEN[c] - DIM[c] * 0.35) * mix) for c in range(3))
        surface.fill(color, pygame.Rect(bar.x + i, bar.y, 1, bar.h))
    blit_text(surface, fonts["sm"], "NEAR", (bar.x, bar.bottom + 3), DIM)
    far_label = fonts["sm"].render("FAR", True, DIM)
    surface.blit(far_label, (bar.right - far_label.get_width(), bar.bottom + 3))


def path_length(stations) -> float:
    total = 0.0
    for left, right in zip(stations, stations[1:]):
        total += math.hypot(right[1] - left[1], right[2] - left[2])
    return total


def map_stations(stations, rect: pygame.Rect):
    xs = [item[1] for item in stations]
    ys = [item[2] for item in stations]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = max(0.1, max_x - min_x)
    span_y = max(0.1, max_y - min_y)
    pad = 18
    usable_w = max(1, rect.w - pad * 2)
    usable_h = max(1, rect.h - pad * 2)

    def convert(x, y):
        px = rect.left + pad + (x - min_x) / span_x * usable_w
        py = rect.bottom - pad - (y - min_y) / span_y * usable_h
        return px, py

    return [(*item, *convert(item[1], item[2])) for item in stations]


def point_along(points, distance):
    """Walk a polyline. Returns x, y, dx, dy at ``distance`` (wrapped)."""

    if len(points) < 2:
        x, y = points[0] if points else (0, 0)
        return x, y, 1.0, 0.0
    lengths = []
    total = 0.0
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        step = math.hypot(x1 - x0, y1 - y0)
        lengths.append(step)
        total += step
    if total < 1e-3:
        return points[0][0], points[0][1], 1.0, 0.0
    distance = distance % total
    covered = 0.0
    for (x0, y0), (x1, y1), step in zip(points, points[1:], lengths):
        if covered + step >= distance and step > 0:
            mix = (distance - covered) / step
            dx, dy = x1 - x0, y1 - y0
            return x0 + dx * mix, y0 + dy * mix, dx, dy
        covered += step
    x0, y0 = points[-2]
    x1, y1 = points[-1]
    return x1, y1, x1 - x0, y1 - y0


def draw_dashed(surface, points, color, dash=8, gap=5, width=1):
    if len(points) < 2:
        return
    period = dash + gap
    travelled = 0.0
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        seg = math.hypot(x1 - x0, y1 - y0)
        if seg < 0.2:
            continue
        ux, uy = (x1 - x0) / seg, (y1 - y0) / seg
        pos = 0.0
        while pos < seg:
            into = (travelled + pos) % period
            if into < dash:
                run = min(dash - into, seg - pos)
                drawing = True
            else:
                run = min(period - into, seg - pos)
                drawing = False
            if drawing and run > 0.3:
                ax = x0 + ux * pos
                ay = y0 + uy * pos
                bx = x0 + ux * (pos + run)
                by = y0 + uy * (pos + run)
                pygame.draw.line(surface, color, (ax, ay), (bx, by), width)
            pos += max(run, 0.1)
        travelled += seg


def draw_log(surface, fonts, session: Session, rect: pygame.Rect):
    stations = session.stations
    map_rect = pygame.Rect(rect.left + 6, rect.top + 6, 292, rect.h - 14)
    mapped = map_stations(stations, map_rect)
    inbound = [(item[3], item[4]) for item in mapped]
    outbound = list(reversed(inbound))

    if len(inbound) >= 2:
        pygame.draw.lines(surface, DIM, False, inbound, 2)
    draw_dashed(surface, outbound, GREEN, dash=7, gap=5, width=2)

    list_x = rect.left + 308
    for index, (name, _x, _y, px, py) in enumerate(mapped, start=1):
        pygame.draw.circle(surface, GREEN, (int(px), int(py)), 3)
        label = fonts["sm"].render(f"{index} {name}", True, GREEN)
        lx = int(px) + 6
        ly = int(py) - 14
        if lx + label.get_width() > list_x - 8:
            lx = int(px) - 8 - label.get_width()
        if ly < rect.top + 2:
            ly = int(py) + 4
        if ly + label.get_height() > rect.bottom - 4:
            ly = rect.bottom - 4 - label.get_height()
        surface.blit(label, (lx, ly))

    metres = path_length(stations)
    duration = 12.0
    # March by fraction of the drawn polyline, not by metres.
    screen_len = 0.0
    for (x0, y0), (x1, y1) in zip(outbound, outbound[1:]):
        screen_len += math.hypot(x1 - x0, y1 - y0)
    mx, my, dx, dy = point_along(outbound, (session.t % duration) / duration * max(screen_len, 1.0))
    pygame.draw.circle(surface, BLACK, (int(mx), int(my)), 6)
    pygame.draw.circle(surface, GREEN, (int(mx), int(my)), 5)
    length = math.hypot(dx, dy) or 1.0
    ux, uy = dx / length, dy / length
    tip = (mx + ux * 9, my + uy * 9)
    left = (mx - ux * 6 - uy * 4, my - uy * 6 + ux * 4)
    right = (mx - ux * 6 + uy * 4, my - uy * 6 - ux * 4)
    pygame.draw.polygon(surface, GREEN, (tip, left, right))

    blit_text(surface, fonts["md_b"], "WAY OUT", (list_x, rect.top + 6), GREEN)
    blit_text(surface, fonts["sm"], f"{metres:0.0f} m  reversed", (list_x, rect.top + 26), DIM)
    step = int(((session.t % duration) / duration) * max(1, len(stations) - 1))
    # step 0 is still at END, the first stop of the way out.
    reversed_names = list(reversed(stations))
    for index, (name, _x, _y) in enumerate(reversed_names):
        color = GREEN if index == step else DIM
        marker = ">" if index == step else " "
        blit_text(
            surface,
            fonts["sm"],
            f"{marker}{index + 1:d} {name}",
            (list_x, rect.top + 48 + index * 18),
            color,
        )
    blit_text(surface, fonts["sm"], "IN  solid", (list_x, rect.bottom - 42), DIM)
    blit_text(surface, fonts["sm"], "OUT dashed", (list_x, rect.bottom - 26), GREEN)


def draw_wire(surface, fonts, session: Session, rect: pygame.Rect):
    alarm, flash = session.alarm()
    ink = BLACK if flash else GREEN
    dim_ink = BLACK if flash else DIM
    if flash:
        pygame.draw.rect(surface, GREEN, rect)
    title = "PERIMETER BREACH" if alarm else "PERIMETER ARMED"
    face = fonts["xl"] if alarm else fonts["lg"]
    image = face.render(title, True, ink)
    surface.blit(image, (rect.centerx - image.get_width() // 2, rect.top + 8))

    plan = pygame.Rect(rect.left + 28, rect.top + 52, 250, 140)
    wall = ink if not alarm else (BLACK if flash else GREEN)
    beam_ok = dim_ink
    beam_hot = BLACK if flash else GREEN
    pygame.draw.line(surface, wall, plan.topleft, plan.topright, 2)
    pygame.draw.line(surface, wall, plan.topleft, plan.bottomleft, 2)
    pygame.draw.line(surface, wall, plan.topright, plan.bottomright, 2)
    gap = 48
    mid = plan.centerx
    pygame.draw.line(surface, wall, (plan.left, plan.bottom), (mid - gap // 2, plan.bottom), 2)
    pygame.draw.line(surface, wall, (mid + gap // 2, plan.bottom), (plan.right, plan.bottom), 2)
    door = ((mid - 16, plan.bottom), (mid + 16, plan.bottom))
    beams = {
        "N": ((plan.left + 8, plan.top + 8), (plan.right - 8, plan.top + 8)),
        "E": ((plan.right - 8, plan.top + 8), (plan.right - 8, plan.bottom - 8)),
        "W": ((plan.left + 8, plan.top + 8), (plan.left + 8, plan.bottom - 8)),
        "S": door,
    }
    for name, (start, end) in beams.items():
        hot = alarm and name == "S"
        color = beam_hot if hot else beam_ok
        width = 3 if hot else 1
        pygame.draw.line(surface, color, start, end, width)
    camp = fonts["sm"].render("CAMP", True, dim_ink)
    surface.blit(camp, (plan.centerx - camp.get_width() // 2, plan.centery - 8))

    list_x = plan.right + 28
    blit_text(surface, fonts["sm"], "BEAMS", (list_x, plan.top), ink)
    for index, name in enumerate(("N", "E", "S", "W")):
        tripped = alarm and name == "S"
        label = "TRIP" if tripped else "OK"
        color = beam_hot if tripped else dim_ink
        blit_text(surface, fonts["md"], f"{name}  {label}", (list_x, plan.top + 22 + index * 22), color)
    blit_text(surface, fonts["sm"], "SIMULATED BEAMS", (rect.left + 28, rect.bottom - 18), dim_ink)


def draw_chrome(surface, fonts, layout: Layout, session: Session, mode: int, note: str):
    for name, rect in layout.tabs:
        active = name == "SCAN"
        if active:
            pygame.draw.rect(surface, DIM, rect)
            pygame.draw.rect(surface, GREEN, rect, 1)
            blit_center(surface, fonts["md_b"], name, rect, GREEN)
        else:
            pygame.draw.rect(surface, DIM, rect, 1)
            blit_center(surface, fonts["md"], name, rect, DIM)

    badge_text = "DEMO DATA" if session.demo else "LIVE LINK"
    pygame.draw.rect(surface, DIM, layout.badge)
    pygame.draw.rect(surface, GREEN, layout.badge, 1)
    blit_center(surface, fonts["md_b"], badge_text, layout.badge, GREEN)

    for number, label, rect in layout.modes:
        active = number == mode
        if active:
            pygame.draw.rect(surface, DIM, rect)
            pygame.draw.rect(surface, GREEN, rect, 1)
            blit_center(surface, fonts["sm"], label, rect, GREEN)
        else:
            pygame.draw.rect(surface, DIM, rect, 1)
            blit_center(surface, fonts["sm"], label, rect, DIM)
    pygame.draw.rect(surface, DIM, layout.back, 1)
    blit_center(surface, fonts["sm"], "BACK", layout.back, GREEN)

    pygame.draw.rect(surface, DIM, layout.view, 1)
    draw_corners(surface, layout.view, GREEN, 14)

    footer_left = note or "1-4 MODE    ARROWS TURN    Q BACK"
    if session.last_event and not session.demo:
        footer_left = f"EVT {session.last_event}"
    blit_text(surface, fonts["sm"], footer_left, (8, 300), DIM if not note else GREEN)
    right = f"PAN {session.pan:05.1f}  TILT {session.tilt:05.1f}"
    image = fonts["sm"].render(right, True, DIM)
    surface.blit(image, (WIDTH - 8 - image.get_width(), 300))


def render(surface, fonts, layout: Layout, session: Session, mode: int, note: str):
    flash = session.alarm()[1]
    surface.fill(BLACK)
    # Breach fills the viewport; chrome stays so BACK still reads.
    if mode == 4 and flash:
        pygame.draw.rect(surface, GREEN, layout.view)
    if mode == 1:
        draw_room(surface, fonts, session, layout.view)
    elif mode == 2:
        draw_depth(surface, fonts, session, layout.view)
    elif mode == 3:
        draw_log(surface, fonts, session, layout.view)
    else:
        draw_wire(surface, fonts, session, layout.view)
    draw_chrome(surface, fonts, layout, session, mode, note)
    apply_scanlines(surface)


# --- input / display ----------------------------------------------------------


@dataclass
class InputState:
    quit: bool = False
    mode: int | None = None
    yaw: float = 0.0
    pitch: float = 0.0
    click: tuple | None = None
    dragged: bool = False


class EvdevInputs:
    """Touch from the ADS7846 and keys from the USB keyboard."""

    def __init__(self, calibration):
        self.cx, self.cy = calibration
        self.touches = []
        self.keys = []
        self.raw_x = 0
        self.raw_y = 0
        self.have_raw = False
        self.pointer_down = False
        self.pointer = (0, 0)
        self.origin = (0, 0)
        self.moved = False
        self.held = set()
        self._open()

    def _open(self):
        try:
            import evdev
            from evdev import ecodes
        except ImportError:
            sys.stderr.write("cavemap: python3-evdev missing; USB keyboard and touch are off\n")
            return
        self.evdev = evdev
        self.ecodes = ecodes
        for path in evdev.list_devices():
            try:
                dev = evdev.InputDevice(path)
            except OSError:
                continue
            touch, keyboard = _classify(dev, ecodes)
            if touch:
                self.touches.append(dev)
            elif keyboard:
                self.keys.append(dev)
        for dev in self.touches + self.keys:
            try:
                dev.set_nonblocking(True)
                dev.grab()
            except OSError:
                pass

    def close(self):
        for dev in self.touches + self.keys:
            try:
                dev.ungrab()
            except OSError:
                pass
            try:
                dev.close()
            except OSError:
                pass

    def poll(self, view: pygame.Rect) -> InputState:
        state = InputState()
        if not self.touches and not self.keys:
            return state
        ecodes = self.ecodes
        for dev in self.touches + self.keys:
            try:
                events = dev.read()
            except (BlockingIOError, OSError):
                continue
            for event in events:
                if event.type == ecodes.EV_ABS and dev in self.touches:
                    if event.code == ecodes.ABS_X:
                        self.raw_x = event.value
                        self.have_raw = True
                    elif event.code == ecodes.ABS_Y:
                        self.raw_y = event.value
                        self.have_raw = True
                    elif event.code == ecodes.ABS_PRESSURE and self.have_raw:
                        self._touch(event.value > 0, state, view)
                    if self.pointer_down and self.have_raw and event.code in (ecodes.ABS_X, ecodes.ABS_Y):
                        self._drag(state, view)
                elif event.type == ecodes.EV_KEY and dev in self.touches and event.code == ecodes.BTN_TOUCH:
                    if self.have_raw:
                        self._touch(event.value != 0, state, view)
                elif event.type == ecodes.EV_KEY and dev in self.keys:
                    self._key(event.code, event.value, state)
        self._held_arrows(state)
        return state

    def _screen(self):
        x, y = apply_cal(self.raw_x, self.raw_y, self.cx, self.cy)
        return max(0, min(WIDTH - 1, x)), max(0, min(HEIGHT - 1, y))

    def _touch(self, down: bool, state: InputState, view: pygame.Rect):
        if down and not self.pointer_down:
            self.pointer_down = True
            self.pointer = self._screen()
            self.origin = self.pointer
            self.moved = False
        elif not down and self.pointer_down:
            self.pointer_down = False
            if not self.moved:
                state.click = self.pointer

    def _drag(self, state: InputState, view: pygame.Rect):
        x, y = self._screen()
        if abs(x - self.origin[0]) + abs(y - self.origin[1]) > 8:
            self.moved = True
        if self.moved and view.collidepoint(*self.origin):
            state.yaw += (x - self.pointer[0]) * 0.01
            state.pitch += (y - self.pointer[1]) * 0.01
            state.dragged = True
        self.pointer = (x, y)

    def _key(self, code, value, state: InputState):
        ecodes = self.ecodes
        if value == 0:
            self.held.discard(code)
            return
        if value != 1:
            return
        self.held.add(code)
        modes = {ecodes.KEY_1: 1, ecodes.KEY_2: 2, ecodes.KEY_3: 3, ecodes.KEY_4: 4}
        if code in modes:
            state.mode = modes[code]
        if code in (ecodes.KEY_Q, ecodes.KEY_ESC):
            state.quit = True

    def _held_arrows(self, state: InputState):
        ecodes = self.ecodes
        if ecodes.KEY_LEFT in self.held:
            state.yaw -= 0.045
            state.dragged = True
        if ecodes.KEY_RIGHT in self.held:
            state.yaw += 0.045
            state.dragged = True
        if ecodes.KEY_UP in self.held:
            state.pitch += 0.035
            state.dragged = True
        if ecodes.KEY_DOWN in self.held:
            state.pitch -= 0.035
            state.dragged = True


def _classify(dev, ecodes):
    caps = dev.capabilities()
    keys = set()
    axes = set()
    for entry in caps.get(ecodes.EV_KEY, ()):
        keys.add(entry if isinstance(entry, int) else entry[0])
    for entry in caps.get(ecodes.EV_ABS, ()):
        axes.add(entry[0] if isinstance(entry, tuple) else entry)
    name = (dev.name or "").lower()
    touch = ecodes.ABS_X in axes and ecodes.ABS_Y in axes and (
        ecodes.BTN_TOUCH in keys or "ads7846" in name or "touch" in name
    )
    keyboard = (
        ecodes.KEY_Q in keys
        and ecodes.KEY_ESC in keys
        and ecodes.KEY_1 in keys
        and not touch
    )
    return touch, keyboard


def poll_window(scale: int, held: set, pointer: dict, view: pygame.Rect) -> InputState:
    state = InputState()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            state.quit = True
        elif event.type == pygame.KEYDOWN:
            held.add(event.key)
            modes = {pygame.K_1: 1, pygame.K_2: 2, pygame.K_3: 3, pygame.K_4: 4}
            if event.key in modes:
                state.mode = modes[event.key]
            if event.key in (pygame.K_q, pygame.K_ESCAPE):
                state.quit = True
        elif event.type == pygame.KEYUP:
            held.discard(event.key)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = (event.pos[0] // scale, event.pos[1] // scale)
            pointer["down"] = True
            pointer["pos"] = pos
            pointer["origin"] = pos
            pointer["moved"] = False
        elif event.type == pygame.MOUSEMOTION and pointer.get("down"):
            pos = (event.pos[0] // scale, event.pos[1] // scale)
            if abs(pos[0] - pointer["origin"][0]) + abs(pos[1] - pointer["origin"][1]) > 8:
                pointer["moved"] = True
            if pointer["moved"] and view.collidepoint(*pointer["origin"]):
                state.yaw += (pos[0] - pointer["pos"][0]) * 0.01
                state.pitch += (pos[1] - pointer["pos"][1]) * 0.01
                state.dragged = True
            pointer["pos"] = pos
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and pointer.get("down"):
            pointer["down"] = False
            if not pointer.get("moved"):
                state.click = pointer["pos"]
    if pygame.K_LEFT in held:
        state.yaw -= 0.045
        state.dragged = True
    if pygame.K_RIGHT in held:
        state.yaw += 0.045
        state.dragged = True
    if pygame.K_UP in held:
        state.pitch += 0.035
        state.dragged = True
    if pygame.K_DOWN in held:
        state.pitch -= 0.035
        state.dragged = True
    return state


class Console:
    """Take the VT out of text mode while the LCD is ours, then give it back."""

    def __init__(self):
        self.fd = None
        self.graphics = False
        self.hid_cursor = False

    def enter(self):
        try:
            self.fd = os.open("/dev/tty", os.O_RDWR | os.O_NOCTTY)
            import fcntl

            fcntl.ioctl(self.fd, KDSETMODE, KD_GRAPHICS)
            self.graphics = True
        except OSError:
            if self.fd is not None:
                try:
                    os.close(self.fd)
                except OSError:
                    pass
            self.fd = None
        if sys.stdout.isatty():
            sys.stdout.write("\033[?25l")
            sys.stdout.flush()
            self.hid_cursor = True

    def leave(self):
        if self.graphics and self.fd is not None:
            try:
                import fcntl

                fcntl.ioctl(self.fd, KDSETMODE, KD_TEXT)
            except OSError:
                pass
        if self.fd is not None:
            try:
                os.close(self.fd)
            except OSError:
                pass
            self.fd = None
        self.graphics = False
        if self.hid_cursor and sys.stdout.isatty():
            sys.stdout.write("\033[?25h\033[0m")
            sys.stdout.flush()
            self.hid_cursor = False


class Framebuffer:
    """RGB565 writer for the piscreen overlay on /dev/fb0."""

    def __init__(self, path="/dev/fb0"):
        self.path = path
        self.fd = os.open(path, os.O_RDWR)
        name = os.path.basename(path)
        self.stride = _sysfs_int(f"/sys/class/graphics/{name}/stride", WIDTH * 2)
        bpp = _sysfs_int(f"/sys/class/graphics/{name}/bits_per_pixel", 16)
        if bpp != 16:
            sys.stderr.write(f"cavemap: {path} is {bpp} bpp; this program writes RGB565\n")
        if self.stride < WIDTH * 2:
            self.stride = WIDTH * 2

    def blit(self, surface: pygame.Surface):
        raw = surface_to_rgb565(surface)
        width = surface.get_width()
        row_bytes = width * 2
        if self.stride != row_bytes:
            padded = np.zeros((raw.shape[0], self.stride // 2), dtype="<u2")
            padded[:, :width] = raw
            payload = padded.tobytes()
        else:
            payload = raw.tobytes()
        os.lseek(self.fd, 0, os.SEEK_SET)
        view = memoryview(payload)
        while view:
            written = os.write(self.fd, view)
            view = view[written:]

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None


def _sysfs_int(path: str, default: int) -> int:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return int(handle.read().strip() or default)
    except (OSError, ValueError):
        return default


def rgb888_to_565(red: int, green: int, blue: int) -> int:
    return ((red >> 3) << 11) | ((green >> 2) << 5) | (blue >> 3)


def surface_to_rgb565(surface: pygame.Surface) -> np.ndarray:
    """Height × width little-endian RGB565, the layout /dev/fb0 expects."""

    pixels = pygame.surfarray.pixels3d(surface)
    try:
        rgb = np.transpose(pixels, (1, 0, 2))
    finally:
        del pixels
    red = rgb[:, :, 0].astype(np.uint16)
    green = rgb[:, :, 1].astype(np.uint16)
    blue = rgb[:, :, 2].astype(np.uint16)
    packed = ((red >> 3) << 11) | ((green >> 2) << 5) | (blue >> 3)
    return np.ascontiguousarray(packed, dtype="<u2")


# --- app loop -----------------------------------------------------------------


@dataclass
class App:
    session: Session
    mode: int = 1
    note: str = ""
    note_until: float = 0.0
    spin_pause: float = 0.0

    def active_note(self) -> str:
        if self.note and self.session.t < self.note_until:
            return self.note
        return ""

    def handle(self, layout: Layout, inp: InputState) -> str:
        if inp.quit:
            return "quit"
        if inp.mode:
            self.mode = inp.mode
        if inp.click:
            x, y = inp.click
            picked = layout.mode_at(x, y)
            if picked:
                self.mode = picked
            elif layout.back.collidepoint(x, y):
                return "quit"
            else:
                tab = layout.tab_at(x, y)
                if tab == "DATA":
                    self.note = "DATA LINK DARK"
                    self.note_until = self.session.t + 2.0
                elif tab == "RADIO":
                    self.note = "RADIO LINK DARK"
                    self.note_until = self.session.t + 2.0
                elif tab == "SCAN":
                    self.note = ""
        if inp.yaw or inp.pitch:
            self.session.yaw += inp.yaw
            self.session.pitch = min(0.95, max(-0.45, self.session.pitch + inp.pitch))
            if inp.dragged:
                self.spin_pause = self.session.t + 1.5
        return ""


def boot_pygame(window: bool):
    if not window:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.display.init()
    pygame.font.init()
    if window:
        screen = pygame.display.set_mode((WIDTH * 2, HEIGHT * 2))
        pygame.display.set_caption("cavemap — SCAN")
        return screen
    pygame.display.set_mode((1, 1))
    return None


def present(screen, surface, fb):
    if screen is not None:
        pygame.transform.scale(surface, screen.get_size(), screen)
        pygame.display.flip()
    elif fb is not None:
        fb.blit(surface)


def run_loop(window: bool, session: Session, fps: int):
    screen = boot_pygame(window)
    fonts = load_fonts()
    layout = make_layout()
    surface = pygame.Surface((WIDTH, HEIGHT))
    fb = None
    console = Console()
    evdev = None
    try:
        if not window:
            fb = Framebuffer("/dev/fb0")
            console.enter()
            evdev = EvdevInputs(load_calibration())
        app = App(session)
        held: set = set()
        pointer = {"down": False, "pos": (0, 0), "origin": (0, 0), "moved": False}
        frame_dt = 1.0 / max(1, fps)
        while True:
            started = time.perf_counter()
            if window:
                incoming = poll_window(2, held, pointer, layout.view)
            else:
                incoming = evdev.poll(layout.view) if evdev else InputState()
            if app.handle(layout, incoming) == "quit":
                break
            spin = app.session.t >= app.spin_pause
            # Yaw/pitch from this frame's input were already applied.
            app.session.advance(frame_dt, spin=spin)
            render(surface, fonts, layout, app.session, app.mode, app.active_note())
            present(screen, surface, fb)
            remain = frame_dt - (time.perf_counter() - started)
            if remain > 0:
                time.sleep(remain)
    finally:
        if evdev is not None:
            evdev.close()
        if fb is not None:
            fb.close()
        console.leave()
        pygame.quit()


# --- screenshots / self-test --------------------------------------------------


SHOTS = (
    ("room_scan_early", 1, {"t": 5.5, "yaw": 0.62, "pitch": 0.46}),
    ("room_scan_late", 1, {"t": 18.0, "yaw": 1.45, "pitch": 0.34}),
    ("depth_heatmap", 2, {"t": 2.2, "yaw": 0.62, "pitch": 0.46}),
    ("depth_heatmap_later", 2, {"t": 6.8, "yaw": 0.62, "pitch": 0.46}),
    ("cave_log", 3, {"t": 0.4, "yaw": 0.62, "pitch": 0.46}),
    ("cave_log_way_out", 3, {"t": 8.0, "yaw": 0.62, "pitch": 0.46}),
    ("perimeter_armed", 4, {"t": 1.2, "yaw": 0.62, "pitch": 0.46}),
    ("perimeter_breach", 4, {"t": 5.0, "yaw": 0.62, "pitch": 0.46}),
)


def render_shot(fonts, layout, mode: int, placed: dict) -> pygame.Surface:
    session = Session(demo=True)
    session.place(**placed)
    surface = pygame.Surface((WIDTH, HEIGHT))
    render(surface, fonts, layout, session, mode, "")
    return surface


def dump_screenshots(directory: str) -> list[str]:
    os.makedirs(directory, exist_ok=True)
    boot_pygame(window=False)
    fonts = load_fonts()
    layout = make_layout()
    written = []
    try:
        for name, mode, placed in SHOTS:
            surface = render_shot(fonts, layout, mode, placed)
            path = os.path.join(directory, f"{name}.png")
            pygame.image.save(surface, path)
            written.append(path)
    finally:
        pygame.quit()
    return written


def _bright_count(surface) -> int:
    array = pygame.surfarray.array3d(surface)
    green = array[:, :, 1]
    red = array[:, :, 0]
    return int(((green > 150) & (green > red + 20)).sum())


def self_test() -> int:
    failures = []

    def check(cond, message):
        if not cond:
            failures.append(message)

    check(parse_line("") is None, "blank line")
    check(parse_line("# comment") is None, "comment")
    check(parse_line("  # indented") is None, "indented comment")
    breach = parse_line("BREACH")
    check(breach is not None and breach.event == "BREACH", "BREACH event")
    check(parse_line("left").event == "LEFT", "event case")
    check(parse_line("BREACH now") is None, "event with extra words")
    check(parse_line("F 1 2") is None, "short frame")
    frame_line = "F " + " ".join(["1000"] * 64)
    reading = parse_line(frame_line)
    check(reading is not None and reading.frame is not None and reading.frame.shape == (8, 8), "frame shape")
    check(reading is not None and float(reading.frame[1, 2]) == 1000.0, "frame row major")
    angles = parse_line("A 12.5 80")
    check(angles is not None and angles.pan == 12.5 and angles.tilt == 80, "angles")
    check(parse_line("A no 1") is None, "bad angle")
    check(parse_line("HELLO") is None, "unknown")

    sx, sy = apply_cal(100, 200, [0.5, 0.25, 3], [0.0, 2.0, -1])
    check((sx, sy) == (103, 399), f"calibration math {(sx, sy)}")
    check(rgb888_to_565(0x1A, 0xFF, 0x80) == 0x1FF0, "rgb565 pack")
    check(load_calibration("/no/such/touchcal.json")[0][0] > 0, "missing cal falls back")

    pts = frame_to_points(np.full((8, 8), 1000.0, np.float32), 90, 90)
    check(len(pts) == 64, "boresight count")
    check(abs(float(pts[:, 0].mean())) < 0.08, "boresight x")
    check(abs(float(pts[:, 1].mean())) < 0.08, "boresight y")
    check(float(pts[:, 2].mean()) > 0.9, "boresight z")
    dropped = frame_to_points(np.full((8, 8), 8000.0, np.float32), 90, 90)
    check(len(dropped) == 0, "no-return drop")

    class MemoryPort:
        def __init__(self, payload: bytes):
            self.payload = payload
            self.closed = False

        def read(self, _n):
            data, self.payload = self.payload, b""
            return data

        def close(self):
            self.closed = True

    blob = b"A 10 80\nF " + b" ".join([b"1500"] * 64) + b"\nBREACH\nHOLD\nPUSH\n"
    source = SerialSource(MemoryPort(blob), "memory")
    # Split across polls to prove the line buffer.
    source.ser.payload = b"A 10 80\nF " + b" ".join([b"1500"] * 32)
    first = source.poll()
    check(first is not None and len(first) == 1 and first[0].pan == 10, "partial line holds")
    source.ser.payload = b" " + b" ".join([b"1500"] * 32) + b"\nLEFT\n"
    second = source.poll()
    check(second is not None and len(second) == 2 and second[0].frame is not None, "partial line completes")
    check(second[1].event == "LEFT", "event after frame")

    live = Session(demo=False, serial=SerialSource(MemoryPort(blob), "memory"))
    live.advance(0.05, spin=False)
    check(live.pan == 10 and live.tilt == 80, "session angles")
    check(live.cloud_n == 64, "session absorbed frame")
    check(live.alarm_latched is False, "HOLD cleared BREACH")
    check(len(live.stations) == len(DEMO_STATIONS) + 1, "PUSH added a stop")
    check(live.demo is False, "stays live while the port is quiet")
    live.serial.ser.payload = b""
    # A dead port falls back. MemoryPort.read does not raise; simulate it.
    live.serial.ser.read = lambda _n: (_ for _ in ()).throw(OSError("gone"))
    live.advance(0.05, spin=False)
    check(live.demo is True, "dead port falls back to demo")

    armed, _flash = breach_state(1.2)
    hot, flash_on = breach_state(5.0)
    check(armed is False and hot is True and flash_on is True, "demo tripwire timing")

    boot_pygame(window=False)
    try:
        fonts = load_fonts()
        layout = make_layout()
        check(layout.mode_at(*layout.modes[0][2].center) == 1, "hit room button")
        check(layout.mode_at(*layout.modes[3][2].center) == 4, "hit wire button")
        check(layout.back.collidepoint(*layout.back.center), "hit back")
        check(layout.tab_at(*layout.tabs[0][1].center) == "SCAN", "hit scan tab")
        early = render_shot(fonts, layout, 1, SHOTS[0][2])
        late = render_shot(fonts, layout, 1, SHOTS[1][2])
        check(early.get_size() == (WIDTH, HEIGHT), "frame size")
        sample = pygame.Surface((4, 2))
        sample.fill(GREEN)
        sample.set_at((3, 1), (0, 0, 255))
        packed = surface_to_rgb565(sample)
        check(packed.shape == (2, 4), "565 is height by width")
        check(int(packed[0, 0]) == 0x1FF0, "565 green pixel")
        check(int(packed[1, 3]) == rgb888_to_565(0, 0, 255), "565 keeps x and y")
        check(_bright_count(late) > _bright_count(early), "scan builds up")
        depth = render_shot(fonts, layout, 2, SHOTS[2][2])
        check(_bright_count(depth) > 500, "depth has ink")
        log = render_shot(fonts, layout, 3, SHOTS[4][2])
        check(_bright_count(log) > 200, "log has ink")
        armed_s = render_shot(fonts, layout, 4, SHOTS[6][2])
        breach_s = render_shot(fonts, layout, 4, SHOTS[7][2])
        check(_bright_count(breach_s) > _bright_count(armed_s) * 2, "breach flash fills")
        app = App(Session(demo=True))
        app.session.place(t=1.0)
        click = InputState(click=layout.modes[2][2].center)
        check(app.handle(layout, click) == "" and app.mode == 3, "click selects log")
        check(app.handle(layout, InputState(click=layout.back.center)) == "quit", "back quits")
        check(app.handle(layout, InputState(quit=True)) == "quit", "q quits")
        app.mode = 1
        app.handle(layout, InputState(mode=4))
        check(app.mode == 4, "number key selects wire")
        data_click = InputState(click=layout.tabs[1][1].center)
        app.handle(layout, data_click)
        check(app.active_note() == "DATA LINK DARK", "data tab note")
    finally:
        pygame.quit()

    if failures:
        for message in failures:
            sys.stderr.write(f"FAIL {message}\n")
        return 1
    print(f"cavemap self-test ok ({len(SHOTS)} shot cases, protocol, serial stub)")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Cave Mapper SCAN screen for the 480x320 Pi LCD."
    )
    parser.add_argument(
        "--window",
        action="store_true",
        help="open a desktop window instead of writing /dev/fb0",
    )
    parser.add_argument("--demo", action="store_true", help="force built-in demo data")
    parser.add_argument("--serial", metavar="PORT", help="read this serial port at 115200")
    parser.add_argument("--fps", type=int, default=TARGET_FPS, help="frame cap (default 18)")
    parser.add_argument("--dump", metavar="DIR", help="write 480x320 screenshots and exit")
    parser.add_argument("--self-test", action="store_true", help="check the protocol, serial stub, and renderer")
    args = parser.parse_args(argv)

    if args.self_test:
        code = self_test()
        if args.dump:
            for path in dump_screenshots(args.dump):
                print(path)
        return code
    if args.dump:
        for path in dump_screenshots(args.dump):
            print(path)
        return 0

    import signal

    def _on_term(_signum, _frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, _on_term)
    window = bool(args.window)
    if not window and not os.path.exists("/dev/fb0"):
        sys.stderr.write("cavemap: no /dev/fb0, opening a window\n")
        window = True
    try:
        session = open_session(force_demo=args.demo, port=args.serial)
    except Exception as error:
        sys.stderr.write(f"cavemap: {error}\n")
        return 1

    try:
        run_loop(window=window, session=session, fps=args.fps)
    except (OSError, pygame.error) as error:
        sys.stderr.write(
            f"cavemap: display failed ({error}). "
            "Need /dev/fb0 (video group or sudo), or run with --window.\n"
        )
        return 1
    except KeyboardInterrupt:
        pass
    finally:
        if session.serial is not None:
            session.serial.close()
    print("Scanner closed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
