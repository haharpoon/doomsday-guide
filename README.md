# Doomsday Guide

Offline field guide for a Raspberry Pi. Shelter, first aid, water, fire, knots, food, tools and wildlife, sanitation, navigation, signals and radio, clothing, weather, power, emergency planning, and an offline library guide are stored on the Pi. Medicine and places search the Kiwix archives already on the device.

On the Pi, install it with:

```bash
curl -fsSL https://raw.githubusercontent.com/haharpoon/doomsday-guide/main/install.sh -o /tmp/install.sh
sudo bash /tmp/install.sh
```

The installer asks whether login on this screen should open the touch guide or the keyboard guide. If a touchscreen is connected, touch is the default. It installs `python3-pygame`, `python3-evdev`, `python3-numpy`, and `python3-serial`, copies `cavemap` onto `PATH`, and adds your user to the `input`, `video`, and `dialout` groups. Log in again so those groups apply.

Type `field` for the keyboard menu. Type `field_touch` for the 480×320 touchscreen. The top bar is GUIDE, SCAN, and RADIO. GUIDE is this guide. SCAN runs `cavemap` and comes back here when it exits. RADIO is the frequency guide, listening log, and Morse trainer. Tap a section. Prev and Next turn pages, and so does a swipe. Search on the GUIDE home row looks through every card already on the Pi: titles match first, then the card text, and the list updates as you type. A-Z is every card title. Archive search still uses the on-screen keyboard.

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

That needs the ILI9486 panel (the framebuffer named `fb_ili9486`) and `/dev/input`. Use sudo, or the groups above. When an HDMI framebuffer is present, the same frames are mirrored there. The top bar is the shared GUIDE, SCAN, RADIO strip. SCAN is this screen. GUIDE, or the HOME button under the bar, leaves the scanner and returns to the touch guide. RADIO leaves for the radio screen. Keys `1`–`4` select room scan, depth, cave log, and the perimeter tripwire. Drag the room, or use the arrow keys, to turn it. `q`, Esc, or `h` does the same as HOME. The status line shows DEMO DATA or LIVE LINK, the time, and the frame rate.

The picture is labelled DEMO DATA until a USB serial device shows up. A desktop window, for trying the demo off the Pi:

```bash
python3 cavemap.py --window
```

`python3 cavemap.py --dump screenshots` writes one 480×320 PNG of each mode. The frames in `screenshots/` are from that demo.

### Desktop and manual aim

On a PC the sensor is aimed by hand. The pan/tilt servo is not fitted, so the sketch does not send `A` lines yet.

```bash
python3 cavemap.py --desktop --serial COM12
```

`--desktop` is the default on Windows, and `CAVEMAP_DESKTOP=1` forces it. It opens the same 2× window as `--window`, quits back to the shell, and (once the link is live, rather than the demo) lets the keyboard set pan and tilt until a real `A` line arrives. `--manual-aim`, or `CAVEMAP_MANUAL_AIM=1`, turns on that keyboard aim without the rest of desktop mode. `run_scan.bat` is the Windows launcher: it runs the command above on COM12.

Left and Right pan by 10 degrees. Up and Down tilt by 10. Hold Shift for 2 degrees. W A S D, or a mouse drag, turn the view. Space or Enter captures again. L toggles live capture. C clears the cloud. Z aims back to 90/90. 1–4 are the modes. Q, Esc, or H quits. In desktop mode, GUIDE, HOME, and RADIO flash `DESKTOP: ESC QUITS` and the scanner stays open.

An angle change waits half a second, then stores the per-zone median of five frames as one snapshot. A zone counts only when it returns in more than half of those frames. Live capture adds every frame, still only after the angle has been steady for half a second. The room HUD shows SETTLE, SNAP n/5, HELD, or LIVE. If the link drops, the screen falls back to the demo and the arrow keys orbit that picture again.

`tools/live_view.py COM12` is a separate 8×8 depth window (pyserial and tkinter). `tools/read_serial.py COM12 5` prints a few seconds of the raw stream. Neither is installed on the Pi.

### ESP32 link

The flashed sketch is `firmware/doomsday_scan/` (ESP32-WROOM-32, Pimoroni VL53L5CX on I2C `0x29`, SDA GPIO21, SCL GPIO22). See that README for the library and how to flash it. Hold BOOT while esptool connects; auto-reset on this board is flaky. The sketch sends `F` lines at about 15 Hz. `A` lines wait until a servo is fitted. I2C `0x10` and `0x11` stay free for a later RDA5807 on the same bus.

A USB serial device (`/dev/ttyACM*`, `/dev/ttyUSB*`, or `/dev/serial/by-id/*`) is read at 115200 8N1 and replaces the demo. `CAVEMAP_PORT` or `--serial /dev/ttyACM0` picks the port. On the PC that port is usually `COM12`. `--demo` keeps the built-in data. `dialout` is the usual group for that port. The Pi GPIO UART stays with the console.

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

`READY` and `ERR,...` from the sketch are ignored, same as any other unknown line.

### Simulated sweep

`sim/sim_sweep.py` writes a best-case room scan as `A` and `F` lines (a 2 degree serpentine sweep by default). `sim/render_sim.py` feeds that file through the same parser the app uses and writes a room picture. The lift, zoom, ceiling cut, and furniture colours happen only in that picture. The Pi installer leaves both scripts where they are. `sweep.txt` and the PNGs are generated output.

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

A future ESP32 with an RDA5807 can share the Cave Mapper serial link. Set `RADIO_RDA_PORT=/dev/ttyUSB0` and the live screen writes `FREQ 93.5` and `OFF` at 115200 8N1. Nothing is read back yet. Without that variable the live screen says `RDA5807 not attached`. The scanner sketch leaves I2C `0x10` and `0x11` free beside the VL53L5CX at `0x29`.

Try it on the Pi after install:

```bash
field_touch
```

Tap RADIO. Swipe, or Prev and Next, to move through the cards. To try it from a checkout of this branch instead of the copy on main:

```bash
sudo bash install.sh
```

The installer uses the files next to it when they are there, and it still installs if `rtl-sdr` or `alsa-utils` is not in the archive.
