#!/usr/bin/env python3
"""RADIO tab for the 480x320 field guide.

Three tools that need no extra hardware, plus a live FM screen when an
RTL-SDR is plugged in:

* UK frequency cards, edited in ``content/radio_freqs.json``
* a listening log in ``~/.doomsday/radio_log.json``
* a Morse / SOS trainer at standard timing

The Signals & Radio sheet (``content/signals.md``) keeps the long notes.
Cards only store the frequency and a one-line pointer.

ESP32 + RDA5807 FM (not required)
---------------------------------
A later build can hang an RDA5807 off the same ESP32 Cave Mapper already
uses, and forward tune commands on USB serial at 115200 8N1, UTF-8, LF.

Set ``RADIO_RDA_PORT`` (for example ``/dev/ttyUSB0``). This module then
writes one line when the live frequency changes::

    FREQ 93.5

and ``OFF`` when listening stops. It does not speak I2C, and it does not
open a port unless that variable is set. With no reply the status stays
"RDA5807 not attached".

Live FM audio, when an RTL-SDR is present, is::

    rtl_fm -f 93.5M -M wbfm -s 200000 -r 48000 -A fast | aplay -r 48000 -f S16_LE -t raw -c 1 -q

``-A fast`` keeps the Pi 3B cooler. ``RADIO_ALSA_DEVICE`` picks the aplay
device. A spectrum sweep is a separate one-shot ``rtl_power`` and only
runs when you tap BARS, never while audio is playing.
"""

import json
import os
import shutil
import subprocess
import time
from decimal import Decimal

import pygame

WIDTH = 480
HEIGHT = 320
TAB_H = 36
MODE_H = 44
STATUS_H = 42
MARGIN = 4
GAP = 4
GREEN = (0x1A, 0xFF, 0x80)
DIM = (0x0A, 0x5C, 0x2E)
BLACK = (0, 0, 0)

# Exit code cavemap uses when the RADIO tab should open in the waiting guide.
RADIO_EXIT = 7

NO_RADIO = "No radio hardware - plug in an RTL-SDR to listen live"
RTL_IDS = {("0bda", "2838"), ("0bda", "2832")}
TAGS = ("heard", "clear", "noisy", "nothing")
LOG_CAP = 200
WPM = 10
DIT_S = 1.2 / WPM
FM_LOW = 87.5
FM_HIGH = 108.0
FM_STEP = 0.1
PMR_BASE = Decimal("446.00625")
PMR_STEP = Decimal("0.0125")
MORSE = {
    "A": ".-",
    "B": "-...",
    "C": "-.-.",
    "D": "-..",
    "E": ".",
    "F": "..-.",
    "G": "--.",
    "H": "....",
    "I": "..",
    "J": ".---",
    "K": "-.-",
    "L": ".-..",
    "M": "--",
    "N": "-.",
    "O": "---",
    "P": ".--.",
    "Q": "--.-",
    "R": ".-.",
    "S": "...",
    "T": "-",
    "U": "..-",
    "V": "...-",
    "W": ".--",
    "X": "-..-",
    "Y": "-.--",
    "Z": "--..",
    "0": "-----",
    "1": ".----",
    "2": "..---",
    "3": "...--",
    "4": "....-",
    "5": ".....",
    "6": "-....",
    "7": "--...",
    "8": "---..",
    "9": "----.",
    "SOS": "...---...",
}
DECODE = {code: letter for letter, code in MORSE.items() if letter != "SOS"}
PRESET_WORDS = ("SOS", "OK", "HELP", "CQ")
LETTER_PAGES = (
    "ABCDEFGH",
    "IJKLMNOP",
    "QRSTUVWXYZ",
)


class Hardware:
    def __init__(self, present, line, via="", usb=""):
        self.present = bool(present)
        self.line = line
        self.via = via
        self.usb = usb


