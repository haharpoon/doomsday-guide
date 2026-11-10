# Doomsday Guide

Offline field guide for a Raspberry Pi. Shelter, first aid, water, fire, knots, food, tools and wildlife, sanitation, navigation, signals and radio, clothing, weather, power, emergency planning, and an offline library guide are stored on the Pi. Medicine and places search the Kiwix archives already on the device.

A blank microSD card and a Raspberry Pi are enough to rebuild the whole deck from this repo. The steps below are the ones that match the working card: a Pi 3B, Raspberry Pi OS Lite 64-bit (Debian 13 Trixie), and a 128 GB card whose library uses about 83 GB under `/var/lib/kiwix`.

Wi-Fi names, Wi-Fi passwords, and the Pi login are not in this repo. Examples say `YOUR_SSID`, `YOUR_WIFI_PASSWORD`, and `YOUR_USER`. Put the real values into Raspberry Pi Imager, or into NetworkManager on the card.

## Build your own

### Hardware

- Raspberry Pi 3B or newer. This screen setup was taken from a Pi 3B. A Pi 4 uses the same kind of SPI panel overlay. On a Pi 5, prefer HDMI or SSH unless you already know this overlay on that board.
- goodtft or Waveshare-style 3.5 inch resistive touchscreen, 480×320, ILI9486, on SPI. Skip it if you will use HDMI or SSH. See [No touchscreen?](#no-touchscreen).
- microSD card. 128 GB is the comfortable size, because the full library is about 83 GB on disk. `scripts/fetch_library.sh` prints a higher download total, about 89 GB, because it counts the files in decimal gigabytes and checks free space before it starts. A smaller card works if you trim that list first (the English Wikipedia file is the big one, about 53 GB).
- A power supply meant for that Pi, or a power bank that can hold 5 V with the Pi and the screen on.
- Optional, for the SCAN tab: an ESP32-WROOM-32 and a Pimoroni VL53L5CX. See `firmware/doomsday_scan/README.md`.
- Optional, for live FM on the RADIO tab: a USB RTL-SDR dongle. The frequency cards, the listening log, and Morse work without it.

### Flash the card

1. Install [Raspberry Pi Imager](https://www.raspberrypi.com/software/) on a computer.
2. Choose Raspberry Pi OS Lite, 64-bit. The working card is Debian 13 (Trixie), aarch64.
3. Open the OS customisation settings. Set a hostname, a username, and a password. Turn SSH on. Enter your Wi-Fi name, password, and country. Those stay on the card.
4. Write the image and boot the Pi on that network.

With only the little panel fitted, the screen stays blank on this first boot. The panel overlay is not on a stock image yet. SSH is how you get in. With an HDMI monitor and a USB keyboard you can log in on the console instead.

### Run the setup

On the Pi:

```bash
sudo apt update
sudo apt install -y git
git clone https://github.com/haharpoon/doomsday-guide.git
cd doomsday-guide
sudo bash scripts/setup_pi.sh
```

The script is safe to run again. It installs the packages from `system/packages.txt` (Kiwix, the guide libraries, RTL-SDR, ALSA, BlueZ, and PipeWire), turns Wi-Fi powersave off, blacklists the TV driver that grabs RTL-SDR sticks, and installs the Wi-Fi watchdog, Kiwix, and the library download.

It then asks about the 3.5 inch panel. Answer yes if that screen is fitted. The script copies `config.txt` and `cmdline.txt` to `config.txt.doomsday-pre-tft` and `cmdline.txt.doomsday-pre-tft` before it changes them, comments out `dtoverlay=vc4-kms-v3d`, installs `disable-fwfb.dtbo`, and adds:

```
dtparam=spi=on
dtoverlay=disable-fwfb
dtoverlay=tft35a:rotate=90
```

plus `initcall_blacklist=simplefb_driver_init` on the kernel command line. That is what makes the panel `/dev/fb0`. The card's own `root=PARTUUID=...` stays as it is.

`system/boot/config.txt.example` is the working Pi's config, for reading. The script edits the card's own file. Copying the example over the card would replace another board's settings. `system/boot/cmdline.txt.example` shows the extra token with a placeholder `PARTUUID`. Leave the card's cmdline in place.

Answer no for an HDMI or SSH Pi. The boot files stay as Imager wrote them. To skip the question:

```bash
sudo DOOMSDAY_TFT=1 bash scripts/setup_pi.sh
sudo DOOMSDAY_TFT=0 bash scripts/setup_pi.sh
```

It finishes by running `install.sh`, which asks whether login on this screen should open the touch guide or the keyboard guide. Choose touch for the panel. Choose the keyboard guide for HDMI. The console then logs itself in as the user you created, and the guide opens. SSH still asks for your key or password.

Reboot when it tells you to.

```bash
sudo reboot
```

To install only the guide, on a Pi that is already set up:

```bash
curl -fsSL https://raw.githubusercontent.com/haharpoon/doomsday-guide/main/install.sh -o /tmp/install.sh
sudo bash /tmp/install.sh
```

#### Unattended first boot

`system/boot-doomsday/` is the first-boot installer from the working Pi, pointed at this repo so the steps are not copied twice. `setup.sh` waits for the network, installs git, clones the repo, and runs `scripts/setup_pi.sh`.

On a computer that can see the card's boot partition, copy the contents of `system/boot-doomsday/` to a folder named `doomsday` on that partition (`/boot/firmware/doomsday` once the Pi is running). If the panel is fitted, also copy `enable-tft.example` to `enable-tft` in that folder. The file's contents are not read. Only the name matters.

The service file also has to be installed on the Linux partition, as `/etc/systemd/system/doomsday-setup.service`, with a symlink in `multi-user.target.wants`. That needs a machine that can write ext4. The log is `/var/log/doomsday-setup.log`. If writing the Linux partition is awkward, boot, SSH in, and run `setup_pi.sh` yourself.

Wi-Fi for that first boot still comes from Imager. `system/cloud-init/` shows the shape of those files with placeholders, for a card you are writing by hand. If Imager already wrote `user-data` and `network-config`, keep those.

### The library download

`doomsday-library.service` runs `scripts/fetch_library.sh` with the prompt already answered, so the download starts on its own and resumes after a dropout (`wget -c`, and the service tries again two minutes after a failure). The full set is tens of gigabytes. On a home connection it is an afternoon or an overnight job. A faster line finishes sooner.

For a smaller card, edit the `ZIMS` list in `scripts/fetch_library.sh` before the first boot finishes the big files. Stop a download that has already started with `sudo systemctl stop doomsday-library`, edit the list, then `sudo systemctl start doomsday-library`. The script refuses to start when the free space is short of the total it printed.

Watch it:

```bash
tail -f /var/log/doomsday-library.log
du -sh /var/lib/kiwix
systemctl status doomsday-library
systemctl status kiwix
```

`/var/lib/kiwix/.library-done` appears when the fetch has finished. Until then, Kiwix may restart in a loop because `library.xml` is not there yet, and the guide will say `Library not reachable`. The sheets in the guide still work. When the download has finished, `systemctl status kiwix` should show `kiwix-serve` running.

### Calibration, the splash, and HDMI

On the panel, the touch map for this screen (tft35a, rotate 90) is:

```bash
sudo touch_calibrate --preset
```

If taps land in the wrong place, `sudo touch_calibrate` draws five crosshairs on the panel named `fb_ili9486` and writes `~/.touchcal.json`. Details are in the next section.

The touch guide plays a boot splash for about six seconds, then the menu. Tap to skip it. `splash=off` in `/etc/doomsday/field-touch.conf`, or `FIELD_TOUCH_SPLASH=0`, turns it off.

The panel setup leaves HDMI off so the small screen owns the console. To mirror the picture on an HDMI display:

```bash
sudo doomsday-hdmi on
sudo reboot
```

`sudo doomsday-hdmi status` prints whether the boot files are asking for that mirror. `sudo doomsday-hdmi off`, then a reboot, returns to the panel only. The tft35a overlay stays either way.

## No touchscreen?

Skip the panel question (`sudo DOOMSDAY_TFT=0 bash scripts/setup_pi.sh`, or answer no). The boot files are left alone, so an HDMI monitor keeps working.

The keyboard guide is `field`. It is a terminal program: it reads the keyboard and prints text. It does not open a framebuffer. On the Pi, plug in an HDMI monitor and a USB keyboard, log in, and type:

```bash
field
```

Over SSH it is the same program:

```bash
ssh YOUR_USER@<pi-ip>
field
```

`YOUR_USER` is the account you set in Imager. Find the address with:

```bash
hostname -I
```

The console login screen prints it as well, once `install.sh` has written `/etc/issue`.

The offline library is a normal website on port 8080. `kiwix.service` runs:

```
kiwix-serve --library --monitorLibrary --port 8080 /var/lib/kiwix/library.xml
```

There is no `--address` flag. Current `kiwix-serve` treats that as every interface, so a phone or a laptop on the same network opens the whole library at:

```
http://<pi-ip>:8080
```

The books are on the card. The browser only has to reach the Pi. A router or a phone hotspot with no internet is enough, as long as the Pi and the other device are on that network. The guide's own archive search uses `http://127.0.0.1:8080`, which is the same server.

## Troubleshooting

- **Blank panel.** On the first boot, before setup, a blank panel is expected: SSH in and run the setup. After a reboot with the panel enabled, check that `/boot/firmware/overlays/disable-fwfb.dtbo` is there, that `config.txt` has `dtoverlay=tft35a:rotate=90` and `dtoverlay=disable-fwfb`, that the `dtoverlay=vc4-kms-v3d` line is commented out, and that `cmdline.txt` contains `initcall_blacklist=simplefb_driver_init`. Then reboot. `cat /sys/class/graphics/fb0/name` should print `fb_ili9486`. To go back, copy `/boot/firmware/config.txt.doomsday-pre-tft` over `config.txt` and `/boot/firmware/cmdline.txt.doomsday-pre-tft` over `cmdline.txt`, then reboot.
- **Library not reachable.** The guide says this when it cannot open Kiwix on port 8080. Check `systemctl status kiwix` and `curl -I localhost:8080`. During the download that failure is normal. Follow `/var/log/doomsday-library.log` until `.library-done` appears. From another device, use `http://<pi-ip>:8080` and the address from `hostname -I`.
- **Touch is offset.** Run `sudo touch_calibrate`. For this panel, `sudo touch_calibrate --preset` writes the known map for `tft35a` at rotate 90. A previous file is kept as `~/.touchcal.json.bak-<date>`.
- **Wi-Fi drops.** `wifi-watchdog.timer` runs about two minutes after the previous check, starting three minutes after boot. It pings the gateway, reconnects the USB stick (`wlan1` unless `/etc/default/wifi-watchdog` sets `WIFI_IFACE`), resets that USB port after repeated failures, and reboots the Pi if the gateway is still quiet after several checks. `journalctl -t wifi-watchdog` shows what it did. `sudo systemctl disable --now wifi-watchdog.timer` stops it. Powersave is turned off by `/etc/NetworkManager/conf.d/zz-wifi-powersave-off.conf` (`wifi.powersave = 2`).

## The guides

The installer asks whether login on this screen should open the touch guide or the keyboard guide. If a touchscreen is connected, touch is the default. It installs `python3-pygame`, `python3-evdev`, `python3-numpy`, and `python3-serial`, copies `cavemap` onto `PATH`, and adds your user to the `input`, `video`, and `dialout` groups. Log in again so those groups apply.

Type `field` for the keyboard menu. Type `field_touch` for the 480×320 touchscreen. The top bar is GUIDE, SCAN, and RADIO. GUIDE is this guide. SCAN runs `cavemap` and comes back here when it exits. RADIO is the frequency guide, listening log, and Morse trainer. Tap a section. Prev and Next turn pages, and so does a swipe. Search on the GUIDE home row looks through every card already on the Pi: titles match first, then the card text, and the list updates as you type. A-Z is every card title. Archive search still uses the on-screen keyboard.

The picture is written to `/dev/fb0` (16-bit color). Touch calibration is `~/.touchcal.json`:

```json
{"cx": [a, b, c], "cy": [d, e, f]}
```

Screen position is `x = a*rawX + b*rawY + c` and `y = d*rawX + e*rawY + f`. Raw values are ABS_X / ABS_Y from the ADS7846. On a desktop with no framebuffer, `field_touch` opens a window instead.

Recalibrate on the Pi with `sudo touch_calibrate`. It stops the touch guide, shows five crosshairs on the panel named `fb_ili9486`, and writes that map to `~/.touchcal.json`. For the goodtft 3.5 inch screen with `dtoverlay=tft35a:rotate=90`, `sudo touch_calibrate --preset` writes the known map without tapping. A previous file is copied to `~/.touchcal.json.bak-<date>` before the new one is saved. The installer puts the tool at `/usr/local/bin/touch_calibrate` and leaves a calibration that is already there in place.

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
