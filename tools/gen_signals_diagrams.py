"""Draw the Signals & Radio diagrams (480x284, #1AFF80 on black).

Run from the repo root: python3 tools/gen_signals_diagrams.py
Writes content/img/signals-*.png. No photographs. Line art only.
"""
import os
from PIL import Image, ImageDraw, ImageFont

G = (0x1A, 0xFF, 0x80)
W, H = 480, 284


def font(size):
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def canvas(title, size=18):
    image = Image.new("RGB", (W, H), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.text((W // 2, 14), title, fill=G, font=font(size), anchor="mm")
    return image, draw


OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "content", "img")


def save(image, name):
    image.save(os.path.join(OUT, "signals-%s.png" % name))


def footer(draw, text, y=262, size=15):
    draw.text((W // 2, y), text, fill=G, font=font(size), anchor="mm")


# --- SOS -----------------------------------------------------------------
image, draw = canvas("SOS  =  short x3   long x3   short x3")
y = 108
pattern = "...---..."
width = 0
for mark in pattern:
    width += 28 if mark == "." else 58
width += 8 * (len(pattern) - 1)
x = (W - width) // 2
for mark in pattern:
    if mark == ".":
        draw.ellipse((x, y - 12, x + 24, y + 12), fill=G)
        x += 36
    else:
        draw.rectangle((x, y - 12, x + 50, y + 12), fill=G)
        x += 66
draw.text((W // 2, 160), "One block. No gap between the letters.", fill=G, font=font(16), anchor="mm")
draw.text((W // 2, 196), "Whistle, torch, horn, tap, or a mirror.", fill=G, font=font(16), anchor="mm")
footer(draw, "Three of anything = I need help. Then wait and listen.")
save(image, "sos")

# --- whistle summary -----------------------------------------------------
image, draw = canvas("Whistle codes")
rows = (
    ("Distress, mountain", "6 long blasts in 1 minute, then silence"),
    ("Reply / understood", "3 blasts in 1 minute"),
    ("Distress, SOS", "short x3, long x3, short x3"),
    ("Group: I am here", "1 short  (agree this first)"),
    ("Group: come to me", "2 shorts  (agree this first)"),
)
for index, (left, right) in enumerate(rows):
    top = 42 + index * 42
    draw.text((16, top), left, fill=G, font=font(16))
    draw.text((16, top + 18), right, fill=G, font=font(14))
save(image, "whistle")

# --- alpine --------------------------------------------------------------
image, draw = canvas("Alpine distress: 6, wait, 6")
for index in range(6):
    x = 36 + index * 72
    draw.ellipse((x, 70, x + 36, 106), fill=G)
    draw.text((x + 18, 128), str(index + 1), fill=G, font=font(16), anchor="mm")
draw.text((W // 2, 168), "Six blasts or flashes inside one minute.", fill=G, font=font(16), anchor="mm")
draw.text((W // 2, 198), "Stop for one minute. Repeat.", fill=G, font=font(16), anchor="mm")
footer(draw, "The reply is THREE in a minute. Keep going after it.")
save(image, "alpine")

# --- horn ----------------------------------------------------------------
image, draw = canvas("Horn and banging")
draw.polygon([(70, 150), (150, 110), (150, 190)], fill=G)
draw.rectangle((150, 130, 210, 170), fill=G)
draw.text((140, 210), "horn", fill=G, font=font(16), anchor="mm")
for index, label in enumerate(("bang", "bang", "bang")):
    x = 280 + index * 58
    draw.line((x, 90, x, 160), fill=G, width=8)
    draw.ellipse((x - 16, 150, x + 16, 182), outline=G, width=4)
    draw.text((x, 210), label, fill=G, font=font(14), anchor="mm")
footer(draw, "Three, then silence so you can hear the reply.")
save(image, "horn")

# --- torch ---------------------------------------------------------------
image, draw = canvas("Torch: flash, do not leave it on")
draw.rectangle((40, 70, 78, 150), outline=G, width=4)
draw.polygon([(40, 70), (78, 70), (90, 48), (28, 48)], outline=G)
draw.line((90, 100, 200, 80), fill=G, width=3)
draw.text((160, 120), "short", fill=G, font=font(14), anchor="mm")
draw.line((90, 130, 250, 150), fill=G, width=6)
draw.text((180, 175), "long = three shorts", fill=G, font=font(14), anchor="mm")
draw.text((340, 90), "SOS", fill=G, font=font(22), anchor="mm")
draw.text((340, 130), "... --- ...", fill=G, font=font(18), anchor="mm")
draw.text((340, 175), "or 6 / minute", fill=G, font=font(16), anchor="mm")
footer(draw, "Cover the lens. Point at the searchers, not into eyes.")
save(image, "torch")

# --- glow ----------------------------------------------------------------
image, draw = canvas("Glow stick: hang it, or swing a disc")
draw.rectangle((70, 80, 92, 170), fill=G)
draw.line((81, 70, 81, 80), fill=G, width=3)
draw.text((81, 200), "hung", fill=G, font=font(14), anchor="mm")
cx, cy, r = 320, 130, 70
draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=G, width=3)
draw.line((cx, cy, cx + 50, cy - 40), fill=G, width=4)
draw.rectangle((cx + 40, cy - 58, cx + 54, cy - 28), fill=G)
draw.text((cx, 230), "buzz-saw swing", fill=G, font=font(14), anchor="mm")
footer(draw, "A moving light is easier to see than a still one.")
save(image, "glow")

# --- headlights ----------------------------------------------------------
image, draw = canvas("Car: flash SOS, then save the battery")
draw.rectangle((80, 120, 400, 190), outline=G, width=4)
draw.ellipse((110, 136, 160, 176), outline=G, width=4)
draw.ellipse((320, 136, 370, 176), outline=G, width=4)
draw.polygon([(150, 120), (180, 90), (300, 90), (330, 120)], outline=G)
draw.text((W // 2, 70), "roof: bright cloth", fill=G, font=font(14), anchor="mm")
footer(draw, "Three flashes, pause, three flashes. Do not dazzle traffic.")
save(image, "lights")

# --- mirror aim ----------------------------------------------------------
image, draw = canvas("Aim a mirror with a V of fingers")
draw.ellipse((24, 58, 84, 118), outline=G, width=4)
draw.text((54, 88), "SUN", fill=G, font=font(14), anchor="mm")
draw.rectangle((150, 150, 196, 196), outline=G, width=4)
draw.text((173, 220), "mirror", fill=G, font=font(14), anchor="mm")
draw.line((84, 100, 160, 160), fill=G, width=3)
draw.line((300, 150, 324, 100), fill=G, width=6)
draw.line((348, 150, 324, 100), fill=G, width=6)
draw.text((324, 172), "V", fill=G, font=font(16), anchor="mm")
draw.line((196, 160, 430, 78), fill=G, width=3)
draw.polygon([(448, 70), (424, 72), (432, 94)], fill=G)
draw.text((400, 52), "target", fill=G, font=font(14), anchor="mm")
footer(draw, "Put the bright spot on the V, then rock it onto the target.")
save(image, "mirror")

# --- improvised mirrors --------------------------------------------------
image, draw = canvas("Anything flat and shiny")
items = (("CD", 70), ("phone", 190), ("lid", 310), ("foil", 420))
for label, x in items:
    if label == "CD":
        draw.ellipse((x - 36, 90, x + 36, 162), outline=G, width=4)
        draw.ellipse((x - 8, 118, x + 8, 134), outline=G, width=3)
    elif label == "phone":
        draw.rounded_rectangle((x - 28, 88, x + 28, 164), radius=6, outline=G, width=4)
    elif label == "lid":
        draw.ellipse((x - 36, 96, x + 36, 156), outline=G, width=4)
    else:
        draw.line((x - 30, 100, x + 20, 150), fill=G, width=3)
        draw.line((x - 20, 120, x + 30, 140), fill=G, width=3)
    draw.text((x, 200), label, fill=G, font=font(16), anchor="mm")
footer(draw, "No sighting hole needed. Use the V of your fingers.")
save(image, "mirror-make")

# --- fires ---------------------------------------------------------------
image, draw = canvas("3 fires in a triangle = distress")
points = ((240, 78), (120, 200), (360, 200))
draw.line(points + (points[0],), fill=G, width=2)
for x, y in points:
    draw.polygon([(x, y - 36), (x - 18, y + 8), (x + 18, y + 8)], fill=G)
footer(draw, "About 25 m apart. One fire you can tend beats three cold ones.")
save(image, "fire")

# --- smoke ---------------------------------------------------------------
image, draw = canvas("Day: smoke that contrasts")
draw.polygon([(90, 200), (70, 230), (150, 230)], outline=G)
draw.ellipse((80, 150, 130, 190), outline=G, width=3)
draw.ellipse((70, 110, 140, 160), outline=G, width=3)
draw.text((110, 70), "WHITE", fill=G, font=font(16), anchor="mm")
draw.text((110, 258), "green leaves, moss", fill=G, font=font(13), anchor="mm")
draw.polygon([(330, 200), (310, 230), (390, 230)], outline=G)
draw.polygon([(300, 120), (360, 200), (400, 150), (340, 90)], outline=G)
draw.text((350, 70), "BLACK", fill=G, font=font(16), anchor="mm")
draw.text((350, 258), "oil, rubber: toxic", fill=G, font=font(13), anchor="mm")
save(image, "smoke")

# --- survivor ground symbols ---------------------------------------------
image, draw = canvas("Survivors' ground signals", 17)
cells = (
    ("V", "Need", "help"),
    ("X", "Need", "medical"),
    ("N", "No", ""),
    ("Y", "Yes", ""),
    ("->", "Going", "this way"),
)
for index, (symbol, line1, line2) in enumerate(cells):
    cx = 48 + index * 95
    cy = 118
    if symbol == "V":
        draw.line((cx - 26, cy - 36, cx, cy + 28, cx + 26, cy - 36), fill=G, width=8)
    elif symbol == "X":
        draw.line((cx - 24, cy - 32, cx + 24, cy + 28), fill=G, width=8)
        draw.line((cx + 24, cy - 32, cx - 24, cy + 28), fill=G, width=8)
    elif symbol == "N":
        draw.line((cx - 22, cy + 28, cx - 22, cy - 32, cx + 22, cy + 28, cx + 22, cy - 32), fill=G, width=8)
    elif symbol == "Y":
        draw.line((cx - 24, cy - 32, cx, cy - 4), fill=G, width=8)
        draw.line((cx + 24, cy - 32, cx, cy - 4), fill=G, width=8)
        draw.line((cx, cy - 4, cx, cy + 30), fill=G, width=8)
    else:
        draw.line((cx - 30, cy, cx + 10, cy), fill=G, width=8)
        draw.polygon([(cx + 32, cy), (cx + 8, cy - 16), (cx + 8, cy + 16)], fill=G)
    draw.text((cx, cy + 52), line1, fill=G, font=font(14), anchor="mm")
    if line2:
        draw.text((cx, cy + 70), line2, fill=G, font=font(14), anchor="mm")
footer(draw, "If unsure, spell SOS. ICAO: at least 2.5 m long.")
save(image, "ground-air")

# --- rescue unit symbols -------------------------------------------------
image, draw = canvas("Rescue units (not for a lost group)", 16)
rescue = (
    ("LLL", "Finished"),
    ("LL", "Found all"),
    ("++", "Found some"),
    ("XX", "Going back"),
    ("NN", "None yet"),
)
for index, (symbol, label) in enumerate(rescue):
    x = 16 + index * 94
    draw.text((x + 40, 80), symbol, fill=G, font=font(22), anchor="mm")
    draw.text((x + 40, 120), label, fill=G, font=font(13), anchor="mm")
draw.text((70, 175), "two arrows apart", fill=G, font=font(15))
draw.text((70, 198), "= split, each way shown", fill=G, font=font(14))
draw.line((300, 186, 360, 186), fill=G, width=4)
draw.polygon([(372, 186), (356, 176), (356, 196)], fill=G)
draw.line((300, 210, 250, 210), fill=G, width=4)
draw.polygon([(238, 210), (254, 200), (254, 220)], fill=G)
draw.text((70, 240), "two arrows, same way = aircraft is that way", fill=G, font=font(14))
save(image, "ground-rescue")

# --- size ----------------------------------------------------------------
image, draw = canvas("Big, wide, and a different colour")
draw.line((40, 160, 200, 80), fill=G, width=18)
draw.line((200, 80, 360, 160), fill=G, width=18)
draw.text((200, 190), "lines about 1 m wide", fill=G, font=font(15), anchor="mm")
draw.text((W // 2, 40), "2.5 m minimum. 6 m is easier to see.", fill=G, font=font(15), anchor="mm")
footer(draw, "Dark on snow. Light on peat. A shadow helps at low sun.")
save(image, "ground-size")

# --- body signals --------------------------------------------------------
image, draw = canvas("Body signals the pilot can read", 17)
figures = (
    (70, "YES", "cloth up-down"),
    (180, "NO", "cloth sideways"),
    (290, "ALL OK", "one arm waving"),
    (400, "HELP", "both arms up"),
)
for cx, title, caption in figures:
    draw.ellipse((cx - 8, 48, cx + 8, 64), outline=G, width=2)
    draw.line((cx, 64, cx, 110), fill=G, width=3)
    draw.line((cx, 110, cx - 12, 140), fill=G, width=3)
    draw.line((cx, 110, cx + 12, 140), fill=G, width=3)
    draw.text((cx, 160), title, fill=G, font=font(13), anchor="mm")
    draw.text((cx, 178), caption, fill=G, font=font(11), anchor="mm")
# yes: one arm up-down suggested by a vertical cloth
draw.line((70, 78, 70, 48), fill=G, width=3)
draw.rectangle((64, 40, 76, 52), fill=G)
# no: arms out with cloth horizontal
draw.line((180 - 22, 84, 180 + 22, 84), fill=G, width=3)
draw.rectangle((180 + 16, 78, 180 + 30, 90), outline=G, width=2)
# all ok: one arm up
draw.line((290, 78, 290, 48), fill=G, width=3)
draw.line((290, 78, 290 + 18, 96), fill=G, width=3)
# help: both arms up
draw.line((400, 74, 400 - 14, 48), fill=G, width=3)
draw.line((400, 74, 400 + 14, 48), fill=G, width=3)
footer(draw, "Open ground. Move slowly. Repeat until the aircraft answers.", 250)
save(image, "body")

image, draw = canvas("More rescue poses", 17)
more = (
    (80, "MEDICAL", "lie flat, arms", "above head"),
    (200, "LAND", "squat, point", "the way in"),
    (320, "DON'T LAND", "wave arms", "across face"),
    (420, "WAIT", "one arm", "straight out"),
)
for cx, title, a, b in more:
    draw.text((cx, 48), title, fill=G, font=font(13), anchor="mm")
    if title == "MEDICAL":
        draw.ellipse((cx - 40, 100, cx - 26, 114), outline=G, width=2)
        draw.line((cx - 26, 107, cx + 24, 107), fill=G, width=3)
        draw.line((cx + 24, 107, cx + 40, 96), fill=G, width=3)
        draw.line((cx + 24, 107, cx + 40, 118), fill=G, width=3)
    elif title == "LAND":
        draw.ellipse((cx - 8, 78, cx + 8, 94), outline=G, width=2)
        draw.line((cx, 94, cx, 120), fill=G, width=3)
        draw.line((cx, 120, cx - 16, 132), fill=G, width=3)
        draw.line((cx, 120, cx + 16, 132), fill=G, width=3)
        draw.line((cx, 104, cx + 28, 104), fill=G, width=3)
        draw.polygon([(cx + 36, 104), (cx + 24, 98), (cx + 24, 110)], fill=G)
    elif title == "DON'T LAND":
        draw.ellipse((cx - 8, 78, cx + 8, 94), outline=G, width=2)
        draw.line((cx, 94, cx, 130), fill=G, width=3)
        draw.line((cx - 20, 100, cx + 20, 120), fill=G, width=3)
        draw.line((cx + 20, 100, cx - 20, 120), fill=G, width=3)
    else:
        draw.ellipse((cx - 8, 78, cx + 8, 94), outline=G, width=2)
        draw.line((cx, 94, cx, 130), fill=G, width=3)
        draw.line((cx, 104, cx + 26, 104), fill=G, width=3)
        draw.line((cx, 130, cx - 12, 152), fill=G, width=3)
        draw.line((cx, 130, cx + 12, 152), fill=G, width=3)
    draw.text((cx, 180), a, fill=G, font=font(12), anchor="mm")
    draw.text((cx, 196), b, fill=G, font=font(12), anchor="mm")
footer(draw, "Urgent medical: only when a life is at stake.", 246)
save(image, "body-more")

# --- semaphore -----------------------------------------------------------
# Positions as you look at the sender. Their right hand is on your left.
POS = {
    ("R", "down"): (-0.28, 1.0),
    ("R", "low"): (-0.9, 0.72),
    ("R", "out"): (-1.05, 0.0),
    ("R", "high"): (-0.9, -0.72),
    ("R", "up"): (-0.22, -1.05),
    ("L", "down"): (0.28, 1.0),
    ("L", "low"): (0.9, 0.72),
    ("L", "out"): (1.05, 0.0),
    ("L", "high"): (0.9, -0.72),
    ("L", "up"): (0.22, -1.05),
}
# (left-hand side, left-hand pos, right-hand side, right-hand pos)
SEMAPHORE = {
    "A": ("L", "down", "R", "low"),
    "B": ("L", "down", "R", "out"),
    "C": ("L", "down", "R", "high"),
    "D": ("L", "down", "R", "up"),
    "E": ("L", "high", "R", "down"),
    "F": ("L", "out", "R", "down"),
    "G": ("L", "low", "R", "down"),
    "H": ("R", "low", "R", "out"),
    "I": ("R", "low", "R", "up"),
    "J": ("L", "out", "R", "up"),
    "K": ("L", "up", "R", "low"),
    "L": ("L", "high", "R", "low"),
    "M": ("L", "out", "R", "low"),
    "N": ("L", "low", "R", "low"),
    "O": ("R", "high", "R", "out"),
    "P": ("L", "up", "R", "out"),
    "Q": ("L", "high", "R", "out"),
    "R": ("L", "out", "R", "out"),
    "S": ("L", "low", "R", "out"),
    "T": ("L", "up", "R", "high"),
    "U": ("L", "high", "R", "high"),
    "V": ("L", "low", "R", "up"),
    "W": ("L", "out", "L", "high"),
    "X": ("L", "low", "L", "high"),
    "Y": ("L", "out", "R", "high"),
    "Z": ("L", "out", "L", "low"),
}


def draw_letter(draw, letter, cx, cy, scale=16):
    spec = SEMAPHORE[letter]
    draw.ellipse((cx - 4, cy - 16, cx + 4, cy - 8), outline=G, width=2)
    draw.line((cx, cy - 8, cx, cy + 12), fill=G, width=2)
    pairs = ((spec[0], spec[1]), (spec[2], spec[3]))
    for side, pos in pairs:
        dx, dy = POS[(side, pos)]
        x2 = cx + dx * scale
        y2 = cy + dy * scale
        draw.line((cx, cy - 4, x2, y2), fill=G, width=3)
        draw.rectangle((x2 - 4, y2 - 3, x2 + 4, y2 + 3), fill=G)
    draw.text((cx, cy + 28), letter, fill=G, font=font(13), anchor="mm")


def semaphore_page(title, letters, name):
    image, draw = canvas(title, 16)
    cols = 7
    for index, letter in enumerate(letters):
        col = index % cols
        row = index // cols
        draw_letter(draw, letter, 40 + col * 64, 58 + row * 78, 15)
    save(image, name)


semaphore_page("Semaphore A to M  (you face the sender)", "ABCDEFGHIJKLM", "semaphore")
semaphore_page("Semaphore N to Z", "NOPQRSTUVWXYZ", "semaphore-2")

# --- flag ----------------------------------------------------------------
image, draw = canvas("Cloth high, where the sky is behind it")
draw.line((120, 240, 120, 60), fill=G, width=4)
draw.polygon([(120, 60), (210, 84), (120, 108)], fill=G)
draw.text((250, 120), "bright cloth", fill=G, font=font(16))
draw.text((250, 148), "on a pole", fill=G, font=font(16))
footer(draw, "Move it. A still flag looks like washing.")
save(image, "flag")

# --- trail ---------------------------------------------------------------
image, draw = canvas("Trail marks you agreed beforehand")
# cairn
draw.ellipse((40, 150, 70, 168), outline=G, width=3)
draw.ellipse((55, 132, 85, 152), outline=G, width=3)
draw.ellipse((48, 114, 72, 136), outline=G, width=3)
draw.text((64, 196), "cairn", fill=G, font=font(14), anchor="mm")
# arrow
draw.line((150, 150, 230, 150), fill=G, width=6)
draw.polygon([(248, 150), (220, 134), (220, 166)], fill=G)
draw.text((190, 196), "we went", fill=G, font=font(14), anchor="mm")
# X
draw.line((300, 120, 360, 180), fill=G, width=6)
draw.line((360, 120, 300, 180), fill=G, width=6)
draw.text((330, 196), "danger", fill=G, font=font(14), anchor="mm")
# note
draw.rectangle((400, 120, 460, 175), outline=G, width=3)
draw.text((430, 196), "note", fill=G, font=font(14), anchor="mm")
footer(draw, "Take your own marks down when the group is together.")
save(image, "trail")

# --- morse ---------------------------------------------------------------
image, draw = canvas("Morse    . short    - long", 16)
MORSE = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".", "F": "..-.",
    "G": "--.", "H": "....", "I": "..", "J": ".---", "K": "-.-", "L": ".-..",
    "M": "--", "N": "-.", "O": "---", "P": ".--.", "Q": "--.-", "R": ".-.",
    "S": "...", "T": "-", "U": "..-", "V": "...-", "W": ".--", "X": "-..-",
    "Y": "-.--", "Z": "--..",
    "1": ".----", "2": "..---", "3": "...--", "4": "....-", "5": ".....",
    "6": "-....", "7": "--...", "8": "---..", "9": "----.", "0": "-----",
}
keys = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890")
face = font(14)
for index, key in enumerate(keys):
    col = index // 9
    row = index % 9
    draw.text((8 + col * 118, 32 + row * 26), "%s  %s" % (key, MORSE[key]), fill=G, font=face)
save(image, "morse")

image, draw = canvas("Procedure signals, sent as one block", 16)
prosigns = (
    ("SOS", "...---...", "distress"),
    ("AR", ".-.-.", "end of message"),
    ("SK", "...-.-", "end of contact"),
    ("BT", "-...-", "break"),
    ("KN", "-.--.", "named station only"),
    ("AS", ".-...", "wait"),
    ("error", "........", "8 dots, then resend"),
)
for index, (name, code, meaning) in enumerate(prosigns):
    y = 40 + index * 30
    draw.text((16, y), name, fill=G, font=font(15))
    draw.text((110, y), code, fill=G, font=font(15))
    draw.text((250, y), meaning, fill=G, font=font(15))
save(image, "prosigns")

# --- phonetic ------------------------------------------------------------
image, draw = canvas("Phonetic alphabet", 16)
words = (
    "A Alfa", "B Bravo", "C Charlie", "D Delta", "E Echo", "F Foxtrot",
    "G Golf", "H Hotel", "I India", "J Juliett", "K Kilo", "L Lima",
    "M Mike", "N November", "O Oscar", "P Papa", "Q Quebec", "R Romeo",
    "S Sierra", "T Tango", "U Uniform", "V Victor", "W Whiskey", "X X-ray",
    "Y Yankee", "Z Zulu",
)
face = font(13)
for index, word in enumerate(words):
    col = index // 13
    row = index % 13
    draw.text((16 + col * 230, 32 + row * 18), word, fill=G, font=face)
save(image, "phonetic")

# --- tap code ------------------------------------------------------------
image, draw = canvas("Tap code: row, pause, column", 16)
grid = ("A", "B", "C/K", "D", "E", "F", "G", "H", "I", "J", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z")
left, top, cell = 150, 40, 36
for n in range(1, 6):
    draw.text((left - 22, top + (n - 1) * cell + 8), str(n), fill=G, font=font(13))
    draw.text((left + (n - 1) * cell + 10, top - 16), str(n), fill=G, font=font(13))
for index, letter in enumerate(grid):
    col = index % 5
    row = index // 5
    x = left + col * cell
    y = top + row * cell
    draw.rectangle((x, y, x + cell, y + cell), outline=G, width=1)
    draw.text((x + cell / 2, y + cell / 2), letter, fill=G, font=font(11), anchor="mm")
footer(draw, "H is 2 then 3. K shares the C square.", 268)
save(image, "tap")

# --- timing --------------------------------------------------------------
image, draw = canvas("Timing you can count")
draw.text((24, 48), "short  =  1", fill=G, font=font(18))
draw.ellipse((200, 44, 228, 72), fill=G)
draw.text((24, 88), "long   =  3 shorts", fill=G, font=font(18))
draw.rectangle((200, 84, 290, 112), fill=G)
draw.text((24, 140), "inside a letter: gap of 1", fill=G, font=font(16))
draw.text((24, 170), "between letters: gap of 3", fill=G, font=font(16))
draw.text((24, 200), "between words: gap of 7", fill=G, font=font(16))
footer(draw, "Count seconds for a torch. The deck's trainer is faster.")
save(image, "timing")

# --- mayday --------------------------------------------------------------
image, draw = canvas("MAYDAY on VHF channel 16", 17)
lines = (
    "1  MAYDAY, MAYDAY, MAYDAY",
    "2  This is <name>, three times",
    "3  Call sign or MMSI",
    "4  MAYDAY, name, call sign, MMSI",
    "5  Position",
    "6  What is wrong, help needed",
    "7  How many people. OVER",
)
for index, line in enumerate(lines):
    draw.text((18, 40 + index * 30), line, fill=G, font=font(16))
save(image, "mayday")

# --- prowords ------------------------------------------------------------
image, draw = canvas("Prowords")
rows = (
    ("OVER", "your turn to answer"),
    ("OUT", "I am finished. No reply."),
    ("SAY AGAIN", "repeat your last message"),
    ("ROGER", "I heard you"),
    ("WILCO", "I heard you and I will do it"),
)
for index, (word, meaning) in enumerate(rows):
    y = 48 + index * 40
    draw.text((16, y), word, fill=G, font=font(16))
    draw.text((170, y), meaning, fill=G, font=font(15))
save(image, "prowords")

# --- PACE ----------------------------------------------------------------
image, draw = canvas("PACE: four ways, in order")
labels = ("Primary", "Alternate", "Contingency", "Emergency")
hints = ("phone", "PMR446", "note / mesh", "999 + signal")
for index, (label, hint) in enumerate(zip(labels, hints)):
    y = 44 + index * 52
    draw.rectangle((16, y, 46, y + 30), outline=G, width=3)
    draw.text((31, y + 15), "PACE"[index], fill=G, font=font(16), anchor="mm")
    draw.text((60, y + 2), label, fill=G, font=font(16))
    draw.text((230, y + 2), hint, fill=G, font=font(16))
save(image, "pace")

# --- wallet --------------------------------------------------------------
image, draw = canvas("Wallet card")
draw.rectangle((70, 40, 410, 250), outline=G, width=3)
rows = (
    "Names and phone numbers",
    "Out-of-area contact",
    "Rally point near / far",
    "Radio channel and tone",
    "Check-in times",
    "Code words: safe / help",
    "Home grid or address",
)
for index, line in enumerate(rows):
    draw.text((86, 52 + index * 26), line, fill=G, font=font(15))
save(image, "wallet")

# --- dipole --------------------------------------------------------------
image, draw = canvas("Half-wave dipole  (receive)")
draw.line((40, 130, 210, 130), fill=G, width=6)
draw.line((270, 130, 440, 130), fill=G, width=6)
draw.line((230, 130, 230, 210), fill=G, width=3)
draw.line((250, 130, 250, 210), fill=G, width=3)
draw.text((125, 100), "75 / f", fill=G, font=font(16), anchor="mm")
draw.text((355, 100), "75 / f", fill=G, font=font(16), anchor="mm")
draw.text((240, 230), "coax", fill=G, font=font(14), anchor="mm")
footer(draw, "f in MHz, length in metres. Each leg = 75 / f.")
save(image, "dipole")

# --- j-pole --------------------------------------------------------------
image, draw = canvas("Roll-up J-pole  (receive)")
draw.line((180, 40, 180, 230), fill=G, width=4)
draw.line((230, 140, 230, 230), fill=G, width=4)
draw.line((180, 230, 230, 230), fill=G, width=4)
draw.line((200, 190, 250, 210), fill=G, width=2)
draw.text((250, 70), "half wave", fill=G, font=font(14))
draw.text((250, 170), "quarter-wave stub", fill=G, font=font(14))
footer(draw, "Short the bottom. Tape the coax a little above it.")
save(image, "jpole")

# --- ground plane --------------------------------------------------------
image, draw = canvas("Ground plane from a coax socket")
draw.rectangle((220, 70, 260, 100), outline=G, width=3)
draw.line((240, 100, 240, 200), fill=G, width=4)
draw.line((240, 100, 160, 160), fill=G, width=3)
draw.line((240, 100, 320, 160), fill=G, width=3)
draw.line((240, 100, 190, 180), fill=G, width=3)
draw.line((240, 100, 290, 180), fill=G, width=3)
draw.text((300, 80), "socket", fill=G, font=font(14))
footer(draw, "Vertical and each radial: 75 / f metres.")
save(image, "groundplane")

# --- pmr -----------------------------------------------------------------
image, draw = canvas("PMR446 group plan")
draw.text((20, 48), "Primary channel   ____    tone ____", fill=G, font=font(16))
draw.text((20, 88), "Backup channel    ____    tone ____", fill=G, font=font(16))
draw.text((20, 128), "Check-in          ____    and ____", fill=G, font=font(16))
draw.text((20, 176), "Same channel AND same tone,", fill=G, font=font(16))
draw.text((20, 204), "or a filtered radio stays quiet.", fill=G, font=font(16))
footer(draw, "0.5 W, built-in aerial. No official calling channel.")
save(image, "pmr")

# --- ctcss ---------------------------------------------------------------
image, draw = canvas("CTCSS is a filter, not a lock")
draw.rectangle((40, 80, 200, 160), outline=G, width=3)
draw.text((120, 110), "radio A", fill=G, font=font(16), anchor="mm")
draw.text((120, 136), "tone 12", fill=G, font=font(14), anchor="mm")
draw.rectangle((280, 80, 440, 160), outline=G, width=3)
draw.text((360, 110), "radio B", fill=G, font=font(16), anchor="mm")
draw.text((360, 136), "tone 12", fill=G, font=font(14), anchor="mm")
draw.line((200, 120, 280, 120), fill=G, width=3)
draw.polygon([(270, 120), (254, 112), (254, 128)], fill=G)
footer(draw, "Anyone with the tone off can still hear you.")
save(image, "ctcss")

# --- alerts --------------------------------------------------------------
image, draw = canvas("UK Emergency Alerts")
draw.rounded_rectangle((150, 50, 330, 220), radius=12, outline=G, width=3)
draw.text((240, 90), "SIREN", fill=G, font=font(20), anchor="mm")
draw.text((240, 130), "about 10 seconds", fill=G, font=font(14), anchor="mm")
draw.text((240, 160), "even if silent", fill=G, font=font(14), anchor="mm")
footer(draw, "Stop. Read it when safe. Follow the instruction.")
save(image, "alerts")

# --- radio tab -----------------------------------------------------------
image, draw = canvas("RADIO tab on this deck")
tabs = ("FREQ", "LOG", "MORSE", "LIVE")
for index, label in enumerate(tabs):
    x = 16 + index * 116
    draw.rectangle((x, 48, x + 104, 88), outline=G, width=3)
    draw.text((x + 52, 68), label, fill=G, font=font(16), anchor="mm")
draw.text((24, 110), "FREQ   cards. LISTEN OK or NOT FOR YOU", fill=G, font=font(15))
draw.text((24, 142), "LOG    what you heard, on this Pi", fill=G, font=font(15))
draw.text((24, 174), "MORSE  trainer, and a practice key", fill=G, font=font(15))
draw.text((24, 206), "LIVE   FM only, with an RTL-SDR", fill=G, font=font(15))
footer(draw, "LIVE: DOWN, LISTEN, UP, presets, then BARS.")
save(image, "radio-tab")

# --- mesh ----------------------------------------------------------------
image, draw = canvas("Meshtastic: text hops by radio")
centres = ((80, 130), (240, 80), (400, 130), (240, 200))
for cx, cy in centres:
    draw.rounded_rectangle((cx - 36, cy - 22, cx + 36, cy + 22), radius=6, outline=G, width=3)
    draw.text((cx, cy), "node", fill=G, font=font(14), anchor="mm")
draw.line((116, 120, 204, 90), fill=G, width=2)
draw.line((276, 90, 364, 120), fill=G, width=2)
draw.line((240, 102, 240, 178), fill=G, width=2)
draw.line((110, 148, 210, 190), fill=G, width=2)
draw.line((270, 190, 370, 148), fill=G, width=2)
footer(draw, "UK: region EU_868 before it transmits.")
save(image, "mesh")
