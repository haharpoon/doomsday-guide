#!/bin/bash
# Build the doomsday deck on a fresh Raspberry Pi OS Lite.
# Safe to run again.
#
#   git clone https://github.com/haharpoon/doomsday-guide.git
#   cd doomsday-guide
#   sudo bash scripts/setup_pi.sh
#
# The 3.5 inch SPI panel is opt-in. HDMI-only and SSH-only Pis skip it.
#   sudo DOOMSDAY_TFT=1 bash scripts/setup_pi.sh
#   sudo DOOMSDAY_TFT=0 bash scripts/setup_pi.sh
#
# Wi-Fi name, Wi-Fi password, and the Pi login are never written here.
# Imager (or NetworkManager on the card) already has them.
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

if [ "${1:-}" = "--self-test" ]; then
  python3 "$SCRIPT_DIR/apply_tft_boot.py" --self-test
  bash -n "$REPO/scripts/setup_pi.sh"
  bash -n "$REPO/system/boot-doomsday/setup.sh"
  sh -n "$REPO/system/wifi-watchdog/wifi-watchdog.sh"
  echo "setup_pi self-test ok"
  exit 0
fi

if [ "$(id -u)" -ne 0 ]; then
  echo "Run this as root: sudo bash scripts/setup_pi.sh" >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

deck_user() {
  if [ -n "${DOOMSDAY_USER:-}" ]; then
    printf '%s\n' "$DOOMSDAY_USER"
    return
  fi
  if [ -n "${SUDO_USER:-}" ] && [ "$SUDO_USER" != "root" ]; then
    printf '%s\n' "$SUDO_USER"
    return
  fi
  awk -F: '$3>=1000 && $1!="nobody" {print $1; exit}' /etc/passwd
}

DECK_USER=$(deck_user)
if [ -z "$DECK_USER" ]; then
  echo "No user to install for. Set DOOMSDAY_USER to the account you created in Imager." >&2
  exit 1
fi
case "$DECK_USER" in
  root|YOUR_USER)
    echo "Refusing to install for '$DECK_USER'. Set DOOMSDAY_USER to the account you created." >&2
    exit 1
    ;;
esac
if ! printf '%s\n' "$DECK_USER" | grep -qE '^[a-z_][a-z0-9_-]*[$]?$'; then
  echo "Username '$DECK_USER' has characters this setup will not put in a unit file." >&2
  exit 1
fi
if ! id "$DECK_USER" >/dev/null 2>&1; then
  echo "User '$DECK_USER' does not exist on this Pi." >&2
  exit 1
fi
if [ -z "${SUDO_USER:-}" ] || [ "$SUDO_USER" = "root" ]; then
  export SUDO_USER="$DECK_USER"
fi

case "$REPO" in
  *[[:space:]]*|*'\"'*|*"'"*|*%*)
    echo "Move the checkout to a simpler path: $REPO" >&2
    exit 1
    ;;
esac

echo "Doomsday setup for user $DECK_USER"
echo "Checkout: $REPO"

install_packages() {
  missing=""
  while IFS= read -r pkg; do
    status=$(dpkg-query -W -f='${Status}' "$pkg" 2>/dev/null || true)
    if [ "$status" != "install ok installed" ]; then
      missing="$missing $pkg"
    fi
  done < <(grep -vE '^[[:space:]]*(#|$)' "$REPO/system/packages.txt")
  if [ -z "$missing" ]; then
    echo "Packages already installed."
    return 0
  fi
  # shellcheck disable=SC2086
  apt-get update
  # shellcheck disable=SC2086
  apt-get install -y $missing
}

copy_if_needed() {
  src=$1
  dest=$2
  mode=$3
  mkdir -p "$(dirname "$dest")"
  if [ -f "$dest" ] && cmp -s "$src" "$dest"; then
    return 0
  fi
  install -m "$mode" "$src" "$dest"
  echo "Installed $dest"
}

