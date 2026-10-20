#!/usr/bin/env python3
"""Touchscreen front end for the doomsday field guide.

The Pi panel is /dev/fb0 at 480x320, 16-bit RGB565. pygame cannot open that
framebuffer, so this draws with the dummy SDL driver and writes a frame only
when the picture changes. With no framebuffer, it opens a 480x320 window.

Touch input is the ADS7846 device via evdev. The top bar is GUIDE | SCAN | RADIO
(see tabbar.py, shared with Cave Mapper). GUIDE home has Search and A-Z. Search
matches the card index built when the sheets load: titles first, then card
text, updating as you type. A-Z lists every card. RADIO is the frequency guide,
listening log, and Morse trainer in radio.py. Calibration in ~/.touchcal.json
is {"cx": [a, b, c], "cy": [d, e, f]}:

    x = a*rawX + b*rawY + c
    y = d*rawX + e*rawY + f

A missing or unreadable file falls back to the device's raw axis range.
FIELD_TOUCH_MIRROR_X=1 mirrors X only in that fallback.

Tap an inline diagram to open it on the full 480x320 panel, keeping its
shape and the card's green tint. There is no tab bar. Tap, or the X, closes
it on the same card and page. A card with several pictures steps through
them with a sideways swipe or the arrows.
"""

import importlib.util
import json
import os
import select
import shutil
import subprocess
import sys
import time
import traceback
import warnings

# tty1 and /dev/fb0 are the same pixels. pygame's import-time RuntimeWarning
# ("neon capable ... PYGAME_DETECT_AVX2") is drawn on top of this UI.
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
warnings.filterwarnings("ignore", category=RuntimeWarning, module="pygame")
warnings.filterwarnings("ignore", message=".*neon capable.*")
warnings.filterwarnings("ignore", message=".*avx2.*")

try:
    import pygame
except ImportError:
    sys.stderr.write("field_touch needs python3-pygame.\n")
    raise

import tabbar

try:
    import evdev
    from evdev import ecodes
except ImportError:
    evdev = None
    ecodes = None

try:
    import content
except ImportError:
    content = None

try:
    import radio
except ImportError:
    radio = None


def load_field():
    """Load field.py, including the extensionless copy install.sh places on PATH.

    importlib refuses spec_from_file_location on a file with no suffix, so the
    installed /usr/local/bin/field is loaded with SourceFileLoader.
    """
    import importlib.machinery

    here = os.path.dirname(os.path.abspath(__file__))
    for name in ("field.py", "field"):
        path = os.path.join(here, name)
        if not os.path.isfile(path):
            continue
        # An explicit loader is required: spec_from_file_location returns None
        # for the extensionless /usr/local/bin/field installed by install.sh.
        loader = importlib.machinery.SourceFileLoader("field", path)
        spec = importlib.util.spec_from_file_location("field", path, loader=loader)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        sys.modules["field"] = module
        spec.loader.exec_module(module)
        return module
    import field as module
    return module


field = load_field()

WIDTH = 480
HEIGHT = 320
MARGIN = 4
GAP = 4
NAV_H = 60
MENU_PER = 2
RESULT_PER = 2
FIND_PER = 2
INDEX_PER = 3
# Guide search shares the 320px panel with a keyboard, so the keys stay
# near the archive keyboard's 56px and the two result rows take what remains.
FIND_KEY_H = 50
FIND_QUERY_H = 40
FIND_BACK_W = 80
INDEX_LETTER_H = 36
SWIPE = 36
# Short enough that a Pi 3B can paint it, long enough to read as a slide.
SLIDE_FRAMES = 4
SLIDE_FRAME_MS = 28
DEBOUNCE = 0.20
KEY_H = 56
TAB_H = tabbar.TAB_H
GREEN = (0x1A, 0xFF, 0x80)
DIM = (0x0A, 0x5C, 0x2E)
BLACK = (0, 0, 0)
RGB565_MASKS = (0xF800, 0x07E0, 0x001F, 0)
LIBRARY_DOWN = "Library not reachable. The sheets in this guide still work."
FONT_REGULAR = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
    "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",
)
FONT_BOLD = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSansMono-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSansMono-Bold.ttf",
)
DIAGRAM = set(r"\/|_()XO-:. ")
_MISSING = object()


def env_flag(name):
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def first_font(paths):
    for path in paths:
        if os.path.isfile(path):
            return path
    return None


# pygame can open these. Terminus on the Pi console is a .psf bitmap; handing
# that path to Font() is not a usable face and must not be tried.
FONT_SUFFIXES = (".ttf", ".otf", ".ttc")


def load_font(size, bold=False):
    """Load a UI face. A missing file or a console bitmap falls back to pygame's default."""
    if not pygame.font.get_init():
        pygame.font.init()
    size = max(1, int(size))
    paths = list(FONT_BOLD if bold else FONT_REGULAR)
    paths.extend(FONT_REGULAR if bold else ())
    seen = set()
    for path in paths:
        if not path or path in seen:
            continue
        seen.add(path)
        if not str(path).lower().endswith(FONT_SUFFIXES):
            continue
        if not os.path.isfile(path):
            continue
        try:
            font = pygame.font.Font(path, size)
            font.render(" ", True, BLACK)
            return font
        except (pygame.error, OSError, FileNotFoundError, TypeError, ValueError):
            continue
    try:
        return pygame.font.Font(None, size)
    except (pygame.error, OSError, FileNotFoundError, TypeError, ValueError):
        return pygame.font.SysFont(None, size, bold=bool(bold))


def ellipsize(font, text, width):
    if width <= 0:
        return ""
    if font.size(text)[0] <= width:
        return text
    trimmed = text
    while trimmed and font.size(trimmed + "...")[0] > width:
        trimmed = trimmed[:-1]
    return (trimmed + "...") if trimmed else ""


def wrap_words(font, text, width):
    words = text.split()
    if not words:
        return [""]
    lines = []
    current = ""
    for word in words:
        trial = word if not current else current + " " + word
        if font.size(trial)[0] <= width:
            current = trial
            continue
        if current:
            lines.append(current)
            current = ""
        if font.size(word)[0] <= width:
            current = word
            continue
        chunk = ""
        for char in word:
            if font.size(chunk + char)[0] <= width:
                chunk += char
            else:
                if chunk:
                    lines.append(chunk)
                chunk = char
        current = chunk
    if current:
        lines.append(current)
    return lines or [""]


def is_diagram(line):
    if line.startswith("  "):
        return True
    stripped = line.strip()
    return bool(stripped) and set(stripped) <= DIAGRAM


def wrap_body(text, font, small, width):
    lines = []
    for paragraph in (text or "").splitlines():
        if not paragraph.strip():
            lines.append("")
            continue
        if is_diagram(paragraph):
            lines.append(paragraph.rstrip())
            continue
        lines.extend(wrap_words(font, paragraph.strip(), width))
    return lines or ["(empty)"]


