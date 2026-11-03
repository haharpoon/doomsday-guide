# doomsday_scan

VL53L5CX 8×8 depth grid for the Cave Mapper SCAN tab. This is the sketch flashed on the ESP32. `cavemap.py` already parses the lines it prints.

## Board

ESP32-WROOM-32 DevKit V1, 30-pin, CH340 USB serial. Flash it as **ESP32 Dev Module**.

## Wiring

Pimoroni VL53L5CX breakout. INT is not connected; the sketch polls. Leave LPn at the breakout default so the sensor stays enabled.

| VL53L5CX | ESP32 |
| --- | --- |
| SDA | GPIO21 |
| SCL | GPIO22 |
| 3V3 | 3V3 |
| GND | GND |

The sensor is I2C `0x29`. GPIO18 and GPIO19 are free for a later pan/tilt servo. USB serial is UART0 (GPIO1 TX, GPIO3 RX).

An RDA5807 FM module can share this I2C bus later. It uses `0x10` and `0x11`, which this sketch never addresses. The bus is left at 400 kHz for the VL53L5CX. A later radio driver can drop the clock for its own transactions. Nothing in this sketch claims the whole bus, and the UART is still free to read lines (the sketch only writes today). The radio is not implemented here.

## Library

Arduino-ESP32 core, plus the SparkFun VL53L5CX Arduino Library (`SparkFun_VL53L5CX_Library.h`). `Wire` comes with the core.

In the Arduino IDE Library Manager, install **SparkFun VL53L5CX Arduino Library**. The Pimoroni breakout is the hardware. The sketch talks to it through the SparkFun library, not a Pimoroni one.

`begin()` uploads the sensor's own firmware over I2C and takes a few seconds. Do not call `setWireMaxPacketSize()` before `begin()`. The library's I/O object does not exist yet, and the call panics.

## Flash

Serial monitor at 115200. The first line is a `#` comment, then `READY` once ranging starts. After that, `F` lines at about 15 Hz. `ERR,<reason>` repeats if init fails (`no_ack_at_0x29` means the sensor is not on the bus).

This board's auto-reset is flaky. Hold **BOOT** (IO0) while esptool connects, and release it once the upload is writing.

Arduino IDE: choose the CH340 COM port, then Sketch → Upload, and hold BOOT when the console says `Connecting`.

arduino-cli, from the repo root:

```bash
arduino-cli compile --fqbn esp32:esp32:esp32dev firmware/doomsday_scan
arduino-cli upload -p COM12 --fqbn esp32:esp32:esp32dev firmware/doomsday_scan
```

Hold BOOT when the upload says `Connecting`. Use the COM port (or `/dev/ttyUSB*`) that appears when the board is plugged in. If no port appears, the CH340 driver is missing.

## Protocol

115200 8N1, one record per line, LF. This matches the ESP32 link in `cavemap.py`.

```
F m0 m1 ... m63     64 distances in millimetres, row-major.
                    Index 0 is row 0, column 0. 0 is no return.
READY               ranging has started. cavemap.py ignores this.
ERR,<reason>        init failed. cavemap.py ignores this.
A pan tilt          not sent yet. Servos are not fitted.
```

Pan, when it exists: 0 left, 90 forward, 180 right. Tilt: 0 down, 90 level, 180 up. Until those `A` lines exist, aim from the PC with `python3 cavemap.py --desktop`.
