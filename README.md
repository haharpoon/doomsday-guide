# Doomsday Guide

Offline field guide for a Raspberry Pi. Shelter, water, fire, knots, food, sanitation, navigation, signaling, and clothing are stored on the Pi. Medicine and places search the Kiwix archives already on the device.

On the Pi, install it with:

```bash
curl -fsSL https://raw.githubusercontent.com/haharpoon/doomsday-guide/main/install.sh -o /tmp/install.sh
sudo bash /tmp/install.sh
```

Then type `field`.

On the HDMI screen, log in and the guide opens. The startup page is titled DOOMSDAY GUIDE. Type a number, then Enter. Enter continues a page. `n` is the next set of search results. `q` goes back. Page Up and Page Down are not used.

## Cave Mapper

Pip-Boy SCAN screen for the 3.5 inch LCD (480×320). Once `cavemap` is on `PATH`, the guide asks `Start Cave Mapper?` at startup and lists it under More.

On the Pi:

```bash
python3 cavemap.py
```

That needs `/dev/fb0` and `/dev/input`. Use sudo, or join the `video` and `input` groups and log in again:

```bash
sudo usermod -aG video,input,dialout "$USER"
```

`q`, Esc, or the on-screen BACK button leaves the scanner and restores the console. Keys `1`–`4` select room scan, depth, cave log, and the perimeter tripwire. Drag the room, or use the arrow keys, to turn it. `install.sh` copies the program to `/usr/local/bin/cavemap`.

Nothing is wired to a sensor yet, so the picture is labelled DEMO DATA. A desktop window, for trying it off the Pi:

```bash
python3 cavemap.py --window
```

`python3 cavemap.py --dump screenshots` writes one 480×320 PNG of each mode. The frames in `screenshots/` are from that demo.

### ESP32 link

A USB serial device (`/dev/ttyACM*`, `/dev/ttyUSB*`, or `/dev/serial/by-id/*`) is read at 115200 8N1 and replaces the demo. `CAVEMAP_PORT` or `--serial /dev/ttyACM0` picks the port. `--demo` keeps the built-in data. `dialout` is the usual group for that port. The GPIO UART stays with the console.

UTF-8, one record per line, LF or CRLF. Blank lines and lines starting with `#` are ignored.

```
F m0 m1 ... m63     VL53L5CX frame, 64 millimetre ranges, row-major.
                    0 or anything above 4000 is no return.
A pan tilt          Servo degrees. Pan 0 left, 90 forward, 180 right.
                    Tilt 0 down, 90 level, 180 up.
LEFT RIGHT UP DOWN PUSH PULL HOLD BREACH
                    One word, alone on the line. BREACH trips the
                    perimeter alarm. HOLD clears it.
```

Touch calibration is `~/.touchcal.json`: `{"cx":[a,b,c],"cy":[d,e,f]}` with `screen_x = a*rawX + b*rawY + c` and the same form for `y`. Raw values are ABS_X / ABS_Y from the ADS7846 device.
