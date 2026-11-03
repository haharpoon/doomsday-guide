// doomsday_scan.ino - VL53L5CX 8x8 depth grid -> USB serial for the
// doomsday-guide Cave Mapper SCAN tab (cavemap.py).
//
// Board : ESP32-WROOM-32 DevKit V1 (30-pin, CH340)
// Sensor: Pimoroni VL53L5CX breakout, I2C 0x29, SDA=GPIO21, SCL=GPIO22, 3V3.
//         INT not connected (we poll), LPn left at board default.
//
// Serial protocol (matches cavemap.py "ESP32 link"): 115200 8N1, one record
// per line, LF.
//   F m0 m1 ... m63   64 distances in mm, row-major, space separated.
//                     Index 0 = row 0, column 0. 0 = no return / invalid zone.
//   A pan tilt        (future) servo angles in degrees.
// Status lines that cavemap.py ignores (unknown records are skipped):
//   READY             sensor initialised and ranging
//   ERR,<reason>      initialisation failed
//
// Pin budget: only GPIO21/22 (I2C) and USB UART0 (GPIO1/3) are used.
// GPIO18/19 and the rest stay free for future pan/tilt servos.

#include <Wire.h>
#include <SparkFun_VL53L5CX_Library.h>

#define I2C_SDA 21
#define I2C_SCL 22
#define SENSOR_ADDR 0x29
#define RANGING_HZ 15          // 8x8 mode tops out at 15 Hz

// ---- Future pan/tilt head --------------------------------------------------
// Servos will go here, e.g. PAN_PIN 18, TILT_PIN 19 (ESP32Servo / LEDC).
// After moving, print "A <pan> <tilt>" (pan 0 left, 90 fwd, 180 right;
// tilt 0 down, 90 level, 180 up) so cavemap.py can place each frame.
// #define PAN_PIN  18
// #define TILT_PIN 19
// ---------------------------------------------------------------------------

SparkFun_VL53L5CX imager;
VL53L5CX_ResultsData results;
char line[8 + 64 * 6];

void fail(const char *reason) {
  for (;;) {                       // repeat so a late serial reader still sees it
    Serial.print("ERR,");
    Serial.println(reason);
    delay(2000);
  }
}

void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println("# doomsday_scan booting, uploading VL53L5CX firmware...");

  Wire.begin(I2C_SDA, I2C_SCL);
  Wire.setClock(400000);           // 400 kHz; firmware upload still takes a few s

  Wire.beginTransmission(SENSOR_ADDR);
  if (Wire.endTransmission() != 0) fail("no_ack_at_0x29");

  // begin() uploads ~84 KB of sensor firmware over I2C (several seconds).
  // NOTE: do not call setWireMaxPacketSize() before begin(): the library's
  // IO object is only created/attached to Wire inside begin(), so calling it
  // earlier dereferences a null pointer (StoreProhibited panic).
  if (!imager.begin(SENSOR_ADDR, Wire)) fail("begin_failed");
  imager.setWireMaxPacketSize(128);   // ESP32 Wire buffer is 128 bytes
  if (!imager.setResolution(8 * 8)) fail("set_resolution_failed");
  if (!imager.setRangingFrequency(RANGING_HZ)) fail("set_frequency_failed");
  if (!imager.startRanging()) fail("start_ranging_failed");

  Serial.println("READY");
}

void loop() {
  if (imager.isDataReady() && imager.getRangingData(&results)) {
    char *p = line;
    *p++ = 'F';
    for (int i = 0; i < 64; i++) {
      int mm = results.distance_mm[i];
      uint8_t st = results.target_status[i];
      bool ok = results.nb_target_detected[i] > 0 && (st == 5 || st == 6 || st == 9);
      if (!ok || mm <= 0 || mm > 4000) mm = 0;   // 0 = no return in cavemap.py
      p += sprintf(p, " %d", mm);
    }
    *p++ = '\n';
    Serial.write((const uint8_t *)line, p - line);
  }
  delay(2);
}
