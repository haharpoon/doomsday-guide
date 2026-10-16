#!/bin/bash
set -eu
if [ "$(id -u)" -ne 0 ]; then
  echo "Run this installer as root: sudo bash install.sh" >&2
  exit 1
fi

if ! dpkg -s python3-pygame >/dev/null 2>&1 || ! dpkg -s python3-evdev >/dev/null 2>&1; then
  apt-get install -y python3-pygame python3-evdev \
    || { apt-get update && apt-get install -y python3-pygame python3-evdev; }
fi

BASE="https://raw.githubusercontent.com/haharpoon/doomsday-guide/main"
curl -fsSL "$BASE/field.py" -o /usr/local/bin/field
curl -fsSL "$BASE/field_touch.py" -o /usr/local/bin/field_touch
chmod 755 /usr/local/bin/field /usr/local/bin/field_touch
python3 -m py_compile /usr/local/bin/field /usr/local/bin/field_touch

TARGET="${SUDO_USER:-}"
if [ -z "$TARGET" ] || [ "$TARGET" = "root" ]; then
  TARGET=$(awk -F: '$3>=1000 && $1!="nobody" {print $1; exit}' /etc/passwd)
fi
HOME_DIR=$(getent passwd "$TARGET" | cut -d: -f6)
for grp in input video; do
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
  LAUNCH='/usr/local/bin/field_touch || /usr/local/bin/field || true'
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
  Touchscreen: tap a section. Swipe, or tap Prev and Next, to turn pages.
  Keyboard: type a number, then Enter. Enter continues a page. q goes back.
  Page Up and Page Down are not used.
  Touch guide:  field_touch
  Keyboard guide:  field

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
if [ "$CHOICE" = "1" ]; then
  echo "After login on this screen, the touch guide opens."
  echo "Keyboard guide: type field"
else
  echo "After login on this screen, the keyboard guide opens."
  echo "Touch guide: type field_touch"
fi
echo "Log out or reboot once so this screen and the input group take effect."
