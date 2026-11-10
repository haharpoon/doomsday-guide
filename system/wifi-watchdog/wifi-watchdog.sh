#!/bin/sh
# wifi-watchdog: recover the USB Wi-Fi stick if the Pi loses its network.
# The profile name is local to the card. Set WIFI_CONNECTION in
# /etc/default/wifi-watchdog to pick one. Leave it empty to reconnect
# whatever profile NetworkManager already has for WIFI_IFACE.
# Do not put a Wi-Fi password in this script or in that file.
STATE=/run/wifi-watchdog.fail
SAVED=/var/lib/wifi-watchdog.usbpath
IFACE=wlan1
WIFI_CONNECTION=
if [ -f /etc/default/wifi-watchdog ]; then
  # shellcheck disable=SC1091
  . /etc/default/wifi-watchdog
fi
IFACE=${WIFI_IFACE:-$IFACE}
GW=$(ip route show default | awk '{print $3; exit}')
[ -z "$GW" ] && GW=192.168.1.1
if ping -c 3 -W 3 "$GW" >/dev/null 2>&1; then
  rm -f "$STATE"
  # remember the USB device that holds the interface, so we can reset it
  # if it vanishes
  p=$(readlink -f "/sys/class/net/$IFACE/device" 2>/dev/null)
  while [ -n "$p" ] && [ "$p" != "/" ] && [ ! -f "$p/authorized" -o -f "$p/bInterfaceNumber" ]; do p=$(dirname "$p"); done
  [ -n "$p" ] && [ -f "$p/authorized" ] && echo "$p" > "$SAVED"
  exit 0
fi
n=$(cat "$STATE" 2>/dev/null || echo 0); n=$((n+1)); echo "$n" > "$STATE"
logger -t wifi-watchdog "network check failed ($n in a row)"
case "$n" in
  1) nmcli dev disconnect "$IFACE" >/dev/null 2>&1; sleep 3
     if [ -n "$WIFI_CONNECTION" ]; then
       nmcli con up "$WIFI_CONNECTION" >/dev/null 2>&1 || nmcli dev connect "$IFACE" >/dev/null 2>&1
     else
       nmcli dev connect "$IFACE" >/dev/null 2>&1
     fi
     logger -t wifi-watchdog "reconnected $IFACE" ;;
  2|3) p=$(cat "$SAVED" 2>/dev/null)
     if [ -n "$p" ] && [ -f "$p/authorized" ]; then
       echo 0 > "$p/authorized"; sleep 3; echo 1 > "$p/authorized"
       logger -t wifi-watchdog "reset USB Wi-Fi stick at $p"
     fi ;;
  *) if [ "$n" -ge 6 ]; then logger -t wifi-watchdog "still offline, rebooting"; rm -f "$STATE"; systemctl reboot; fi ;;
esac
