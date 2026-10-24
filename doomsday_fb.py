"""Framebuffer lookup and HDMI mirror for the Doomsday Pi.

The 3.5 inch panel shows up as a framebuffer whose sysfs name is
``fb_ili9486``. HDMI is a different device. Its name depends on the boot
config: ``vc4drmfb`` when the KMS driver owns the connector, ``BCM2708 FB``
for the legacy firmware framebuffer, or ``simple-framebuffer`` for the
early firmware node. Those numbers (fb0, fb1) follow probe order, so this
module never picks a device by number.

``FIELD_TOUCH_SYSFS`` and ``FIELD_TOUCH_DEVDIR`` redirect the sysfs and
device directories. Tests point them at ordinary files.
"""

import os
import re
import struct
import sys
import threading
import time

TFT_NAME = "fb_ili9486"
# Preference order when more than one HDMI-class node is visible.
# vc4drmfb is the one KMS is scanning out. The simple-framebuffer node is
# only the live picture when KMS has not taken it over.
HDMI_ORDER = (
    "vc4drmfb",
    "bcm2708 fb",
    "simple-framebuffer",
    "simplefb",
)
HDMI_NAMES = frozenset(HDMI_ORDER)
MAX_MIRROR_BYTES = 32 * 1024 * 1024
FBIOGET_VSCREENINFO = 0x4600
FBIOGET_FSCREENINFO = 0x4602
_MODE_SIZE = re.compile(r"(\d+)x(\d+)")


class FbNode:
    def __init__(self, entry, name, device):
        self.entry = entry
        self.name = name
        self.device = device


class FbInfo:
    def __init__(self, width, height, bpp, stride, yoffset, red, green, blue, transp):
        self.width = int(width)
        self.height = int(height)
        self.bpp = int(bpp)
        self.stride = int(stride)
        self.yoffset = int(yoffset)
        self.red = red
        self.green = green
        self.blue = blue
        self.transp = transp


def graphics_root():
    return os.environ.get("FIELD_TOUCH_SYSFS", "/sys/class/graphics")


def dev_root():
    return os.environ.get("FIELD_TOUCH_DEVDIR", "/dev")


def _read_text(directory, leaf):
    try:
        with open(os.path.join(directory, leaf), encoding="ascii", errors="replace") as handle:
            return handle.read().strip()
    except OSError:
        return None


def list_framebuffers():
    root = graphics_root()
    nodes = []
    try:
        entries = sorted(os.listdir(root))
    except OSError:
        return nodes
    for entry in entries:
        if len(entry) < 3 or not entry.startswith("fb") or not entry[2:].isdigit():
            continue
        name = _read_text(os.path.join(root, entry), "name")
        if not name:
            continue
        nodes.append(FbNode(entry, name.strip(), os.path.join(dev_root(), entry)))
    return nodes


def tft_path():
    """Path of the ILI9486 panel.

    ``FIELD_TOUCH_FB`` wins. Otherwise the device whose name is
    ``fb_ili9486``. If that node is not listed, ``/dev/fb0`` remains the
    legacy single-panel path (and the path a desktop without sysfs checks).
    """
    override = os.environ.get("FIELD_TOUCH_FB", "").strip()
    if override:
        return override
    for node in list_framebuffers():
        if node.name.lower() == TFT_NAME:
            return node.device
    return os.path.join(dev_root(), "fb0")


def is_hdmi_name(name):
    return (name or "").strip().lower() in HDMI_NAMES


def hdmi_path(exclude=None):
    """Best HDMI framebuffer, or None when the boot config has not created one."""
    forced = os.environ.get("FIELD_TOUCH_HDMI_DEV", "").strip()
    if forced:
        if exclude and _same_path(forced, exclude):
            return None
        return forced
    found = {}
    for node in list_framebuffers():
        found.setdefault(node.name.lower(), node.device)
    for name in HDMI_ORDER:
        device = found.get(name)
        if device and not (exclude and _same_path(device, exclude)):
            return device
    return None


def _same_path(left, right):
    try:
        return os.path.realpath(left) == os.path.realpath(right)
    except OSError:
        return left == right


def default_fields(bpp):
    """Pi defaults: RGB565, or XRGB8888 (red at bit 16) for 32-bit."""
    if bpp == 16:
        return (11, 5), (5, 6), (0, 5), (0, 0)
    if bpp == 32:
        return (16, 8), (8, 8), (0, 8), (24, 8)
    return (0, 0), (0, 0), (0, 0), (0, 0)