def tint_surface(surface):
    """Map brightness onto the guide green. Falls back to the original picture."""
    try:
        gray = pygame.transform.grayscale(surface.convert())
        colored = pygame.Surface(gray.get_size())
        colored.fill(GREEN)
        gray.blit(colored, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        return gray
    except (pygame.error, TypeError, ValueError):
        return surface


def fit_surface(surface, max_w, max_h, enlarge=False):
    width, height = surface.get_size()
    if width <= 0 or height <= 0 or max_w <= 0 or max_h <= 0:
        return surface
    scale = min(max_w / width, max_h / height)
    if not enlarge:
        scale = min(scale, 1)
    if scale == 1:
        return surface
    target = (max(1, int(round(width * scale))), max(1, int(round(height * scale))))
    if target == (width, height):
        return surface
    try:
        return pygame.transform.smoothscale(surface, target)
    except pygame.error:
        return pygame.transform.scale(surface, target)


def load_card_image(relpath, max_w, max_h, directory, tint, enlarge=False):
    """Load a content image fitted to a box. None when it cannot be shown."""
    if content is None or not relpath:
        return None
    path = content.resolve_image(directory, relpath)
    if path is None:
        return None
    try:
        image = pygame.image.load(str(path))
    except (pygame.error, OSError, FileNotFoundError):
        return None
    if pygame.display.get_init():
        try:
            image = image.convert()
        except pygame.error:
            pass
    image = fit_surface(image, max_w, max_h, enlarge=enlarge)
    if tint:
        image = tint_surface(image)
    return image


ENLARGE_MARK = "[+]"


def enlarge_badge_size(font):
    """Pixel size of the black [+] box, including its padding. (0, 0) with no font."""
    if font is None:
        return 0, 0
    text_w, text_h = font.size(ENLARGE_MARK)
    if text_w <= 0 or text_h <= 0:
        return 0, 0
    return text_w + 6, text_h + 4


def draw_enlarge_badge(canvas, font, image_rect, strip_h):
    """Green [+] on a black box, in the strip above the picture's top-right.

    The box is outside image_rect, so it never paints over the diagram or its caption.
    """
    if font is None or strip_h <= 0 or image_rect.width < 8 or image_rect.height < 8:
        return None
    label = font.render(ENLARGE_MARK, True, GREEN)
    box_w = label.get_width() + 6
    box_h = label.get_height() + 4
    if box_w <= 0 or box_h <= 0 or box_h > strip_h:
        return None
    x = image_rect.right - box_w
    x = max(0, min(x, WIDTH - box_w))
    y = image_rect.top - box_h
    if y < 0:
        return None
    box = pygame.Rect(x, y, box_w, box_h)
    pygame.draw.rect(canvas, BLACK, box)
    pygame.draw.rect(canvas, GREEN, box, 1)
    canvas.blit(
        label,
        (
            box.x + (box_w - label.get_width()) // 2,
            box.y + (box_h - label.get_height()) // 2,
        ),
    )
    return box


def layout_pages(text, font, small, width, page_px, directory, tint):
    """Paginate card text and pictures. A picture moves to the next page when it does not fit."""
    line_h = max(1, font.get_linesize())
    page_px = max(line_h, page_px)
    blocks = []
    if content is None:
        parts = [("text", text or "")]
    else:
        parts = content.split_parts(text or "")
    for kind, *rest in parts:
        if kind == "text":
            for line in wrap_body(rest[0], font, small, width):
                blocks.append({"kind": "text", "text": line, "px": line_h})
            continue
        alt, relpath = rest
        # 480x284 is the artboard. The live box is the reader pane under the title.
        # A strip above the picture holds the enlarge badge so the caption stays clear.
        badge_h = enlarge_badge_size(small)[1]
        max_h = min(page_px, 284)
        if badge_h >= max_h:
            badge_h = 0
        image = load_card_image(relpath, min(width, 480), max(1, max_h - badge_h), directory, tint)
        if image is None:
            label = f"[diagram: {alt}]" if alt else "[diagram]"
            for line in wrap_body(label, font, small, width):
                blocks.append({"kind": "text", "text": line, "px": line_h})
            continue
        blocks.append(
            {
                "kind": "image",
                "image": image,
                "alt": alt,
                "relpath": relpath,
                "px": image.get_height() + badge_h,
                "badge_h": badge_h,
            }
        )
    zoom = 0
    for block in blocks:
        if block["kind"] == "image":
            block["zoom"] = zoom
            zoom += 1
    if not blocks:
        blocks = [{"kind": "text", "text": "(empty)", "px": line_h}]
    pages = []
    current = []
    used = 0
    for block in blocks:
        height = block["px"]
        if current and used + height > page_px:
            pages.append(current)
            current = []
            used = 0
        current.append(block)
        used += height
    if current:
        pages.append(current)
    return pages or [[{"kind": "text", "text": "(empty)", "px": line_h}]]


def button_lines(font, label, width):
    if font.size(label)[0] <= width:
        return [label]
    lines = wrap_words(font, label, width)[:2]
    if len(lines) == 2 and font.size(lines[1])[0] > width:
        lines[1] = ellipsize(font, lines[1], width)
    return lines or [label]


def draw_button(canvas, rect, label, font, enabled, pressed):
    if pressed:
        pygame.draw.rect(canvas, GREEN, rect)
        color = BLACK
    else:
        pygame.draw.rect(canvas, BLACK, rect)
        border = GREEN if enabled else DIM
        pygame.draw.rect(canvas, border, rect, 2)
        color = GREEN if enabled else DIM
    lines = button_lines(font, label, rect.width - 12)
    line_h = font.get_linesize()
    block_h = line_h * len(lines)
    y = rect.y + max(0, (rect.height - block_h) // 2)
    for line in lines:
        img = font.render(line, True, color)
        canvas.blit(img, (rect.x + (rect.width - img.get_width()) // 2, y))
        y += line_h


def make_scanlines():
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    color = (0, 0, 0, 64)
    for y in range(0, HEIGHT, 3):
        pygame.draw.line(overlay, color, (0, y), (WIDTH - 1, y))
    return overlay


def calibration_path():
    override = os.environ.get("FIELD_TOUCH_CAL")
    if override:
        return override
    return os.path.join(os.path.expanduser("~"), ".touchcal.json")


def load_calibration(path=None):
    """Return {'cx': [a, b, c], 'cy': [d, e, f]} or None.

    The Pi writes exactly that shape. Other key layouts are not applied.
    """
    path = calibration_path() if path is None else path
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError, UnicodeError):
        sys.stderr.write(f"field_touch: could not read calibration {path}\n")
        return None
    if not isinstance(data, dict):
        sys.stderr.write(f"field_touch: could not read calibration {path}\n")
        return None
    cx = data.get("cx")
    cy = data.get("cy")
    if not isinstance(cx, (list, tuple)) or not isinstance(cy, (list, tuple)):
        sys.stderr.write(f"field_touch: could not read calibration {path}\n")
        return None
    if len(cx) != 3 or len(cy) != 3:
        sys.stderr.write(f"field_touch: could not read calibration {path}\n")
        return None
    try:
        return {"cx": [float(value) for value in cx], "cy": [float(value) for value in cy]}
    except (TypeError, ValueError):
        sys.stderr.write(f"field_touch: could not read calibration {path}\n")
        return None


def scale_axis(raw, info, size):
    if info is None:
        return float(raw)
    span = info.max - info.min
    if span <= 0:
        return 0.0
    return (raw - info.min) * (size - 1) / span


def map_touch(raw_x, raw_y, calib, width=WIDTH, height=HEIGHT, abs_x=None, abs_y=None, mirror=False):
    """Map a raw touch sample to a screen pixel.

    With calibration, x = a*rawX + b*rawY + c and y = d*rawX + e*rawY + f.
    The result is rounded and clamped so a wild sample still hits the screen.
    """
    if calib is not None:
        a, b, c = calib["cx"]
        d, e, f = calib["cy"]
        x = a * raw_x + b * raw_y + c
        y = d * raw_x + e * raw_y + f
    else:
        x = scale_axis(raw_x, abs_x, width)
        y = scale_axis(raw_y, abs_y, height)
        if mirror:
            x = (width - 1) - x
    pixel_x = max(0, min(width - 1, int(round(x))))
    pixel_y = max(0, min(height - 1, int(round(y))))
    return pixel_x, pixel_y


def _pack_strip(frame, stride, y0, height):
    """RGB565 bytes for `height` rows of `frame` starting at y0."""
    width = frame.get_width()
    converted = pygame.Surface((width, height), 0, 16, RGB565_MASKS)
    converted.blit(frame, (0, -y0))
    pitch = converted.get_pitch()
    raw = bytes(converted.get_buffer().raw)
    row_bytes = width * 2
    take = min(row_bytes, stride, pitch)
    if stride == pitch:
        return raw
    packed = bytearray(stride * height)
    for y in range(height):
        start = y * pitch
        dest = y * stride
        packed[dest : dest + take] = raw[start : start + take]
    return bytes(packed)


def pack_rgb565(frame, stride):
    """Convert an RGB surface to little-endian RGB565 bytes, one row per stride."""
    return _pack_strip(frame, stride, 0, frame.get_height())


def pack_rgb565_rows(frame, stride, y0, y1):
    """RGB565 bytes for rows [y0, y1) only. Same packing as pack_rgb565."""
    return _pack_strip(frame, stride, y0, y1 - y0)


def read_fb_geometry(path):
    name = os.path.basename(path)
    base = os.path.join("/sys/class/graphics", name)
    width, height, bpp, stride = 480, 320, 16, None

    def read_text(leaf):
        with open(os.path.join(base, leaf), encoding="ascii") as handle:
            return handle.read().strip()

    try:
        raw = read_text("virtual_size")
        wide, high = raw.split(",")
        width, height = int(wide), int(high)
    except (OSError, ValueError):
        pass
    try:
        bpp = int(read_text("bits_per_pixel"))
    except (OSError, ValueError):
        pass
    try:
        stride = int(read_text("stride"))
    except (OSError, ValueError):
        stride = None
    return width, height, bpp, stride


def ioctl_stride(fd):
    import struct
    import fcntl

    buf = bytearray(256)
    try:
        fcntl.ioctl(fd, 0x4602, buf)
    except OSError:
        return None
    offset = 48 if struct.calcsize("P") == 8 else 44
    value = struct.unpack_from("=I", buf, offset)[0]
    if 100 <= value <= 8192:
        return value
    return None


class Framebuffer:
    def __init__(self, path):
        self.path = path
        self.width, self.height, self.bpp, stride = read_fb_geometry(path)
        self.fd = open(path, "r+b", buffering=0)
        if stride is None:
            stride = ioctl_stride(self.fd.fileno())
        if stride is None:
            stride = self.width * 2
        self.stride = stride
        if self.bpp != 16:
            self.fd.close()
            raise OSError(f"{path} is {self.bpp}-bit, not 16-bit RGB565")
        self.last = None

    def write(self, canvas, rows=None):
        frame = canvas
        if canvas.get_size() != (self.width, self.height):
            frame = pygame.transform.scale(canvas, (self.width, self.height))
            rows = None
        if rows is not None and self.last is not None:
            y0 = max(0, min(self.height, int(rows[0])))
            y1 = max(y0, min(self.height, int(rows[1])))
            if y1 > y0:
                self._write_rows(frame, y0, y1)
                return
        data = pack_rgb565(frame, self.stride)
        if data == self.last:
            return
        self._write_at(data, 0)
        self.last = data

    def _write_rows(self, frame, y0, y1):
        chunk = pack_rgb565_rows(frame, self.stride, y0, y1)
        start = y0 * self.stride
        end = y1 * self.stride
        last = self.last
        if bytes(last[start:end]) == chunk:
            return
        self._write_at(chunk, start)
        if isinstance(last, bytearray):
            last[start:end] = chunk
        else:
            buf = bytearray(last)
            buf[start:end] = chunk
            self.last = buf

    def _write_at(self, data, offset):
        self.fd.seek(offset)
        view = memoryview(data)
        while view:
            wrote = self.fd.write(view)
            if not wrote:
                raise OSError("short framebuffer write")
            view = view[wrote:]

    def close(self):
        if self.fd is not None:
            self.fd.close()
            self.fd = None


def framebuffer_path():
    return os.environ.get("FIELD_TOUCH_FB", "/dev/fb0")


def fb_is_rgb565(path):
    if not (os.path.exists(path) and os.access(path, os.R_OK | os.W_OK)):
        return False
    _width, _height, bpp, _stride = read_fb_geometry(path)
    # No sysfs node: the Pi panel is 16-bit, so trust the default.
    sysfs_bpp = os.path.join("/sys/class/graphics", os.path.basename(path), "bits_per_pixel")
    if not os.path.isfile(sysfs_bpp):
        return True
    return bpp == 16


def choose_mode():
    if env_flag("FIELD_TOUCH_WINDOW"):
        return "window"
    path = framebuffer_path()
    if fb_is_rgb565(path):
        return "fb"
    driver = os.environ.get("SDL_VIDEODRIVER", "").lower()
    if driver == "dummy" or (not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY")):
        return "dummy"
    return "window"


class Display:
    def __init__(self, mode):
        self.mode = mode
        self.window = None
        self.canvas = None
        self.fb = None
        self.scale = 1

    def open(self):
        if not pygame.get_init():
            pygame.init()
        if not pygame.display.get_init():
            pygame.display.init()
        if self.mode == "window":
            try:
                self.scale = max(1, min(4, int(os.environ.get("FIELD_TOUCH_SCALE", "1"))))
            except ValueError:
                self.scale = 1
            self.window = pygame.display.set_mode((WIDTH * self.scale, HEIGHT * self.scale))
            pygame.display.set_caption("Doomsday Field Guide")
        else:
            self.scale = 1
            pygame.display.set_mode((WIDTH, HEIGHT))
            self.window = None
        self.canvas = pygame.Surface((WIDTH, HEIGHT))
        if self.mode == "fb":
            self.fb = Framebuffer(framebuffer_path())

    def close(self):
        if self.fb is not None:
            self.fb.close()
            self.fb = None
        self.window = None
        self.canvas = None
        if pygame.display.get_init():
            pygame.display.quit()

    def force_next(self):
        """Write every pixel on the next present, even if the picture matches."""
        if self.fb is not None:
            self.fb.last = None

    def present(self, canvas, rows=None):
        if self.mode == "fb" and self.fb is not None:
            self.fb.write(canvas, rows=rows)
        elif self.mode == "window" and self.window is not None:
            if self.scale == 1:
                self.window.blit(canvas, (0, 0))
                if rows:
                    pygame.display.update(pygame.Rect(0, rows[0], WIDTH, max(1, rows[1] - rows[0])))
                else:
                    pygame.display.flip()
            else:
                frame = pygame.transform.scale(canvas, self.window.get_size())
                self.window.blit(frame, (0, 0))
                pygame.display.flip()

    def canvas_xy(self, x, y):
        if self.scale <= 1:
            return int(x), int(y)
        return int(x / self.scale), int(y / self.scale)


def find_touch_device():
    if evdev is None:
        return None
    found = []
    for path in evdev.list_devices():
        try:
            found.append(evdev.InputDevice(path))
        except (OSError, PermissionError):
            continue
    override = os.environ.get("FIELD_TOUCH_DEVICE")
    if override:
        for device in found:
            if device.path == override or device.name == override:
                return device
    for device in found:
        if device.name == "ADS7846 Touchscreen":
            return device
    for device in found:
        name = (device.name or "").lower()
        if "ads7846" in name or "touchscreen" in name:
            return device
    return None


class TouchInput:
    def __init__(self):
        self.dev = None
        self.calib = load_calibration()
        self.abs_x = None
        self.abs_y = None
        self.raw_x = None
        self.raw_y = None
        self.seen_btn = False
        self.btn_down = False
        self.pressure_down = False
        self.touching = False

    def open(self):
        self.dev = find_touch_device()
        if self.dev is None:
            return
        try:
            os.set_blocking(self.dev.fd, False)
            if ecodes is not None:
                self.abs_x = self.dev.absinfo(ecodes.ABS_X)
                self.abs_y = self.dev.absinfo(ecodes.ABS_Y)
        except (OSError, PermissionError) as error:
            sys.stderr.write(f"field_touch: touchscreen unreadable ({error}).\n")
            self.dev = None

    def close(self):
        if self.dev is not None:
            try:
                self.dev.close()
            except OSError:
                pass
            self.dev = None
        self.touching = False
        self.raw_x = None
        self.raw_y = None
        self.seen_btn = False
        self.btn_down = False
        self.pressure_down = False

    def poll(self):
        if self.dev is None or ecodes is None:
            return []
        out = []
        while True:
            try:
                event = self.dev.read_one()
            except (BlockingIOError, OSError):
                break
            if event is None:
                break
            self._take(event, out)
        return out

    def _take(self, event, out):
        if event.type == ecodes.EV_ABS:
            if event.code == ecodes.ABS_X:
                self.raw_x = event.value
            elif event.code == ecodes.ABS_Y:
                self.raw_y = event.value
            elif event.code == ecodes.ABS_PRESSURE and not self.seen_btn:
                self.pressure_down = event.value > 0
        elif event.type == ecodes.EV_KEY and event.code == ecodes.BTN_TOUCH:
            self.seen_btn = True
            self.btn_down = event.value == 1
        elif event.type == ecodes.EV_SYN and event.code == ecodes.SYN_REPORT:
            self._sync(out)

    def _sync(self, out):
        if self.raw_x is None or self.raw_y is None:
            return
        x, y = map_touch(
            self.raw_x,
            self.raw_y,
            self.calib,
            abs_x=self.abs_x,
            abs_y=self.abs_y,
            mirror=env_flag("FIELD_TOUCH_MIRROR_X"),
        )
        down = self.btn_down if self.seen_btn else self.pressure_down
        if down and not self.touching:
            self.touching = True
            out.append(("down", x, y))
        elif down and self.touching:
            out.append(("move", x, y))
        elif (not down) and self.touching:
            self.touching = False
            out.append(("up", x, y))


def sheet(label, body, search_book=_MISSING, tint=True):
    item = {"label": label, "action": "sheet", "title": label.upper(), "body": body, "tint": tint}
    if search_book is not _MISSING:
        item["search_book"] = search_book
    return item


def search_action(label, book, title, hint):
    return {"label": label, "action": "search", "book": book, "title": title, "hint": hint}


def menu(label, title, intro, items):
    return {"label": label, "action": "menu", "title": title, "intro": intro, "items": items}


def topic_to_item(topic):
    """Turn one content file into a touch menu entry, sheet, or search."""
    view = field.GUIDE.present(topic.slug)
    if view is None:
        return sheet(topic.title, "(empty)")
    cards = view["cards"]
    children = view["children"]
    book = view["book"]
    tint = topic.tint
    if view["kind"] == "search":
        return search_action(
            topic.title,
            book if book is not None else "",
            topic.title.upper(),
            topic.hint or search_hint(book),
        )
    if view["kind"] == "sheet":
        body = cards[0][1] if cards else "(empty)"
        if book is not None:
            return sheet(topic.title, body, book, tint=tint)
        return sheet(topic.title, body, tint=tint)
    items = [sheet(name, body, tint=tint) for name, body in cards]
    for child in children:
        items.append(topic_to_item(child))
    if topic.slug == "more":
        items.append(search_action("Places", field.VOY, "PLACES", "Type a town, region, river, or country."))
        items.append(search_action("Search all archives", "", "SEARCH", "Search both archives on this Pi."))
    if book is not None and (cards or children):
        items.append(
            search_action(
                "Search the archive",
                book,
                topic.title.upper(),
                topic.hint or search_hint(book),
            )
        )
    intro = " ".join((topic.intro or "").split())
    return menu(topic.title, topic.title.upper(), intro, items)


def home_items():
    topics = field.GUIDE.home_topics()
    if not topics:
        return [
            search_action(
                "Medicine",
                field.MED,
                "MEDICINE",
                "Medical encyclopedia on this Pi. Doses: see First aid.",
            ),
            search_action("Search all archives", "", "SEARCH", "Search both archives on this Pi."),
        ]
    return [topic_to_item(topic) for topic in topics]


def search_hint(book):
    if book == field.MED:
        return "Search the medical encyclopedia on this Pi."
    if book == field.VOY:
        return "Type a town, region, river, or country."
    return "Search both archives on this Pi."


def letter_rows(shifted=False):
    def chars(text):
        return list(text.upper() if shifted else text)

    return [
        chars("qwertyuiop"),
        chars("asdfghjkl"),
        ["SHIFT"] + chars("zxcvbnm") + ["BKSP"],
        ["123", "SPACE", "ENTER"],
    ]


def number_rows():
    return [
        list("1234567890"),
        ["-", "'", ".", ",", "/", "?", "!", "(", ")", "BKSP"],
        ["+", ":", ";", '"', "&", "@", "#", "*", "="],
        ["ABC", "SPACE", "ENTER"],
    ]


def key_label(token):
    if token == "NUM":
        return "123"
    return token


def guide_key_rows():
    """Letter keyboard for card search: backspace, clear, and a wide space."""
    return [
        list("qwertyuiop"),
        list("asdfghjkl") + ["BKSP"],
        list("zxcvbnm") + ["CLEAR", "SPACE"],
    ]


def card_index():
    """Card index built when the guide loaded. Missing guides yield nothing."""
    guide = getattr(field, "GUIDE", None)
    if guide is None:
        return ()
    found = getattr(guide, "index", None)
    if found is None:
        return ()
    return found


class App:
    def __init__(self, show_cave=None):
        self.show_cave = show_cave
        self.stack = [{"kind": "home"}]
        self.widgets = []
        self.pressed = None
        self.origin = None
        self.swiping = False
        self.pending = None
        self.notice = ""
        self.quit_requested = False
        self.font_title = None
        self.font_body = None
        self.font_small = None
        self.font_button = None
        self.font_tab = None
        self.scanlines = None
        self.tab_hits = []
        self.tab_pressed = None
        self.tab_flash = None
        self.slide_from = None
        self._band = None
        self.last_fire = None
        self.suppress = None

    def ensure_fonts(self):
        if not pygame.font.get_init():
            pygame.font.init()
        if self.font_title is None:
            self.font_title = load_font(18, bold=True)
            self.font_body = load_font(16)
            self.font_button = load_font(16)
            self.font_tab = load_font(16)
            self.font_small = load_font(13)
            self.font_freq = load_font(28, bold=True)
            for screen in self.stack:
                screen.pop("_lines", None)
                screen.pop("_pages", None)
        if self.scanlines is None:
            self.scanlines = make_scanlines()

    def cave_on(self):
        if self.show_cave is None:
            return shutil.which("cavemap") is not None
        return bool(self.show_cave)

    def current(self):
        return self.stack[-1]

    def header_bottom(self):
        self.ensure_fonts()
        return TAB_H + 2 + self.font_title.get_linesize() + 8

    def home_grid(self, top):
        rows = 4
        avail_h = HEIGHT - 2 - top
        avail_w = WIDTH - 2 * MARGIN
        btn_h = (avail_h - GAP * (rows - 1)) // rows
        btn_w = (avail_w - GAP * 2) // 3
        extra = avail_w - (btn_w * 3 + GAP * 2)
        rects = []
        for row in range(3):
            x = MARGIN
            y = top + row * (btn_h + GAP)
            for col in range(3):
                width = btn_w + (1 if col < extra else 0)
                rects.append(pygame.Rect(x, y, width, btn_h))
                x += width + GAP
        rects.append(pygame.Rect(MARGIN, top + 3 * (btn_h + GAP), avail_w, btn_h))
        return rects, btn_h

    def _tab_pressed_name(self):
        if self.tab_pressed:
            return self.tab_pressed
        if self.pressed and self.pressed.startswith("tab:"):
            return self.pressed.split(":", 1)[1]
        return None

    def content_width(self):
        return WIDTH - 2 * MARGIN

    def reader_page_px(self):
        line_h = max(1, self.font_body.get_linesize())
        nav_y = HEIGHT - MARGIN - NAV_H
        area = max(line_h, nav_y - self.header_bottom())
        slots = max(1, area // line_h)
        return slots * line_h

    def reader_pages(self, screen):
        # page_delta asks for the page count before the first draw. Fonts have
        # to exist first, or font_body is still None.
        self.ensure_fonts()
        cached = screen.get("_pages")
        if cached is None:
            directory = screen.get("_image_dir", getattr(field.GUIDE, "directory", None))
            cached = layout_pages(
                screen.get("body") or "",
                self.font_body,
                self.font_small,
                self.content_width(),
                self.reader_page_px(),
                directory,
                screen.get("tint", True),
            )
            screen["_pages"] = cached
        return cached

    def page_count(self, screen):
        kind = screen["kind"]
        if kind == "menu":
            return max(1, (len(screen["items"]) + MENU_PER - 1) // MENU_PER)
        if kind == "reader":
            return max(1, len(self.reader_pages(screen)))
        if kind == "results":
            return max(1, (len(screen["results"]) + RESULT_PER - 1) // RESULT_PER)
        if kind == "find":
            return max(1, (len(self.find_hits(screen)) + FIND_PER - 1) // FIND_PER)
        if kind == "index":
            return max(1, (len(card_index()) + INDEX_PER - 1) // INDEX_PER)
        return 1

    def can_prev(self, screen):
        return screen.get("page", 0) > 0

    def can_next(self, screen):
        if screen["kind"] == "index":
            return screen.get("page", 0) + INDEX_PER < len(card_index())
        if screen["kind"] == "results" and len(screen["results"]) < screen.get("total", 0):
            return True
        return screen.get("page", 0) + 1 < self.page_count(screen)

    def page_delta(self, delta):
        screen = self.current()
        if screen["kind"] == "index":
            # `page` is the first visible card, so a letter jump can land
            # mid-page and the next swipe still moves a full row of titles.
            old = screen.get("page", 0)
            total = len(card_index())
            if delta < 0:
                if old <= 0:
                    return False
                screen["page"] = max(0, old - INDEX_PER)
            else:
                if old + INDEX_PER >= total:
                    return False
                screen["page"] = old + INDEX_PER
            self.slide_from = old
            return True
        if screen["kind"] not in ("menu", "reader", "results", "find"):
            return False
        old = screen.get("page", 0)
        moved = False
        if delta < 0:
            if old > 0:
                screen["page"] = old - 1
                moved = True
        elif old + 1 < self.page_count(screen):
            screen["page"] = old + 1
            moved = True
        elif screen["kind"] == "results" and len(screen["results"]) < screen.get("total", 0):
            before = len(screen["results"])
            self.fetch_more()
            if len(screen["results"]) > before and old + 1 < self.page_count(screen):
                screen["page"] = old + 1
                moved = True
        if moved:
            self.slide_from = old
        return moved

    def stop_radio_audio(self):
        if radio is None:
            return
        for screen in self.stack:
            if screen.get("kind") == "radio":
                radio.stop_audio(screen)

    def open_radio(self):
        self.notice = ""
        self.slide_from = None
        if radio is None:
            self.notice = "Radio is not available."
            return
        for index, screen in enumerate(self.stack):
            if screen.get("kind") == "radio":
                self.stack = self.stack[: index + 1]
                return
        if not self.stack or self.stack[0].get("kind") != "home":
            self.stack.insert(0, {"kind": "home"})
        self.stack = [self.stack[0], radio.new_screen()]

    def open_signals(self, slug="signals"):
        topics = getattr(field.GUIDE, "topics", {}) or {}
        topic = topics.get(slug)
        if topic is None:
            self.notice = "Signals sheet is not installed."
            return
        self.open_item(topic_to_item(topic))

    def back(self):
        if self.current().get("kind") == "radio":
            self.stop_radio_audio()
        if len(self.stack) > 1:
            self.slide_from = None
            self.stack.pop()

    def open_item(self, item):
        self.notice = ""
        self.slide_from = None
        action = item["action"]
        if action == "sheet":
            screen = {
                "kind": "reader",
                "title": item["title"],
                "body": item.get("body") or "(empty)",
                "page": 0,
                "tint": item.get("tint", True),
            }
            if "search_book" in item:
                screen["search_book"] = item["search_book"]
            self.stack.append(screen)
        elif action == "menu":
            self.stack.append(
                {
                    "kind": "menu",
                    "title": item["title"],
                    "intro": item.get("intro") or "",
                    "items": item["items"],
                    "page": 0,
                }
            )
        elif action == "search":
            self.stack.append(
                {
                    "kind": "search",
                    "title": item["title"],
                    "hint": item.get("hint") or search_hint(item.get("book")),
                    "status": item.get("hint") or search_hint(item.get("book")),
                    "status_bad": False,
                    "query": "",
                    "book": item.get("book") or "",
                    "num_mode": False,
                }
            )

    def open_search_book(self, book):
        self.open_item(search_action("Search", book, "SEARCH", search_hint(book)))

    def activate(self, wid):
        screen = self.current()
        if wid == "exit":
            self.quit_requested = True
            return
        if wid == "home-prev":
            screen["home_page"] = max(0, screen.get("home_page", 0) - 1)
            return
        if wid == "home-next":
            screen["home_page"] = screen.get("home_page", 0) + 1
            return
        if wid in ("cave", "tab:SCAN"):
            self.tab_flash = "SCAN"
            if self.cave_on():
                self.stop_radio_audio()
                self.pending = "cave"
                self.notice = "Opening Cave Mapper..."
            else:
                self.notice = "Cave Mapper is not installed."
            return
        if wid == "tab:GUIDE":
            self.tab_flash = "GUIDE"
            self.stop_radio_audio()
            self.notice = ""
            self.slide_from = None
            if screen["kind"] != "home" or len(self.stack) > 1:
                self.stack = [{"kind": "home"}]
            return
        if wid == "tab:RADIO":
            self.tab_flash = "RADIO"
            self.notice = ""
            self.open_radio()
            return
        if wid.startswith("radio:"):
            if radio is not None and screen.get("kind") == "radio":
                radio.on_tap(self, wid.split(":", 1)[1])
            return
        if wid == "back":
            self.back()
            return
        if wid == "prev":
            self.page_delta(-1)
            return
        if wid == "next":
            self.page_delta(1)
            return
        if wid == "search":
            book = screen.get("search_book", "")
            self.open_search_book(book)
            return
        if wid == "guide-search":
            self.open_find()
            return
        if wid == "guide-index":
            self.open_index()
            return
        if wid in ("find-prev", "find-next"):
            self.page_delta(-1 if wid == "find-prev" else 1)
            return
        if wid.startswith("hit:"):
            self.open_find_hit(wid.split(":", 1)[1])
            return
        if wid.startswith("index:"):
            self.open_index_hit(wid.split(":", 1)[1])
            return
        if wid.startswith("letter:"):
            self.jump_letter(wid.split(":", 1)[1])
            return
        if wid.startswith("home:"):
            index = int(wid.split(":", 1)[1])
            items = home_items()
            if 0 <= index < len(items):
                self.open_item(items[index])
            return
        if wid.startswith("menu:"):
            index = int(wid.split(":", 1)[1])
            items = screen.get("items") or []
            if 0 <= index < len(items):
                self.open_item(items[index])
            return
        if wid.startswith("key:"):
            self.on_token(wid[4:])
            return
        if wid.startswith("result:"):
            index = int(wid.split(":", 1)[1])
            self.open_result(index)
            return
        if wid == "diagram-close":
            self.back()
            return
        if wid == "diagram-prev":
            self.diagram_delta(-1)
            return
        if wid == "diagram-next":
            self.diagram_delta(1)
            return
        if wid.startswith("zoom:"):
            try:
                index = int(wid.split(":", 1)[1])
            except ValueError:
                return
            self.open_diagram(index)

    def open_find(self):
        self.notice = ""
        self.slide_from = None
        self.stack.append(
            {
                "kind": "find",
                "query": "",
                "page": 0,
            }
        )

    def open_index(self):
        self.notice = ""
        self.slide_from = None
        self.stack.append({"kind": "index", "page": 0})

    def find_hits(self, screen):
        query = screen.get("query") or ""
        if screen.get("_find_query") != query or "_hits" not in screen:
            screen["_find_query"] = query
            if content is None:
                screen["_hits"] = []
            else:
                screen["_hits"] = content.search_cards(card_index(), query)
            pages = max(1, (len(screen["_hits"]) + FIND_PER - 1) // FIND_PER)
            if screen.get("page", 0) >= pages:
                screen["page"] = 0
        return screen["_hits"]

    def open_entry(self, entry):
        if entry is None:
            return
        self.open_item(sheet(entry.title, entry.body, tint=entry.tint))

    def open_find_hit(self, raw_index):
        try:
            index = int(raw_index)
        except ValueError:
            return
        hits = self.find_hits(self.current())
        if 0 <= index < len(hits):
            self.open_entry(hits[index])

    def open_index_hit(self, raw_index):
        try:
            index = int(raw_index)
        except ValueError:
            return
        entries = card_index()
        if 0 <= index < len(entries):
            self.open_entry(entries[index])

    def jump_letter(self, letter):
        entries = card_index()
        for index, entry in enumerate(entries):
            if entry.letter == letter:
                self.current()["page"] = index
                return

    def on_find_token(self, token):
        screen = self.current()
        if token in ("DEL", "BKSP"):
            screen["query"] = (screen.get("query") or "")[:-1]
        elif token == "CLEAR":
            screen["query"] = ""
        elif token == "SPACE":
            if len(screen.get("query") or "") < 80:
                screen["query"] = (screen.get("query") or "") + " "
        elif len(token) == 1 and len(screen.get("query") or "") < 80:
            screen["query"] = (screen.get("query") or "") + token
        else:
            return
        screen["page"] = 0
        screen.pop("_hits", None)
        screen.pop("_find_query", None)

    def on_token(self, token):
        screen = self.current()
        if screen["kind"] == "find":
            self.on_find_token(token)
            return
        if screen["kind"] != "search":
            return
        if token in ("BACK",):
            self.back()
        elif token in ("SEARCH", "ENTER"):
            screen["status"] = "Searching the library on this Pi..."
            screen["status_bad"] = False
            self.pending = "search"
        elif token in ("DEL", "BKSP"):
            screen["query"] = screen["query"][:-1]
        elif token == "SPACE":
            if len(screen["query"]) < 80:
                screen["query"] += " "
        elif token == "SHIFT":
            screen["shift"] = not screen.get("shift")
        elif token in ("NUM", "123"):
            screen["num_mode"] = True
        elif token == "ABC":
            screen["num_mode"] = False
        elif len(token) == 1 and len(screen["query"]) < 80:
            screen["query"] += token
            if token.isalpha():
                screen["shift"] = False

    def run_search(self):
        screen = self.current()
        if screen["kind"] != "search":
            return
        query = screen["query"].strip()
        if not query:
            screen["status"] = "Type a word, then tap SEARCH."
            screen["status_bad"] = False
            return
        book = screen.get("book") or ""
        try:
            total, hits = field.search(query, book, 0, timeout=8, page_size=8)
        except Exception as error:
            sys.stderr.write(f"field_touch search failed: {error}\n")
            screen["status"] = LIBRARY_DOWN
            screen["status_bad"] = True
            return
        if not hits:
            screen["status"] = "No entries. Try a different word."
            screen["status_bad"] = False
            return
        self.stack.append(
            {
                "kind": "results",
                "title": "RESULTS",
                "intro": f"{total} entries",
                "query": query,
                "book": book,
                "results": list(hits),
                "total": total,
                "page": 0,
                "status": "",
            }
        )

    def fetch_more(self):
        screen = self.current()
        try:
            total, hits = field.search(
                screen["query"],
                screen.get("book") or "",
                len(screen["results"]),
                timeout=8,
                page_size=8,
            )
        except Exception as error:
            sys.stderr.write(f"field_touch search failed: {error}\n")
            screen["status"] = LIBRARY_DOWN
            return
        screen["total"] = total
        if hits:
            screen["results"].extend(hits)

    def open_result(self, index):
        screen = self.current()
        results = screen.get("results") or []
        if not 0 <= index < len(results):
            return
        title, href, _snippet = results[index]
        try:
            body = field.article_text(href, timeout=8)
        except Exception as error:
            sys.stderr.write(f"field_touch article failed: {error}\n")
            screen["status"] = "Could not open that entry. The library may be stopped."
            return
        self.stack.append({"kind": "reader", "title": title, "body": body, "page": 0})

    def launch_cave(self, display, touch=None):
        exe = shutil.which("cavemap")
        if touch is not None:
            touch.close()
        display.close()
        message = ""
        if not exe:
            message = "Cave Mapper is not installed."
        else:
            try:
                env = os.environ.copy()
                env["CAVEMAP_FROM_GUIDE"] = "1"
                code = subprocess.call([exe], env=env)
                if radio is not None and code == radio.RADIO_EXIT:
                    self.open_radio()
                elif code != 0:
                    message = "Cave Mapper closed with an error."
            except OSError as error:
                sys.stderr.write(f"field_touch cavemap failed: {error}\n")
                message = "Cave Mapper could not start."
        display.open()
        if touch is not None:
            touch.open()
        self.font_title = None
        self.scanlines = None
        self.ensure_fonts()
        self.notice = message

    def open_diagram(self, index):
        """Open one inline picture fitted to the panel. Frames are built once."""
        screen = self.current()
        if screen.get("kind") != "reader":
            return
        shots = []
        for page in self.reader_pages(screen):
            for block in page:
                if block.get("kind") == "image":
                    shots.append(block)
        if not shots or not (0 <= index < len(shots)):
            return
        directory = screen.get("_image_dir", getattr(field.GUIDE, "directory", None))
        tint = bool(screen.get("tint", True))
        frames = []
        for block in shots:
            frame = load_card_image(
                block.get("relpath") or "",
                WIDTH,
                HEIGHT,
                directory,
                tint,
                enlarge=True,
            )
            if frame is None:
                frame = fit_surface(block["image"], WIDTH, HEIGHT, enlarge=True)
            frames.append(frame)
        self.slide_from = None
        self.stack.append({"kind": "diagram", "frames": frames, "index": index})

    def diagram_delta(self, delta):
        screen = self.current()
        if screen.get("kind") != "diagram":
            return False
        frames = screen.get("frames") or []
        index = screen.get("index", 0) + delta
        if index < 0 or index >= len(frames):
            return False
        screen["index"] = index
        return True

    def pointer(self, kind, x, y):
        if kind == "down":
            hit = self.hit(x, y)
            now = time.monotonic()
            if (
                hit
                and hit != "radio:key"
                and self.last_fire is not None
                and self.last_fire[0] == hit
                and now - self.last_fire[1] < DEBOUNCE
            ):
                self.suppress = hit
                self.pressed = None
                self.origin = None
                self.swiping = False
                return False
            self.suppress = None
            self.origin = (x, y)
            self.swiping = False
            self.pressed = hit
            if hit == "radio:key" and self.current().get("kind") == "radio":
                self.current()["key_down_at"] = now
            return True
        if kind == "move":
            if self.suppress or self.origin is None:
                return False
            if self.pressed and self.pressed.startswith("tab:"):
                if self.hit(x, y) != self.pressed:
                    self.pressed = None
                    return True
                return False
            if self.pressed == "radio:key":
                return False
            if self.current().get("kind") == "diagram":
                dx = x - self.origin[0]
                dy = y - self.origin[1]
                if not self.swiping and max(abs(dx), abs(dy)) >= SWIPE:
                    self.swiping = True
                    self.pressed = None
                    return True
                if self.pressed and self.hit(x, y) != self.pressed:
                    self.pressed = None
                    return True
                return False
            dx = x - self.origin[0]
            dy = y - self.origin[1]
            if abs(dy) >= SWIPE and abs(dy) > abs(dx) and not self.swiping:
                self.swiping = True
                self.pressed = None
                return True
            if self.pressed and self.hit(x, y) != self.pressed:
                self.pressed = None
                return True
            return False
        if kind == "up":
            if self.suppress:
                self.suppress = None
                self.pressed = None
                self.origin = None
                self.swiping = False
                return False
            origin = self.origin
            pressed = self.pressed
            swiping = self.swiping
            self.origin = None
            self.pressed = None
            self.swiping = False
            if origin is None:
                return True
            dx = x - origin[0]
            dy = y - origin[1]
            if self.current().get("kind") == "diagram":
                frames = self.current().get("frames") or []
                if len(frames) > 1 and abs(dx) >= SWIPE and abs(dx) > abs(dy):
                    self.diagram_delta(-1 if dx > 0 else 1)
                    return True
                if swiping or abs(dx) >= SWIPE or abs(dy) >= SWIPE:
                    return True
                if pressed in ("diagram-prev", "diagram-next") and self.hit(x, y) == pressed:
                    self.last_fire = (pressed, time.monotonic())
                    self.activate(pressed)
                    return True
                self.back()
                return True
            if self.current().get("kind") == "radio" and radio is not None:
                if pressed == "radio:key" or (
                    pressed
                    and pressed.startswith("radio:")
                    and not swiping
                    and abs(dx) < SWIPE
                    and abs(dy) < SWIPE
                ):
                    self.last_fire = (pressed, time.monotonic())
                    self.activate(pressed)
                    return True
                if abs(dx) >= SWIPE and abs(dx) > abs(dy):
                    radio.swipe(self.current(), -1 if dx > 0 else 1)
                    return True
                if abs(dy) >= SWIPE and abs(dy) > abs(dx):
                    radio.swipe(self.current(), -1 if dy > 0 else 1)
                    return True
            on_tab = bool(pressed) and pressed.startswith("tab:")
            if (not on_tab) and (swiping or (abs(dy) >= SWIPE and abs(dy) > abs(dx))):
                if self.current()["kind"] in ("reader", "menu", "results", "find", "index"):
                    self.page_delta(-1 if dy > 0 else 1)
                return True
            if pressed and self.hit(x, y) == pressed:
                self.last_fire = (pressed, time.monotonic())
                self.activate(pressed)
            return True
        return False

    def on_key(self, event):
        screen = self.current()
        if event.key == pygame.K_ESCAPE:
            if screen["kind"] == "home":
                self.quit_requested = True
            else:
                self.back()
            return True
        if screen["kind"] == "search":
            if event.key == pygame.K_BACKSPACE:
                screen["query"] = screen["query"][:-1]
                return True
            if event.key == pygame.K_RETURN:
                self.on_token("SEARCH")
                return True
            text = event.unicode or ""
            if text.isprintable() and text not in "\r\n\t":
                if len(screen["query"]) < 80:
                    screen["query"] += text
                return True
            return False
        if screen["kind"] == "find":
            if event.key == pygame.K_BACKSPACE:
                self.on_find_token("BKSP")
                return True
            text = event.unicode or ""
            if text == " ":
                self.on_find_token("SPACE")
                return True
            if len(text) == 1 and text.isprintable() and text not in "\r\n\t":
                self.on_find_token(text)
                return True
        if screen["kind"] == "radio" and radio is not None:
            if event.key in (pygame.K_LEFT, pygame.K_UP, pygame.K_PAGEUP):
                radio.swipe(screen, -1)
                return True
            if event.key in (pygame.K_RIGHT, pygame.K_DOWN, pygame.K_PAGEDOWN):
                radio.swipe(screen, 1)
                return True
        if screen["kind"] == "diagram":
            if event.key in (pygame.K_LEFT, pygame.K_UP, pygame.K_PAGEUP):
                self.diagram_delta(-1)
                return True
            if event.key in (pygame.K_RIGHT, pygame.K_DOWN, pygame.K_PAGEDOWN):
                self.diagram_delta(1)
                return True
        if event.key in (pygame.K_UP, pygame.K_PAGEUP, pygame.K_LEFT):
            self.page_delta(-1)
            return True
        if event.key in (pygame.K_DOWN, pygame.K_PAGEDOWN, pygame.K_RIGHT):
            self.page_delta(1)
            return True
        if event.key in (pygame.K_BACKSPACE, pygame.K_q):
            if screen["kind"] == "home":
                self.quit_requested = True
            else:
                self.back()
            return True
        if screen["kind"] == "home" and event.unicode and event.unicode.isdigit():
            number = int(event.unicode)
            if 1 <= number <= 9:
                self.activate(f"home:{number - 1}")
                return True
        return False

    def hit(self, x, y):
        for hit in self.tab_hits:
            if hit["rect"].collidepoint(x, y):
                return "tab:" + hit["name"]
        for widget in reversed(self.widgets):
            if widget["enabled"] and widget["rect"].collidepoint(x, y):
                return widget["id"]
        return None

    def add_button(self, canvas, rect, label, wid, enabled=True, latched=False):
        pressed = (enabled and self.pressed == wid) or latched
        draw_button(canvas, rect, label, self.font_button, enabled, pressed)
        self.widgets.append({"rect": rect, "id": wid, "enabled": enabled, "label": label})

    def draw_header(self, canvas, title, page=None, pages=None):
        y = TAB_H + 2
        counter = ""
        counter_w = 0
        if pages and pages > 1:
            counter = f"{page + 1}/{pages}"
            counter_w = self.font_body.size(counter)[0] + 12
        label = ellipsize(self.font_title, title, self.content_width() - counter_w)
        img = self.font_title.render(label, True, GREEN)
        canvas.blit(img, (MARGIN, y))
        if counter:
            cimg = self.font_body.render(counter, True, GREEN)
            canvas.blit(
                cimg,
                (WIDTH - MARGIN - cimg.get_width(), y + max(0, (img.get_height() - cimg.get_height()) // 2)),
            )
        rule = y + self.font_title.get_linesize() + 3
        pygame.draw.line(canvas, DIM, (MARGIN, rule), (WIDTH - MARGIN, rule))
        return rule + 5

    def draw_intro(self, canvas, text, y):
        if not text:
            return y
        line = ellipsize(self.font_small, text, self.content_width())
        img = self.font_small.render(line, True, GREEN)
        canvas.blit(img, (MARGIN, y))
        return y + self.font_small.get_linesize() + 4

    def draw_nav(self, canvas, specs):
        nav_y = HEIGHT - MARGIN - NAV_H
        avail_w = WIDTH - 2 * MARGIN
        count = len(specs)
        btn_w = (avail_w - GAP * (count - 1)) // count
        extra = avail_w - (btn_w * count + GAP * (count - 1))
        x = MARGIN
        for index, (label, wid, enabled) in enumerate(specs):
            grow = 1 if index < extra else 0
            rect = pygame.Rect(x, nav_y, btn_w + grow, NAV_H)
            self.add_button(canvas, rect, label, wid, enabled)
            x += btn_w + grow + GAP
        return nav_y

    def nav_specs(self, screen, with_search=False):
        specs = [
            ("Prev", "prev", self.can_prev(screen)),
            ("Back", "back", True),
            ("Next", "next", self.can_next(screen)),
        ]
        if with_search:
            specs.append(("Search", "search", True))
        return specs

    def draw(self, canvas, scan=True):
        self.ensure_fonts()
        self.widgets = []
        self._band = None
        canvas.fill(BLACK)
        kind = self.current()["kind"]
        if kind == "diagram":
            self.tab_hits = []
            self.draw_diagram(canvas)
            if scan:
                canvas.blit(self.scanlines, (0, 0))
            return
        active = "GUIDE"
        if any(screen.get("kind") == "radio" for screen in self.stack) and kind != "home":
            active = "RADIO"
        self.tab_hits = tabbar.draw_tabbar(
            canvas,
            self.font_tab,
            active=active,
            pressed=self._tab_pressed_name(),
            enabled={"GUIDE": True, "SCAN": self.cave_on(), "RADIO": radio is not None},
        )
        if kind == "home":
            self.draw_home(canvas)
        elif kind == "menu":
            self.draw_menu(canvas)
        elif kind == "reader":
            self.draw_reader(canvas)
        elif kind == "search":
            self.draw_search(canvas)
        elif kind == "find":
            self.draw_find(canvas)
        elif kind == "index":
            self.draw_index(canvas)
        elif kind == "results":
            self.draw_results(canvas)
        elif kind == "radio" and radio is not None:
            radio.render(self, canvas)
        if scan:
            canvas.blit(self.scanlines, (0, 0))

    def draw_home(self, canvas):
        line = self.notice or "ON THIS PI"
        y = TAB_H + 2
        img = self.font_small.render(
            ellipsize(self.font_small, line, self.content_width()),
            True,
            GREEN if self.notice else DIM,
        )
        top_with_line = y + img.get_height() + 2
        _rects, tall = self.home_grid(top_with_line)
        if tall >= 60 or self.notice:
            canvas.blit(img, ((WIDTH - img.get_width()) // 2, y))
            top = top_with_line
        else:
            top = y
        rects, _btn_h = self.home_grid(top)
        items = home_items()
        page = 0
        pages = 1
        if len(items) > 9:
            pages = (len(items) + 8) // 9
            page = min(max(0, self.current().get("home_page", 0)), pages - 1)
            self.current()["home_page"] = page
        start = page * 9
        for offset, item in enumerate(items[start : start + 9]):
            self.add_button(canvas, rects[offset], item["label"], f"home:{start + offset}")
        action = rects[9]
        if pages == 1:
            row = [
                ("Search", "guide-search", True),
                ("A-Z", "guide-index", True),
                ("Exit", "exit", True),
            ]
        else:
            row = [
                ("Prev", "home-prev", page > 0),
                ("Search", "guide-search", True),
                ("A-Z", "guide-index", True),
                ("Exit", "exit", True),
                ("Next", "home-next", page + 1 < pages),
            ]
        self._fill_row(canvas, action, row)

    def draw_menu(self, canvas):
        screen = self.current()
        pages = self.page_count(screen)
        page = min(screen.get("page", 0), pages - 1)
        screen["page"] = page
        top = self.draw_header(canvas, screen["title"], page, pages)
        top = self.draw_intro(canvas, screen.get("intro") or "", top)
        nav_y = self.draw_nav(canvas, self.nav_specs(screen))
        self._band = pygame.Rect(0, top, WIDTH, max(1, nav_y - top))
        area = nav_y - 4 - top
        per = MENU_PER
        btn_h = max(1, (area - GAP * (per - 1)) // per)
        start = page * per
        for offset, item in enumerate(screen["items"][start : start + per]):
            rect = pygame.Rect(MARGIN, top + offset * (btn_h + GAP), self.content_width(), btn_h)
            self.add_button(canvas, rect, item["label"], f"menu:{start + offset}")

    def draw_reader(self, canvas):
        screen = self.current()
        nav_y = HEIGHT - MARGIN - NAV_H
        pages = self.reader_pages(screen)
        count = max(1, len(pages))
        page = min(screen.get("page", 0), count - 1)
        screen["page"] = page
        top = self.draw_header(canvas, screen.get("title") or "SHEET", page, count)
        self.draw_nav(canvas, self.nav_specs(screen, with_search="search_book" in screen))
        self._band = pygame.Rect(0, top, WIDTH, max(1, nav_y - top))
        canvas.set_clip(self._band)
        y = top
        for block in pages[page]:
            if block["kind"] == "image":
                image = block["image"]
                badge_h = block.get("badge_h", 0)
                x = MARGIN + max(0, (self.content_width() - image.get_width()) // 2)
                rect = pygame.Rect(x, y + badge_h, image.get_width(), image.get_height())
                canvas.blit(image, rect.topleft)
                draw_enlarge_badge(canvas, self.font_small, rect, badge_h)
                # The whole picture is the tap target. The badge sits in the strip above it.
                self.widgets.append(
                    {
                        "rect": rect,
                        "id": f"zoom:{block.get('zoom', 0)}",
                        "enabled": True,
                        "label": "diagram",
                    }
                )
            elif block.get("text"):
                line = block["text"]
                use = self.font_body
                if use.size(line)[0] > self.content_width() and self.font_small.size(line)[0] <= self.content_width():
                    use = self.font_small
                img = use.render(line, True, GREEN)
                canvas.blit(img, (MARGIN, y))
            y += block["px"]
        canvas.set_clip(None)

    def draw_diagram(self, canvas):
        screen = self.current()
        frames = screen.get("frames") or []
        index = screen.get("index", 0)
        if frames:
            index = max(0, min(index, len(frames) - 1))
            screen["index"] = index
            image = frames[index]
            canvas.blit(image, ((WIDTH - image.get_width()) // 2, (HEIGHT - image.get_height()) // 2))
        close = pygame.Rect(WIDTH - 32, 4, 28, 28)
        self._diagram_close(canvas, close, self.pressed == "diagram-close")
        self.widgets.append({"rect": close, "id": "diagram-close", "enabled": True, "label": "X"})
        count = len(frames)
        if count > 1:
            prev = pygame.Rect(4, HEIGHT - 44, 48, 40)
            nxt = pygame.Rect(WIDTH - 52, HEIGHT - 44, 48, 40)
            self._diagram_arrow(canvas, prev, -1, self.pressed == "diagram-prev")
            self._diagram_arrow(canvas, nxt, 1, self.pressed == "diagram-next")
            self.widgets.append({"rect": prev, "id": "diagram-prev", "enabled": True, "label": "Prev"})
            self.widgets.append({"rect": nxt, "id": "diagram-next", "enabled": True, "label": "Next"})
            marker = self.font_small.render(f"{index + 1}/{count}", True, GREEN)
            canvas.blit(marker, ((WIDTH - marker.get_width()) // 2, HEIGHT - marker.get_height() - 14))

    def _diagram_close(self, canvas, rect, pressed):
        color = BLACK if pressed else GREEN
        if pressed:
            pygame.draw.rect(canvas, GREEN, rect)
        else:
            pygame.draw.rect(canvas, BLACK, rect)
            pygame.draw.rect(canvas, GREEN, rect, 1)
        pad = 7
        start = (rect.left + pad, rect.top + pad)
        end = (rect.right - pad - 1, rect.bottom - pad - 1)
        pygame.draw.line(canvas, color, start, end, 2)
        pygame.draw.line(canvas, color, (end[0], start[1]), (start[0], end[1]), 2)

    def _diagram_arrow(self, canvas, rect, direction, pressed):
        color = BLACK if pressed else GREEN
        if pressed:
            pygame.draw.rect(canvas, GREEN, rect)
        else:
            pygame.draw.rect(canvas, BLACK, rect)
            pygame.draw.rect(canvas, GREEN, rect, 2)
        cx, cy = rect.center
        span = 8
        if direction < 0:
            points = [(cx + span, cy - span), (cx - span, cy), (cx + span, cy + span)]
        else:
            points = [(cx - span, cy - span), (cx + span, cy), (cx - span, cy + span)]
        pygame.draw.polygon(canvas, color, points)

    def draw_search(self, canvas):
        screen = self.current()
        rows = number_rows() if screen.get("num_mode") else letter_rows(bool(screen.get("shift")))
        block = KEY_H * len(rows) + GAP * (len(rows) - 1)
        key_top = HEIGHT - block
        field_top = TAB_H
        field_h = 30
        status_top = field_top + field_h
        status_h = max(1, key_top - status_top)
        self.draw_query(canvas, screen.get("query") or "", field_top, field_h)
        status = screen.get("status") or ""
        color = GREEN if screen.get("status_bad") or status.startswith("Searching") else DIM
        self.draw_wrapped(canvas, status, color, status_top, status_h)
        area = pygame.Rect(MARGIN, key_top, self.content_width(), block)
        latched = bool(screen.get("shift")) and not screen.get("num_mode")
        for rect, token in layout_keys(rows, area):
            self.add_button(
                canvas,
                rect,
                key_label(token),
                "key:" + token,
                latched=latched and token == "SHIFT",
            )

    def _fill_row(self, canvas, action, specs):
        count = len(specs)
        if count < 1:
            return
        btn_w = (action.width - GAP * (count - 1)) // count
        extra = action.width - (btn_w * count + GAP * (count - 1))
        x = action.x
        for index, (label, wid, enabled) in enumerate(specs):
            grow = 1 if index < extra else 0
            rect = pygame.Rect(x, action.y, btn_w + grow, action.height)
            self.add_button(canvas, rect, label, wid, enabled)
            x += btn_w + grow + GAP

    def _draw_hit_row(self, canvas, rect, entry, wid):
        """One full-width row: card title, topic name in dim on the right."""
        pressed = self.pressed == wid
        if pressed:
            pygame.draw.rect(canvas, GREEN, rect)
            title_color = BLACK
            topic_color = BLACK
        else:
            pygame.draw.rect(canvas, BLACK, rect)
            pygame.draw.rect(canvas, GREEN, rect, 2)
            title_color = GREEN
            topic_color = DIM
        pad = 8
        topic = ellipsize(self.font_small, entry.topic_title, max(40, rect.width // 3))
        topic_img = self.font_small.render(topic, True, topic_color)
        title_w = max(20, rect.width - pad * 3 - topic_img.get_width())
        title = ellipsize(self.font_button, entry.title, title_w)
        title_img = self.font_button.render(title, True, title_color)
        title_y = rect.y + max(0, (rect.height - title_img.get_height()) // 2)
        topic_y = rect.y + max(0, (rect.height - topic_img.get_height()) // 2)
        canvas.blit(title_img, (rect.x + pad, title_y))
        canvas.blit(topic_img, (rect.right - pad - topic_img.get_width(), topic_y))
        self.widgets.append({"rect": rect, "id": wid, "enabled": True, "label": entry.title})

    def draw_find(self, canvas):
        screen = self.current()
        hits = self.find_hits(screen)
        pages = max(1, (len(hits) + FIND_PER - 1) // FIND_PER)
        page = min(max(0, screen.get("page", 0)), pages - 1)
        screen["page"] = page
        rows = guide_key_rows()
        block = FIND_KEY_H * len(rows) + GAP * (len(rows) - 1)
        key_top = HEIGHT - block
        row_y = TAB_H + 2
        back = pygame.Rect(MARGIN, row_y, FIND_BACK_W, FIND_QUERY_H)
        self.add_button(canvas, back, "Back", "back")
        query_x = back.right + GAP
        query_w = WIDTH - MARGIN - query_x
        count = ""
        reserve = 0
        if (screen.get("query") or "").strip():
            count = str(len(hits))
            reserve = self.font_small.size(count)[0] + 12
        query_rect = self.draw_query(
            canvas,
            screen.get("query") or "",
            row_y,
            FIND_QUERY_H,
            reserve=reserve,
            x=query_x,
            width=query_w,
            placeholder="card title or word",
        )
        if count:
            img = self.font_small.render(count, True, DIM if hits else GREEN)
            canvas.blit(
                img,
                (
                    query_rect.right - 8 - img.get_width(),
                    query_rect.y + (query_rect.height - img.get_height()) // 2,
                ),
            )
        list_top = row_y + FIND_QUERY_H + GAP
        list_bottom = key_top - GAP
        show_pages = pages > 1
        page_w = 68 if show_pages else 0
        list_w = self.content_width() - (page_w + GAP if show_pages else 0)
        area = max(1, list_bottom - list_top)
        btn_h = max(1, (area - GAP * (FIND_PER - 1)) // FIND_PER)
        self._band = pygame.Rect(MARGIN, list_top, list_w, min(area, FIND_PER * btn_h + GAP * (FIND_PER - 1)))
        if not hits:
            hint = "No cards match." if (screen.get("query") or "").strip() else "Titles match first, then the card text."
            self.draw_wrapped(canvas, hint, DIM, list_top + 4, area)
        else:
            start = page * FIND_PER
            for offset, entry in enumerate(hits[start : start + FIND_PER]):
                rect = pygame.Rect(MARGIN, list_top + offset * (btn_h + GAP), list_w, btn_h)
                self._draw_hit_row(canvas, rect, entry, f"hit:{start + offset}")
        if show_pages:
            prev = pygame.Rect(MARGIN + list_w + GAP, list_top, page_w, btn_h)
            nxt = pygame.Rect(MARGIN + list_w + GAP, list_top + btn_h + GAP, page_w, btn_h)
            self.add_button(canvas, prev, "Prev", "find-prev", page > 0)
            self.add_button(canvas, nxt, "Next", "find-next", page + 1 < pages)
        area_keys = pygame.Rect(MARGIN, key_top, self.content_width(), block)
        for rect, token in layout_keys(rows, area_keys, weights={"SPACE": 3}):
            self.add_button(canvas, rect, key_label(token), "key:" + token)

    def draw_index(self, canvas):
        screen = self.current()
        entries = list(card_index())
        start = screen.get("page", 0)
        if start < 0 or (entries and start >= len(entries)):
            start = 0
        screen["page"] = start
        y = TAB_H + 2
        title = self.font_title.render("A-Z", True, GREEN)
        canvas.blit(title, (MARGIN, y))
        if len(entries) > INDEX_PER:
            counter = f"{start + 1}/{len(entries)}"
            cimg = self.font_body.render(counter, True, GREEN)
            canvas.blit(
                cimg,
                (WIDTH - MARGIN - cimg.get_width(), y + max(0, (title.get_height() - cimg.get_height()) // 2)),
            )
        y += title.get_height() + 2
        present = {entry.letter for entry in entries}
        current = entries[start].letter if entries else None
        letters = content.INDEX_LETTERS if content is not None else tuple("ABCDEFGHIJKLMNOPQRSTUVWXYZ") + ("#",)
        rows = (letters[:13], letters[13:])
        for row in rows:
            count = len(row)
            avail = self.content_width()
            btn_w = (avail - GAP * (count - 1)) // count if count else avail
            extra = avail - (btn_w * count + GAP * (count - 1)) if count else 0
            x = MARGIN
            for index, letter in enumerate(row):
                grow = 1 if index < extra else 0
                rect = pygame.Rect(x, y, btn_w + grow, INDEX_LETTER_H)
                enabled = letter in present
                self.add_button(
                    canvas,
                    rect,
                    letter,
                    "letter:" + letter,
                    enabled=enabled,
                    latched=enabled and letter == current,
                )
                x += btn_w + grow + GAP
            y += INDEX_LETTER_H + 2
        nav_y = self.draw_nav(canvas, self.nav_specs(screen))
        list_top = y + 2
        area = max(1, nav_y - 4 - list_top)
        per = INDEX_PER
        btn_h = max(1, (area - GAP * (per - 1)) // per)
        self._band = pygame.Rect(0, list_top, WIDTH, max(1, nav_y - list_top))
        if not entries:
            self.draw_wrapped(canvas, "No cards are installed.", DIM, list_top, area)
            return
        for offset, entry in enumerate(entries[start : start + per]):
            rect = pygame.Rect(MARGIN, list_top + offset * (btn_h + GAP), self.content_width(), btn_h)
            self._draw_hit_row(canvas, rect, entry, f"index:{start + offset}")

    def draw_query(self, canvas, query, y, height=34, reserve=0, x=None, width=None, placeholder="type a word"):
        if x is None:
            x = MARGIN
        if width is None:
            width = self.content_width()
        rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(canvas, BLACK, rect)
        pygame.draw.rect(canvas, GREEN, rect, 2)
        font = self.font_body
        pad = 8
        caret_w = 2
        limit = rect.width - pad * 2 - caret_w - 8 - max(0, reserve)
        if query:
            shown = query
            while shown and font.size(shown)[0] > limit:
                shown = shown[1:]
            img = font.render(shown, True, GREEN)
            text_x = rect.x + pad
        else:
            shown = ""
            img = font.render(placeholder, True, DIM)
            text_x = rect.x + pad + caret_w + 4
        text_y = rect.y + (rect.height - img.get_height()) // 2
        canvas.blit(img, (text_x, text_y))
        if query:
            caret_x = rect.x + pad + font.size(shown)[0] + 2
        else:
            caret_x = rect.x + pad
        caret_x = min(caret_x, rect.right - pad - caret_w - max(0, reserve))
        caret_h = max(8, font.get_height() - 2)
        caret_y = rect.y + (rect.height - caret_h) // 2
        pygame.draw.rect(canvas, GREEN, (caret_x, caret_y, caret_w, caret_h))
        return rect

    def draw_wrapped(self, canvas, text, color, y, height):
        if not text:
            return
        max_w = self.content_width()
        lines = []
        current = ""
        for word in text.split():
            trial = word if not current else current + " " + word
            if self.font_small.size(trial)[0] <= max_w:
                current = trial
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        line_h = self.font_small.get_linesize()
        max_lines = max(1, height // line_h)
        truncated = len(lines) > max_lines
        lines = lines[:max_lines]
        if truncated and lines:
            lines[-1] = ellipsize(self.font_small, lines[-1], max_w)
        yy = y
        for line in lines:
            img = self.font_small.render(line, True, color)
            canvas.blit(img, (MARGIN, yy))
            yy += line_h

    def draw_results(self, canvas):
        screen = self.current()
        pages = self.page_count(screen)
        page = min(screen.get("page", 0), max(0, pages - 1))
        screen["page"] = page
        top = self.draw_header(canvas, screen.get("title") or "RESULTS", page, pages)
        intro = screen.get("status") or screen.get("intro") or ""
        top = self.draw_intro(canvas, intro, top)
        nav_y = self.draw_nav(canvas, self.nav_specs(screen))
        self._band = pygame.Rect(0, top, WIDTH, max(1, nav_y - top))
        area = nav_y - 4 - top
        per = RESULT_PER
        btn_h = (area - GAP * (per - 1)) // per
        start = page * per
        for offset, (title, _href, snippet) in enumerate(screen["results"][start : start + per]):
            rect = pygame.Rect(MARGIN, top + offset * (btn_h + GAP), self.content_width(), btn_h)
            wid = f"result:{start + offset}"
            pressed = self.pressed == wid
            if pressed:
                pygame.draw.rect(canvas, GREEN, rect)
                title_color = BLACK
                snip_color = BLACK
            else:
                pygame.draw.rect(canvas, BLACK, rect)
                pygame.draw.rect(canvas, GREEN, rect, 2)
                title_color = GREEN
                snip_color = DIM
            title_img = self.font_button.render(
                ellipsize(self.font_button, title, rect.width - 16), True, title_color
            )
            canvas.blit(title_img, (rect.x + 8, rect.y + 8))
            if snippet:
                snip = self.font_small.render(
                    ellipsize(self.font_small, snippet, rect.width - 16), True, snip_color
                )
                canvas.blit(snip, (rect.x + 8, rect.y + 8 + self.font_button.get_linesize()))
            self.widgets.append({"rect": rect, "id": wid, "enabled": True, "label": title})

    def draw_goodbye(self, canvas):
        self.ensure_fonts()
        canvas.fill(BLACK)
        lines = [
            "GUIDE CLOSED",
            "Type field_touch to open it again.",
            "Keyboard guide: type field",
        ]
        y = 90
        for index, line in enumerate(lines):
            font = self.font_title if index == 0 else self.font_body
            img = font.render(line, True, GREEN)
            canvas.blit(img, ((WIDTH - img.get_width()) // 2, y))
            y += font.get_linesize() + 8
        canvas.blit(self.scanlines, (0, 0))


def layout_keys(rows, area, weights=None):
    wide = {
        "SHIFT": 76,
        "BKSP": 72,
        "ENTER": 96,
        "123": 64,
        "ABC": 64,
        "NUM": 64,
        "SEARCH": 96,
        "BACK": 72,
        "DEL": 72,
        "CLEAR": 76,
    }
    weights = weights or {}
    count = len(rows)
    key_h = (area.height - GAP * (count - 1)) // count if count else area.height
    if key_h < 1:
        key_h = 1
    rects = []
    y = area.y
    for row in rows:
        flex = []
        fixed = 0
        for token in row:
            if token == "SPACE" or token not in wide:
                flex.append(token)
            else:
                fixed += wide[token]
        gaps = GAP * max(0, len(row) - 1)
        remain = area.width - fixed - gaps
        flex_weights = [max(1, int(weights.get(token, 1))) for token in flex]
        weight_sum = sum(flex_weights) if flex_weights else 1
        if flex and all(item == 1 for item in flex_weights):
            share = max(1, remain // len(flex))
            extra = remain - share * len(flex)
            widths = [share + (1 if index < extra else 0) for index in range(len(flex))]
        elif flex:
            widths = []
            used = 0
            for index, item in enumerate(flex_weights):
                if index == len(flex_weights) - 1:
                    width = remain - used
                else:
                    width = remain * item // weight_sum
                if width < 1:
                    width = 1
                widths.append(width)
                used += width
            overflow = used - remain
            if overflow > 0 and widths:
                widths[-1] = max(1, widths[-1] - overflow)
        else:
            widths = []
        x = area.x
        flex_i = 0
        for token in row:
            if token in wide and token != "SPACE":
                width = wide[token]
            else:
                width = widths[flex_i] if flex_i < len(widths) else 1
                flex_i += 1
            if width < 1:
                width = 1
            rects.append((pygame.Rect(x, y, width, key_h), token))
            x += width + GAP
        y += key_h + GAP
    return rects


def boot_pygame():
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    if not pygame.get_init():
        pygame.init()
    if not pygame.display.get_init():
        pygame.display.init()


def present_frame(app, display, force=False):
    if force:
        display.force_next()
    app.draw(display.canvas)
    display.present(display.canvas)


def play_slide(app, display, old_page, new_page):
    """Slide the page body in a handful of frames. Chrome stays put.

    Returns how many frames were presented. Middle frames write only the
    rows that moved.
    """
    screen = app.current()
    canvas = display.canvas
    delta = 1 if new_page > old_page else -1
    screen["page"] = old_page
    app.draw(canvas, scan=False)
    old_band = None if app._band is None else app._band.copy()
    old = None
    if old_band is not None and old_band.height >= 8:
        old = canvas.subsurface(old_band).copy()
    screen["page"] = new_page
    app.draw(canvas, scan=False)
    band = None if app._band is None else app._band.copy()
    if old is None or band is None or old_band.size != band.size:
        canvas.blit(app.scanlines, (0, 0))
        display.present(canvas)
        return 1
    fresh = canvas.subsurface(band).copy()
    base = canvas.copy()
    for step in range(1, SLIDE_FRAMES + 1):
        shift = band.height * step // SLIDE_FRAMES
        canvas.blit(base, (0, 0))
        canvas.set_clip(band)
        if delta > 0:
            canvas.blit(old, (band.x, band.y - shift))
            canvas.blit(fresh, (band.x, band.y + band.height - shift))
        else:
            canvas.blit(old, (band.x, band.y + shift))
            canvas.blit(fresh, (band.x, band.y - band.height + shift))
        canvas.set_clip(None)
        canvas.blit(app.scanlines, (0, 0))
        # First frame also refreshes the page indicator and Prev/Next.
        rows = None if step in (1, SLIDE_FRAMES) else (band.top, band.bottom)
        display.present(canvas, rows=rows)
        if step != SLIDE_FRAMES:
            pygame.time.wait(SLIDE_FRAME_MS)
    return SLIDE_FRAMES


def flash_tab(app, display):
    name = app.tab_flash
    app.tab_flash = None
    if not name:
        return
    app.tab_pressed = name
    app.draw(display.canvas)
    display.present(display.canvas)
    pygame.time.wait(80)
    app.tab_pressed = None


def run(start=None):
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    mode = choose_mode()
    if mode == "fb":
        os.environ["SDL_VIDEODRIVER"] = "dummy"
    elif mode == "dummy":
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    boot_pygame()
    app = App()
    if start == "radio":
        app.open_radio()
    display = Display(mode)
    touch = TouchInput()
    try:
        display.open()
        touch.open()
        if mode == "fb" and touch.dev is None:
            sys.stderr.write("field_touch: ADS7846 touchscreen was not found.\n")
        # Paint immediately, then once more after the console has had a chance
        # to stamp leftover text onto /dev/fb0. The second write ignores the
        # unchanged-frame skip so it covers that text.
        present_frame(app, display)
        time.sleep(0.5)
        present_frame(app, display, force=True)
        loop(app, display, touch)
        if display.mode == "fb" and display.canvas is not None:
            app.draw_goodbye(display.canvas)
            display.present(display.canvas)
    finally:
        app.stop_radio_audio()
        touch.close()
        display.close()
    return 0


def collect_events(display, touch):
    events = []
    if pygame.display.get_init():
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                events.append(("quit",))
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                x, y = display.canvas_xy(*event.pos)
                events.append(("down", x, y))
            elif event.type == pygame.MOUSEMOTION and event.buttons[0]:
                x, y = display.canvas_xy(*event.pos)
                events.append(("move", x, y))
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                x, y = display.canvas_xy(*event.pos)
                events.append(("up", x, y))
            elif event.type == pygame.KEYDOWN:
                events.append(("key", event))
    events.extend(touch.poll())
    return events


def idle_wait(touch):
    try:
        if touch.dev is not None:
            select.select([touch.dev.fd], [], [], 0.05)
        else:
            pygame.time.wait(50)
    except (InterruptedError, OSError):
        pass


def loop(app, display, touch):
    while not app.quit_requested:
        changed = False
        events = collect_events(display, touch)
        for index, event in enumerate(events):
            kind = event[0]
            if kind == "quit":
                app.quit_requested = True
            elif kind == "key":
                changed = app.on_key(event[1]) or changed
            elif kind == "down":
                changed = app.pointer("down", event[1], event[2]) or changed
                # A tap that arrives as down+up in one read still gets a visible press.
                nxt = events[index + 1] if index + 1 < len(events) else None
                if app.pressed and nxt is not None and nxt[0] == "up":
                    app.draw(display.canvas)
                    display.present(display.canvas)
                    pygame.time.wait(50)
            else:
                changed = app.pointer(kind, event[1], event[2]) or changed
        if app.quit_requested:
            break
        if app.tab_flash:
            flash_tab(app, display)
            changed = True
        if app.slide_from is not None:
            old = app.slide_from
            app.slide_from = None
            new = app.current().get("page", old)
            kind = app.current()["kind"]
            if (
                display.canvas is not None
                and kind in ("menu", "reader", "results", "find", "index")
                and old != new
            ):
                play_slide(app, display, old, new)
                changed = False
            else:
                changed = True
        if radio is not None and app.current().get("kind") == "radio":
            if radio.tick(app.current()):
                changed = True
        if app.pending:
            app.draw(display.canvas)
            display.present(display.canvas)
            action = app.pending
            app.pending = None
            if action == "search":
                app.run_search()
            elif action == "cave":
                app.launch_cave(display, touch)
            changed = True
        if changed and not app.quit_requested:
            app.draw(display.canvas)
            display.present(display.canvas)
        elif not app.quit_requested:
            if radio is not None and radio.busy(app.current()):
                pygame.time.wait(20)
            else:
                idle_wait(touch)


class Axis:
    def __init__(self, low, high):
        self.min = low
        self.max = high


def check(condition, message, failures):
    if not condition:
        failures.append(message)


# Batch 7: topics split into sub-menus. Each row is
# (home id, title, own cards, first card, sub-menus, ends with search).
# A sub-menu is (label, cards, first card, last card); one card opens as a sheet.
GUIDE7_MENUS = (
    ("home:6", "Fire", 8, "Fire triangle", (
        ("Ways to light a fire", 14, "Which method?", "Pump drill"),
        ("Tinder and firewood", 7, "Birch bark", "Choosing firewood"),
        ("Fires for jobs", 8, "Dakota fire hole", "Low-smoke fire"),
        ("Keep, carry, put out", 3, "Bank a fire overnight", "Put it out properly"),
        ("Fire sources", 1, "Fire sources", "Fire sources"),
    ), False),
    ("home:0", "Shelter", 14, "Choose a site", (
        ("More wild shelters", 9, "Wickiup or tipi", "Swamp bed"),
        ("Snow shelters", 4, "Snow trench", "Igloo basics"),
        ("Buildings and cars", 4, "Choose a building", "Car as shelter"),
        ("Long-term building", 5, "Plan a long-term shelter", "Thatching basics"),
        ("Shelter sources", 1, "Shelter sources", "Shelter sources"),
    ), False),
    ("home:5", "Water", 7, "Find it and carry it", (
        ("Finding and collecting", 10, "Where to look", "Seawater: never drink it"),
        ("Making it safe", 12, "Which method?", "Clean your containers"),
        ("Water sources", 1, "Water sources", "Water sources"),
    ), True),
    ("home:8", "Food", 10, "Food", (
        ("Deadly plants", 7, "Deadly: hemlock and water dropwort", "Ragwort"),
        ("Wild greens", 9, "Nettle and cleavers", "Marsh samphire"),
        ("Fruit, nuts and seeds", 10, "Blackberry and hazelnut", "Acorns: leach first"),
        ("Seashore food", 3, "Seaweeds", "Shellfish poisoning"),
        ("Mushrooms", 5, "Why to say no", "Penny bun (cep)"),
        ("Food sources", 1, "Food sources", "Food sources"),
    ), True),
    ("home:15", "Navigation", 12, "Lost? STOP", (
        ("Without a compass", 9, "Sun and watch", "Natural signs and their limits"),
        ("Routes and conditions", 8, "Plan a route: Naismith", "Draw a map from memory"),
        ("Navigation sources", 1, "Navigation sources", "Navigation sources"),
    ), False),
)
GUIDE7_SLUGS = (
    "fire", "fire_light", "fire_fuel", "fire_build", "fire_keep",
    "shelter", "shelter_wild", "shelter_snow", "shelter_town", "shelter_long",
    "water", "water_find", "water_treat",
    "food", "food_deadly", "food_greens", "food_fruit", "food_shore", "food_fungi",
    "navigation", "nav_nocompass", "nav_route",
)
GUIDE7_PICTURES = 91


def self_test(screenshot_dir=None):
    global FONT_REGULAR, FONT_BOLD
    failures = []
    with warnings.catch_warnings(record=True) as caught:
        warnings.warn(
            "Your system is neon capable but pygame was not built with support for it. PYGAME_DETECT_AVX2",
            RuntimeWarning,
        )
    check(not caught, "neon RuntimeWarning silenced", failures)
    check(
        any(
            action == "ignore"
            and category is RuntimeWarning
            and module is not None
            and module.match("pygame.base")
            for action, _message, category, module, _lineno in warnings.filters
        ),
        "pygame RuntimeWarning filter installed",
        failures,
    )
    check(os.environ.get("PYGAME_HIDE_SUPPORT_PROMPT") == "1", "pygame support prompt hidden", failures)
    cached = Display("fb")
    cached.fb = type("CachedFrame", (), {"last": b"stale"})()
    cached.force_next()
    check(cached.fb.last is None, "forced redraw drops the cached frame", failures)

    calib = {"cx": [2.0, 3.0, 4.0], "cy": [5.0, 6.0, 7.0]}
    check(map_touch(1, 1, calib) == (9, 18), "affine calibration", failures)
    check(map_touch(1, 1, calib, mirror=True) == (9, 18), "mirror ignored when calibrated", failures)
    rounded = {"cx": [0.2, 0.0, 0.0], "cy": [0.0, 0.2, 0.0]}
    check(map_touch(3, 8, rounded) == (1, 2), "calibration rounding", failures)
    check(map_touch(5, 5, {"cx": [-1, 0, 0], "cy": [0, -1, 0]}) == (0, 0), "calibration clamp", failures)
    axis = Axis(0, 100)
    check(map_touch(0, 0, None, abs_x=axis, abs_y=axis, mirror=True) == (479, 0), "fallback mirror", failures)
    check(map_touch(100, 100, None, abs_x=axis, abs_y=axis, mirror=True) == (0, 319), "fallback mirror far corner", failures)
    check(map_touch(0, 50, None, abs_x=axis, abs_y=axis, mirror=False)[0] == 0, "fallback raw x", failures)

    import tempfile

    missing = load_calibration(os.path.join(tempfile.gettempdir(), "field-touch-no-such-cal.json"))
    check(missing is None, "missing calibration", failures)
    with tempfile.TemporaryDirectory() as tmp:
        bad = os.path.join(tmp, "bad.json")
        with open(bad, "w", encoding="utf-8") as handle:
            handle.write("{")
        check(load_calibration(bad) is None, "broken calibration", failures)
        wrong = os.path.join(tmp, "wrong.json")
        with open(wrong, "w", encoding="utf-8") as handle:
            json.dump({"swap_xy": True}, handle)
        check(load_calibration(wrong) is None, "non-affine calibration ignored", failures)
        good = os.path.join(tmp, "good.json")
        with open(good, "w", encoding="utf-8") as handle:
            json.dump({"cx": ["1", "0", "2"], "cy": [0, 1, 3], "swap_xy": True}, handle)
        loaded = load_calibration(good)
        check(loaded == {"cx": [1.0, 0.0, 2.0], "cy": [0.0, 1.0, 3.0]}, "string coefficients", failures)

    import inspect
    import re

    signature = inspect.signature(field.search)
    check(signature.parameters["timeout"].default == 60, "keyboard search timeout unchanged", failures)
    check(signature.parameters["page_size"].default is None, "keyboard page size unchanged", failures)
    guide = subprocess.run(
        [sys.executable, field.__file__],
        input=b"n\nq\n",
        capture_output=True,
        timeout=10,
        check=False,
    )
    check(guide.returncode == 0, f"keyboard guide exit {guide.returncode}", failures)
    check(b"Shelter" in guide.stdout, "keyboard guide still prints Shelter", failures)

    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    boot_pygame()
    pygame.display.set_mode((WIDTH, HEIGHT))
    saved_regular, saved_bold = FONT_REGULAR, FONT_BOLD
    try:
        bogus = os.path.join(tempfile.gettempdir(), "Terminus.psf")
        with open(bogus, "wb") as handle:
            handle.write(b"\x36\x04not-a-font")
        FONT_REGULAR = (bogus, "/no/such/DejaVuSansMono.ttf")
        FONT_BOLD = (bogus,)
        fallback = load_font(16, bold=True)
        swatch = fallback.render("Pi", True, GREEN)
        check(swatch.get_width() > 0 and swatch.get_height() > 0, "default font fallback", failures)
    finally:
        FONT_REGULAR, FONT_BOLD = saved_regular, saved_bold
    app = App(show_cave=False)
    canvas = pygame.Surface((WIDTH, HEIGHT))
    app.draw(canvas)
    labels = [widget["label"] for widget in app.widgets]
    check(labels[:9] == [item["label"] for item in home_items()][:9], "home labels", failures)
    check({"home-prev", "home-next"} <= {widget["id"] for widget in app.widgets}, "home has a second page", failures)
    paged = App(show_cave=False)
    paged.draw(canvas)
    paged.activate("home-next")
    paged.draw(canvas)
    page_two = [widget["label"] for widget in paged.widgets if widget["id"].startswith("home:")]
    check(
        page_two
        == [
            "Cooking & preserving",
            "Growing food",
            "Animals & livestock",
            "Tools and wildlife",
            "Hunting & fishing",
            "Sanitation",
            "Navigation",
            "More",
        ],
        f"home page two {page_two}",
        failures,
    )
    check("Exit" in labels and "Cave Mapper" not in labels, "exit without cavemap", failures)
    heights = [widget["rect"].height for widget in app.widgets]
    check(all(height >= 60 for height in heights), f"home button height {heights}", failures)
    check(all(0 <= widget["rect"].left and widget["rect"].right <= WIDTH and widget["rect"].bottom <= HEIGHT for widget in app.widgets), "home buttons on screen", failures)
    check(any(canvas.get_at((widget["rect"].x + 2, widget["rect"].y + 1))[1] > 40 for widget in app.widgets), "buttons visible", failures)

    cave_app = App(show_cave=True)
    cave_app.draw(canvas)
    cave_labels = [widget["label"] for widget in cave_app.widgets]
    check("Exit" in cave_labels and "Cave Mapper" not in cave_labels, "scan tab replaces the cave button", failures)
    check(all(widget["rect"].height >= 60 for widget in cave_app.widgets), "cave home button height", failures)
    scan = next(hit for hit in cave_app.tab_hits if hit["name"] == "SCAN")
    radio_tab = next(hit for hit in cave_app.tab_hits if hit["name"] == "RADIO")
    guide = next(hit for hit in cave_app.tab_hits if hit["name"] == "GUIDE")
    check(scan["enabled"] and radio_tab["enabled"] and guide["enabled"], "scan and radio are on", failures)
    check(guide["rect"].height == 36 and scan["rect"].width == radio_tab["rect"].width == guide["rect"].width, "equal 36px tabs", failures)
    check(guide["rect"].width * 3 == WIDTH, "tabs fill the width", failures)
    # y=2 misses the scanline; the active GUIDE fill is the main green.
    check(tuple(canvas.get_at((8, 2))[:3]) == GREEN, "active tab is filled green", failures)
    cave_app.tab_pressed = "GUIDE"
    cave_app.draw(canvas)
    check(tuple(canvas.get_at((8, 2))[:3]) == BLACK, "tab flash inverts the active fill", failures)
    cave_app.tab_pressed = None
    cave_app.pointer("down", *scan["rect"].center)
    cave_app.pointer("up", *scan["rect"].center)
    check(cave_app.pending == "cave", "scan tab launches cavemap", failures)
    dark = App(show_cave=False)
    dark.draw(canvas)
    dark_scan = next(hit for hit in dark.tab_hits if hit["name"] == "SCAN")
    check(not dark_scan["enabled"], "scan disabled without cavemap", failures)
    dark_radio = next(hit for hit in dark.tab_hits if hit["name"] == "RADIO")
    check(dark_radio["enabled"], "radio stays on when cavemap is missing", failures)

    app.pointer("down", *app.widgets[0]["rect"].center)
    app.pointer("up", *app.widgets[0]["rect"].center)
    check(app.current()["kind"] == "menu" and app.current()["title"] == "SHELTER", "shelter menu", failures)
    app.draw(canvas)
    menu_heights = [widget["rect"].height for widget in app.widgets if widget["id"].startswith("menu:")]
    check(menu_heights and all(height >= 60 for height in menu_heights), f"section button height {menu_heights}", failures)
    app.pointer("down", *next(widget["rect"].center for widget in app.widgets if widget["id"] == "menu:0"))
    app.pointer("up", *next(widget["rect"].center for widget in app.widgets if widget["id"] == "menu:0"))
    # The second hit uses widgets from the menu draw. After the first pointer the
    # widgets still describe the menu, so the second lookup is valid.
    check(app.current()["kind"] == "reader", "opened a sheet", failures)
    check("Look up before you look down" in app.current()["body"], "sheet text comes from the guide", failures)
    app.draw(canvas)
    nav = {widget["id"]: widget for widget in app.widgets}
    check(set(["prev", "back", "next"]).issubset(nav), "reader nav", failures)
    check(nav["prev"]["rect"].height >= 60 and not nav["prev"]["enabled"], "prev disabled on first page", failures)
    before = app.current()["page"]
    app.pointer("down", 240, 180)
    app.pointer("move", 240, 80)
    app.pointer("up", 240, 80)
    check(app.current()["page"] == before + 1, "swipe up pages forward", failures)
    check(app.slide_from == before, "swipe arms a slide from the old page", failures)
    app.slide_from = None
    app.draw(canvas)
    indicator = f"{app.current()['page'] + 1}/{app.page_count(app.current())}"
    check("/" in indicator and indicator != "1/1", f"page indicator {indicator}", failures)

    fake = type("FakeDisplay", (), {})()
    fake.canvas = canvas
    fake.presents = []

    def _present(surface, rows=None):
        fake.presents.append(rows)

    fake.present = _present
    app.slide_from = None
    frames = play_slide(app, fake, before, before + 1)
    check(frames == SLIDE_FRAMES, f"slide uses {frames} frames", failures)
    check(len(fake.presents) == SLIDE_FRAMES, "slide presents once per frame", failures)
    check(any(item is not None for item in fake.presents), "middle slide frames are dirty rows", failures)
    check(app.current()["page"] == before + 1, "slide lands on the new page", failures)

    app.stack = [{"kind": "home"}]
    app.activate("home:1")
    app.current()["query"] = "hypothermia"
    saved_host = field.HOST
    field.HOST = "http://127.0.0.1:9"
    try:
        app.run_search()
    finally:
        field.HOST = saved_host
    check(app.current()["kind"] == "search", "stays on search when library is down", failures)
    check(app.current()["status"] == LIBRARY_DOWN, "friendly library message", failures)
    app.current()["num_mode"] = True
    app.draw(canvas)
    key_labels = [widget["label"] for widget in app.widgets if widget["id"].startswith("key:")]
    check("1" in key_labels and "ABC" in key_labels and "ENTER" in key_labels, "number keyboard", failures)
    check(all(widget["rect"].height >= KEY_H for widget in app.widgets if widget["id"].startswith("key:")), "key height", failures)
    app.current()["num_mode"] = False
    app.current()["shift"] = True
    app.draw(canvas)
    letter_labels = [widget["label"] for widget in app.widgets if widget["id"].startswith("key:")]
    check(
        {"SHIFT", "BKSP", "SPACE", "ENTER", "Q"} <= set(letter_labels),
        f"letter keyboard {letter_labels}",
        failures,
    )
    space = next(widget for widget in app.widgets if widget["id"] == "key:SPACE")
    app.current()["query"] = ""
    app.current()["shift"] = False
    app.pointer("down", *space["rect"].center)
    app.pointer("up", *space["rect"].center)
    app.pointer("down", *space["rect"].center)
    app.pointer("up", *space["rect"].center)
    check(app.current()["query"] == " ", "debounced tap inserts one space", failures)
    app.last_fire = ("key:SPACE", time.monotonic() - 5)
    app.pointer("down", *space["rect"].center)
    app.pointer("up", *space["rect"].center)
    check(app.current()["query"] == "  ", "tap works again after the debounce", failures)

    food = App(show_cave=False)
    food.activate("home:8")
    food.draw(canvas)
    food_items = food.current().get("items", [])
    check(
        food.current()["kind"] == "menu" and len(food_items) == 17 and food_items[-1].get("action") == "search",
        f"food menu keeps search {[item.get('label') for item in food_items]}",
        failures,
    )
    check(food_items and food_items[0]["label"] == "Food" and food_items[0]["body"].startswith("Cook meat, fish,"), "food first card", failures)

    check(content is not None, "content loader imports", failures)
    home_titles = [topic.title for topic in field.GUIDE.home_topics()]
    check(
        home_titles
        == [
            "Shelter",
            "Medicine",
            "First aid",
            "Childbirth",
            "Mental health",
            "Water",
            "Fire",
            "Knots",
            "Food",
            "Cooking & preserving",
            "Growing food",
            "Animals & livestock",
            "Tools and wildlife",
            "Hunting & fishing",
            "Sanitation",
            "Navigation",
            "More",
        ],
        f"home menu order {home_titles}",
        failures,
    )
    check(len(field.SHELTER) == 14 and len(field.WATER) == 7 and len(field.FIRE) == 8, f"sheet counts {len(field.SHELTER)} {len(field.WATER)} {len(field.FIRE)}", failures)
    knot_main_cards = [name for name, _body in field.KNOTS_MAIN]
    check(
        knot_main_cards
        == [
            "Which knot",
            "Rope words",
            "Square knot",
            "Sheet bend",
            "Bowline",
            "Figure-eight loop",
            "Clove hitch",
            "Round turn and two half hitches",
            "Taut-line hitch",
        ],
        f"main knots {knot_main_cards}",
        failures,
    )
    check(field.KNOT_WHICH == field.KNOTS_MAIN[0][1], "which knot text", failures)
    check([name for name, _body in field.KNOTS_MORE][:1] == ["Rolling hitch"] and len(field.KNOTS_MORE) == 5, "grip and haul knots", failures)
    check("Right end over the left end" in field.KNOTS_MAIN[2][1], "square knot steps", failures)
    check(
        content.console_body("See ![ridge pole](img/ridge.png) here.") == "See [diagram: ridge pole] here.",
        "console diagram placeholder",
        failures,
    )
    check(content.console_body(field.SHELTER[0][1]) == field.SHELTER[0][1], "plain sheet is unchanged", failures)
    knots = App(show_cave=False)
    knots.activate("home:7")
    knot_items = knots.current()["items"]
    knot_labels = [item["label"] for item in knot_items]
    knot_menus = [
        ("Stoppers", 3, "Overhand knot", "Double overhand stopper"),
        ("Hitches", 10, "Two half hitches", "Munter hitch"),
        ("Grip and haul", 5, "Rolling hitch", "Trucker's hitch"),
        ("Loops", 7, "Figure-eight follow-through", "Slip knot"),
        ("Bends and joins", 6, "Double sheet bend", "Water knot"),
        ("Fishing and snare knots", 5, "Improved clinch knot", "Snare noose"),
        ("Lashings", 7, "Start and finish lashings", "Floor lashing"),
        ("Rope care", 6, "Rope care and strength", "Tie a ridge line"),
    ]
    check(
        knot_labels[:9] == knot_main_cards and knot_labels[9:] == [menu[0] for menu in knot_menus],
        f"knots menu {knot_labels}",
        failures,
    )
    which_text = field.KNOT_WHICH.lower()
    knot_pictures = []
    for label, count, first, last in knot_menus:
        item = next((entry for entry in knot_items if entry["label"] == label), {})
        labels = [entry["label"] for entry in item.get("items", [])]
        check(
            item.get("action") == "menu" and len(labels) == count and labels[0] == first and labels[-1] == last,
            f"knots {label} menu {labels}",
            failures,
        )
        for entry in item.get("items", []):
            check(entry["label"].lower() in which_text, f"which knot lists {entry['label']}", failures)
            found = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", entry.get("body", ""))
            if entry["label"] != "Rope care and strength":
                check(bool(found), f"knot card has a diagram: {entry['label']}", failures)
            knot_pictures.extend(found)
    for name, body in field.KNOTS_MAIN[2:]:
        check(name.lower() in which_text, f"which knot lists {name}", failures)
        found = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", body)
        check(bool(found), f"knot card has a diagram: {name}", failures)
        knot_pictures.extend(found)
    knot_missing = [rel for rel in knot_pictures if content.resolve_image(field.GUIDE.directory, rel) is None]
    check(not knot_missing, f"knot diagrams exist {knot_missing}", failures)
    knot_sizes = {
        pygame.image.load(str(content.resolve_image(field.GUIDE.directory, rel))).get_size()
        for rel in set(knot_pictures)
        if rel not in knot_missing
    }
    check(knot_sizes <= {(480, 284)}, f"knot diagrams are 480x284 {knot_sizes}", failures)
    more = App(show_cave=False)
    more.activate("home:16")
    more_labels = [item["label"] for item in more.current()["items"]]
    check(
        more_labels
        == [
            "Signals & Radio",
            "Clothing",
            "Weather",
            "Power",
            "Repairs & making",
            "Emergency plan",
            "Offline library",
            "Places",
            "Search all archives",
        ],
        f"more menu {more_labels}",
        failures,
    )
    signals_item = more.current()["items"][0]
    signals_labels = [item["label"] for item in signals_item.get("items", [])]
    signals_expected = [
        "Rule of Three and SOS",
        "UK Emergency Numbers",
        "Sound",
        "Light",
        "Mirrors",
        "Fire and smoke",
        "Ground-to-air",
        "Body signals",
        "Flags and cloth",
        "Trail markers",
        "Codes",
        "Radio procedure",
        "PMR446",
        "Comms plan",
        "Antennas",
        "Radio power",
        "News and info",
        "On this deck",
        "Mesh text",
        "Sources",
    ]
    check(
        signals_item.get("action") == "menu" and signals_labels == signals_expected,
        f"signals menu {signals_labels}",
        failures,
    )
    check(signals_item["items"][-1].get("action") == "sheet", "sources opens as a sheet", failures)
    signal_counts = {
        "signals": 2,
        "signals_sound": 6,
        "signals_light": 4,
        "signals_mirrors": 3,
        "signals_fire": 5,
        "signals_ground": 4,
        "signals_body": 3,
        "signals_flags": 4,
        "signals_trail": 5,
        "signals_codes": 6,
        "signals_radio": 8,
        "signals_pmr": 4,
        "signals_plan": 5,
        "signals_antennas": 5,
        "signals_power": 3,
        "signals_news": 4,
        "signals_deck": 3,
        "signals_mesh": 3,
        "signals_sources": 1,
    }
    for slug, count in signal_counts.items():
        got = len(field.GUIDE.cards(slug))
        check(got == count, f"{slug} cards {got}", failures)
    kept = {
        "Rule of Three and SOS",
        "Whistle and Torch Signals",
        "Signal Mirror",
        "Ground-to-Air Signals",
        "Smoke and Fire Signals",
        "Group Signal Plan",
        "Morse Code Table",
        "UK Emergency Numbers",
        "Broadcast Radio for News",
        "PMR446 Walkie-Talkies",
        "Marine VHF Channel 16",
        "Mayday and Pan-Pan",
        "Amateur Radio Notes",
        "RTL-SDR: What You Can Listen To",
        "Sources",
    }
    found_heads = set()
    signal_pics = []
    for slug in signal_counts:
        for name, body in field.GUIDE.cards(slug):
            found_heads.add(name)
            signal_pics.extend(re.findall(r"!\[[^\]]*\]\(([^)]+)\)", body))
    check(kept <= found_heads, f"original signals cards missing {kept - found_heads}", failures)
    check(len(signal_pics) == 36, f"signals diagrams {len(signal_pics)}", failures)
    signal_missing = [rel for rel in signal_pics if content.resolve_image(field.GUIDE.directory, rel) is None]
    check(not signal_missing, f"signals diagrams exist {signal_missing}", failures)
    signal_sizes = {
        pygame.image.load(str(content.resolve_image(field.GUIDE.directory, rel))).get_size()
        for rel in signal_pics
        if rel not in signal_missing
    }
    check(signal_sizes <= {(480, 284)}, f"signals diagrams are 480x284 {signal_sizes}", failures)
    weather_item = more.current()["items"][2]
    weather_labels = [item["label"] for item in weather_item.get("items", [])]
    check(
        weather_item.get("action") == "menu" and len(weather_labels) == 16 and weather_labels[0] == "Read the sky",
        f"weather menu {weather_labels}",
        failures,
    )
    clothing_labels = [item["label"] for item in more.current()["items"][1].get("items", [])]
    check(len(clothing_labels) == 16 and clothing_labels[0] == "Layers", f"clothing menu {clothing_labels}", failures)
    sanitation = App(show_cave=False)
    sanitation.activate("home:14")
    san_items = sanitation.current().get("items", [])
    check(
        sanitation.current()["kind"] == "menu"
        and len(san_items) == 21
        and san_items[1]["label"] == "Cat hole"
        and san_items[-1].get("action") == "search",
        f"sanitation menu keeps search {[item.get('label') for item in san_items]}",
        failures,
    )
    navigation = App(show_cave=False)
    navigation.activate("home:15")
    nav_labels = [item["label"] for item in navigation.current().get("items", [])]
    check(
        len(nav_labels) == 15 and nav_labels[0] == "Lost? STOP" and nav_labels[-1] == "Navigation sources",
        f"navigation menu {nav_labels}",
        failures,
    )
    guide5_pictures = []
    for home_id, label, count, first, last in (
        ("home:3", "Childbirth", 14, "Signs of labour", "Childbirth sources"),
        ("home:4", "Mental health", 14, "Stress is normal", "Mental health sources"),
        ("home:10", "Growing food", 14, "Fast crops", "Growing sources"),
    ):
        topic_app = App(show_cave=False)
        topic_app.activate(home_id)
        topic_labels = [item["label"] for item in topic_app.current().get("items", [])]
        check(
            topic_app.current()["kind"] == "menu"
            and topic_app.current()["title"] == label.upper()
            and len(topic_labels) == count
            and topic_labels[0] == first
            and topic_labels[-1] == last,
            f"{label} menu {topic_labels}",
            failures,
        )
    for slug in ("childbirth", "mentalhealth", "growing"):
        for _name, body in field.GUIDE.cards(slug):
            guide5_pictures.extend(re.findall(r"!\[[^\]]*\]\(([^)]+)\)", body))
    check(len(guide5_pictures) == 14, f"childbirth, mental health and growing diagrams {len(guide5_pictures)}", failures)
    guide5_missing = [rel for rel in guide5_pictures if content.resolve_image(field.GUIDE.directory, rel) is None]
    check(not guide5_missing, f"childbirth, mental health and growing diagrams exist {guide5_missing}", failures)
    guide5_sizes = {
        pygame.image.load(str(content.resolve_image(field.GUIDE.directory, rel))).get_size()
        for rel in guide5_pictures
        if rel not in guide5_missing
    }
    check(guide5_sizes <= {(480, 284)}, f"childbirth, mental health and growing diagrams are 480x284 {guide5_sizes}", failures)
    new_menus = {}
    for index, (label, count, first, last) in (
        (3, ("Power", 15, "Volts, amps, watts", "Power sources")),
        (5, ("Emergency plan", 17, "Make a plan", "Emergency sources")),
        (6, ("Offline library", 7, "What Kiwix is", "Library sources")),
    ):
        item = more.current()["items"][index]
        labels = [entry["label"] for entry in item.get("items", [])]
        new_menus[label] = item
        check(
            item.get("action") == "menu" and len(labels) == count and labels[0] == first and labels[-1] == last,
            f"{label} menu {labels}",
            failures,
        )
    guide4_pictures = []
    for slug in ("power", "emergency", "library"):
        for _name, body in field.GUIDE.cards(slug):
            guide4_pictures.extend(re.findall(r"!\[[^\]]*\]\(([^)]+)\)", body))
    check(len(guide4_pictures) == 17, f"power and emergency diagrams {len(guide4_pictures)}", failures)
    guide4_missing = [rel for rel in guide4_pictures if content.resolve_image(field.GUIDE.directory, rel) is None]
    check(not guide4_missing, f"power and emergency diagrams exist {guide4_missing}", failures)
    guide4_sizes = {
        pygame.image.load(str(content.resolve_image(field.GUIDE.directory, rel))).get_size()
        for rel in guide4_pictures
        if rel not in guide4_missing
    }
    check(guide4_sizes <= {(480, 284)}, f"power and emergency diagrams are 480x284 {guide4_sizes}", failures)
    content_dir = field.GUIDE.directory
    pictures = []
    for slug in ("navigation", "sanitation", "clothing", "weather"):
        for _name, body in field.GUIDE.cards(slug):
            pictures.extend(re.findall(r"!\[[^\]]*\]\(([^)]+)\)", body))
    check(len(pictures) == 29, f"new topic diagrams {len(pictures)}", failures)
    missing = [rel for rel in pictures if content.resolve_image(content_dir, rel) is None]
    check(not missing, f"new topic diagrams exist {missing}", failures)
    sizes = {pygame.image.load(str(content.resolve_image(content_dir, rel))).get_size() for rel in pictures if rel not in missing}
    check(sizes <= {(480, 284)}, f"new topic diagrams are 480x284 {sizes}", failures)
    for home_id, label, count, first, last in (
        ("home:2", "First aid", 53, "Scene safety and DRABC", "Sources"),
        ("home:9", "Cooking & preserving", 17, "Flatbread", "Cooking sources"),
        ("home:11", "Animals & livestock", 13, "Before you start (UK rules)", "Animals sources"),
        ("home:13", "Hunting & fishing", 13, "The law first (UK)", "Hunting & fishing sources"),
    ):
        topic_app = App(show_cave=False)
        topic_app.activate(home_id)
        topic_labels = [item["label"] for item in topic_app.current().get("items", [])]
        check(
            topic_app.current()["kind"] == "menu"
            and topic_app.current()["title"] == label.upper()
            and len(topic_labels) == count
            and topic_labels[0] == first
            and topic_labels[-1] == last,
            f"{label} menu {topic_labels}",
            failures,
        )
    repairs_item = more.current()["items"][4]
    repairs_labels = [entry["label"] for entry in repairs_item.get("items", [])]
    check(
        repairs_item.get("action") == "menu"
        and len(repairs_labels) == 14
        and repairs_labels[0] == "Tools to keep"
        and repairs_labels[-1] == "Repairs sources",
        f"repairs menu {repairs_labels}",
        failures,
    )
    guide6_pictures = []
    for slug in ("firstaid", "cooking", "animals", "hunting", "repairs"):
        for _name, body in field.GUIDE.cards(slug):
            guide6_pictures.extend(re.findall(r"!\[[^\]]*\]\(([^)]+)\)", body))
    check(len(guide6_pictures) == 32, f"first aid, cooking, animals, hunting and repairs diagrams {len(guide6_pictures)}", failures)
    guide6_missing = [rel for rel in guide6_pictures if content.resolve_image(content_dir, rel) is None]
    check(not guide6_missing, f"batch 6 diagrams exist {guide6_missing}", failures)
    guide6_sizes = {
        pygame.image.load(str(content.resolve_image(content_dir, rel))).get_size()
        for rel in guide6_pictures
        if rel not in guide6_missing
    }
    check(guide6_sizes <= {(480, 284)}, f"batch 6 diagrams are 480x284 {guide6_sizes}", failures)

    for home_id, label, own, first, subs, searched in GUIDE7_MENUS:
        topic_app = App(show_cave=False)
        topic_app.activate(home_id)
        items = topic_app.current().get("items", [])
        labels = [item["label"] for item in items]
        want = own + len(subs) + (1 if searched else 0)
        check(
            topic_app.current()["kind"] == "menu"
            and topic_app.current()["title"] == label.upper()
            and len(items) == want
            and labels[0] == first
            and labels[own:own + len(subs)] == [sub[0] for sub in subs]
            and (not searched or items[-1].get("action") == "search"),
            f"{label} menu {labels}",
            failures,
        )
        for offset, (sub_label, count, sub_first, sub_last) in enumerate(subs):
            item = items[own + offset] if own + offset < len(items) else {}
            if count == 1:
                check(item.get("action") == "sheet" and item.get("label") == sub_label, f"{label}/{sub_label} sheet", failures)
                continue
            sub_labels = [entry["label"] for entry in item.get("items", [])]
            check(
                item.get("action") == "menu"
                and len(sub_labels) == count
                and sub_labels[:1] == [sub_first]
                and sub_labels[-1:] == [sub_last],
                f"{label}/{sub_label} menu {sub_labels}",
                failures,
            )
        # Walk into the first sub-menu, open its first card, and come back out.
        walker = App(show_cave=False)
        walker.activate(home_id)
        walker.activate(f"menu:{own}")
        check(walker.current()["kind"] == "menu" and walker.current()["title"] == subs[0][0].upper(), f"{label} opens {subs[0][0]}", failures)
        walker.activate("menu:0")
        check(walker.current()["kind"] == "reader" and walker.current()["title"] == subs[0][2].upper(), f"{label} sub-menu card opens", failures)
        walker.back()
        walker.back()
        check(walker.current()["kind"] == "menu" and walker.current()["title"] == label.upper(), f"{label} back from sub-menu", failures)
    guide7_pictures = []
    for slug in GUIDE7_SLUGS:
        for _name, body in field.GUIDE.cards(slug):
            guide7_pictures.extend(re.findall(r"!\[[^\]]*\]\(([^)]+)\)", body))
    check(len(guide7_pictures) == GUIDE7_PICTURES, f"batch 7 diagrams {len(guide7_pictures)}", failures)
    guide7_missing = [rel for rel in guide7_pictures if content.resolve_image(content_dir, rel) is None]
    check(not guide7_missing, f"batch 7 diagrams exist {guide7_missing}", failures)
    guide7_sizes = {
        pygame.image.load(str(content.resolve_image(content_dir, rel))).get_size()
        for rel in guide7_pictures
        if rel not in guide7_missing
    }
    check(guide7_sizes <= {(480, 284)}, f"batch 7 diagrams are 480x284 {guide7_sizes}", failures)

    with tempfile.TemporaryDirectory() as tmp:
        img_dir = os.path.join(tmp, "img")
        os.makedirs(img_dir)
        picture = pygame.Surface((80, 40))
        picture.fill((255, 255, 255))
        pygame.image.save(picture, os.path.join(img_dir, "ridge.png"))
        pages = layout_pages(
            "Before the picture.\n\n![ridge pole](img/ridge.png)\n\nAfter it.",
            app.font_body,
            app.font_small,
            app.content_width(),
            app.reader_page_px(),
            tmp,
            True,
        )
        images = [block for page in pages for block in page if block["kind"] == "image"]
        check(len(images) == 1, "image lays out on a card", failures)
        if images:
            pixel = images[0]["image"].get_at((4, 4))
            check(pixel.g > pixel.r and pixel.g > 100, f"image is green tinted {tuple(pixel)}", failures)
            shown = App(show_cave=False)
            shown.stack.append(
                {
                    "kind": "reader",
                    "title": "RIDGE",
                    "body": "![ridge pole](img/ridge.png)",
                    "page": 0,
                    "tint": True,
                    "_image_dir": tmp,
                }
            )
            shown.draw(canvas)
            hits = 0
            for sample_y in range(36, 140):
                pixel = canvas.get_at((WIDTH // 2, sample_y))
                if pixel.g > 150:
                    hits += 1
            check(hits > 15, f"image is drawn on the card ({hits} green rows)", failures)
            hint_image = images[0]["image"]
            center = hint_image.get_at((4, 4))
            corner = hint_image.get_at((hint_image.get_width() - 2, hint_image.get_height() - 2))
            check(
                abs(corner.g - center.g) < 20 and abs(corner.r - center.r) < 20,
                f"hint is not painted on the picture {tuple(corner)} vs {tuple(center)}",
                failures,
            )
            zoom_widgets = [widget for widget in shown.widgets if widget["id"].startswith("zoom:")]
            check(len(zoom_widgets) == 1 and zoom_widgets[0]["id"] == "zoom:0", "inline image is tappable", failures)
            rect = zoom_widgets[0]["rect"]
            check(
                (rect.width, rect.height) == hint_image.get_size(),
                f"tap target is the whole image {rect.size}",
                failures,
            )
            picture_corner = canvas.get_at((rect.right - 2, rect.top + 1))
            check(picture_corner.g > 150, f"badge stays off the picture {tuple(picture_corner)}", failures)
            badge_w, badge_h = enlarge_badge_size(shown.font_small)
            badge_box = pygame.Rect(rect.right - badge_w, rect.top - badge_h, badge_w, badge_h)
            check(badge_h > 0 and not badge_box.colliderect(rect), "badge strip is outside the picture", failures)
            badge_green = 0
            for py in range(badge_box.top, badge_box.bottom):
                for px in range(badge_box.left, badge_box.right):
                    pixel = canvas.get_at((px, py))
                    if pixel.g > 140 and pixel.g > pixel.r + 40:
                        badge_green += 1
            check(badge_green > 8, f"enlarge badge ({badge_green} px)", failures)
            check(shown.hit(rect.right - 2, rect.top + 2) == "zoom:0", "top-right of the picture is tappable", failures)
            check(shown.hit(rect.left + 1, rect.bottom - 2) == "zoom:0", "bottom of the picture is tappable", failures)
            page_at = shown.current().get("page", 0)
            title_at = shown.current().get("title")
            depth = len(shown.stack)
            shown.pointer("down", *zoom_widgets[0]["rect"].center)
            shown.pointer("up", *zoom_widgets[0]["rect"].center)
            check(shown.current()["kind"] == "diagram", "tap opens the diagram", failures)
            check(len(shown.stack) == depth + 1, "diagram stays on this card", failures)
            shown.draw(canvas)
            check(shown.tab_hits == [], "diagram hides the tab bar", failures)
            check(tuple(canvas.get_at((8, 2))[:3]) == BLACK, "diagram does not fill the tab", failures)
            frame = shown.current()["frames"][0]
            check(
                frame.get_width() <= WIDTH and frame.get_height() <= HEIGHT,
                f"diagram fits {frame.get_size()}",
                failures,
            )
            check(
                frame.get_width() == WIDTH or frame.get_height() == HEIGHT,
                f"diagram uses the panel {frame.get_size()}",
                failures,
            )
            full = frame.get_at((frame.get_width() // 2, frame.get_height() // 2))
            check(full.g > full.r and full.g > 100, f"full screen stays green {tuple(full)}", failures)
            check(
                not any(widget["id"] in ("diagram-prev", "diagram-next") for widget in shown.widgets),
                "one picture has no arrows",
                failures,
            )
            closer = next(widget for widget in shown.widgets if widget["id"] == "diagram-close")
            shown.pointer("down", *closer["rect"].center)
            shown.pointer("up", *closer["rect"].center)
            check(shown.current()["kind"] == "reader" and shown.current().get("title") == title_at, "X closes to the card", failures)
            check(shown.current().get("page") == page_at, "close keeps the page", failures)
            shown.draw(canvas)
            again = next(widget for widget in shown.widgets if widget["id"] == "zoom:0")
            shown.pointer("down", *again["rect"].center)
            shown.pointer("up", *again["rect"].center)
            shown.pointer("down", WIDTH // 2, HEIGHT // 2)
            shown.pointer("up", WIDTH // 2, HEIGHT // 2)
            check(shown.current()["kind"] == "reader", "tap anywhere closes the diagram", failures)

            one = pygame.Surface((40, 20))
            one.fill((255, 255, 255))
            pygame.image.save(one, os.path.join(img_dir, "one.png"))
            two = pygame.Surface((80, 80))
            two.fill((255, 255, 255))
            pygame.draw.rect(two, (0, 0, 0), (0, 0, 80, 20))
            pygame.image.save(two, os.path.join(img_dir, "two.png"))
            multi = App(show_cave=False)
            multi.stack.append(
                {
                    "kind": "reader",
                    "title": "TWO",
                    "body": "![first](img/one.png)\n\n![second](img/two.png)",
                    "page": 0,
                    "tint": True,
                    "_image_dir": tmp,
                }
            )
            multi.draw(canvas)
            first = next(widget for widget in multi.widgets if widget["id"] == "zoom:0")
            multi.pointer("down", *first["rect"].center)
            multi.pointer("up", *first["rect"].center)
            check(multi.current()["kind"] == "diagram" and multi.current()["index"] == 0, "opens the first of two", failures)
            check(len(multi.current()["frames"]) == 2, "both pictures are in the diagram", failures)
            multi.draw(canvas)
            check(
                {"diagram-prev", "diagram-next", "diagram-close"} <= {widget["id"] for widget in multi.widgets},
                "arrows and close on a multi-picture card",
                failures,
            )
            marks = 0
            for py in range(HEIGHT - 30, HEIGHT - 6):
                for px in range(WIDTH // 2 - 24, WIDTH // 2 + 24):
                    if canvas.get_at((px, py)).g > 120:
                        marks += 1
            check(marks > 4, f"n/m indicator ({marks} px)", failures)
            multi.activate("diagram-next")
            check(multi.current()["index"] == 1, "next arrow steps", failures)
            multi.activate("diagram-next")
            check(multi.current()["index"] == 1, "next stops on the last picture", failures)
            multi.pointer("down", 80, 150)
            multi.pointer("move", 360, 150)
            multi.pointer("up", 360, 150)
            check(multi.current()["index"] == 0, "swipe right steps back", failures)
            multi.pointer("down", 360, 150)
            multi.pointer("move", 80, 155)
            multi.pointer("up", 80, 155)
            check(multi.current()["index"] == 1, "swipe left steps forward", failures)
            multi_page = multi.stack[-2].get("page", 0)
            multi.pointer("down", *next(widget["rect"].center for widget in multi.widgets if widget["id"] == "diagram-close"))
            # widgets were from the last draw, which is still the diagram
            multi.pointer("up", *next(widget["rect"].center for widget in multi.widgets if widget["id"] == "diagram-close"))
            check(multi.current()["kind"] == "reader" and multi.current().get("page") == multi_page, "close keeps the multi card", failures)

            red = pygame.Surface((40, 40))
            red.fill((200, 0, 0))
            pygame.image.save(red, os.path.join(img_dir, "red.png"))
            plain = App(show_cave=False)
            plain.stack.append(
                {
                    "kind": "reader",
                    "title": "PLAIN",
                    "body": "![red swatch](img/red.png)",
                    "page": 0,
                    "tint": False,
                    "_image_dir": tmp,
                }
            )
            plain.draw(canvas)
            plain.pointer("down", *next(widget["rect"].center for widget in plain.widgets if widget["id"] == "zoom:0"))
            plain.pointer("up", *next(widget["rect"].center for widget in plain.widgets if widget["id"] == "zoom:0"))
            bare = plain.current()["frames"][0]
            sample = bare.get_at((bare.get_width() // 2, bare.get_height() // 2))
            check(sample.r > 150 and sample.r > sample.g, f"tint false keeps the picture colors {tuple(sample)}", failures)
            plain.back()
            check(plain.current()["kind"] == "reader", "back leaves the untinted card", failures)
        missing_pages = layout_pages(
            "![ridge pole](img/missing.png)",
            app.font_body,
            app.font_small,
            app.content_width(),
            app.reader_page_px(),
            tmp,
            True,
        )
        check(missing_pages[0][0]["text"] == "[diagram: ridge pole]", "missing image uses the placeholder", failures)
        check(content.resolve_image(tmp, "../secret.png") is None, "image path stays in content", failures)
        with open(os.path.join(tmp, "medicine.md"), "w", encoding="utf-8") as handle:
            handle.write(
                "---\ntitle: Medicine\norder: 1\nbook: "
                + field.MED
                + "\n---\n\n## Bleeding\n\nPress on it.\n\n## Burn\n\nCool it.\n"
            )
        loaded = content.load_guide(tmp)
        saved_guide = field.GUIDE
        field.GUIDE = loaded
        try:
            item = topic_to_item(loaded.home_topics()[0])
            labels = [entry["label"] for entry in item["items"]]
            check(
                item["action"] == "menu" and labels == ["Bleeding", "Burn", "Search the archive"],
                f"medicine cards plus search {labels}",
                failures,
            )
            check(item["items"][-1].get("book") == field.MED, "medicine search archive", failures)
        finally:
            field.GUIDE = saved_guide
        empty = content.load_guide(os.path.join(tmp, "absent"))
        check(empty.home_topics() == [] and empty.directory is None, "missing content dir", failures)
        field.GUIDE = empty
        try:
            labels = [item["label"] for item in home_items()]
            check(labels == ["Medicine", "Search all archives"], f"fallback home {labels}", failures)
            fallback = App(show_cave=False)
            fallback.draw(canvas)
            drawn = [widget["label"] for widget in fallback.widgets]
            check(drawn[0] == "Medicine" and "Exit" in drawn, f"fallback screen {drawn}", failures)
        finally:
            field.GUIDE = saved_guide

    listed = App(show_cave=False)
    listed.stack.append(
        {
            "kind": "results",
            "title": "RESULTS",
            "intro": "2 entries",
            "query": "burn",
            "book": field.MED,
            "results": [
                ("Burn", "/content/burn", "A burn is tissue damage from heat."),
                ("Scald", "/content/scald", "Hot liquid on skin."),
            ],
            "total": 2,
            "page": 0,
            "status": "",
        }
    )
    listed.draw(canvas)
    result_ids = [widget["id"] for widget in listed.widgets]
    check(result_ids.count("result:0") == 1 and "result:1" in result_ids, "results are tappable", failures)

    index = card_index()
    check(index is field.GUIDE.index, "search index is the one built at load", failures)
    check(len(index) > 50, f"index has the cards {len(index)}", failures)
    counted = 0
    topics = field.GUIDE.topics
    for topic in topics.values():
        if topic.merge and topic.parent in topics:
            continue
        counted += len(field.GUIDE.cards(topic.slug))
    check(len(index) == counted, f"index lists each card once ({len(index)} vs {counted})", failures)
    folded = [entry.title_fold for entry in index]
    check(folded == sorted(folded), "index is alphabetical", failures)
    which = [entry for entry in index if entry.title == "Which knot"]
    check(len(which) == 1 and which[0].topic_slug == "knots_main" and which[0].topic_title == "Knots", "merged card is listed once under Knots", failures)
    check(all(entry.topic_slug != "knot_which" for entry in index), "merged file is not its own topic", failures)
    bowline = content.search_cards(index, "BOWLINE")
    check(bowline and bowline[0].title == "Bowline" and bowline[0].topic_title == "Knots", f"title match is case-insensitive { [e.title for e in bowline[:3]] }", failures)
    check(bowline[0] is next(entry for entry in index if entry.title == "Bowline"), "search reuses the startup index", failures)
    heat = content.search_cards(index, "heat")
    seen_body = False
    heat_order_ok = True
    for entry in heat:
        in_title = "heat" in entry.title_fold
        if not in_title:
            seen_body = True
        elif seen_body:
            heat_order_ok = False
    check(heat and heat_order_ok and "heat" in heat[0].title_fold, "title matches come before body matches", failures)
    check(content.search_cards(index, "   ") == [], "blank query matches nothing", failures)
    nested_slugs = {slug for slug in signal_counts if slug != "signals"}
    nested_cards = [entry for entry in index if entry.topic_slug in nested_slugs]
    check(
        len(nested_cards) == sum(signal_counts[slug] for slug in nested_slugs),
        f"nested signals cards are indexed {len(nested_cards)}",
        failures,
    )
    whistle = next((entry for entry in index if entry.title == "Whistle and Torch Signals"), None)
    check(
        whistle is not None
        and whistle.topic_slug == "signals_sound"
        and whistle.topic_title == "Sound"
        and "pea whistle" in whistle.body,
        "whistle card is indexed under Sound",
        failures,
    )
    whistle_hits = content.search_cards(index, "whistle")
    check(
        whistle_hits
        and whistle_hits[0].title == "Whistle and Torch Signals"
        and whistle_hits[0].topic_title == "Sound",
        f"search finds the nested whistle card {[entry.title for entry in whistle_hits[:3]]}",
        failures,
    )
    by_topic = {}
    for entry in index:
        by_topic.setdefault(entry.topic_slug, []).append(entry.title)
    for topic in field.GUIDE.topics.values():
        if not topic.parent or (topic.merge and topic.parent in topics):
            continue
        titles = [name for name, _body in field.GUIDE.cards(topic.slug)]
        got = by_topic.get(topic.slug, [])
        check(
            sorted(got) == sorted(titles) and len(got) == len(titles),
            f"sub-menu {topic.slug} cards missing from the index",
            failures,
        )
    drill = next((entry for entry in index if entry.title == "Hand drill"), None)
    check(
        drill is not None
        and drill.topic_slug == "fire_light"
        and drill.topic_title == "Ways to light a fire"
        and "friction fire" in drill.body,
        "hand drill is indexed under its fire sub-menu",
        failures,
    )
    started = time.perf_counter()
    rebuilt = content.build_card_index(field.GUIDE)
    index_s = time.perf_counter() - started
    check(index_s < 0.5 and len(rebuilt) == len(index), f"index rebuild {index_s:.3f}s for {len(index)} cards", failures)
    started = time.perf_counter()
    content.search_cards(index, "shelter")
    search_s = time.perf_counter() - started
    check(search_s < 0.1, f"search scan {search_s:.3f}s", failures)

    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "camp.md"), "w", encoding="utf-8") as handle:
            handle.write(
                "---\ntitle: Camp\n---\n\n"
                "## Boil water\n\nRolling boil.\n\n"
                "## Camp stove\n\nBoil water on the stove if you can.\n\n"
                "## Shelter\n\nA boil is not a shelter.\n"
            )
        with open(os.path.join(tmp, "stove.md"), "w", encoding="utf-8") as handle:
            handle.write("---\ntitle: Stove\nparent: camp\n---\n\n## Wick\n\nTrim the wick.\n")
        sample = content.load_guide(tmp)
        wick = [entry for entry in sample.index if entry.title == "Wick"]
        check(
            len(wick) == 1 and wick[0].topic_slug == "stove" and wick[0].topic_title == "Stove",
            "nested topic cards stay in the index",
            failures,
        )
        ranked = content.search_cards(sample.index, "boil")
        check(
            [entry.title for entry in ranked] == ["Boil water", "Camp stove", "Shelter"],
            f"sample search order {[entry.title for entry in ranked]}",
            failures,
        )
        check(all(entry.topic_title == "Camp" for entry in ranked), "sample results carry the topic", failures)
        both = content.search_cards(sample.index, "water stove")
        check([entry.title for entry in both] == ["Camp stove"], f"every word must match { [entry.title for entry in both] }", failures)
        check(content.search_cards(sample.index, "BOIL")[0].title == "Boil water", "sample search ignores case", failures)

    guide_home = App(show_cave=False)
    guide_home.draw(canvas)
    search_btn = next(widget for widget in guide_home.widgets if widget["id"] == "guide-search")
    index_btn = next(widget for widget in guide_home.widgets if widget["id"] == "guide-index")
    check(search_btn["rect"].height >= 60 and index_btn["rect"].height >= 60, "home search and A-Z are finger sized", failures)
    check(search_btn["rect"].bottom <= HEIGHT and index_btn["rect"].right <= WIDTH, "home search and A-Z stay on screen", failures)
    guide_home.pointer("down", *search_btn["rect"].center)
    guide_home.pointer("up", *search_btn["rect"].center)
    check(guide_home.current()["kind"] == "find", "search opens from GUIDE home", failures)
    guide_home.draw(canvas)
    for char in "bowline":
        key = next(widget for widget in guide_home.widgets if widget["id"] == f"key:{char}")
        check(key["rect"].height >= 48 and key["rect"].width >= 36, f"key {char} size {key['rect'].size}", failures)
        guide_home.pointer("down", *key["rect"].center)
        guide_home.pointer("up", *key["rect"].center)
    check(guide_home.current()["query"] == "bowline", f"typed query {guide_home.current().get('query')}", failures)
    guide_home.draw(canvas)
    hit_rows = [widget for widget in guide_home.widgets if widget["id"].startswith("hit:")]
    check(hit_rows and hit_rows[0]["label"] == "Bowline", f"live results { [widget['label'] for widget in hit_rows] }", failures)
    key_ids = {widget["id"] for widget in guide_home.widgets if widget["id"].startswith("key:")}
    check({"key:BKSP", "key:CLEAR", "key:SPACE"} <= key_ids, f"backspace clear space {key_ids}", failures)
    check(
        all(widget["rect"].height >= 48 and widget["rect"].width >= 36 for widget in guide_home.widgets if widget["id"].startswith("key:")),
        "every search key is finger sized",
        failures,
    )
    check(
        all(0 <= widget["rect"].left and widget["rect"].right <= WIDTH and widget["rect"].bottom <= HEIGHT for widget in guide_home.widgets),
        "search screen stays inside 480x320",
        failures,
    )
    guide_home.pointer("down", *hit_rows[0]["rect"].center)
    guide_home.pointer("up", *hit_rows[0]["rect"].center)
    check(guide_home.current()["kind"] == "reader" and guide_home.current()["title"] == "BOWLINE", "result opens the card", failures)
    check("fixed loop" in guide_home.current()["body"], "opened card is the bowline sheet", failures)
    check("![bowline" in guide_home.current()["body"], "opened card keeps its diagram", failures)
    found_badge = False
    for number in range(guide_home.page_count(guide_home.current())):
        guide_home.current()["page"] = number
        guide_home.slide_from = None
        guide_home.draw(canvas)
        if any(widget["id"].startswith("zoom:") for widget in guide_home.widgets):
            found_badge = True
            break
    check(found_badge, "enlarge badge still shows on a card opened from search", failures)
    guide_home.activate("back")
    check(guide_home.current()["kind"] == "find" and guide_home.current()["query"] == "bowline", "back returns to the results", failures)
    guide_home.draw(canvas)
    clear = next(widget for widget in guide_home.widgets if widget["id"] == "key:CLEAR")
    guide_home.pointer("down", *clear["rect"].center)
    guide_home.pointer("up", *clear["rect"].center)
    check(guide_home.current()["query"] == "", "clear empties the query", failures)
    guide_home.on_find_token("b")
    guide_home.on_find_token("BKSP")
    check(guide_home.current()["query"] == "", "backspace deletes", failures)
    guide_home.on_find_token("SPACE")
    guide_home.on_find_token("a")
    check(guide_home.current()["query"] == " a", "space key inserts a space", failures)

    nested = App(show_cave=False)
    nested.activate("guide-search")
    nested.current()["query"] = "whistle"
    nested.draw(canvas)
    whistle_row = next(widget for widget in nested.widgets if widget["label"] == "Whistle and Torch Signals")
    nested.pointer("down", *whistle_row["rect"].center)
    nested.pointer("up", *whistle_row["rect"].center)
    check(
        nested.current()["kind"] == "reader" and nested.current()["title"] == "WHISTLE AND TORCH SIGNALS",
        "nested search result opens the card",
        failures,
    )
    check("pea whistle" in nested.current()["body"] and "signals-whistle.png" in nested.current()["body"], "nested card keeps its text and diagram", failures)
    nested_badge = False
    for number in range(nested.page_count(nested.current())):
        nested.current()["page"] = number
        nested.slide_from = None
        nested.draw(canvas)
        if any(widget["id"].startswith("zoom:") for widget in nested.widgets):
            nested_badge = True
            break
    check(nested_badge, "nested card still shows the enlarge badge", failures)
    nested.activate("back")
    check(nested.current()["kind"] == "find" and nested.current()["query"] == "whistle", "back returns to the nested search", failures)
    whistle_at = next(i for i, entry in enumerate(card_index()) if entry.title == "Whistle and Torch Signals")
    nested_index = App(show_cave=False)
    nested_index.activate("guide-index")
    nested_index.current()["page"] = whistle_at
    nested_index.draw(canvas)
    index_row = next(widget for widget in nested_index.widgets if widget["id"] == f"index:{whistle_at}")
    check(index_row["label"] == "Whistle and Torch Signals", "A-Z lists the nested whistle card", failures)
    nested_index.pointer("down", *index_row["rect"].center)
    nested_index.pointer("up", *index_row["rect"].center)
    check(nested_index.current()["kind"] == "reader" and "pea whistle" in nested_index.current()["body"], "A-Z opens the nested card", failures)
    nested_index.activate("back")
    check(nested_index.current()["kind"] == "index" and nested_index.current().get("page") == whistle_at, "back returns to that index row", failures)

    submenu = App(show_cave=False)
    submenu.activate("guide-search")
    submenu.current()["query"] = "hand drill"
    submenu.draw(canvas)
    drill_row = next((widget for widget in submenu.widgets if widget["label"] == "Hand drill"), None)
    check(drill_row is not None, "search lists the fire sub-menu card", failures)
    if drill_row is not None:
        submenu.pointer("down", *drill_row["rect"].center)
        submenu.pointer("up", *drill_row["rect"].center)
        check(
            submenu.current()["kind"] == "reader" and submenu.current()["title"] == "HAND DRILL",
            "sub-menu search result opens the card",
            failures,
        )
        check(
            "friction fire" in submenu.current()["body"] and "fire_hand_drill.png" in submenu.current()["body"],
            "sub-menu card keeps its text and diagram",
            failures,
        )
        drill_badge = False
        for number in range(submenu.page_count(submenu.current())):
            submenu.current()["page"] = number
            submenu.slide_from = None
            submenu.draw(canvas)
            if any(widget["id"].startswith("zoom:") for widget in submenu.widgets):
                drill_badge = True
                break
        check(drill_badge, "sub-menu card still shows the enlarge badge", failures)
        submenu.activate("back")
        check(
            submenu.current()["kind"] == "find" and submenu.current()["query"] == "hand drill",
            "back returns to the sub-menu search",
            failures,
        )

    az = App(show_cave=False)
    az.activate("guide-index")
    az.draw(canvas)
    shown = [widget["label"] for widget in az.widgets if widget["id"].startswith("index:")]
    check(shown == [entry.title for entry in index[:INDEX_PER]], f"index first page {shown}", failures)
    check({"letter:A", "letter:Z", "letter:#"} <= {widget["id"] for widget in az.widgets}, "letter jump buttons", failures)
    missing = [letter for letter in content.INDEX_LETTERS if letter not in {entry.letter for entry in index}]
    if missing:
        disabled = next(widget for widget in az.widgets if widget["id"] == "letter:" + missing[0])
        check(not disabled["enabled"], f"empty letter {missing[0]} is not tappable", failures)
    letter_b = next(widget for widget in az.widgets if widget["id"] == "letter:B")
    check(letter_b["rect"].height >= 32, f"letter button height {letter_b['rect'].height}", failures)
    az.pointer("down", *letter_b["rect"].center)
    az.pointer("up", *letter_b["rect"].center)
    az.draw(canvas)
    jumped = [widget for widget in az.widgets if widget["id"].startswith("index:")]
    check(jumped and jumped[0]["label"][:1].upper() == "B", f"B jumps to { [widget['label'] for widget in jumped] }", failures)
    az.pointer("down", *jumped[0]["rect"].center)
    az.pointer("up", *jumped[0]["rect"].center)
    check(az.current()["kind"] == "reader", "index row opens the card", failures)
    opened = az.current()["title"]
    az.activate("back")
    check(az.current()["kind"] == "index" and az.current().get("page", 0) > 0, "back returns to the index page", failures)
    check(opened.startswith("B"), f"opened the B card {opened}", failures)
    present_letters = {entry.letter for entry in index}
    az.draw(canvas)
    for letter in content.INDEX_LETTERS:
        button = next(widget for widget in az.widgets if widget["id"] == "letter:" + letter)
        if letter not in present_letters:
            check(not button["enabled"], f"letter {letter} with no cards stays disabled", failures)
            continue
        az.activate("letter:" + letter)
        az.draw(canvas)
        first = next(widget for widget in az.widgets if widget["id"].startswith("index:"))
        landed = card_index()[az.current()["page"]]
        check(landed.letter == letter and first["label"] == landed.title, f"letter {letter} jumps to {landed.title}", failures)
    az.activate("tab:GUIDE")
    check(az.current()["kind"] == "home" and len(az.stack) == 1, "GUIDE tab still leaves the index", failures)

    scan = make_scanlines()
    sample = pygame.Surface((WIDTH, HEIGHT))
    sample.fill(GREEN)
    sample.blit(scan, (0, 0))
    dark = sample.get_at((10, 0))
    plain = sample.get_at((10, 1))
    check(plain.g == GREEN[1], "scanline skips the open rows", failures)
    check(dark.g < plain.g, "scanline darkens every third row", failures)

    chip = pygame.Surface((2, 1))
    chip.fill(GREEN)
    packed = pack_rgb565(chip, 4)
    check(packed[:4] == bytes.fromhex("f01ff01f"), f"rgb565 {packed[:4].hex()}", failures)
    band = pygame.Surface((4, 3))
    band.fill(GREEN)
    pygame.draw.rect(band, DIM, (0, 1, 4, 1))
    full = pack_rgb565(band, 8)
    part = pack_rgb565_rows(band, 8, 1, 2)
    check(part == full[8:16], "dirty rows match the full frame", failures)

    if screenshot_dir:
        os.makedirs(screenshot_dir, exist_ok=True)
        home = App(show_cave=True)
        home.draw(canvas)
        pygame.image.save(canvas, os.path.join(screenshot_dir, "home.png"))
        home_two = App(show_cave=True)
        home_two.draw(canvas)
        home_two.activate("home-next")
        home_two.draw(canvas)
        pygame.image.save(canvas, os.path.join(screenshot_dir, "home_page2.png"))
        section = App(show_cave=False)
        section.activate("home:0")
        section.activate("menu:0")
        section.draw(canvas)
        pygame.image.save(canvas, os.path.join(screenshot_dir, "section.png"))
        reader = App(show_cave=False)
        reader.activate("home:0")
        reader.activate("menu:0")
        reader.page_delta(1)
        reader.slide_from = None
        reader.draw(canvas)
        pygame.image.save(canvas, os.path.join(screenshot_dir, "reader.png"))
        search = App(show_cave=False)
        search.activate("home:1")
        search.current()["query"] = "burn"
        search.draw(canvas)
        pygame.image.save(canvas, os.path.join(screenshot_dir, "keyboard.png"))
        field.HOST = "http://127.0.0.1:9"
        try:
            search.run_search()
        finally:
            field.HOST = saved_host
        search.draw(canvas)
        pygame.image.save(canvas, os.path.join(screenshot_dir, "search_kiwix_down.png"))
        finder = App(show_cave=False)
        finder.activate("guide-search")
        finder.current()["query"] = "knot"
        finder.draw(canvas)
        pygame.image.save(canvas, os.path.join(screenshot_dir, "guide_search.png"))
        check(any(widget["label"] == "Square knot" for widget in finder.widgets), "search screenshot shows a knot card", failures)
        indexer = App(show_cave=False)
        indexer.activate("guide-index")
        indexer.draw(canvas)
        pygame.image.save(canvas, os.path.join(screenshot_dir, "guide_index.png"))
        check(any(widget["id"].startswith("letter:") for widget in indexer.widgets), "index screenshot draws letter jumps", failures)
        picked = None
        for topic in field.GUIDE.home_topics():
            view = field.GUIDE.present(topic.slug)
            if not view:
                continue
            for name, body in view["cards"]:
                count = body.count("![")
                if count <= 0:
                    continue
                choice = (topic, name, body, count)
                if picked is None or (count >= 2 and picked[3] < 2):
                    picked = choice
                if count >= 2:
                    break
            if picked and picked[3] >= 2:
                break
        if picked:
            topic, name, body, _count = picked
            shot = App(show_cave=False)
            shot.stack.append(
                {
                    "kind": "reader",
                    "title": name.upper(),
                    "body": body,
                    "page": 0,
                    "tint": topic.tint,
                }
            )
            pages = shot.reader_pages(shot.current())
            for number, blocks in enumerate(pages):
                if any(block.get("kind") == "image" for block in blocks):
                    shot.current()["page"] = number
                    break
            shot.draw(canvas)
            pygame.image.save(canvas, os.path.join(screenshot_dir, "diagram_card.png"))
            opener = next(widget for widget in shot.widgets if str(widget["id"]).startswith("zoom:"))
            shot.pointer("down", *opener["rect"].center)
            shot.pointer("up", *opener["rect"].center)
            shot.draw(canvas)
            pygame.image.save(canvas, os.path.join(screenshot_dir, "diagram.png"))
            check(shot.current()["kind"] == "diagram", "screenshot opened a real diagram", failures)

        for slug, card_name, file_name in (
            ("power", "Carbon monoxide", "power_co_card"),
            ("emergency", "Utilities shutoff", "emergency_utilities_card"),
            ("library", "What to get", "library_card"),
            ("childbirth", "Tie and cut the cord", "childbirth_cord_card"),
            ("childbirth", "Heavy bleeding after birth", "childbirth_bleeding_card"),
            ("mentalhealth", "Calm breathing", "mentalhealth_breathing_card"),
            ("growing", "Three Sisters", "growing_three_sisters_card"),
            ("growing", "Potatoes", "growing_potatoes_card"),
            ("firstaid", "Stroke: FAST", "firstaid_fast_card"),
            ("firstaid", "Triage: many hurt", "firstaid_triage_card"),
            ("firstaid", "Nosebleed", "firstaid_nosebleed_card"),
            ("cooking", "Rocket stove", "cooking_rocket_card"),
            ("cooking", "Water-bath canning", "cooking_canning_card"),
            ("hunting", "Kill and clean a fish", "hunting_fish_card"),
            ("animals", "Chickens: housing", "animals_coop_card"),
            ("repairs", "Fix a bike puncture", "repairs_puncture_card"),
            ("sanitation", "Bleach for cleaning", "sanitation_bleach_card"),
            ("fire_light", "Hand drill", "fire_hand_drill_card"),
            ("fire_build", "Swedish torch", "fire_swedish_card"),
            ("shelter_wild", "Hammock and tarp", "shelter_hammock_card"),
            ("shelter_town", "Car as shelter", "shelter_car_card"),
            ("water_treat", "Biosand filter", "water_biosand_card"),
            ("food_fruit", "Sweet chestnut or horse chestnut?", "food_chestnut_card"),
            ("nav_nocompass", "Improvised compass", "nav_needle_card"),
            ("emergency", "Fire at home", "emergency_fire_card"),
            ("tools", "Bow saw frame", "tools_bow_saw_card"),
        ):
            body = dict(field.GUIDE.cards(slug)).get(card_name, "")
            check(bool(body), f"screenshot card {slug}/{card_name}", failures)
            card = App(show_cave=False)
            card.stack.append({"kind": "reader", "title": card_name.upper(), "body": body, "page": 0, "tint": True})
            for number, blocks in enumerate(card.reader_pages(card.current())):
                if any(block.get("kind") == "image" for block in blocks):
                    card.current()["page"] = number
                    break
            card.draw(canvas)
            pygame.image.save(canvas, os.path.join(screenshot_dir, file_name + ".png"))

        knot_shots = App(show_cave=False)
        knot_shots.activate("home:7")
        knot_shots.draw(canvas)
        pygame.image.save(canvas, os.path.join(screenshot_dir, "knots_menu.png"))
        for slug, card_name, file_name in (
            ("knots_main", "Clove hitch", "knots_clove_card"),
            ("knots_stoppers", "Figure-eight stopper", "knots_fig8_stopper_card"),
            ("knots_hitches", "Munter hitch", "knots_munter_card"),
            ("knots_loops", "Alpine butterfly", "knots_butterfly_card"),
            ("knots_bends", "Zeppelin bend", "knots_zeppelin_card"),
            ("knots_fishing", "Snare noose", "knots_snare_card"),
            ("knots_lashing", "Floor lashing", "knots_floor_lashing_card"),
            ("knots_rope", "Tie a ridge line", "knots_ridgeline_card"),
        ):
            body = dict(field.GUIDE.cards(slug)).get(card_name, "")
            check(bool(body), f"screenshot card {slug}/{card_name}", failures)
            card = App(show_cave=False)
            card.stack.append({"kind": "reader", "title": card_name.upper(), "body": body, "page": 0, "tint": True})
            for number, blocks in enumerate(card.reader_pages(card.current())):
                if any(block.get("kind") == "image" for block in blocks):
                    card.current()["page"] = number
                    break
            card.draw(canvas)
            pygame.image.save(canvas, os.path.join(screenshot_dir, file_name + ".png"))

    if radio is not None:
        radio.exercise(lambda: App(show_cave=True), canvas, lambda cond, msg: check(cond, msg, failures), screenshot_dir)
    else:
        check(False, "radio module imports", failures)

    if failures:
        for message in failures:
            sys.stderr.write(message + "\n")
        return 1
    return 0


def main(argv):
    if argv and argv[0] == "--self-test":
        directory = argv[1] if len(argv) > 1 else None
        return self_test(directory)
    if argv and argv[0] == "--screenshots":
        if len(argv) != 2:
            sys.stderr.write("usage: field_touch.py --screenshots DIR\n")
            return 2
        return self_test(argv[1])
    if argv and argv[0] == "--radio":
        return run(start="radio")
    return run()


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        print()
        sys.exit(0)
    except Exception:
        traceback.print_exc()
        sys.exit(1)
