#!/bin/bash
set -eu
if [ "$(id -u)" -ne 0 ]; then
  echo "Run this installer as root: sudo bash install.sh" >&2
  exit 1
fi

if ! dpkg -s python3-pygame >/dev/null 2>&1 || ! dpkg -s python3-evdev >/dev/null 2>&1 \
  || ! dpkg -s python3-numpy >/dev/null 2>&1 || ! dpkg -s python3-serial >/dev/null 2>&1; then
  apt-get install -y python3-pygame python3-evdev python3-numpy python3-serial \
    || { apt-get update && apt-get install -y python3-pygame python3-evdev python3-numpy python3-serial; }
fi

# Live FM is optional. A missing package must not fail the guide install.
if apt-get install -y rtl-sdr alsa-utils; then
  echo "Live radio tools: rtl-sdr and alsa-utils."
else
  echo "rtl-sdr or alsa-utils was not installed. The RADIO tab still opens." >&2
fi

BASE="https://raw.githubusercontent.com/haharpoon/doomsday-guide/main"
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
fetch_file() {
  name="$1"
  dest="$2"
  if [ -f "$SCRIPT_DIR/$name" ]; then
    cp -a "$SCRIPT_DIR/$name" "$dest"
  else
    curl -fsSL "$BASE/$name" -o "$dest"
  fi
}
fetch_file field.py /usr/local/bin/field
fetch_file field_touch.py /usr/local/bin/field_touch
fetch_file tabbar.py /usr/local/bin/tabbar.py
fetch_file cavemap.py /usr/local/bin/cavemap
fetch_file content.py /usr/local/bin/content.py
fetch_file radio.py /usr/local/bin/radio.py
chmod 755 /usr/local/bin/field /usr/local/bin/field_touch /usr/local/bin/cavemap /usr/local/bin/tabbar.py
chmod 644 /usr/local/bin/content.py /usr/local/bin/radio.py
python3 -m py_compile /usr/local/bin/field /usr/local/bin/field_touch /usr/local/bin/cavemap /usr/local/bin/tabbar.py /usr/local/bin/content.py /usr/local/bin/radio.py

# Sheets are Markdown. Writers edit those files; the guides only read them.
install_content() {
  dest="/usr/local/share/doomsday/content"
  rm -rf "$dest"
  mkdir -p "$dest"
  script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
  if [ -d "$script_dir/content" ]; then
    cp -a "$script_dir/content"/. "$dest"/
    chmod -R a+rX "$dest"
    echo "Guide sheets installed to $dest"
    return 0
  fi
  if python3 - "$dest" "$BASE" << 'PY'
import json, os, sys, urllib.request
dest, base = sys.argv[1], sys.argv[2]
api = "https://api.github.com/repos/haharpoon/doomsday-guide/contents/content?ref=main"
headers = {"User-Agent": "doomsday-install", "Accept": "application/vnd.github+json"}

def download(url, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "doomsday-install"})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read()
    with open(path, "wb") as handle:
        handle.write(data)

def fetch_api(url, rel):
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=60) as response:
        items = json.load(response)
    if not isinstance(items, list):
        raise RuntimeError("unexpected content listing")
    for item in items:
        name = item.get("name") or ""
        kind = item.get("type")
        target = os.path.join(dest, rel, name) if rel else os.path.join(dest, name)
        if kind == "dir":
            os.makedirs(target, exist_ok=True)
            fetch_api(item["url"], os.path.join(rel, name) if rel else name)
        elif kind == "file" and item.get("download_url"):
            download(item["download_url"], target)

try:
    fetch_api(api, "")
