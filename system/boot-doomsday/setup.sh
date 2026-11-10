#!/bin/bash
# First-boot install of the doomsday deck. Safe to rerun.
# Lives on the boot partition as /boot/firmware/doomsday/setup.sh
# and is started by doomsday-setup.service.
#
# Wi-Fi, the username, and the password come from Raspberry Pi Imager
# (cloud-init). Nothing in this script is a real network name or a login.
# Optional files next to this script, which you create on the card:
#   enable-tft    the 3.5 inch panel is fitted
#   user          one line, the account to install for, if the Pi has
#                 more than one
exec >>/var/log/doomsday-setup.log 2>&1
set -eu
echo "doomsday first-boot $(date -Is)"

if [ -f /var/lib/doomsday-setup-done ]; then
  echo "Doomsday setup already finished."
  exit 0
fi

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export DEBIAN_FRONTEND=noninteractive

if ! command -v curl >/dev/null 2>&1; then
  apt-get update
  apt-get install -y curl ca-certificates
fi

for i in $(seq 1 60); do
  curl -fsI https://github.com >/dev/null && break
  sleep 10
done

apt-get update
apt-get install -y git ca-certificates curl

if [ -z "${DOOMSDAY_USER:-}" ] && [ -f "$HERE/user" ]; then
  DOOMSDAY_USER=$(head -n 1 "$HERE/user" | tr -d '[:space:]')
fi

if [ -z "${DOOMSDAY_USER:-}" ]; then
  for i in $(seq 1 60); do
    DOOMSDAY_USER=$(awk -F: '$3>=1000 && $1!="nobody" {print $1; exit}' /etc/passwd)
    [ -n "$DOOMSDAY_USER" ] && break
    sleep 5
  done
fi

if [ -z "${DOOMSDAY_USER:-}" ]; then
  echo "No deck user yet. Create one in Imager, or write the name into $HERE/user." >&2
  exit 1
fi
export DOOMSDAY_USER

HOME_DIR=$(getent passwd "$DOOMSDAY_USER" | cut -d: -f6)
if [ -z "$HOME_DIR" ] || [ ! -d "$HOME_DIR" ]; then
  echo "No home directory for $DOOMSDAY_USER" >&2
  exit 1
fi

if [ -z "${DOOMSDAY_TFT:-}" ] && [ -f "$HERE/enable-tft" ]; then
  DOOMSDAY_TFT=1
fi
export DOOMSDAY_TFT="${DOOMSDAY_TFT:-0}"

DEST="$HOME_DIR/doomsday-guide"
if [ -d "$DEST/.git" ]; then
  sudo -u "$DOOMSDAY_USER" git -C "$DEST" pull --ff-only -q || true
else
  sudo -u "$DOOMSDAY_USER" git clone https://github.com/haharpoon/doomsday-guide.git "$DEST"
fi

bash "$DEST/scripts/setup_pi.sh"
systemctl disable doomsday-setup.service || true
touch /var/lib/doomsday-setup-done
sync
reboot
