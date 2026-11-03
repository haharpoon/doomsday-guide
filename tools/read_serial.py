"""Print a few seconds of the doomsday_scan serial stream.

Usage: py tools/read_serial.py [COM12] [seconds]

115200 8N1. Reports frame count, a rough fps, one sample grid, and how
many zones actually returned a range.
"""

import sys
import time

import serial

port = sys.argv[1] if len(sys.argv) > 1 else "COM12"
dur = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
ser = serial.Serial(port, 115200, timeout=0.5)
frames, other, first, last = [], [], None, None
try:
    t0 = time.time()
    while time.time() - t0 < dur:
        raw = ser.readline()
        if not raw:
            continue
        text = raw.decode("utf-8", "replace").strip()
        parts = text.split()
        if len(parts) == 65 and parts[0] == "F":
            now = time.time()
            first = first or now
            last = now
            frames.append([int(item) for item in parts[1:]])
        elif text:
            other.append(text)
finally:
    ser.close()
print("port_closed", ser.is_open is False)
print("other_lines", other[:15])
print("frames", len(frames))
if len(frames) > 1 and last != first:
    print("fps %.2f" % ((len(frames) - 1) / (last - first)))
if frames:
    sample = frames[len(frames) // 2]
    print("SAMPLE F " + " ".join(map(str, sample)))
    for row in range(8):
        print(" ".join("%5d" % value for value in sample[row * 8 : row * 8 + 8]))
    allv = [value for frame in frames for value in frame]
    valid = [value for value in allv if value > 0]
    print(
        "valid_frac %.2f min %s max %s"
        % (len(valid) / len(allv), min(valid) if valid else None, max(valid) if valid else None)
    )