except Exception as error:
    sys.stderr.write(f"directory listing failed ({error}). Fetching known sheets.\n")
    names = [
        "README.md",
        "shelter.md",
        "shelter_wild.md",
        "shelter_snow.md",
        "shelter_town.md",
        "shelter_long.md",
        "shelter_sources.md",
        "medicine.md",
        "water.md",
        "water_find.md",
        "water_treat.md",
        "water_sources.md",
        "fire.md",
        "fire_light.md",
        "fire_fuel.md",
        "fire_build.md",
        "fire_keep.md",
        "fire_sources.md",
        "knot_which.md",
        "knots_main.md",
        "knots_stoppers.md",
        "knots_hitches.md",
        "knots_more.md",
        "knots_loops.md",
        "knots_bends.md",
        "knots_fishing.md",
        "knots_lashing.md",
        "knots_rope.md",
        "firstaid.md",
        "childbirth.md",
        "mentalhealth.md",
        "tools.md",
        "food.md",
        "food_deadly.md",
        "food_greens.md",
        "food_fruit.md",
        "food_shore.md",
        "food_fungi.md",
        "food_sources.md",
        "growing.md",
        "sanitation.md",
        "navigation.md",
        "nav_nocompass.md",
        "nav_route.md",
        "nav_sources.md",
        "more.md",
        "signals.md",
        "signals_sound.md",
        "signals_light.md",
        "signals_mirrors.md",
        "signals_fire.md",
        "signals_ground.md",
        "signals_body.md",
        "signals_flags.md",
        "signals_trail.md",
        "signals_codes.md",
        "signals_radio.md",
        "signals_pmr.md",
        "signals_plan.md",
        "signals_antennas.md",
        "signals_power.md",
        "signals_news.md",
        "signals_deck.md",
        "signals_mesh.md",
        "signals_sources.md",
        "clothing.md",
        "weather.md",
        "power.md",
        "emergency.md",
        "library.md",
        "cooking.md",
        "animals.md",
        "hunting.md",
        "repairs.md",
        "radio_freqs.json",
    ]
    ok = False
    for name in names:
        try:
            download(base + "/content/" + name, os.path.join(dest, name))
            ok = True
        except Exception as item_error:
            sys.stderr.write(f"missing {name} ({item_error})\n")
    if not ok:
        sys.exit(1)
os.makedirs(os.path.join(dest, "img"), exist_ok=True)
PY
  then
    chmod -R a+rX "$dest"
    echo "Guide sheets installed to $dest"
  else
    echo "Could not install guide sheets. The menu still opens, and search still works." >&2
  fi
}
install_content

TARGET="${SUDO_USER:-}"
if [ -z "$TARGET" ] || [ "$TARGET" = "root" ]; then
  TARGET=$(awk -F: '$3>=1000 && $1!="nobody" {print $1; exit}' /etc/passwd)
fi
HOME_DIR=$(getent passwd "$TARGET" | cut -d: -f6)

# The guide and the scanner write /dev/fb0 and read /dev/input. The ESP32 shows up as USB serial.
for grp in input video dialout; do
  if getent group "$grp" >/dev/null; then
    usermod -aG "$grp" "$TARGET" || true
  fi
done

has_touch() {
  if [ -r /proc/bus/input/devices ] && grep -q "ADS7846 Touchscreen" /proc/bus/input/devices; then
    return 0
  fi
  if [ -r /proc/bus/input/devices ] && grep -qi "touchscreen" /proc/bus/input/devices; then
    return 0
  fi
  python3 - << 'PY'
import sys
try:
    import evdev
except Exception:
    sys.exit(1)
for path in evdev.list_devices():
    try:
        dev = evdev.InputDevice(path)
    except Exception:
        continue
    name = (dev.name or "").lower()
    if name == "ads7846 touchscreen" or "touchscreen" in name or "ads7846" in name:
        sys.exit(0)
sys.exit(1)
PY
}

CHOICE=2
if has_touch; then
  CHOICE=1
fi
if [ -t 0 ]; then
  echo "Open which guide on this screen after login?"
  echo "  1) Touch buttons  (field_touch)"
  echo "  2) Keyboard menu  (field)"
  if [ "$CHOICE" = 1 ]; then
    echo "A touchscreen is connected. Press Enter to use touch."
  else
    echo "No touchscreen found. Press Enter to use the keyboard menu."
  fi
  read -r -p "Choice [$CHOICE]: " picked || picked=""
  if [ "$picked" = "1" ] || [ "$picked" = "2" ]; then
    CHOICE=$picked
  fi
fi

