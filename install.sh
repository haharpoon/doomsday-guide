#!/bin/bash
set -eu
curl -fsSL "https://raw.githubusercontent.com/haharpoon/doomsday-guide/main/field.py" -o /usr/local/bin/field
chmod 755 /usr/local/bin/field
python3 -m py_compile /usr/local/bin/field

TARGET="${SUDO_USER:-}"
if [ -z "$TARGET" ] || [ "$TARGET" = "root" ]; then
  TARGET=$(awk -F: '$3>=1000 && $1!="nobody" {print $1; exit}' /etc/passwd)
fi
HOME_DIR=$(getent passwd "$TARGET" | cut -d: -f6)
BR="$HOME_DIR/.bashrc"
touch "$BR"
if ! grep -q "BEGIN DOOMSDAY GUIDE" "$BR"; then
  cat >> "$BR" << 'BASH'
# BEGIN DOOMSDAY GUIDE
case "$(tty 2>/dev/null)" in
  /dev/tty1)
    if [ -z "${FIELD_RUNNING:-}" ]; then
      export FIELD_RUNNING=1
      /usr/local/bin/field || true
    fi
    ;;
esac
# END DOOMSDAY GUIDE
BASH
fi
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

This screen is the guide. A mouse is not required.

ON THIS SCREEN
  Log in with your username and password.
  The guide opens after you log in.
  Type a number, then Enter. Enter continues a page. q goes back.
  Page Up and Page Down are not used.
  If you leave the guide, type:  field

FROM ANOTHER COMPUTER ON THIS NETWORK
  In a browser:  http://\4:8080
  In the remote shell, type:  field

ISSUE

if [ -f /etc/default/console-setup ] && ls /usr/share/consolefonts/*Terminus*32x16*.psf.gz >/dev/null 2>&1; then
  sed -i 's/^FONTFACE=.*/FONTFACE="Terminus"/' /etc/default/console-setup || true
  sed -i 's/^FONTSIZE=.*/FONTSIZE="16x32"/' /etc/default/console-setup || true
fi

echo
echo "INSTALLED"
echo "On the HDMI screen, log out or reboot once to see the startup page."
echo "In this shell, type:  field"