install_packages

copy_if_needed \
  "$REPO/system/network/zz-wifi-powersave-off.conf" \
  /etc/NetworkManager/conf.d/zz-wifi-powersave-off.conf \
  644
if command -v nmcli >/dev/null 2>&1; then
  # Existing Imager profiles keep their own powersave value until it is
  # set on the profile. Names are not printed; they can be the SSID.
  python3 - << 'PY' || true
import subprocess
try:
    out = subprocess.check_output(
        ["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"],
        text=True,
        stderr=subprocess.DEVNULL,
    )
except Exception:
    raise SystemExit(0)
for line in out.splitlines():
    if not line.endswith(":802-11-wireless"):
        continue
    name = line.rsplit(":", 1)[0]
    if not name:
        continue
    subprocess.call(
        ["nmcli", "connection", "modify", name, "802-11-wireless.powersave", "2"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
PY
  systemctl reload NetworkManager >/dev/null 2>&1 || true
fi

copy_if_needed \
  "$REPO/system/modprobe/blacklist-rtlsdr.conf" \
  /etc/modprobe.d/blacklist-rtlsdr.conf \
  644

copy_if_needed \
  "$REPO/system/wifi-watchdog/wifi-watchdog.sh" \
  /usr/local/bin/wifi-watchdog.sh \
  755
copy_if_needed \
  "$REPO/system/wifi-watchdog/wifi-watchdog.service" \
  /etc/systemd/system/wifi-watchdog.service \
  644
copy_if_needed \
  "$REPO/system/wifi-watchdog/wifi-watchdog.timer" \
  /etc/systemd/system/wifi-watchdog.timer \
  644
if [ ! -f /etc/default/wifi-watchdog ]; then
  install -m 644 "$REPO/system/wifi-watchdog/wifi-watchdog.default" /etc/default/wifi-watchdog
  echo "Installed /etc/default/wifi-watchdog (edit WIFI_CONNECTION there if you want a named profile)."
fi
# The saved USB port from the original Pi 3B. Only seed it when that
# port exists on this board. The watchdog rewrites the file once wlan1 is up.
if [ ! -f /var/lib/wifi-watchdog.usbpath ]; then
  usb_path=$(head -n 1 "$REPO/system/wifi-watchdog/wifi-watchdog.usbpath" | tr -d '[:space:]')
  if [ -n "$usb_path" ] && [ -f "$usb_path/authorized" ]; then
    mkdir -p /var/lib
    printf '%s\n' "$usb_path" > /var/lib/wifi-watchdog.usbpath
    echo "Seeded the USB Wi-Fi port at $usb_path"
  fi
fi

autologin() {
  case "${DOOMSDAY_AUTOLOGIN:-1}" in
    0|no|false|off) echo "Leaving console autologin alone."; return 0 ;;
  esac
  dropin=/etc/systemd/system/getty@tty1.service.d/autologin.conf
  mkdir -p "$(dirname "$dropin")"
  sed "s/YOUR_USER/${DECK_USER}/g" "$REPO/system/getty/autologin.conf" > "$dropin"
  chmod 644 "$dropin"
  systemctl set-default multi-user.target >/dev/null 2>&1 || true
  systemctl enable getty@tty1.service >/dev/null 2>&1 || true
  echo "Console on tty1 will log in as $DECK_USER. SSH still asks for your key or password."
}
autologin

find_boot() {
  if [ -n "${DOOMSDAY_BOOT:-}" ]; then
    printf '%s\n' "$DOOMSDAY_BOOT"
    return
  fi
  for dir in /boot/firmware /boot; do
    if [ -f "$dir/config.txt" ] && [ -f "$dir/cmdline.txt" ]; then
      printf '%s\n' "$dir"
      return
    fi
  done
}

want_tft() {
  case "${DOOMSDAY_TFT:-}" in
    1|yes|true|on) return 0 ;;
    0|no|false|off) return 1 ;;
  esac
  if [ ! -t 0 ]; then
    return 1
  fi
  echo
  echo "Enable the 3.5 inch SPI touchscreen (goodtft / Waveshare ILI9486, tft35a, rotate 90)?"
  echo "This comments out the KMS driver and adds initcall_blacklist=simplefb_driver_init"
  echo "so the panel becomes /dev/fb0. HDMI-only: answer no."
  printf 'Enable the panel? [y/N] '
  read -r answer || answer=""
  case "$answer" in
    y|Y|yes|YES) return 0 ;;
    *) return 1 ;;
  esac
}

