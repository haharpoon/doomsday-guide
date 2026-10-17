# Doomsday Guide

Offline field guide for a Raspberry Pi. Shelter, water, fire, knots, food, sanitation, navigation, signaling, and clothing are stored on the Pi. Medicine and places search the Kiwix archives already on the device.

On the Pi, install it with:

```bash
curl -fsSL https://raw.githubusercontent.com/haharpoon/doomsday-guide/main/install.sh -o /tmp/install.sh
sudo bash /tmp/install.sh
```

The installer asks whether login on this screen should open the touch guide or the keyboard guide. If a touchscreen is connected, touch is the default. It installs `python3-pygame`, `python3-evdev`, `python3-numpy`, and `python3-serial`, copies `cavemap` onto `PATH`, and adds your user to the `input`, `video`, and `dialout` groups. Log in again so those groups apply.

Type `field` for the keyboard menu. Type `field_touch` for the 480×320 touchscreen. The top bar is GUIDE, SCAN, and RADIO. GUIDE is this guide. SCAN runs `cavemap` and comes back here when it exits. RADIO is a placeholder. Tap a section. Prev and Next turn pages, and so does a swipe. Search uses the on-screen keyboard.

The picture is written to `/dev/fb0` (16-bit color). Touch calibration is `~/.touchcal.json`:

```json
{"cx": [a, b, c], "cy": [d, e, f]}
```

Screen position is `x = a*rawX + b*rawY + c` and `y = d*rawX + e*rawY + f`. Raw values are ABS_X / ABS_Y from the ADS7846. On a desktop with no framebuffer, `field_touch` opens a window instead.

In the keyboard guide, type a number, then Enter. Enter continues a page. `n` is the next set of search results. `q` goes back. Page Up and Page Down are not used. Once `cavemap` is on `PATH`, the keyboard guide asks `Start Cave Mapper?` at startup and lists it under More.

## Cave Mapper

Pip-Boy SCAN screen for the 3.5 inch LCD (480×320).

On the Pi:

```bash
cavemap
```

That needs `/dev/fb0` and `/dev/input`. Use sudo, or the groups above. The top bar is the shared GUIDE, SCAN, RADIO strip. SCAN is this screen. RADIO is off. GUIDE, or the HOME button under the bar, leaves the scanner and returns to the touch guide. Keys `1`–`4` select room scan, depth, cave log, and the perimeter tripwire. Drag the room, or use the arrow keys, to turn it. `q`, Esc, or `h` does the same as HOME. The status line shows DEMO DATA or LIVE LINK, the time, and the frame rate.

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
