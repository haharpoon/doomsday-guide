#!/bin/sh
# Rebuild the Kiwix library list and switch kiwix-serve to read it.
#
#   sh scripts/kiwix_refresh.sh
#
# 1. Adds every ZIM in /var/lib/kiwix/zim to /var/lib/kiwix/library.xml with
#    kiwix-manage. Books already listed are skipped, so it is safe to rerun.
# 2. Installs /etc/systemd/system/kiwix.service.d/library.conf so that
#    kiwix.service runs kiwix-serve --library --monitorLibrary on port 8080
#    instead of a fixed list of ZIMs. The unit and any old drop-in are backed
#    up first to /var/lib/kiwix/backup/<date>/.
# 3. Reloads systemd and restarts kiwix.service.
#
# Later ZIMs only need step 1: kiwix-serve watches library.xml and reloads it.
# Environment overrides (for testing): KIWIX_DIR, UNIT_DIR, SUDO, NO_SYSTEMCTL=1.
set -eu

KIWIX_DIR=${KIWIX_DIR:-/var/lib/kiwix}
ZIM_DIR=$KIWIX_DIR/zim
LIBRARY=$KIWIX_DIR/library.xml
UNIT=kiwix.service
UNIT_DIR=${UNIT_DIR:-/etc/systemd/system}
DROPIN_DIR=$UNIT_DIR/$UNIT.d
DROPIN=$DROPIN_DIR/library.conf
PORT=8080

if [ -z "${SUDO+x}" ]; then
    if [ "$(id -u)" = 0 ]; then SUDO=; else SUDO=sudo; fi
fi

command -v kiwix-manage >/dev/null 2>&1 || { echo "kiwix-manage not found" >&2; exit 1; }
SERVE=$(command -v kiwix-serve) || { echo "kiwix-serve not found" >&2; exit 1; }

$SUDO mkdir -p "$ZIM_DIR"

# --- library.xml -----------------------------------------------------------
added=0 skipped=0
for zim in "$ZIM_DIR"/*.zim; do
    [ -f "$zim" ] || continue
    # kiwix-manage writes the path into library.xml, absolute or relative to
    # the library file depending on version; skip files already there. (Adding
    # a book twice would only update it, as kiwix-manage keys books by UUID.)
    if [ -f "$LIBRARY" ] && grep -qF -e "path=\"$zim\"" -e "path=\"zim/$(basename "$zim")\"" "$LIBRARY"; then
        skipped=$((skipped + 1))
        continue
    fi
    if $SUDO kiwix-manage "$LIBRARY" add "$zim"; then
        added=$((added + 1))
        echo "Added $(basename "$zim")"
    else
        echo "kiwix-manage could not add $zim (damaged or half-downloaded?)" >&2
    fi
done
echo "library.xml: $added added, $skipped already listed ($LIBRARY)"
[ -f "$LIBRARY" ] || { echo "No ZIMs in $ZIM_DIR, so no library.xml. Stopping before touching $UNIT." >&2; exit 1; }
$SUDO chmod a+r "$LIBRARY"

# --- systemd drop-in --------------------------------------------------------
want=$(cat <<CONF
# Installed by doomsday-guide scripts/kiwix_refresh.sh
[Service]
ExecStart=
ExecStart=$SERVE --library --monitorLibrary --port $PORT $LIBRARY
CONF
)

if [ -f "$DROPIN" ] && [ "$(cat "$DROPIN")" = "$want" ]; then
    echo "Drop-in already in place: $DROPIN"
    changed=0
else
    backup=$KIWIX_DIR/backup/$(date +%Y%m%d-%H%M%S)
    $SUDO mkdir -p "$backup"
    [ -f "$UNIT_DIR/$UNIT" ] && $SUDO cp -p "$UNIT_DIR/$UNIT" "$backup/"
    [ -d "$DROPIN_DIR" ] && $SUDO cp -rp "$DROPIN_DIR" "$backup/"
    if [ -z "${NO_SYSTEMCTL:-}" ]; then
        systemctl cat "$UNIT" > /tmp/kiwix.service.cat 2>/dev/null && $SUDO mv /tmp/kiwix.service.cat "$backup/$UNIT.systemctl-cat" || true
    fi
    echo "Backed up the old unit to $backup"
    $SUDO mkdir -p "$DROPIN_DIR"
    printf '%s\n' "$want" | $SUDO tee "$DROPIN.tmp" >/dev/null
    $SUDO mv "$DROPIN.tmp" "$DROPIN"
    echo "Wrote $DROPIN"
    changed=1
fi

if [ -n "${NO_SYSTEMCTL:-}" ]; then
    echo "NO_SYSTEMCTL set: skipping daemon-reload and restart."
    exit 0
fi
if [ "$changed" = 1 ] || ! systemctl is-active --quiet "$UNIT"; then
    $SUDO systemctl daemon-reload
    $SUDO systemctl restart "$UNIT"
fi
sleep 2
if systemctl is-active --quiet "$UNIT"; then
    echo "$UNIT is running: http://<pi-address>:$PORT"
else
    echo "$UNIT failed to start. See: journalctl -u $UNIT -n 50" >&2
    echo "To undo: sudo rm $DROPIN && sudo systemctl daemon-reload && sudo systemctl restart $UNIT" >&2
    exit 1
fi
