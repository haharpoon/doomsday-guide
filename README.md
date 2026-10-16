# Doomsday Guide

Offline field guide for a Raspberry Pi. Shelter, water, fire, knots, food, sanitation, navigation, signaling, and clothing are stored on the Pi. Medicine and places search the Kiwix archives already on the device.

On the Pi, install it with:

```bash
curl -fsSL https://raw.githubusercontent.com/haharpoon/doomsday-guide/main/install.sh -o /tmp/install.sh
sudo bash /tmp/install.sh
```

The installer asks whether login on this screen should open the touch guide or the keyboard guide. If a touchscreen is connected, touch is the default. It also installs `python3-pygame` and `python3-evdev`, and adds your user to the `input` and `video` groups so the touchscreen and framebuffer are readable after the next login.

Type `field` for the keyboard menu. Type `field_touch` for the 480×320 touchscreen. Tap a section. Prev and Next turn pages, and so does a swipe. Search uses the on-screen keyboard. Cave Mapper is on the home screen when `cavemap` is installed.

The picture is written to `/dev/fb0` (16-bit color). Touch calibration is `~/.touchcal.json`:

```json
{"cx": [a, b, c], "cy": [d, e, f]}
```

Screen position is `x = a*rawX + b*rawY + c` and `y = d*rawX + e*rawY + f`. The touch device is the ADS7846. On a desktop with no framebuffer, `field_touch` opens a window instead.

In the keyboard guide, type a number, then Enter. Enter continues a page. `n` is the next set of search results. `q` goes back. Page Up and Page Down are not used.