class FmPlayer:
    """rtl_fm piped to aplay. Idle until start(); stop() is safe to repeat."""

    def __init__(self):
        self.rtl = None
        self.play = None
        self.mhz = None

    def playing(self):
        return self.rtl is not None and self.rtl.poll() is None

    def start(self, mhz):
        self.stop()
        if os.environ.get("RADIO_NO_AUDIO") == "1":
            self.mhz = float(mhz)
            return "audio disabled"
        rtl_cmd, play_cmd = fm_pipeline(mhz)
        rtl = shutil.which("rtl_fm")
        play = shutil.which("aplay")
        if not rtl or not play:
            return "rtl_fm or aplay is not installed"
        rtl_cmd = [rtl] + rtl_cmd[1:]
        play_cmd = [play] + play_cmd[1:]
        try:
            self.rtl = subprocess.Popen(rtl_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            self.play = subprocess.Popen(
                play_cmd,
                stdin=self.rtl.stdout,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if self.rtl.stdout is not None:
                self.rtl.stdout.close()
        except OSError as error:
            self.stop()
            return str(error)
        self.mhz = float(mhz)
        return ""

    def stop(self):
        for proc in (self.play, self.rtl):
            if proc is not None and proc.poll() is None:
                proc.terminate()
        for proc in (self.play, self.rtl):
            if proc is None:
                continue
            try:
                proc.wait(timeout=0.3)
            except subprocess.TimeoutExpired:
                proc.kill()
        self.rtl = None
        self.play = None


class Rda5807Hook:
    """Serial stub for a future ESP32-attached RDA5807. See the module docstring."""

    def __init__(self, port="", send=None):
        self.port = port or ""
        self.send = send
        self.sent = []

    def status(self):
        if not self.port:
            return "RDA5807 not attached"
        return f"RDA5807 hook {self.port}"

    def tune(self, mhz):
        self._write(f"FREQ {float(mhz):.1f}")

    def off(self):
        self._write("OFF")

    def _write(self, line):
        self.sent.append(line)
        if self.send is not None:
            self.send(line)
            return
        if self.port:
            serial_write(self.port, line)


def serial_write(port, line):
    """Write one LF line at 115200. False when pyserial or the port is missing."""

    try:
        import serial
    except ImportError:
        return False
    try:
        with serial.Serial(port, 115200, timeout=0.2, write_timeout=0.2) as handle:
            handle.write((line.rstrip("\n") + "\n").encode("utf-8"))
        return True
    except Exception:
        return False


def pmr446_mhz(channel):
    """Channel 1 is 446.00625 MHz. Later channels step up by 12.5 kHz."""

    return PMR_BASE + Decimal(channel - 1) * PMR_STEP


def freqs_path():
    env = os.environ.get("DOOMSDAY_CONTENT", "").strip()
    names = []
    if env:
        names.append(os.path.join(env, "radio_freqs.json"))
    names.append("/usr/local/share/doomsday/content/radio_freqs.json")
    here = os.path.dirname(os.path.abspath(__file__))
    names.append(os.path.join(here, "content", "radio_freqs.json"))
    for path in names:
        if path and os.path.isfile(path):
            return path
    return names[-1]


def _as_bool(value):
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "ok", "on"}
    return bool(value)


def load_freqs(path=None):
    """Cards from the JSON file. A missing file still yields Radio 4."""

    path = freqs_path() if path is None else path
    fallback = {
        "legal": "Airband, marine, PMR: unintended recipients under the Wireless Telegraphy Act s48.",
        "guide": "signals",
        "cards": [
            {
                "title": "BBC Radio 4 FM",
                "short": "R4",
                "listen": True,
                "group": "broadcast",
                "freq": "92.5-96.1 / 103.5-104.9 MHz",
                "preset": "93.5",
                "summary": "See Signals & Radio.",
            }
        ],
        "path": None,
    }
    try:
        with open(path, encoding="utf-8") as handle:
            raw = json.load(handle)
    except (OSError, json.JSONDecodeError, UnicodeError):
        return fallback
    if not isinstance(raw, dict):
        return fallback
    cards = []
    for item in raw.get("cards") or []:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        freq = str(item.get("freq") or "").strip()
        if not title or not freq:
            continue
        cards.append(
            {
                "title": title,
                "short": str(item.get("short") or title).strip() or title,
                "listen": _as_bool(item.get("listen")),
                "group": str(item.get("group") or "").strip().lower(),
                "freq": freq,
                "preset": str(item.get("preset") or "").strip(),
                "summary": " ".join(str(item.get("summary") or "").split()),
            }
        )
    if not cards:
        return fallback
    legal = str(raw.get("legal") or fallback["legal"]).strip()
    guide = str(raw.get("guide") or "signals").strip() or "signals"
    return {"legal": legal, "guide": guide, "cards": cards, "path": path}


def log_path():
    env = os.environ.get("RADIO_LOG", "").strip()
    if env:
        return env
    return os.path.join(os.path.expanduser("~"), ".doomsday", "radio_log.json")


def read_log(path):
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return []
    except (OSError, json.JSONDecodeError, UnicodeError):
        return []
    if not isinstance(data, list):
        return []
    rows = []
    for item in data:
        if not isinstance(item, dict):
            continue
        tag = str(item.get("tag") or "")
        if tag not in TAGS:
            continue
        rows.append(
            {
                "at": str(item.get("at") or ""),
                "freq": str(item.get("freq") or ""),
                "tag": tag,
                "label": str(item.get("label") or ""),
            }
        )
    return rows


def append_log(path, freq, tag, label, at=None):
    if tag not in TAGS:
        raise ValueError(tag)
    rows = read_log(path)
    if at is None:
        at = time.strftime("%Y-%m-%dT%H:%M:%S")
    rows.append(
        {
            "at": str(at),
            "freq": str(freq),
            "tag": tag,
            "label": str(label),
        }
    )
    if len(rows) > LOG_CAP:
        rows = rows[-LOG_CAP:]
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    temp = path + ".tmp"
    with open(temp, "w", encoding="utf-8") as handle:
        json.dump(rows, handle, indent=2)
        handle.write("\n")
    os.replace(temp, path)
    return rows[-1]


def pattern(text):
    """Standard Morse timing in units. SOS is the prosign, with no letter gaps."""

    words = str(text or "").strip().upper().split()
    events = []
    for word_index, word in enumerate(words):
        if word == "SOS":
            symbols = ["SOS"]
        else:
            symbols = [char for char in word if char in MORSE]
        for symbol_index, symbol in enumerate(symbols):
            code = MORSE.get(symbol)
            if not code:
                continue
            for element_index, element in enumerate(code):
                events.append((True, 3 if element == "-" else 1))
                if element_index != len(code) - 1:
                    events.append((False, 1))
            if symbol_index != len(symbols) - 1:
                events.append((False, 3))
        if word_index != len(words) - 1 and events:
            events.append((False, 7))
    return events


def schedule(text, wpm=WPM):
    unit = 1.2 / float(wpm)
    return [(on, units * unit) for on, units in pattern(text)]


def decode_elements(elements):
    return DECODE.get(elements, "?")


def find_rtl_usb(usb_root="/sys/bus/usb/devices"):
    root = usb_root or "/sys/bus/usb/devices"
    if not os.path.isdir(root):
        return ""
    try:
        names = os.listdir(root)
    except OSError:
        return ""
    for name in names:
        vendor_path = os.path.join(root, name, "idVendor")
        product_path = os.path.join(root, name, "idProduct")
        try:
            with open(vendor_path, encoding="utf-8") as handle:
                vendor = handle.read().strip().lower().removeprefix("0x")
            with open(product_path, encoding="utf-8") as handle:
                product = handle.read().strip().lower().removeprefix("0x")
        except OSError:
            continue
        if (vendor, product) in RTL_IDS:
            return f"{vendor}:{product}"
    return ""


def rtl_test_succeeds(timeout=8):
    """True when ``rtl_test -t`` exits 0. A timeout is not a detection."""

    exe = shutil.which("rtl_test")
    if not exe:
        return False
    try:
        proc = subprocess.run(
            [exe, "-t"],
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    if proc.returncode == 0:
        return True
    text = (proc.stdout + proc.stderr).decode("utf-8", "replace").lower()
    return "found" in text and "no supported device" not in text


def detect(usb_root="/sys/bus/usb/devices", run_test=None, rtl_test=None):
    """USB id 0bda:2838 / 0bda:2832, or a successful rtl_test."""

    if run_test is None:
        run_test = os.environ.get("RADIO_SKIP_RTL_TEST") != "1"
    usb = find_rtl_usb(usb_root)
    if usb:
        return Hardware(True, f"RTL-SDR ready ({usb})", "usb", usb)
    if run_test:
        ok = rtl_test() if rtl_test is not None else rtl_test_succeeds()
        if ok:
            return Hardware(True, "RTL-SDR ready", "rtl_test", "")
    return Hardware(False, NO_RADIO, "", "")


def fm_pipeline(mhz):
    """The two commands live FM uses. Names only; start() fills in PATH."""

    freq = f"{float(mhz):.4f}M"
    rtl_cmd = ["rtl_fm", "-f", freq, "-M", "wbfm", "-s", "200000", "-r", "48000", "-A", "fast"]
    play_cmd = ["aplay", "-r", "48000", "-f", "S16_LE", "-t", "raw", "-c", "1", "-q"]
    device = os.environ.get("RADIO_ALSA_DEVICE", "").strip()
    if device:
        play_cmd[1:1] = ["-D", device]
    return rtl_cmd, play_cmd


def nudge_mhz(mhz, steps):
    value = round(float(mhz) + steps * FM_STEP, 1)
    return min(FM_HIGH, max(FM_LOW, value))


def rtl_power_cmd():
    return ["rtl_power", "-f", "88M:108M:1M", "-i", "1s", "-1", "-g", "20", "-"]


def parse_rtl_power(text):
    best = None
    for line in str(text or "").splitlines():
        if not line or line.lstrip().startswith("#"):
            continue
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 7:
            continue
        try:
            values = [float(part) for part in parts[6:]]
        except ValueError:
            continue
        if values:
            best = values
    if not best:
        return None
    if len(best) <= 32:
        return best
    out = []
    step = len(best) / 32
    for index in range(32):
        chunk = best[int(index * step) : int((index + 1) * step)] or [best[min(len(best) - 1, int(index * step))]]
        out.append(sum(chunk) / len(chunk))
    return out


def capture_spectrum(timeout=4):
    """One low-res FM sweep. None when rtl_power is missing or too slow."""

    exe = shutil.which("rtl_power")
    if not exe:
        return None, 0.0
    cmd = rtl_power_cmd()
    cmd[0] = exe
    started = time.monotonic()
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None, time.monotonic() - started
    elapsed = time.monotonic() - started
    if elapsed > 2.5:
        return parse_rtl_power(proc.stdout.decode("utf-8", "replace")), elapsed
    if proc.returncode != 0:
        return None, elapsed
    return parse_rtl_power(proc.stdout.decode("utf-8", "replace")), elapsed


def new_screen(log_path=None, usb_root=None, run_test=None, rda_port=None):
    guide = load_freqs()
    if rda_port is None:
        rda_port = os.environ.get("RADIO_RDA_PORT", "")
    return {
        "kind": "radio",
        "mode": "freqs",
        "pane": "",
        "card": 0,
        "pick": 0,
        "log_page": 0,
        "letter_page": 0,
        "typed": "",
        "digits": "",
        "log_path": log_path or log_path_default(),
        "guide": guide,
        "hardware": detect(usb_root=usb_root or "/sys/bus/usb/devices", run_test=run_test),
        "usb_root": usb_root or "/sys/bus/usb/devices",
        "hw_at": time.monotonic(),
        "live_mhz": 93.5,
        "player": FmPlayer(),
        "rda": Rda5807Hook(rda_port),
        "spectrum": None,
        "falls": [],
        "spectrum_ok": True,
        "flash": None,
        "practice": {"elements": "", "text": "", "last_up": None},
        "notice": "",
        "notice_until": 0.0,
        "key_down_at": None,
    }


def log_path_default():
    return log_path()


def cards_of(screen):
    return screen["guide"]["cards"]


def current_card(screen):
    cards = cards_of(screen)
    if not cards:
        return None
    index = max(0, min(len(cards) - 1, int(screen.get("card") or 0)))
    screen["card"] = index
    return cards[index]


def stop_audio(screen):
    player = screen.get("player")
    if player is not None:
        player.stop()
    hook = screen.get("rda")
    if hook is not None and hook.sent and hook.sent[-1] != "OFF":
        hook.off()
    elif hook is not None and player is not None and player.mhz is not None:
        hook.off()


def set_mode(screen, mode):
    if mode not in {"freqs", "log", "morse", "live"}:
        return
    if mode != screen.get("mode"):
        screen["flash"] = None
    if mode == "morse":
        stop_audio(screen)
    screen["mode"] = mode
    screen["pane"] = ""
    if mode == "live":
        card = current_card(screen)
        if card and card.get("group") == "broadcast":
            try:
                screen["live_mhz"] = nudge_mhz(float(card["preset"]), 0)
            except (TypeError, ValueError):
                pass


def step_card(screen, delta):
    cards = cards_of(screen)
    if not cards:
        return
    screen["card"] = max(0, min(len(cards) - 1, int(screen.get("card") or 0) + delta))
    screen["pick"] = screen["card"]


def step_pick(screen, delta):
    cards = cards_of(screen)
    if not cards:
        return
    screen["pick"] = (int(screen.get("pick") or 0) + delta) % len(cards)
    screen["digits"] = ""


def picked_card(screen):
    cards = cards_of(screen)
    if not cards:
        return None
    index = int(screen.get("pick") or 0) % len(cards)
    screen["pick"] = index
    return cards[index]


def listen_label(card):
    return "LISTEN OK" if card.get("listen") else "NOT FOR YOU"


def headline(card, digits=""):
    if digits:
        return f"{digits} MHz"
    return card.get("freq") or ""


def clock_of(at):
    text = str(at or "")
    if "T" in text:
        return text.split("T", 1)[1][:5]
    return text[:5]


def wrap_lines(font, text, width, limit):
    words = str(text or "").split()
    if not words or width <= 0 or limit <= 0:
        return []
    lines = []
    current = ""
    used = 0
    overflow = False
    for word in words:
        trial = word if not current else current + " " + word
        if font.size(trial)[0] <= width:
            current = trial
            used += 1
            continue
        if current:
            lines.append(current)
            current = ""
            if len(lines) == limit:
                overflow = True
                break
        if font.size(word)[0] <= width:
            current = word
            used += 1
            continue
        chunk = ""
        for char in word:
            if font.size(chunk + char)[0] <= width:
                chunk += char
            else:
                break
        current = chunk
        used += 1
    if current and len(lines) < limit:
        lines.append(current)
    if used < len(words):
        overflow = True
    if overflow and lines:
        last = lines[-1]
        while last and font.size(last + "...")[0] > width:
            last = last[:-1]
        lines[-1] = (last + "...") if last else "..."
    return lines


def blit(canvas, font, text, xy, color):
    image = font.render(text, True, color)
    canvas.blit(image, xy)
    return image


def content_box():
    top = TAB_H + MODE_H + 2
    bottom = HEIGHT - STATUS_H
    return pygame.Rect(0, top, WIDTH, max(1, bottom - top))


def add_row(app, canvas, y, height, items):
    """items: (label, wid, enabled, latched). Returns the row rect bottom."""

    count = len(items)
    if count <= 0:
        return y
    avail = WIDTH - 2 * MARGIN
    width = (avail - GAP * (count - 1)) // count
    extra = avail - (width * count + GAP * (count - 1))
    x = MARGIN
    for index, (label, wid, enabled, latched) in enumerate(items):
        grow = 1 if index < extra else 0
        rect = pygame.Rect(x, y, width + grow, height)
        app.add_button(canvas, rect, label, wid, enabled, latched)
        x += width + grow + GAP
    return y + height


def render(app, canvas):
    screen = app.current()
    flash = screen.get("flash")
    if flash and flash.get("on"):
        canvas.fill(GREEN)
        label = flash.get("text") or "SOS"
        image = app.font_freq.render(label, True, BLACK)
        canvas.blit(image, ((WIDTH - image.get_width()) // 2, (HEIGHT - image.get_height()) // 2))
        app.widgets.append(
            {
                "rect": pygame.Rect(0, TAB_H, WIDTH, HEIGHT - TAB_H),
                "id": "radio:stop",
                "enabled": True,
                "label": "STOP",
            }
        )
        return
    _draw_modes(app, canvas, screen)
    box = content_box()
    mode = screen.get("mode")
    pane = screen.get("pane") or ""
    if mode == "freqs":
        _draw_freqs(app, canvas, screen, box)
    elif mode == "log":
        if pane == "add":
            _draw_add(app, canvas, screen, box)
        elif pane == "digits":
            _draw_digits(app, canvas, screen, box)
        else:
            _draw_log(app, canvas, screen, box)
    elif mode == "morse":
        if pane == "practice":
            _draw_practice(app, canvas, screen, box)
        elif pane == "type":
            _draw_type(app, canvas, screen, box)
        else:
            _draw_morse(app, canvas, screen, box)
    else:
        _draw_live(app, canvas, screen, box)
    _draw_status(app, canvas, screen)


def _draw_modes(app, canvas, screen):
    modes = (
        ("FREQ", "freqs"),
        ("LOG", "log"),
        ("MORSE", "morse"),
        ("LIVE", "live"),
    )
    items = [
        (label, f"radio:mode:{name}", True, screen.get("mode") == name) for label, name in modes
    ]
    add_row(app, canvas, TAB_H, MODE_H, items)


def _draw_status(app, canvas, screen):
    top = HEIGHT - STATUS_H
    pygame.draw.line(canvas, DIM, (MARGIN, top), (WIDTH - MARGIN, top))
    now = time.monotonic()
    if screen.get("notice") and now < screen.get("notice_until", 0):
        text = screen["notice"]
    else:
        hardware = screen.get("hardware")
        text = hardware.line if hardware is not None else NO_RADIO
    lines = wrap_lines(app.font_body, text, WIDTH - 2 * MARGIN, 2)
    y = top + 2
    for line in lines:
        blit(canvas, app.font_body, line, (MARGIN, y), GREEN)
        y += app.font_body.get_linesize()


def _draw_freqs(app, canvas, screen, box):
    card = current_card(screen)
    cards = cards_of(screen)
    y = box.top
    legal = wrap_lines(app.font_body, screen["guide"].get("legal") or "", box.width - 2 * MARGIN, 2)
    for line in legal:
        blit(canvas, app.font_body, line, (MARGIN, y), GREEN)
        y += app.font_body.get_linesize()
    y += 2
    if card is None:
        blit(canvas, app.font_title, "No frequency file", (MARGIN, y), GREEN)
    else:
        counter = f"{screen['card'] + 1}/{len(cards)}"
        counter_w = app.font_body.size(counter)[0] + 8
        title = card["title"]
        while title and app.font_title.size(title)[0] > box.width - counter_w - 8:
            title = title[:-1]
        blit(canvas, app.font_title, title, (MARGIN, y), GREEN)
        image = blit(canvas, app.font_body, counter, (WIDTH - MARGIN - app.font_body.size(counter)[0], y), GREEN)
        y += max(app.font_title.get_linesize(), image.get_height()) + 2
        freq = card["freq"]
        face = app.font_freq
        if face.size(freq)[0] > box.width - 2 * MARGIN:
            face = app.font_title
        image = blit(canvas, face, freq, (MARGIN, y), GREEN)
        y += image.get_height() + 2
        mark = listen_label(card)
        blit(canvas, app.font_button, mark, (MARGIN, y), GREEN)
        y += app.font_button.get_linesize() + 2
        summary = wrap_lines(app.font_body, card.get("summary") or "", box.width - 2 * MARGIN, 1)
        for line in summary:
            blit(canvas, app.font_body, line, (MARGIN, y), GREEN)
            y += app.font_body.get_linesize()
    button_h = 48
    button_y = box.bottom - button_h
    index = int(screen.get("card") or 0)
    add_row(
        app,
        canvas,
        button_y,
        button_h,
        [
            ("Prev", "radio:prev", index > 0, False),
            ("Signals", "radio:signals", True, False),
            ("Next", "radio:next", index + 1 < len(cards), False),
        ],
    )


def _draw_log(app, canvas, screen, box):
    rows = list(reversed(read_log(screen["log_path"])))
    button_h = 48
    list_bottom = box.bottom - button_h - GAP
    row_h = 44
    per = max(1, (list_bottom - box.top) // (row_h + GAP))
    per = min(per, 3)
    pages = max(1, (len(rows) + per - 1) // per)
    page = max(0, min(pages - 1, int(screen.get("log_page") or 0)))
    screen["log_page"] = page
    screen["_log_per"] = per
    if not rows:
        blit(canvas, app.font_title, "No entries yet", (MARGIN, box.top + 8), GREEN)
        blit(canvas, app.font_body, "Tap ADD to log what you hear.", (MARGIN, box.top + 36), GREEN)
    else:
        y = box.top
        for entry in rows[page * per : page * per + per]:
            line = f"{clock_of(entry['at'])}  {entry['freq']}"
            tag = entry["tag"].upper()
            blit(canvas, app.font_body, line, (MARGIN, y + 2), GREEN)
            tag_image = app.font_button.render(tag, True, GREEN)
            canvas.blit(tag_image, (WIDTH - MARGIN - tag_image.get_width(), y + 2))
            label = entry["label"]
            while label and app.font_body.size(label)[0] > box.width - 8:
                label = label[:-1]
            blit(canvas, app.font_body, label, (MARGIN, y + app.font_body.get_linesize() + 2), GREEN)
            y += row_h + GAP
    add_row(
        app,
        canvas,
        box.bottom - button_h,
        button_h,
        [
            ("Up", "radio:log-up", page > 0, False),
            ("ADD", "radio:log-add", True, False),
            ("Down", "radio:log-down", page + 1 < pages, False),
        ],
    )


def _draw_add(app, canvas, screen, box):
    card = picked_card(screen)
    tag_h = 44
    row_h = 44
    tags2_y = box.bottom - tag_h
    tags1_y = tags2_y - GAP - tag_h
    nav_y = tags1_y - GAP - row_h
    y = box.top
    stamp = time.strftime("%H:%M")
    blit(canvas, app.font_body, stamp, (MARGIN, y), GREEN)
    if card is not None:
        title = card["title"]
        while title and app.font_body.size(stamp + "  " + title)[0] > box.width - 8:
            title = title[:-1]
        blit(canvas, app.font_body, title, (MARGIN + app.font_body.size(stamp + "  ")[0], y), GREEN)
    y += app.font_body.get_linesize() + 2
    text = headline(card or {}, screen.get("digits") or "")
    face = app.font_freq if app.font_freq.size(text)[0] <= box.width - 8 else app.font_title
    if y + face.get_height() > nav_y:
        face = app.font_title
    blit(canvas, face, text, (MARGIN, y), GREEN)
    add_row(
        app,
        canvas,
        nav_y,
        row_h,
        [
            ("Prev", "radio:pick-prev", True, False),
            ("123", "radio:digits", True, False),
            ("Next", "radio:pick-next", True, False),
        ],
    )
    add_row(
        app,
        canvas,
        tags1_y,
        tag_h,
        [
            ("HEARD", "radio:tag:heard", True, False),
            ("CLEAR", "radio:tag:clear", True, False),
        ],
    )
    add_row(
        app,
        canvas,
        tags2_y,
        tag_h,
        [
            ("NOISY", "radio:tag:noisy", True, False),
            ("NOTHING", "radio:tag:nothing", True, False),
        ],
    )


def _draw_digits(app, canvas, screen, box):
    done_h = 44
    done_y = box.bottom - done_h
    y = box.top
    text = (screen.get("digits") or "") + "_"
    blit(canvas, app.font_title, text, (MARGIN, y), GREEN)
    y += app.font_title.get_linesize() + 2
    rows = (("1", "2", "3"), ("4", "5", "6"), ("7", "8", "9"))
    gap_budget = GAP * len(rows)
    row_h = max(40, (done_y - y - gap_budget) // len(rows))
    for row in rows:
        items = [(token, f"radio:digit:{token}", True, False) for token in row]
        add_row(app, canvas, y, row_h, items)
        y += row_h + GAP
    add_row(
        app,
        canvas,
        done_y,
        done_h,
        [
            (".", "radio:digit:.", True, False),
            ("0", "radio:digit:0", True, False),
            ("DEL", "radio:digit:DEL", True, False),
            ("OK", "radio:digit:OK", True, False),
        ],
    )


def _draw_morse(app, canvas, screen, box):
    y = box.top
    add_row(app, canvas, y, 64, [("SOS", "radio:word:SOS", True, False)])
    y += 64 + GAP
    add_row(
        app,
        canvas,
        y,
        44,
        [(word, f"radio:word:{word}", True, screen.get("typed") == word) for word in PRESET_WORDS if word != "SOS"],
    )
    y += 44 + GAP
    word = screen.get("typed") or "SOS"
    blit(canvas, app.font_body, f"{word}   {WPM} WPM", (MARGIN, y), GREEN)
    y = box.bottom - 48
    playing = bool(screen.get("flash"))
    add_row(
        app,
        canvas,
        y,
        48,
        [
            ("STOP" if playing else "TYPE", "radio:stop" if playing else "radio:type", True, False),
            ("PRACTICE", "radio:practice", True, False),
        ],
    )


def _draw_type(app, canvas, screen, box):
    y = box.top
    word = screen.get("typed") or ""
    blit(canvas, app.font_title, word or "(word)", (MARGIN, y), GREEN)
    y += app.font_title.get_linesize() + GAP
    page = int(screen.get("letter_page") or 0) % len(LETTER_PAGES)
    screen["letter_page"] = page
    letters = LETTER_PAGES[page]
    row_h = 48
    mid = (len(letters) + 1) // 2
    for chunk in (letters[:mid], letters[mid:]):
        if not chunk:
            continue
        items = [(char, f"radio:letter:{char}", True, False) for char in chunk]
        add_row(app, canvas, y, row_h, items)
        y += row_h + GAP
    add_row(
        app,
        canvas,
        box.bottom - 48,
        48,
        [
            ("DEL", "radio:letter:DEL", True, False),
            ("MORE", "radio:letters-more", True, False),
            ("DONE", "radio:type-done", True, False),
        ],
    )


def _draw_practice(app, canvas, screen, box):
    practice = screen.get("practice") or {}
    y = box.top
    text = practice.get("text") or ""
    elements = practice.get("elements") or ""
    shown = text if text else "—"
    image = blit(canvas, app.font_freq, shown, (MARGIN, y), GREEN)
    y += image.get_height() + 2
    blit(canvas, app.font_title, elements or "tap", (MARGIN, y), GREEN)
    y += app.font_title.get_linesize() + GAP
    key_bottom = box.bottom - 48 - GAP
    key_h = max(48, key_bottom - y)
    app.add_button(canvas, pygame.Rect(MARGIN, y, WIDTH - 2 * MARGIN, key_h), "KEY", "radio:key", True, False)
    add_row(
        app,
        canvas,
        box.bottom - 48,
        48,
        [
            ("CLEAR", "radio:clear", True, False),
            ("BACK", "radio:practice-back", True, False),
        ],
    )


def _broadcast_presets(screen):
    found = []
    for card in cards_of(screen):
        if card.get("group") != "broadcast":
            continue
        try:
            mhz = float(card.get("preset") or "")
        except ValueError:
            continue
        if FM_LOW <= mhz <= FM_HIGH:
            found.append((card["short"], mhz))
    return found[:4]


def _draw_live(app, canvas, screen, box):
    hardware = screen.get("hardware")
    present = bool(hardware and hardware.present)
    y = box.top
    if not present:
        lines = wrap_lines(app.font_title, NO_RADIO, box.width - 2 * MARGIN, 4)
        for line in lines:
            blit(canvas, app.font_title, line, (MARGIN, y), GREEN)
            y += app.font_title.get_linesize() + 2
        blit(canvas, app.font_body, screen["rda"].status(), (MARGIN, box.bottom - app.font_body.get_linesize() - 4), GREEN)
        return
    mhz = screen.get("live_mhz") or 93.5
    image = blit(canvas, app.font_freq, f"{mhz:.1f} MHz", (MARGIN, y), GREEN)
    y += image.get_height() + GAP
    playing = screen["player"].playing() or (
        os.environ.get("RADIO_NO_AUDIO") == "1" and screen.get("_listen_armed")
    )
    add_row(
        app,
        canvas,
        y,
        44,
        [
            ("DOWN", "radio:down", True, False),
            ("STOP" if playing else "LISTEN", "radio:listen", True, playing),
            ("UP", "radio:up", True, False),
        ],
    )
    y += 44 + GAP
    presets = _broadcast_presets(screen)
    if presets:
        items = []
        for short, value in presets:
            items.append((short, f"radio:preset:{value}", True, abs(value - float(mhz)) < 0.05))
        add_row(app, canvas, y, 40, items)
        y += 40 + GAP
    plot_bottom = box.bottom - app.font_body.get_linesize() - 4
    plot = pygame.Rect(MARGIN, y, WIDTH - 2 * MARGIN, max(8, plot_bottom - y))
    _draw_spectrum(canvas, app, screen, plot)
    app.widgets.append({"rect": plot, "id": "radio:bars", "enabled": True, "label": "BARS"})
    blit(canvas, app.font_body, screen["rda"].status(), (MARGIN, box.bottom - app.font_body.get_linesize()), DIM)


def _draw_spectrum(canvas, app, screen, rect):
    bins = screen.get("spectrum")
    if not screen.get("spectrum_ok", True):
        blit(canvas, app.font_body, "Spectrum skipped. Too slow on this Pi.", (rect.x, rect.y), GREEN)
        return
    if not bins:
        blit(canvas, app.font_body, "BARS", (rect.x, rect.y), GREEN)
        blit(canvas, app.font_body, "Tap for a low-res FM sweep", (rect.x, rect.y + app.font_body.get_linesize()), GREEN)
        return
    low = min(bins)
    high = max(bins)
    span = high - low or 1.0
    count = len(bins)
    gap = 1
    bar_w = max(1, (rect.width - gap * (count - 1)) // count)
    for index, value in enumerate(bins):
        height = max(2, int((value - low) / span * (rect.height - 4)))
        column = pygame.Rect(rect.x + index * (bar_w + gap), rect.bottom - height, bar_w, height)
        pygame.draw.rect(canvas, GREEN, column)
    falls = screen.get("falls") or []
    if len(falls) >= 2:
        row_h = 3
        top = rect.y
        for row_index, row in enumerate(falls[-6:]):
            for index, value in enumerate(row[:count]):
                unit = (value - low) / span
                if unit < 0.55:
                    continue
                pixel = pygame.Rect(rect.x + index * (bar_w + gap), top + row_index * row_h, bar_w, 2)
                pygame.draw.rect(canvas, DIM if unit < 0.8 else GREEN, pixel)


def refresh_hardware(screen, now=None):
    now = time.monotonic() if now is None else now
    if now - screen.get("hw_at", 0) < 5:
        return False
    screen["hw_at"] = now
    usb = find_rtl_usb(screen.get("usb_root") or "/sys/bus/usb/devices")
    hardware = screen.get("hardware")
    if usb and (hardware is None or not hardware.present or hardware.via == "usb"):
        screen["hardware"] = Hardware(True, f"RTL-SDR ready ({usb})", "usb", usb)
        return True
    if not usb and hardware is not None and hardware.via == "usb":
        stop_audio(screen)
        screen["hardware"] = Hardware(False, NO_RADIO, "", "")
        return True
    return False


def tick(screen, now=None):
    """Advance a Morse flash or a practice letter. True when the picture changes."""

    if screen.get("kind") != "radio":
        return False
    now = time.monotonic() if now is None else now
    changed = refresh_hardware(screen, now)
    flash = screen.get("flash")
    if flash is not None and now >= flash.get("until", 0):
        flash["index"] = flash.get("index", 0) + 1
        events = flash.get("events") or []
        if flash["index"] >= len(events):
            screen["flash"] = None
        else:
            on, duration = events[flash["index"]]
            flash["on"] = on
            flash["until"] = now + duration
        changed = True
    practice = screen.get("practice") or {}
    elements = practice.get("elements") or ""
    last = practice.get("last_up")
    if elements and last is not None and screen.get("key_down_at") is None and now - last >= DIT_S * 3:
        letter = decode_elements(elements)
        text = practice.get("text") or ""
        if now - last >= DIT_S * 7 and text and not text.endswith(" "):
            letter += " "
        practice["text"] = (text + letter)[-24:]
        practice["elements"] = ""
        practice["last_up"] = None
        changed = True
    return changed


def busy(screen):
    if not screen or screen.get("kind") != "radio":
        return False
    if screen.get("flash"):
        return True
    practice = screen.get("practice") or {}
    return bool(practice.get("elements"))


def note(screen, text, seconds=1.6):
    screen["notice"] = text
    screen["notice_until"] = time.monotonic() + seconds


def start_flash(screen, text, now=None):
    events = schedule(text)
    if not events:
        return
    stop_audio(screen)
    now = time.monotonic() if now is None else now
    on, duration = events[0]
    screen["flash"] = {
        "events": events,
        "index": 0,
        "on": on,
        "until": now + duration,
        "text": text,
    }
    screen["typed"] = text


def key_hold(screen, held, now=None):
    practice = screen.setdefault("practice", {"elements": "", "text": "", "last_up": None})
    practice["elements"] = (practice.get("elements") or "") + ("-" if held >= DIT_S * 2 else ".")
    practice["last_up"] = time.monotonic() if now is None else now


def save_tag(screen, tag):
    card = picked_card(screen)
    digits = screen.get("digits") or ""
    if digits:
        freq = f"{digits} MHz"
        label = "manual"
    elif card is not None:
        freq = card["freq"]
        label = card["title"]
    else:
        return
    append_log(screen["log_path"], freq, tag, label)
    screen["pane"] = ""
    screen["digits"] = ""
    screen["log_page"] = 0
    note(screen, f"Saved {freq} {tag.upper()}")


def on_tap(app, wid, now=None):
    screen = app.current()
    if screen.get("kind") != "radio":
        return
    now = time.monotonic() if now is None else now
    if wid == "stop":
        screen["flash"] = None
        return
    if wid.startswith("mode:"):
        set_mode(screen, wid.split(":", 1)[1])
        return
    mode = screen.get("mode")
    pane = screen.get("pane") or ""
    if wid == "signals":
        app.open_signals(screen["guide"].get("guide") or "signals")
        return
    if wid == "prev":
        step_card(screen, -1)
        return
    if wid == "next":
        step_card(screen, 1)
        return
    if wid == "log-add":
        screen["pane"] = "add"
        screen["pick"] = int(screen.get("card") or 0)
        screen["digits"] = ""
        return
    if wid == "log-up":
        screen["log_page"] = max(0, int(screen.get("log_page") or 0) - 1)
        return
    if wid == "log-down":
        screen["log_page"] = int(screen.get("log_page") or 0) + 1
        return
    if wid == "pick-prev":
        step_pick(screen, -1)
        return
    if wid == "pick-next":
        step_pick(screen, 1)
        return
    if wid == "digits":
        card = picked_card(screen)
        if not screen.get("digits") and card is not None and card.get("preset"):
            screen["digits"] = card["preset"]
        screen["pane"] = "digits"
        return
    if wid.startswith("digit:"):
        token = wid.split(":", 1)[1]
        if token == "OK":
            screen["pane"] = "add"
            return
        digits = screen.get("digits") or ""
        if token == "DEL":
            screen["digits"] = digits[:-1]
        elif token == ".":
            if "." not in digits and len(digits) < 10:
                screen["digits"] = digits + "."
        elif token.isdigit() and len(digits) < 10:
            screen["digits"] = digits + token
        return
    if wid.startswith("tag:"):
        save_tag(screen, wid.split(":", 1)[1])
        return
    if wid.startswith("word:"):
        start_flash(screen, wid.split(":", 1)[1], now)
        return
    if wid == "type":
        screen["pane"] = "type"
        screen["typed"] = ""
        return
    if wid == "practice":
        screen["pane"] = "practice"
        screen["flash"] = None
        screen["practice"] = {"elements": "", "text": "", "last_up": None}
        return
    if wid == "practice-back" or wid == "type-done":
        screen["pane"] = ""
        return
    if wid == "letters-more":
        screen["letter_page"] = (int(screen.get("letter_page") or 0) + 1) % len(LETTER_PAGES)
        return
    if wid.startswith("letter:"):
        token = wid.split(":", 1)[1]
        typed = screen.get("typed") or ""
        if token == "DEL":
            screen["typed"] = typed[:-1]
        elif len(typed) < 12:
            screen["typed"] = typed + token
        return
    if wid == "clear":
        screen["practice"] = {"elements": "", "text": "", "last_up": None}
        return
    if wid == "key":
        down = screen.pop("key_down_at", None)
        if down is not None:
            key_hold(screen, max(0.0, now - down), now)
        return
    if mode == "live" and wid == "down":
        _retune(screen, -1)
        return
    if mode == "live" and wid == "up":
        _retune(screen, 1)
        return
    if wid.startswith("preset:"):
        try:
            screen["live_mhz"] = nudge_mhz(float(wid.split(":", 1)[1]), 0)
        except ValueError:
            return
        if screen["player"].playing() or screen.get("_listen_armed"):
            _engage(screen)
        return
    if wid == "listen":
        if screen["player"].playing() or screen.get("_listen_armed"):
            screen["_listen_armed"] = False
            stop_audio(screen)
            note(screen, "Stopped")
        else:
            _engage(screen)
        return
    if wid == "bars":
        _sweep(screen)
        return


def _retune(screen, steps):
    screen["live_mhz"] = nudge_mhz(screen.get("live_mhz") or 93.5, steps)
    if screen["player"].playing() or screen.get("_listen_armed"):
        _engage(screen)


def _engage(screen):
    hardware = screen.get("hardware")
    if hardware is None or not hardware.present:
        note(screen, NO_RADIO)
        return
    mhz = screen.get("live_mhz") or 93.5
    screen["rda"].tune(mhz)
    message = screen["player"].start(mhz)
    if message == "audio disabled":
        screen["_listen_armed"] = True
        note(screen, f"Tuned {mhz:.1f} MHz")
        return
    if message:
        note(screen, message)
        return
    screen["_listen_armed"] = True
    note(screen, f"Listening {mhz:.1f} MHz")


def _sweep(screen):
    hardware = screen.get("hardware")
    if hardware is None or not hardware.present:
        note(screen, NO_RADIO)
        return
    if screen["player"].playing():
        note(screen, "Stop listening before a sweep")
        return
    if not screen.get("spectrum_ok", True):
        note(screen, "Spectrum skipped. Too slow on this Pi.")
        return
    bins, elapsed = capture_spectrum()
    if elapsed > 2.5:
        screen["spectrum_ok"] = False
        note(screen, "Spectrum skipped. Too slow on this Pi.")
    if bins:
        screen["spectrum"] = bins
        falls = list(screen.get("falls") or [])
        falls.append(list(bins))
        screen["falls"] = falls[-6:]
    elif screen.get("spectrum_ok", True):
        note(screen, "No sweep. rtl_power did not run.")


def swipe(screen, direction):
    """direction -1 is toward the previous card (finger moved right)."""

    if screen.get("kind") != "radio":
        return False
    mode = screen.get("mode")
    pane = screen.get("pane") or ""
    if mode == "freqs" and not pane:
        step_card(screen, direction)
        return True
    if mode == "log" and pane == "add":
        step_pick(screen, direction)
        return True
    if mode == "morse" and pane == "type":
        screen["letter_page"] = (int(screen.get("letter_page") or 0) + direction) % len(LETTER_PAGES)
        return True
    if mode == "log" and not pane:
        screen["log_page"] = max(0, int(screen.get("log_page") or 0) + direction)
        return True
    return False


def check_logic(check):
    """Data, Morse, log, and hardware checks. No pygame drawing."""

    guide = load_freqs()
    cards = guide["cards"]
    check(guide.get("guide") == "signals", "frequency file points at the signals sheet")
    legal = guide.get("legal") or ""
    check("Wireless Telegraphy Act s48" in legal and "PMR" in legal and "marine" in legal, "legal note")
    check("Airband" in legal, "legal note names airband")
    by_title = {card["title"]: card for card in cards}
    radio4 = by_title.get("BBC Radio 4 FM")
    check(radio4 is not None and "92.5-96.1" in radio4["freq"] and "103.5-104.9" in radio4["freq"], "Radio 4 FM ranges")
    check(radio4 is not None and radio4["listen"] is True, "broadcast listening is marked ok")
    pmr = [card for card in cards if card["title"].startswith("PMR446 ch ")]
    check(len(pmr) == 16, f"PMR446 has 16 channels ({len(pmr)})")
    for index, card in enumerate(pmr, start=1):
        check(card["title"].endswith(str(index)), f"PMR order {card['title']}")
        check(Decimal(card["preset"]) == pmr446_mhz(index), f"PMR {index} frequency {card['preset']}")
        check(card["listen"] is False, f"PMR {index} is not general reception")
    marine = by_title.get("Marine VHF Ch16")
    check(marine is not None and marine["preset"] == "156.8" and marine["listen"] is False, "marine Ch16")
    calling = by_title.get("2 m calling")
    check(calling is not None and calling["preset"] == "145.500" and calling["listen"] is True, "2 m calling")
    msf = by_title.get("MSF time signal")
    check(msf is not None and "60 kHz" in msf["freq"] and msf["listen"] is True, "MSF")
    lora = by_title.get("Meshtastic EU868")
    check(lora is not None and "869.525" in lora["freq"] and lora["listen"] is False, "Meshtastic")
    blob = json.dumps(guide)
    check("MAYDAY" not in blob, "frequency file does not copy the signals sheet")

    check(pattern("E") == [(True, 1)], "E is one dit")
    check(pattern("A") == [(True, 1), (False, 1), (True, 3)], "A timing")
    sos = pattern("SOS")
    check(sos[0] == (True, 1) and sos[-1] == (True, 1), "SOS prosign ends on a dit")
    ons = [units for on, units in sos if on]
    check(ons == [1, 1, 1, 3, 3, 3, 1, 1, 1], f"SOS elements {ons}")
    check(all(units == 1 for on, units in sos if not on), "SOS has no letter gap")
    check(schedule("E", wpm=10) == [(True, 0.12)], "10 WPM dit is 120 ms")
    check(decode_elements(".-") == "A" and decode_elements("...") == "S", "decode A and S")
    check(decode_elements("---") == "O" and decode_elements("..") == "I", "decode O and I")

    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "radio_log.json")
        check(read_log(path) == [], "missing log is empty")
        saved = append_log(path, "92.5-96.1 / 103.5-104.9 MHz", "heard", "BBC Radio 4 FM", at="2026-10-20T21:04:00")
        rows = read_log(path)
        check(len(rows) == 1 and rows[0] == saved, "log round trip")
        check(rows[0]["tag"] == "heard" and rows[0]["at"].endswith("21:04:00"), "log stamp and tag")
        append_log(path, "145.500 MHz", "nothing", "2 m calling", at="2026-10-20T21:10:00")
        check([row["tag"] for row in read_log(path)] == ["heard", "nothing"], "log keeps order")
        try:
            append_log(path, "1", "nope", "x")
            check(False, "bad tag rejected")
        except ValueError:
            check(True, "bad tag rejected")

        usb = os.path.join(tmp, "usb")
        device = os.path.join(usb, "1-1")
        os.makedirs(device)
        with open(os.path.join(device, "idVendor"), "w", encoding="utf-8") as handle:
            handle.write("0bda\n")
        with open(os.path.join(device, "idProduct"), "w", encoding="utf-8") as handle:
            handle.write("2838\n")
        found = detect(usb_root=usb, run_test=False)
        check(found.present and found.usb == "0bda:2838", f"USB RTL-SDR {found.usb}")
        other = os.path.join(tmp, "empty")
        os.makedirs(other)
        missing = detect(usb_root=other, run_test=False)
        check((not missing.present) and missing.line == NO_RADIO, "missing dongle message")
        via_test = detect(usb_root=other, run_test=True, rtl_test=lambda: True)
        check(via_test.present and via_test.via == "rtl_test", "rtl_test success enables live")
        skipped = detect(usb_root=other, run_test=True, rtl_test=lambda: False)
        check(not skipped.present, "failed rtl_test stays offline")

    rtl_cmd, play_cmd = fm_pipeline(93.5)
    check(rtl_cmd[:3] == ["rtl_fm", "-f", "93.5000M"] and "-A" in rtl_cmd and "fast" in rtl_cmd, "rtl_fm command")
    check(play_cmd[0] == "aplay" and "48000" in play_cmd, "aplay command")
    check(nudge_mhz(108.0, 1) == 108.0 and nudge_mhz(87.5, -1) == 87.5, "FM stays in broadcast")
    check(abs(nudge_mhz(93.5, 1) - 93.6) < 0.001, "FM step is 0.1")
    sample = "2026-10-20, 12:00:00, 88000000, 108000000, 1000000, 1, -40, -20, -10"
    parsed = parse_rtl_power(sample)
    check(parsed == [-40.0, -20.0, -10.0], f"rtl_power parse {parsed}")
    hook = Rda5807Hook(port="", send=lambda _line: None)
    check(hook.status() == "RDA5807 not attached", "RDA hook idle")
    hook.tune(93.5)
    hook.off()
    check(hook.sent == ["FREQ 93.5", "OFF"], f"RDA lines {hook.sent}")
    armed = Rda5807Hook(port="/dev/ttyUSB0", send=lambda _line: None)
    check(armed.status().startswith("RDA5807 hook"), "RDA hook names the port")


def _tap(app, wid):
    app.last_fire = None
    widget = next(item for item in app.widgets if item["id"] == wid)
    app.pointer("down", *widget["rect"].center)
    app.pointer("up", *widget["rect"].center)


def _fit(check, app, label):
    limit = HEIGHT - STATUS_H
    for widget in app.widgets:
        rect = widget["rect"]
        floor = HEIGHT if widget["id"] == "radio:stop" else limit
        check(
            rect.left >= 0 and rect.top >= TAB_H and rect.right <= WIDTH and rect.bottom <= floor,
            f"{label} {widget['id']} on screen {tuple(rect)}",
        )
        if widget["id"].startswith(("radio:mode:", "radio:tag:")) or widget["id"] in {"radio:word:SOS", "radio:log-add"}:
            check(rect.height >= 44, f"{label} {widget['id']} height {rect.height}")
    for index, widget in enumerate(app.widgets):
        for other in app.widgets[index + 1 :]:
            if widget["rect"].colliderect(other["rect"]):
                check(False, f"{label} overlap {widget['id']} {other['id']}")


def exercise(make_app, canvas, check, screenshot_dir=None):
    """Drive the RADIO screens the same way the touch loop does."""

    os.environ["RADIO_SKIP_RTL_TEST"] = "1"
    os.environ["RADIO_NO_AUDIO"] = "1"
    check_logic(check)
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "radio_log.json")
        app = make_app()
        app.activate("tab:RADIO")
        check(app.current().get("kind") == "radio", "RADIO tab opens the radio screen")
        check(app.notice != "Radio is not available.", "RADIO tab is not the old placeholder")
        app.current()["log_path"] = path
        app.draw(canvas)
        check(any(widget["id"] == "radio:mode:freqs" for widget in app.widgets), "freq mode button")
        _fit(check, app, "freqs")
        titles = []
        guard = 0
        while guard < 40:
            card = current_card(app.current())
            titles.append(card["title"] if card else "")
            if card and card["title"] == "BBC Radio 4 FM":
                break
            _tap(app, "radio:next")
            app.draw(canvas)
            guard += 1
        check(current_card(app.current())["title"] == "BBC Radio 4 FM", "next reaches Radio 4")
        app.draw(canvas)
        if screenshot_dir:
            pygame.image.save(canvas, os.path.join(screenshot_dir, "radio_freqs.png"))
        _tap(app, "radio:signals")
        opened = app.current()
        check(opened.get("kind") == "menu" and "SIGNAL" in opened.get("title", ""), f"signals link {opened.get('title')}")
        labels = [item["label"] for item in opened.get("items") or []]
        check(labels and labels[0] == "Rule of Three and SOS", f"signals cards {labels[:3]}")
        app.back()
        check(app.current().get("kind") == "radio", "back returns to radio")

        app.draw(canvas)
        guard = 0
        while current_card(app.current())["title"] != "PMR446 ch 1" and guard < 40:
            _tap(app, "radio:next")
            app.draw(canvas)
            guard += 1
        app.draw(canvas)
        if screenshot_dir:
            pygame.image.save(canvas, os.path.join(screenshot_dir, "radio_pmr.png"))
        check(listen_label(current_card(app.current())) == "NOT FOR YOU", "PMR card is marked")

        _tap(app, "radio:mode:log")
        app.draw(canvas)
        _tap(app, "radio:log-add")
        app.draw(canvas)
        _fit(check, app, "add")
        if screenshot_dir:
            pygame.image.save(canvas, os.path.join(screenshot_dir, "radio_add.png"))
        _tap(app, "radio:tag:heard")
        rows = read_log(path)
        check(len(rows) == 1 and rows[0]["tag"] == "heard" and "446.00625" in rows[0]["freq"], f"saved PMR log {rows}")
        app.draw(canvas)
        _fit(check, app, "log")
        if screenshot_dir:
            pygame.image.save(canvas, os.path.join(screenshot_dir, "radio_log.png"))

        _tap(app, "radio:mode:morse")
        app.draw(canvas)
        _fit(check, app, "morse")
        if screenshot_dir:
            pygame.image.save(canvas, os.path.join(screenshot_dir, "radio_morse.png"))
        start_flash(app.current(), "SOS", now=0.0)
        app.current()["flash"]["on"] = True
        app.draw(canvas)
        sample_y = 100 if 100 % 3 else 101
        pixel = canvas.get_at((WIDTH // 2, sample_y))
        check(pixel.g > 180 and pixel.g > pixel.r, f"SOS flash is green {tuple(pixel)}")
        if screenshot_dir:
            pygame.image.save(canvas, os.path.join(screenshot_dir, "radio_morse_flash.png"))
        app.current()["flash"] = None
        _tap(app, "radio:practice")
        app.draw(canvas)
        key = next(widget for widget in app.widgets if widget["id"] == "radio:key")
        check(key["rect"].height >= 48, "practice key is tall")
        # Three dits, then a letter gap, spells S. Hold times go through key_hold.
        practice = app.current()
        for offset in (0.0, 0.2, 0.4):
            practice["key_down_at"] = offset
            on_tap(app, "key", now=offset + 0.05)
        tick(practice, 0.4 + 0.05 + DIT_S * 3 + 0.01)
        check(practice["practice"]["text"] == "S", f"practice decodes S ({practice['practice']})")
        app.draw(canvas)
        if screenshot_dir:
            pygame.image.save(canvas, os.path.join(screenshot_dir, "radio_practice.png"))

        _tap(app, "radio:mode:live")
        app.current()["hardware"] = Hardware(False, NO_RADIO, "", "")
        app.draw(canvas)
        if screenshot_dir:
            pygame.image.save(canvas, os.path.join(screenshot_dir, "radio_live_none.png"))
        check(not any(widget["id"] == "radio:listen" for widget in app.widgets), "live controls wait for hardware")
        app.current()["hardware"] = Hardware(True, "RTL-SDR ready (0bda:2838)", "usb", "0bda:2838")
        app.current()["spectrum"] = [-42, -36, -20, -18, -28, -40, -33, -22]
        app.current()["falls"] = [list(app.current()["spectrum"]), list(app.current()["spectrum"])]
        app.draw(canvas)
        _fit(check, app, "live")
        check(any(widget["id"] == "radio:listen" for widget in app.widgets), "live controls when a dongle is present")
        if screenshot_dir:
            pygame.image.save(canvas, os.path.join(screenshot_dir, "radio_live.png"))
        _tap(app, "radio:up")
        check(abs(app.current()["live_mhz"] - 93.6) < 0.001, "up steps 0.1 MHz")
        _tap(app, "radio:listen")
        check(app.current().get("_listen_armed") is True, "listen arms without opening the dongle in the test")
        check(app.current()["rda"].sent[-1] == "FREQ 93.6", "RDA stub hears the tune")

        guide_app = make_app()
        guide_app.activate("tab:RADIO")
        guide_app.activate("tab:GUIDE")
        check(guide_app.current().get("kind") == "home", "GUIDE still returns home")
        scan_app = make_app()
        scan_app.show_cave = True
        scan_app.draw(canvas)
        scan = next(hit for hit in scan_app.tab_hits if hit["name"] == "SCAN")
        radio_hit = next(hit for hit in scan_app.tab_hits if hit["name"] == "RADIO")
        check(scan["enabled"] and radio_hit["enabled"], "scan and radio both enabled")
        scan_app.pointer("down", *scan["rect"].center)
        scan_app.pointer("up", *scan["rect"].center)
        check(scan_app.pending == "cave", "SCAN still launches cavemap")

    for name in (
        "radio_freqs.png",
        "radio_pmr.png",
        "radio_add.png",
        "radio_log.png",
        "radio_morse.png",
        "radio_morse_flash.png",
        "radio_practice.png",
        "radio_live_none.png",
        "radio_live.png",
    ):
        if not screenshot_dir:
            break
        shot = pygame.image.load(os.path.join(screenshot_dir, name))
        check(shot.get_size() == (WIDTH, HEIGHT), f"{name} is 480x320")
