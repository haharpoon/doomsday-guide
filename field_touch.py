#!/usr/bin/env python3
"""Touchscreen front end for the doomsday field guide.

The Pi panel is /dev/fb0 at 480x320, 16-bit RGB565. pygame cannot open that
framebuffer, so this draws with the dummy SDL driver and writes a frame only
when the picture changes. With no framebuffer, it opens a 480x320 window.

Touch input is the ADS7846 device via evdev. The top bar is GUIDE | SCAN | RADIO
(see tabbar.py, shared with Cave Mapper). Calibration in ~/.touchcal.json
is {"cx": [a, b, c], "cy": [d, e, f]}:

    x = a*rawX + b*rawY + c
    y = d*rawX + e*rawY + f

A missing or unreadable file falls back to the device's raw axis range.
FIELD_TOUCH_MIRROR_X=1 mirrors X only in that fallback.
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


def load_font(size, bold=False):
    path = first_font(FONT_BOLD if bold else FONT_REGULAR)
    if path:
        return pygame.font.Font(path, size)
    return pygame.font.Font(None, size)


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


def fit_surface(surface, max_w, max_h):
    width, height = surface.get_size()
    if width <= 0 or height <= 0 or max_w <= 0 or max_h <= 0:
        return surface
    scale = min(max_w / width, max_h / height, 1)
    if scale >= 1:
        return surface
    target = (max(1, int(round(width * scale))), max(1, int(round(height * scale))))
    try:
        return pygame.transform.smoothscale(surface, target)
    except pygame.error:
        return pygame.transform.scale(surface, target)


def load_card_image(relpath, max_w, max_h, directory, tint):
    """Load a content image scaled to the reader area. None when it cannot be shown."""
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
    image = fit_surface(image, max_w, max_h)
    if tint:
        image = tint_surface(image)
    return image


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
        image = load_card_image(relpath, min(width, 480), min(page_px, 284), directory, tint)
        if image is None:
            label = f"[diagram: {alt}]" if alt else "[diagram]"
            for line in wrap_body(label, font, small, width):
                blocks.append({"kind": "text", "text": line, "px": line_h})
            continue
        blocks.append({"kind": "image", "image": image, "alt": alt, "px": image.get_height()})
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
        return 1

    def can_prev(self, screen):
        return screen.get("page", 0) > 0

    def can_next(self, screen):
        if screen["kind"] == "results" and len(screen["results"]) < screen.get("total", 0):
            return True
        return screen.get("page", 0) + 1 < self.page_count(screen)

    def page_delta(self, delta):
        screen = self.current()
        if screen["kind"] not in ("menu", "reader", "results"):
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

    def back(self):
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
                self.pending = "cave"
                self.notice = "Opening Cave Mapper..."
            else:
                self.notice = "Cave Mapper is not installed."
            return
        if wid == "tab:GUIDE":
            self.tab_flash = "GUIDE"
            self.notice = ""
            self.slide_from = None
            if screen["kind"] != "home" or len(self.stack) > 1:
                self.stack = [{"kind": "home"}]
            return
        if wid == "tab:RADIO":
            self.tab_flash = "RADIO"
            self.notice = "Radio is not available."
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

    def on_token(self, token):
        screen = self.current()
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
                if code != 0:
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

    def pointer(self, kind, x, y):
        if kind == "down":
            hit = self.hit(x, y)
            now = time.monotonic()
            if (
                hit
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
            return True
        if kind == "move":
            if self.suppress or self.origin is None:
                return False
            if self.pressed and self.pressed.startswith("tab:"):
                if self.hit(x, y) != self.pressed:
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
            on_tab = bool(pressed) and pressed.startswith("tab:")
            if (not on_tab) and (swiping or (abs(dy) >= SWIPE and abs(dy) > abs(dx))):
                if self.current()["kind"] in ("reader", "menu", "results"):
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
        self.tab_hits = tabbar.draw_tabbar(
            canvas,
            self.font_tab,
            active="GUIDE",
            pressed=self._tab_pressed_name(),
            enabled={"GUIDE": True, "SCAN": self.cave_on(), "RADIO": False},
        )
        if kind == "home":
            self.draw_home(canvas)
        elif kind == "menu":
            self.draw_menu(canvas)
        elif kind == "reader":
            self.draw_reader(canvas)
        elif kind == "search":
            self.draw_search(canvas)
        elif kind == "results":
            self.draw_results(canvas)
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
        if pages == 1:
            self.add_button(canvas, rects[9], "Exit", "exit")
        else:
            action = rects[9]
            row = [
                ("Prev", "home-prev", page > 0),
                ("Exit", "exit", True),
                ("Next", "home-next", page + 1 < pages),
            ]
            avail_w = WIDTH - 2 * MARGIN
            count = len(row)
            btn_w = (avail_w - GAP * (count - 1)) // count
            extra = avail_w - (btn_w * count + GAP * (count - 1))
            x = MARGIN
            for index, (label, wid, enabled) in enumerate(row):
                grow = 1 if index < extra else 0
                rect = pygame.Rect(x, action.y, btn_w + grow, action.height)
                self.add_button(canvas, rect, label, wid, enabled)
                x += btn_w + grow + GAP

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
                x = MARGIN + max(0, (self.content_width() - image.get_width()) // 2)
                canvas.blit(image, (x, y))
            elif block.get("text"):
                line = block["text"]
                use = self.font_body
                if use.size(line)[0] > self.content_width() and self.font_small.size(line)[0] <= self.content_width():
                    use = self.font_small
                img = use.render(line, True, GREEN)
                canvas.blit(img, (MARGIN, y))
            y += block["px"]
        canvas.set_clip(None)

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

    def draw_query(self, canvas, query, y, height=34):
        rect = pygame.Rect(MARGIN, y, self.content_width(), height)
        pygame.draw.rect(canvas, BLACK, rect)
        pygame.draw.rect(canvas, GREEN, rect, 2)
        font = self.font_body
        pad = 8
        caret_w = 2
        limit = rect.width - pad * 2 - caret_w - 8
        if query:
            shown = query
            while shown and font.size(shown)[0] > limit:
                shown = shown[1:]
            img = font.render(shown, True, GREEN)
            text_x = rect.x + pad
        else:
            shown = ""
            img = font.render("type a word", True, DIM)
            text_x = rect.x + pad + caret_w + 4
        text_y = rect.y + (rect.height - img.get_height()) // 2
        canvas.blit(img, (text_x, text_y))
        if query:
            caret_x = rect.x + pad + font.size(shown)[0] + 2
        else:
            caret_x = rect.x + pad
        caret_x = min(caret_x, rect.right - pad - caret_w)
        caret_h = max(8, font.get_height() - 2)
        caret_y = rect.y + (rect.height - caret_h) // 2
        pygame.draw.rect(canvas, GREEN, (caret_x, caret_y, caret_w, caret_h))
        return rect.bottom

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


def layout_keys(rows, area):
    wide = {"SHIFT": 76, "BKSP": 72, "ENTER": 96, "123": 64, "ABC": 64, "NUM": 64, "SEARCH": 96, "BACK": 72, "DEL": 72}
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
        share = max(1, remain // len(flex)) if flex else 0
        extra = remain - share * len(flex) if flex else 0
        x = area.x
        flex_i = 0
        for token in row:
            if token in wide and token != "SPACE":
                width = wide[token]
            else:
                width = share + (1 if flex_i < extra else 0)
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


def run():
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    mode = choose_mode()
    if mode == "fb":
        os.environ["SDL_VIDEODRIVER"] = "dummy"
    elif mode == "dummy":
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    boot_pygame()
    app = App()
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
                and kind in ("menu", "reader", "results")
                and old != new
            ):
                play_slide(app, display, old, new)
                changed = False
            else:
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
            idle_wait(touch)


class Axis:
    def __init__(self, low, high):
        self.min = low
        self.max = high


def check(condition, message, failures):
    if not condition:
        failures.append(message)


def self_test(screenshot_dir=None):
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
    check(page_two == ["Navigation", "More"], f"home page two {page_two}", failures)
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
    radio = next(hit for hit in cave_app.tab_hits if hit["name"] == "RADIO")
    guide = next(hit for hit in cave_app.tab_hits if hit["name"] == "GUIDE")
    check(scan["enabled"] and not radio["enabled"] and guide["enabled"], "scan on, radio placeholder", failures)
    check(guide["rect"].height == 36 and scan["rect"].width == radio["rect"].width == guide["rect"].width, "equal 36px tabs", failures)
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
    food.activate("home:6")
    food.draw(canvas)
    check("search" in [widget["id"] for widget in food.widgets], "food sheet can search", failures)
    check(food.current()["kind"] == "reader" and food.current()["body"].startswith("Cook meat, fish,"), "food opens the sheet", failures)

    check(content is not None, "content loader imports", failures)
    home_titles = [topic.title for topic in field.GUIDE.home_topics()]
    check(
        home_titles
        == ["Shelter", "Medicine", "First aid", "Water", "Fire", "Knots", "Food", "Tools and wildlife", "Sanitation", "Navigation", "More"],
        f"home menu order {home_titles}",
        failures,
    )
    check(len(field.SHELTER) == 5 and len(field.WATER) == 11 and len(field.FIRE) == 3, "sheet counts", failures)
    check(len(field.KNOTS_MAIN) == 8 and field.KNOTS_MAIN[0][0] == "Which knot", "main knots", failures)
    check(field.KNOT_WHICH == field.KNOTS_MAIN[0][1], "which knot text", failures)
    check(len(field.KNOTS_MORE) == 8, "more knots", failures)
    check("standing     standing" in field.KNOTS_MAIN[1][1], "square knot diagram text", failures)
    check(
        content.console_body("See ![ridge pole](img/ridge.png) here.") == "See [diagram: ridge pole] here.",
        "console diagram placeholder",
        failures,
    )
    check(content.console_body(field.SHELTER[0][1]) == field.SHELTER[0][1], "plain sheet is unchanged", failures)
    knots = App(show_cave=False)
    knots.activate("home:5")
    knot_labels = [item["label"] for item in knots.current()["items"]]
    check(
        knot_labels[0] == "Which knot" and knot_labels[-2:] == ["More knots", "Lashings"] and len(knot_labels) == 10,
        f"knots menu {knot_labels}",
        failures,
    )
    more = App(show_cave=False)
    more.activate("home:10")
    more_labels = [item["label"] for item in more.current()["items"]]
    check(
        more_labels == ["Signals & Radio", "Clothing and weather", "Places", "Search all archives"],
        f"more menu {more_labels}",
        failures,
    )

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