def parse_var_screeninfo(blob):
    """Decode ``fb_var_screeninfo`` from FBIOGET_VSCREENINFO.

    The struct is all 32-bit fields, so the layout is the same on the Pi's
    64-bit kernel and on a 32-bit one. Endianness follows the machine.
    """
    if len(blob) < 80:
        raise ValueError("short var screeninfo")
    xres, yres, xres_v, yres_v, xoff, yoff, bpp, _gray = struct.unpack_from("=8I", blob, 0)

    def bitfield(offset):
        off, length, _msb = struct.unpack_from("=3I", blob, offset)
        return int(off), int(length)

    return {
        "xres": int(xres),
        "yres": int(yres),
        "xres_virtual": int(xres_v),
        "yres_virtual": int(yres_v),
        "xoffset": int(xoff),
        "yoffset": int(yoff),
        "bpp": int(bpp),
        "red": bitfield(32),
        "green": bitfield(44),
        "blue": bitfield(56),
        "transp": bitfield(68),
    }


def parse_fix_stride(blob):
    """``line_length`` from ``fb_fix_screeninfo``. Pointer-sized smem_start shifts it."""
    offset = 48 if struct.calcsize("P") == 8 else 44
    if len(blob) < offset + 4:
        return None
    value = struct.unpack_from("=I", blob, offset)[0]
    if 4 <= value <= 65536:
        return int(value)
    return None


def _sysfs_geometry(path):
    base = os.path.join(graphics_root(), os.path.basename(path))
    width = height = None
    virtual = _read_text(base, "virtual_size")
    if virtual and "," in virtual:
        wide, high = virtual.split(",", 1)
        try:
            width, height = int(wide), int(high)
        except ValueError:
            width = height = None
    # ``modes`` lists every mode, not the active one. Use it only to undo the
    # firmware's double-height virtual size (yres_virtual == 2 * visible).
    modes = _read_text(base, "modes") or ""
    match = _MODE_SIZE.search(modes)
    if match and width and height:
        mode_w, mode_h = int(match.group(1)), int(match.group(2))
        if mode_w == width and mode_h > 0 and height == mode_h * 2:
            height = mode_h
    bpp = _parse_int(_read_text(base, "bits_per_pixel"))
    stride = _parse_int(_read_text(base, "stride"))
    yoffset = _parse_int(_read_text(base, "yoffset")) or 0
    red, green, blue, transp = default_fields(bpp or 0)
    red = _field_file(base, "red", red)
    green = _field_file(base, "green", green)
    blue = _field_file(base, "blue", blue)
    transp = _field_file(base, "transp", transp)
    return width, height, bpp, stride, yoffset, red, green, blue, transp


def _parse_int(text):
    if text is None:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _field_file(base, prefix, default):
    offset = _parse_int(_read_text(base, prefix + "_offset"))
    length = _parse_int(_read_text(base, prefix + "_length"))
    if offset is None or length is None:
        return default
    return offset, length


def _ioctl_geometry(fd):
    import fcntl

    var_buf = bytearray(256)
    try:
        fcntl.ioctl(fd, FBIOGET_VSCREENINFO, var_buf)
        var = parse_var_screeninfo(var_buf)
    except (OSError, ValueError):
        var = None
    fix_buf = bytearray(256)
    stride = None
    try:
        fcntl.ioctl(fd, FBIOGET_FSCREENINFO, fix_buf)
        stride = parse_fix_stride(fix_buf)
    except OSError:
        stride = None
    return var, stride