if [ "$CHOICE" = "1" ]; then
  # tty text is drawn onto /dev/fb0. Hide the cursor, keep the panel awake,
  # and send the touch UI's output to a log. The keyboard fallback stays
  # on the console, and the cursor comes back when the GUI exits.
  LAUNCH='setterm --cursor off --blank 0; /usr/local/bin/field_touch >> ~/.doomsday.log 2>&1 || { setterm --cursor on || true; /usr/local/bin/field || true; }; setterm --cursor on || true'
else
  LAUNCH='/usr/local/bin/field || true'
fi

BR="$HOME_DIR/.bashrc"
touch "$BR"
BLOCK_FILE=$(mktemp)
cat > "$BLOCK_FILE" << EOF
# BEGIN DOOMSDAY GUIDE
case "\$(tty 2>/dev/null)" in
  /dev/tty1)
    if [ -z "\${FIELD_RUNNING:-}" ]; then
      export FIELD_RUNNING=1
      ${LAUNCH}
    fi
    ;;
esac
# END DOOMSDAY GUIDE
EOF
python3 - "$BR" "$BLOCK_FILE" << 'PY'
import pathlib, sys
path, block_path = sys.argv[1:]
text = pathlib.Path(path).read_text(encoding="utf-8")
block = pathlib.Path(block_path).read_text(encoding="utf-8")
if not block.endswith("\n"):
    block += "\n"
start = "# BEGIN DOOMSDAY GUIDE\n"
end = "# END DOOMSDAY GUIDE\n"
if start in text and end in text:
    pre, rest = text.split(start, 1)
    _old, post = rest.split(end, 1)
    text = pre + block + post
else:
    if text and not text.endswith("\n"):
        text += "\n"
    text += "\n" + block
pathlib.Path(path).write_text(text, encoding="utf-8")
PY
rm -f "$BLOCK_FILE"
chown "$TARGET:$TARGET" "$BR"

if [ -f /etc/issue ] && [ ! -f /etc/issue.doomsday.bak ]; then
  cp -a /etc/issue /etc/issue.doomsday.bak
fi

cat > /etc/issue << 'ISSUE'

######   ####   ####  #   #  ####  ######  ####  #   #
#    #  #    # #    # ## ## #      #    # #    # #   #
#    #  #    # #    # # # #  ####  #    # ######  # #
#    #  #    # #    # #   #      # #    # #    #   #
######   ####   ####  #   #  ####  ###### #    #   #

 #####  #   #  #####  ######  ######
#       #   #    #    #    #  #
#  ###  #   #    #    #    #  #####
#    #  #   #    #    #    #  #
 #####   ###   #####  ######  ######

DOOMSDAY GUIDE

This screen is the guide.

ON THIS SCREEN
  Log in with your username and password.
  The guide opens after you log in.
  Touchscreen: GUIDE, SCAN, and RADIO are the top bar. Tap a section.
  Swipe, or tap Prev and Next, to turn pages.
  Keyboard: type a number, then Enter. Enter continues a page. q goes back.
  Page Up and Page Down are not used.
  Touch guide:  field_touch
  Keyboard guide:  field
  Cave Mapper:  cavemap

FROM ANOTHER COMPUTER ON THIS NETWORK
  In a browser:  http://\4:8080
  In the remote shell, type:  field

ISSUE

if [ -f /etc/default/console-setup ] && ls /usr/share/consolefonts/*Terminus16.psf.gz >/dev/null 2>&1; then
  sed -i 's/^FONTFACE=.*/FONTFACE="Terminus"/' /etc/default/console-setup || true
  sed -i 's/^FONTSIZE=.*/FONTSIZE="8x16"/' /etc/default/console-setup || true
fi

echo
echo "INSTALLED"
echo "Guide sheets: /usr/local/share/doomsday/content"
if [ "$CHOICE" = "1" ]; then
  echo "After login on this screen, the touch guide opens."
  echo "Keyboard guide: type field"
else
  echo "After login on this screen, the keyboard guide opens."
  echo "Touch guide: type field_touch"
fi
echo "Cave Mapper is the cavemap command. Log in again if it cannot open the LCD."
echo "RADIO is the top-right tab: UK frequencies, a listening log, and Morse."
echo "Plug in an RTL-SDR to tune live FM. Without one, the other radio tools still work."
echo "Log out or reboot once so this screen and the groups take effect."
