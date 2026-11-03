"""Live 8x8 depth view for the doomsday VL53L5CX scanner.

Usage: py tools/live_view.py [COM12]

Needs pyserial, and tkinter (python3-tk on Linux; included with the
Windows python.org install). Bright green is near. Black is no return.
"""

import queue
import sys
import threading

import serial
import tkinter as tk

PORT = sys.argv[1] if len(sys.argv) > 1 else "COM12"
N, CELL = 8, 80
MIN_MM, MAX_MM = 200, 3000
frames_q = queue.Queue(maxsize=2)
status = {"text": "connecting to " + PORT}


def reader():
    try:
        with serial.Serial(PORT, 115200, timeout=1) as ser:
            status["text"] = "connected on " + PORT
            while True:
                line = ser.readline().decode("utf-8", "ignore").strip()
                if line.startswith("F "):
                    parts = line.split()[1:]
                    if len(parts) == 64:
                        try:
                            vals = [int(part) for part in parts]
                        except ValueError:
                            continue
                        if frames_q.full():
                            try:
                                frames_q.get_nowait()
                            except queue.Empty:
                                pass
                        frames_q.put(vals)
                elif line.startswith("ERR"):
                    status["text"] = "sensor error: " + line
    except Exception as error:
        status["text"] = f"serial error: {error} (close other programs using {PORT})"


def colour(mm):
    if mm <= 0:
        return "#000000"
    t = max(0.0, min(1.0, (mm - MIN_MM) / (MAX_MM - MIN_MM)))
    green = int(255 - t * 215)  # near = bright green, far = dark green
    return f"#{int(green * 0.1):02x}{green:02x}{int(green * 0.5):02x}"


def main():
    root = tk.Tk()
    root.title("Doomsday SCAN - live depth")
    root.configure(bg="black")
    canvas = tk.Canvas(root, width=N * CELL, height=N * CELL, bg="black", highlightthickness=0)
    canvas.pack(padx=10, pady=10)
    info = tk.Label(root, text="", fg="#1AFF80", bg="black", font=("Consolas", 12))
    info.pack(pady=(0, 10))
    rects, labels = [], []
    for row in range(N):
        for col in range(N):
            x, y = col * CELL, row * CELL
            rects.append(
                canvas.create_rectangle(x, y, x + CELL - 2, y + CELL - 2, fill="black", outline="#0A5C2E")
            )
            labels.append(
                canvas.create_text(x + CELL / 2, y + CELL / 2, text="", fill="white", font=("Consolas", 13, "bold"))
            )

    frames = {"n": 0}

    def tick():
        try:
            vals = frames_q.get_nowait()
            frames["n"] += 1
            for index, mm in enumerate(vals):
                canvas.itemconfig(rects[index], fill=colour(mm))
                canvas.itemconfig(
                    labels[index],
                    text=("--" if mm <= 0 else f"{mm / 1000:.2f}m"),
                    fill=("black" if 0 < mm < 1500 else "#1AFF80"),
                )
            good = [value for value in vals if value > 0]
            near = f"nearest {min(good) / 1000:.2f} m" if good else "no returns"
            info.config(text=f"{status['text']}  |  frame {frames['n']}  |  {near}  |  bright = close")
        except queue.Empty:
            if frames["n"] == 0:
                info.config(text=status["text"] + "  |  waiting for frames...")
        root.after(30, tick)

    threading.Thread(target=reader, daemon=True).start()
    tick()
    root.mainloop()


if __name__ == "__main__":
    main()