if want_tft; then
  BOOT=$(find_boot || true)
  if [ -z "${BOOT:-}" ] || [ ! -d "$BOOT" ]; then
    echo "Cannot find config.txt and cmdline.txt under /boot/firmware or /boot." >&2
    exit 1
  fi
  overlay_dir="$BOOT/overlays"
  if [ ! -d "$overlay_dir" ]; then
    echo "No overlays directory at $overlay_dir" >&2
    exit 1
  fi
  copy_if_needed \
    "$REPO/system/boot/overlays/disable-fwfb.dtbo" \
    "$overlay_dir/disable-fwfb.dtbo" \
    644
  python3 "$SCRIPT_DIR/apply_tft_boot.py" "$BOOT"
  if [ -z "${DOOMSDAY_GUIDE:-}" ]; then
    export DOOMSDAY_GUIDE=touch
  fi
else
  echo "HDMI / SSH setup: screen boot files were not changed."
fi

mkdir -p /etc/doomsday /var/lib/kiwix/zim
printf 'DOOMSDAY_REPO=%s\n' "$REPO" > /etc/doomsday/repo.env
chmod 644 /etc/doomsday/repo.env

copy_if_needed \
  "$REPO/system/systemd/kiwix.service" \
  /etc/systemd/system/kiwix.service \
  644
copy_if_needed \
  "$REPO/system/systemd/doomsday-library.service" \
  /etc/systemd/system/doomsday-library.service \
  644

# install.sh adds the guide, the groups, and the login launch.
bash "$REPO/install.sh"

systemctl daemon-reload
systemctl enable wifi-watchdog.timer >/dev/null
systemctl start wifi-watchdog.timer >/dev/null 2>&1 || true

case "${DOOMSDAY_LIBRARY:-1}" in
  0|no|false|off)
    echo "DOOMSDAY_LIBRARY=0: kiwix and the library download were not started."
    ;;
  *)
    systemctl enable kiwix.service >/dev/null
    systemctl enable doomsday-library.service >/dev/null
    # kiwix-serve exits until library.xml exists. That file appears when
    # fetch_library.sh finishes. The unit restarts until then.
    if systemctl is-active --quiet kiwix.service; then
      echo "Kiwix is already running."
    else
      systemctl restart kiwix.service >/dev/null 2>&1 || true
    fi
    if [ -f /var/lib/kiwix/.library-done ]; then
      echo "Library already downloaded (/var/lib/kiwix/.library-done)."
    elif systemctl is-active --quiet doomsday-library.service; then
      echo "Library download is already running. Log: /var/log/doomsday-library.log"
    else
      systemctl start doomsday-library.service >/dev/null 2>&1 || true
      echo "Library download started. Log: /var/log/doomsday-library.log"
    fi
    ;;
esac

touch /var/lib/doomsday-setup-done

echo
echo "SETUP DONE"
echo "User: $DECK_USER"
echo "Guide: type field on the keyboard, or field_touch on the panel."
echo "Library log: /var/log/doomsday-library.log"
echo "Kiwix: systemctl status kiwix    (http://<pi-ip>:8080 once the download has finished)"
if [ "${DOOMSDAY_GUIDE:-}" = "touch" ]; then
  echo "Reboot so the 3.5 inch panel becomes the console."
else
  echo "Reboot once so the login and the groups take effect."
fi