def inspect_fb(path):
    """Visible size, stride, bpp, and channel masks for ``path``.

    ioctl wins. sysfs fills in whatever the ioctl did not return, which is
    the whole record for a regular file used in tests.
    """
    width, height, bpp, stride, yoffset, red, green, blue, transp = _sysfs_geometry(path)
    fd = os.open(path, os.O_RDWR)
    try:
        var, fix_stride = _ioctl_geometry(fd)
    finally:
        os.close(fd)
    if var and var["xres"] > 0 and var["yres"] > 0 and var["bpp"] > 0:
        width = var["xres"]
        height = var["yres"]
        bpp = var["bpp"]
        yoffset = var["yoffset"]
        if var["red"][1] or var["green"][1] or var["blue"][1]:
            red, green, blue, transp = var["red"], var["green"], var["blue"], var["transp"]
        else:
            red, green, blue, transp = default_fields(bpp)
    if fix_stride:
        stride = fix_stride
    if not width or not height or not bpp:
        raise OSError(f"{path}: framebuffer size is unknown")
    if stride is None:
        stride = width * max(1, bpp // 8)
    info = FbInfo(width, height, bpp, stride, yoffset, red, green, blue, transp)
    _validate(info)
    return info


def _validate(info):
    if info.bpp not in (16, 32):
        raise OSError(f"HDMI framebuffer is {info.bpp}-bit; mirroring supports 16 and 32")
    if info.width < 1 or info.height < 1 or info.width > 7680 or info.height > 4320:
        raise OSError(f"HDMI framebuffer size {info.width}x{info.height} is not usable")
    row = info.width * (info.bpp // 8)
    if info.stride < row or info.stride > 65536:
        raise OSError(f"HDMI stride {info.stride} does not match {info.width}x{info.bpp}")
    if info.yoffset < 0 or info.yoffset > 8192:
        raise OSError("HDMI yoffset is not usable")
    total = info.stride * info.height
    if total <= 0 or total > MAX_MIRROR_BYTES:
        raise OSError("HDMI framebuffer is too large to mirror")


def fitted_size(src_w, src_h, dst_w, dst_h):
    """Integer scale when the panel fits at 1x or more, else nearest fit.

    Returns ``(out_w, out_h, x0, y0)`` for a centred letterbox.
    """
    if min(src_w, src_h, dst_w, dst_h) < 1:
        raise ValueError("size")
    factor = min(dst_w // src_w, dst_h // src_h)
    if factor >= 1:
        out_w = src_w * factor
        out_h = src_h * factor
    else:
        scale = min(dst_w / src_w, dst_h / src_h)
        out_w = max(1, min(dst_w, int(src_w * scale)))
        out_h = max(1, min(dst_h, int(src_h * scale)))
    return out_w, out_h, (dst_w - out_w) // 2, (dst_h - out_h) // 2


def compose_frame(rgb, src_w, src_h, info):
    """Letterboxed nearest-neighbour frame, ready to write at yoffset.

    ``rgb`` is tightly packed RGB888, ``src_w * src_h * 3`` bytes.
    The result is ``height * stride`` bytes in the framebuffer's bpp.
    Channel masks come from ``info``. Alpha bits, when the mode has them,
    are set so an ARGB scanout stays opaque; XRGB ignores those bits.
    """
    import numpy as np

    expected = src_w * src_h * 3
    if src_w < 1 or src_h < 1 or len(rgb) != expected:
        raise ValueError("rgb size")
    src = np.frombuffer(rgb, dtype=np.uint8).reshape((src_h, src_w, 3))
    out_w, out_h, x0, y0 = fitted_size(src_w, src_h, info.width, info.height)
    ys = (np.arange(out_h, dtype=np.int32) * src_h) // out_h
    xs = (np.arange(out_w, dtype=np.int32) * src_w) // out_w
    scaled = src[ys][:, xs]
    red = scaled[:, :, 0].astype(np.uint32)
    green = scaled[:, :, 1].astype(np.uint32)
    blue = scaled[:, :, 2].astype(np.uint32)

    def channel(plane, offset, length):
        if length <= 0:
            return 0
        if length >= 8:
            field = np.left_shift(plane, np.uint32(length - 8))
        else:
            field = np.right_shift(plane, np.uint32(8 - length))
        mask = np.uint32((1 << length) - 1)
        return np.left_shift(np.bitwise_and(field, mask), np.uint32(offset))

    pixel = channel(red, *info.red) | channel(green, *info.green) | channel(blue, *info.blue)
    if info.bpp == 16:
        plane = np.zeros((info.height, info.width), dtype="<u2")
        plane[y0 : y0 + out_h, x0 : x0 + out_w] = pixel.astype("<u2")
    else:
        plane = np.zeros((info.height, info.width), dtype="<u4")
        plane[y0 : y0 + out_h, x0 : x0 + out_w] = pixel.astype("<u4")
    if info.transp[1] > 0:
        alpha = np.array(((1 << info.transp[1]) - 1) << info.transp[0], dtype=plane.dtype)
        plane = np.bitwise_or(plane, alpha)
    raw = plane.reshape((info.height, info.width)).view(np.uint8)
    raw = raw.reshape((info.height, info.width * (info.bpp // 8)))
    if info.stride == raw.shape[1]:
        return raw.tobytes()
    buf = np.zeros((info.height, info.stride), dtype=np.uint8)
    buf[:, : raw.shape[1]] = raw
    return buf.tobytes()


class HdmiMirror:
    """Write frames to the HDMI framebuffer without stalling the caller.

    ``submit`` copies the pixels and returns. A daemon thread scales and
    writes. If a new frame arrives while one is still queued, the queued
    one is replaced. The panel thread never waits on the HDMI write, and a
    1GB Pi does not accumulate a backlog of full-HD copies. When the thread
    is idle, every submitted frame is written.
    """

    def __init__(self, path, info=None):
        self.path = path
        self.info = info if info is not None else inspect_fb(path)
        _validate(self.info)
        self.fd = open(path, "r+b", buffering=0)
        self.failed = False
        self.error = None
        self._lock = threading.Lock()
        self._pending = None
        self._busy = False
        self._stop = False
        self._event = threading.Event()
        self._thread = threading.Thread(target=self._loop, name="doomsday-hdmi", daemon=True)
        self._thread.start()

    def submit(self, surface):
        if self.failed or self._stop:
            return
        import pygame

        raw = pygame.image.tobytes(surface, "RGB")
        width, height = surface.get_size()
        with self._lock:
            self._pending = (width, height, raw)
        self._event.set()

    def flush(self, timeout=2.0):
        """Wait until the queued frame has been written. Used by tests and shutdown."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self._lock:
                idle = self._pending is None and not self._busy
            if self.failed or idle:
                return not self.failed
            time.sleep(0.005)
        return False

    def close(self):
        self.flush(timeout=1.0)
        self._stop = True
        self._event.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        fd = self.fd
        self.fd = None
        if fd is not None:
            try:
                fd.close()
            except OSError:
                pass

    def _loop(self):
        while not self._stop:
            self._event.wait()
            if self._stop:
                break
            while not self._stop:
                with self._lock:
                    item = self._pending
                    self._pending = None
                    if item is None:
                        self._event.clear()
                        item = self._pending
                        self._pending = None
                        if item is None:
                            self._busy = False
                            break
                    self._busy = True
                try:
                    width, height, raw = item
                    data = compose_frame(raw, width, height, self.info)
                    self._write(data)
                except Exception as error:
                    self.error = error
                    self.failed = True
                    with self._lock:
                        self._busy = False
                        self._pending = None
                    return
                with self._lock:
                    self._busy = False

    def _write(self, data):
        offset = self.info.yoffset * self.info.stride
        self.fd.seek(offset)
        view = memoryview(data)
        while view:
            wrote = self.fd.write(view)
            if not wrote:
                raise OSError("short HDMI write")
            view = view[wrote:]


def _numpy_ready():
    try:
        import numpy  # noqa: F401
    except ImportError:
        return False
    return True


def open_hdmi_mirror(exclude=None):
    """Open the mirror, or return None. Never raises for a missing display."""
    if setting_off("hdmi", "FIELD_TOUCH_HDMI"):
        return None
    path = hdmi_path(exclude=exclude)
    if not path:
        return None
    if not _numpy_ready():
        sys.stderr.write("doomsday: HDMI mirror needs python3-numpy. Continuing on the TFT.\n")
        return None
    try:
        mirror = HdmiMirror(path)
    except OSError as error:
        sys.stderr.write(f"doomsday: HDMI mirror off ({error}). Continuing on the TFT.\n")
        return None
    info = mirror.info
    sys.stderr.write(
        f"doomsday: mirroring the TFT to {path} "
        f"({info.width}x{info.height}, {info.bpp}-bit, stride {info.stride}).\n"
    )
    return mirror


def parse_config_file(path):
    found = {}
    try:
        handle = open(path, encoding="utf-8")
    except OSError:
        return found
    with handle:
        for line in handle:
            line = line.split("#", 1)[0].strip()
            if not line or "=" not in line:
                continue
            key, value = line.split("=", 1)
            found[key.strip().lower()] = value.strip()
    return found


def read_config():
    """System config, then the user file. ``FIELD_TOUCH_CONFIG`` replaces both."""
    override = os.environ.get("FIELD_TOUCH_CONFIG", "").strip()
    if override:
        paths = [override]
    else:
        paths = [
            "/etc/doomsday/field-touch.conf",
            os.path.expanduser("~/.doomsday/field-touch.conf"),
        ]
    merged = {}
    for path in paths:
        merged.update(parse_config_file(path))
    return merged


def _truthy_off(value):
    return value.strip().lower() in {"0", "false", "no", "off"}


def setting_off(key, env_name):
    """True when an env var or config line turns a default-on feature off."""
    raw = os.environ.get(env_name)
    if raw is not None and raw.strip() != "":
        return _truthy_off(raw)
    value = read_config().get(key)
    if value is None or value == "":
        return False
    return _truthy_off(value)


def splash_seconds(default=6.0):
    raw = os.environ.get("FIELD_TOUCH_SPLASH_SECONDS", "").strip()
    if not raw:
        raw = read_config().get("splash_seconds", "")
    if not raw:
        return default
    try:
        return max(0.0, float(raw))
    except ValueError:
        return default
