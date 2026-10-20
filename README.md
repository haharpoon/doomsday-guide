# Doomsday Guide

Offline field guide for a Raspberry Pi. Shelter, first aid, water, fire, knots, food, tools and wildlife, sanitation, navigation, signals and radio, clothing, weather, power, emergency planning, and an offline library guide are stored on the Pi. Medicine and places search the Kiwix archives already on the device.

On the Pi, install it with:

```bash
curl -fsSL https://raw.githubusercontent.com/haharpoon/doomsday-guide/main/install.sh -o /tmp/install.sh
sudo bash /tmp/install.sh
```

The installer asks whether login on this screen should open the touch guide or the keyboard guide. If a touchscreen is connected, touch is the default. It installs `python3-pygame`, `python3-evdev`, `python3-numpy`, and `python3-serial`, copies `cavemap` onto `PATH`, and adds your user to the `input`, `video`, and `dialout` groups. Log in again so those groups apply.

Type `field` for the keyboard menu. Type `field_touch` for the 480×320 touchscreen. The top bar is GUIDE, SCAN, and RADIO. GUIDE is this guide. SCAN runs `cavemap` and comes back here when it exits. RADIO is the frequency guide, listening log, and Morse trainer. Tap a section. Prev and Next turn pages, and so does a swipe. Search uses the on-screen keyboard.

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

That needs `/dev/fb0` and `/dev/input`. Use sudo, or the groups above. The top bar is the shared GUIDE, SCAN, RADIO strip. SCAN is this screen. GUIDE, or the HOME button under the bar, leaves the scanner and returns to the touch guide. RADIO leaves for the radio screen. Keys `1`–`4` select room scan, depth, cave log, and the perimeter tripwire. Drag the room, or use the arrow keys, to turn it. `q`, Esc, or `h` does the same as HOME. The status line shows DEMO DATA or LIVE LINK, the time, and the frame rate.

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

## Radio

Tap RADIO. No dongle is required for the frequency cards, the listening log, or Morse.

FREQ steps through `content/radio_freqs.json`. Edit that file to change a station. Signals opens the Signals & Radio sheet instead of copying it onto the card. The line under the modes is the listening note: airband, marine, and PMR conversations are unintended recipients under the Wireless Telegraphy Act s48.

LOG stores what you heard in `~/.doomsday/radio_log.json`. ADD uses the card you were just reading. HEARD, CLEAR, NOISY, and NOTHING save straight away. 123 is a digit pad for a frequency that is not on a card.

MORSE flashes the screen at 10 words per minute (a dit is 120 ms, a dah is three dits). SOS is the prosign. PRACTICE treats a short tap as a dit and a longer hold as a dah, then shows the letter.

The status line is the hardware check. It looks for USB ids `0bda:2838` and `0bda:2832`, and otherwise runs `rtl_test -t` when that program exists. With no dongle it reads `No radio hardware - plug in an RTL-SDR to listen live`, and FREQ, LOG, and MORSE keep working.

With a dongle, LIVE tunes broadcast FM:

```bash
rtl_fm -f 93.5M -M wbfm -s 200000 -r 48000 -A fast | aplay -r 48000 -f S16_LE -t raw -c 1 -q
```

DOWN and UP step 0.1 MHz. R1–R4 jump to the BBC presets. BARS runs one `rtl_power` sweep of 88–108 MHz. It does not run while audio is playing, and it gives up if a sweep takes more than a couple of seconds, which keeps a Pi 3B from sitting in a waterfall.

`RADIO_ALSA_DEVICE` is passed to aplay when the Pi's default sound card is not the speaker. `RADIO_LOG` moves the log file.

A future ESP32 with an RDA5807 can share the Cave Mapper serial link. Set `RADIO_RDA_PORT=/dev/ttyUSB0` and the live screen writes `FREQ 93.5` and `OFF` at 115200 8N1. Nothing is read back yet. Without that variable the live screen says `RDA5807 not attached`.

Try it on the Pi after install:

```bash
field_touch
```

Tap RADIO. Swipe, or Prev and Next, to move through the cards. To try it from a checkout of this branch instead of the copy on main:

```bash
sudo bash install.sh
```

The installer uses the files next to it when they are there, and it still installs if `rtl-sdr` or `alsa-utils` is not in the archive.
