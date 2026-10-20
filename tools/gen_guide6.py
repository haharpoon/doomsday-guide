"""Diagrams for batch 6: First aid additions, Hunting & fishing, Cooking & preserving,
Animals & livestock, Repairs & making, and Sanitation. Run from the repo root.

480x284 PNG, bold #1AFF80 lines on black. The drawing helpers (new, t, L, C, E, dot,
arrow, dashed, divider, box, lines, circle_arrow, save) come from gen_guide5.py; only
its helper section is loaded, so its own pictures are not redrawn.
"""
import math
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "gen_guide5.py"), encoding="utf-8") as _handle:
    _src = _handle.read()
exec(_src.split("# ---------------- Childbirth")[0])  # noqa: S102  helpers only


def hatch(d, xy, step=10, w=2):
    """Diagonal hatching inside a box: insulation, soil."""
    x0, y0, x1, y1 = xy
    for k in range(int(x0 - (y1 - y0)), int(x1), step):
        a = (max(x0, k), y1 - (max(x0, k) - k))
        b = (min(x1, k + (y1 - y0)), y1 - (min(x1, k + (y1 - y0)) - k))
        if a[0] < b[0]:
            L(d, [a, b], w)


def dots(d, xy, step=12, r=2):
    x0, y0, x1, y1 = xy
    row = 0
    for y in range(int(y0) + step // 2, int(y1), step):
        off = (step // 2) if row % 2 else 0
        for x in range(int(x0) + step // 2 + off, int(x1), step):
            dot(d, (x, y), r)
        row += 1


def flame(d, cx, base, h=26, w=12):
    d.polygon([(cx - w, base), (cx - w * 0.6, base - h * 0.55), (cx, base - h),
               (cx + w * 0.6, base - h * 0.55), (cx + w, base)], outline=G, width=3)


def cross(d, c, s=10, w=4):
    L(d, [(c[0] - s, c[1] - s), (c[0] + s, c[1] + s)], w)
    L(d, [(c[0] - s, c[1] + s), (c[0] + s, c[1] - s)], w)


def fish(d, cx, cy, s=1.0, fill=None):
    E(d, [cx - 22 * s, cy - 9 * s, cx + 14 * s, cy + 9 * s], 3, fill=fill)
    d.polygon([(cx + 12 * s, cy), (cx + 26 * s, cy - 9 * s), (cx + 26 * s, cy + 9 * s)], outline=G, width=3, fill=fill)


# ======================= FIRST AID =======================
im, d = new("AED PAD PLACEMENT")
# torso, front view. Their right is on the viewer's left.
L(d, [(60, 70), (110, 52), (150, 52)], 5); L(d, [(190, 52), (230, 52), (280, 70)], 5)  # shoulders
d.arc([150, 30, 190, 70], 0, 180, fill=G, width=5)                                    # neck base
L(d, [(60, 70), (64, 260)], 5); L(d, [(280, 70), (276, 260)], 5)                      # sides
L(d, [(110, 70), (160, 76)], 3); L(d, [(180, 76), (230, 70)], 3)                      # collarbones
d.rounded_rectangle([86, 86, 146, 126], 6, outline=G, width=4, fill=None)              # pad 1
t(d, (116, 106), "PAD", 15, "mm")
d.rounded_rectangle([222, 160, 270, 222], 6, outline=G, width=4)                       # pad 2 on the side
t(d, (246, 191), "PAD", 15, "mm")
dot(d, (130, 160), 5); dot(d, (210, 160), 5)                                          # nipples
t(d, (64, 266), "their RIGHT", 14, "lb"); t(d, (276, 266), "their LEFT", 14, "rb")
lines(d, 298, 44, ["1. Switch on,", "   follow voice", "2. Bare, dry", "   chest", "3. Pads on", "4. STAND CLEAR", "5. Shock if told", "6. CPR at once"], 16, 6)
save(im, "fa_aed_pads")

im, d = new("HEART ATTACK: SIT AND REST")
L(d, [(40, 40), (40, 250)], 6)                         # wall
L(d, [(20, 250), (300, 250)], 4)                       # floor
C(d, (70, 84), 22, 5)                                  # head
L(d, [(68, 106), (64, 238)], 8)                        # back against the wall
L(d, [(64, 238), (150, 168)], 7)                       # thigh up to the knee
L(d, [(150, 168), (176, 246)], 7)                      # shin down
L(d, [(176, 246), (206, 246)], 6)                      # foot
L(d, [(66, 132), (142, 174)], 5)                       # arm resting on the knee
t(d, (150, 60), "back against", 15, "ma"); t(d, (150, 78), "a wall", 15, "ma")
arrow(d, (130, 98), (76, 150), 3)
t(d, (222, 190), "knees bent", 15, "ma")
lines(d, 300, 44, ["1. Call 999", "2. Sit like this", "3. Aspirin 300 mg", "   chewed: adults,", "   not allergic", "4. Their GTN spray", "5. Watch breathing", "   CPR + AED if it", "   stops"], 15, 5)
save(im, "fa_heart_attack")

im, d = new("STROKE? THINK F.A.S.T.")
cols = [60, 180, 300, 420]
for cx, letter in zip(cols, "FAST"):
    C(d, (cx, 70), 24, 4)
    t(d, (cx, 70), letter, 26, "mm")
# Face: droop
C(d, (60, 160), 38, 4)
dot(d, (46, 148), 4); dot(d, (74, 152), 4)
d.line([(42, 178), (60, 176), (78, 186)], fill=G, width=4)
t(d, (60, 210), "FACE", 16, "ma"); t(d, (60, 230), "droops", 15, "ma")
# Arms: one drifts down
C(d, (180, 128), 14, 4)
L(d, [(180, 142), (180, 194)], 5)
L(d, [(180, 152), (230, 150)], 5)
L(d, [(180, 152), (138, 178)], 5)
dashed(d, (180, 152), (132, 150), 2, 5, 4)
arrow(d, (126, 152), (128, 178), 2, 8)
t(d, (180, 210), "ARMS", 16, "ma"); t(d, (180, 230), "one drifts", 15, "ma")
# Speech: bubble with a wavy line
d.rounded_rectangle([256, 126, 344, 182], 14, outline=G, width=4)
d.polygon([(276, 182), (270, 198), (292, 182)], fill=G)
pts = [(268 + k * 6, 154 + (6 if k % 2 else -6)) for k in range(13)]
d.line(pts, fill=G, width=3)
t(d, (300, 210), "SPEECH", 16, "ma"); t(d, (300, 230), "slurred", 15, "ma")
# Time: clock and 999
C(d, (420, 154), 34, 4)
L(d, [(420, 154), (420, 132)], 4); L(d, [(420, 154), (438, 164)], 4)
t(d, (420, 210), "TIME", 16, "ma"); t(d, (420, 230), "call 999", 15, "ma")
t(d, (240, 258), "Note the time it started. Nothing by mouth.", 15, "ma")
save(im, "fa_fast")

im, d = new("ASTHMA ATTACK: BLUE RELIEVER")
# inhaler
d.rounded_rectangle([24, 52, 64, 132], 8, outline=G, width=4)
d.rectangle([22, 130, 92, 156], outline=G, width=4)
t(d, (44, 170), "sit up", 15, "ma"); t(d, (44, 188), "shake", 15, "ma")
# puff timeline
y = 98
L(d, [(110, y), (460, y)], 3)
for k in range(10):
    x = 120 + k * 37
    C(d, (x, y), 13, 3, fill=G if k == 0 else None)
    t(d, (x, y), str(k + 1), 13, "mm") if k else None
t(d, (120, y), "1", 13, "mm")
d.text((120, y), "1", fill=K, font=f(13), anchor="mm")
t(d, (285, 60), "1 puff every 30-60 seconds", 16, "ma")
t(d, (285, 124), "up to 10 puffs", 16, "ma")
box(d, (110, 156, 470, 206), "Worse at any time, or no better\nafter 10 puffs: CALL 999", 15)
t(d, (8, 220), "No ambulance after 10 min: repeat the 10 puffs.", 15)
t(d, (8, 244), "AIR/MART inhaler: 1 puff every 1-3 min, max 6.", 15)
save(im, "fa_asthma")

im, d = new("NOSEBLEED")
# side view, leaning forward: torso slants up to the right, head forward and down
L(d, [(60, 262), (140, 166)], 8)                      # torso
C(d, (170, 130), 46, 5)                               # head
d.polygon([(212, 138), (240, 164), (210, 168)], outline=G, width=4)   # nose
L(d, [(204, 186), (218, 184)], 3)                     # mouth
# hand pinching the soft part of the nose, arm back to the body
d.rounded_rectangle([222, 146, 250, 176], 8, outline=G, width=4)
L(d, [(236, 176), (186, 222), (110, 204)], 5)
for k in range(3):
    dot(d, (230, 192 + k * 16), 4)                    # drips fall forward
arrow(d, (60, 70), (120, 96), 3)
t(d, (20, 40), "lean FORWARD", 15)
# small inset: head back is wrong
t(d, (300, 248), "NEVER tip the", 15); t(d, (300, 266), "head back.", 15)
lines(d, 300, 44, ["Pinch the SOFT", "part, above the", "nostrils.", "", "10-15 minutes", "by the clock.", "", "Breathe through", "the mouth.", "Spit blood out."], 15, 3)
save(im, "fa_nosebleed")

im, d = new("TICK REMOVAL")
SK = 196
L(d, [(10, SK), (300, SK)], 4)
for x in range(20, 300, 28):
    L(d, [(x, SK + 8), (x + 12, SK + 8)], 2)
# tick: body above skin, head into skin
E(d, [124, 150, 176, 190], 4)
for k in (-1, 1):
    for j in range(3):
        L(d, [(150 + k * 22, 160 + j * 10), (150 + k * 40, 152 + j * 14)], 3)
L(d, [(150, 190), (150, SK + 8)], 5)
# tweezers jaws gripping at the skin
d.line([(150, 30), (116, 112), (146, 192)], fill=G, width=5, joint="curve")
d.line([(150, 30), (184, 112), (154, 192)], fill=G, width=5, joint="curve")
arrow(d, (222, 180), (222, 70), 4)
t(d, (232, 100), "slow,", 15); t(d, (232, 118), "steady,", 15); t(d, (232, 136), "straight", 15); t(d, (232, 154), "up", 15)
t(d, (150, 228), "grip HERE, at the skin", 15, "ma")
lines(d, 340, 50, ["DO NOT:", "squeeze body", "twist hard", "burn it", "use oil, cream", "", "Then: wash,", "note the date"], 15, 5)
save(im, "fa_tick")

im, d = new("LOG ROLL: TURN AS ONE")
# casualty lying, top view: head left
C(d, (92, 150), 24, 5)
d.rounded_rectangle([118, 128, 360, 172], 20, outline=G, width=5)
L(d, [(360, 140), (440, 140)], 5); L(d, [(360, 160), (440, 160)], 5)   # legs
# head holder
d.rounded_rectangle([20, 128, 54, 172], 10, outline=G, width=4)
t(d, (37, 182), "HEAD", 14, "ma"); t(d, (37, 198), "leads", 14, "ma")
L(d, [(54, 140), (74, 140)], 4); L(d, [(54, 160), (74, 160)], 4)
# helpers kneeling on one side (below)
for x, lab in ((160, "shoulders"), (260, "hips"), (380, "legs")):
    C(d, (x, 222), 16, 4)
    L(d, [(x, 206), (x, 176)], 3)
    t(d, (x, 244), lab, 14, "ma")
# roll arrow toward the helpers
d.arc([180, 60, 300, 140], 200, 340, fill=G, width=3)
arrow(d, (292, 104), (300, 122), 3, 10)
t(d, (240, 40), '"Ready, steady, roll"', 16, "ma")
t(d, (240, 264), "Nose stays in line with the belly button.", 14, "ma")
save(im, "fa_log_roll")

im, d = new("FOUR-HANDED SEAT")
# square of four forearms seen from above
S0, S1 = 110, 190
L(d, [(S0, S0 - 30), (S1, S0 - 30)], 9)                    # A's arm
L(d, [(S1 + 30, S0), (S1 + 30, S1)], 9)                    # B's arm
L(d, [(S1, S1 + 30), (S0, S1 + 30)], 9)
L(d, [(S0 - 30, S1), (S0 - 30, S0)], 9)
for c in ((S0 - 30, S0 - 30), (S1 + 30, S0 - 30), (S1 + 30, S1 + 30), (S0 - 30, S1 + 30)):
    C(d, c, 18, 5)                                         # fists gripping wrists
t(d, (150, 150), "SEAT", 18, "mm")
t(d, (40, 150), "A", 20, "mm"); t(d, (260, 150), "B", 20, "mm")
lines(d, 290, 44, ["Each grips own", "right wrist with", "left hand, then", "the other's left", "wrist.", "", "Casualty sits and", "holds both", "shoulders."], 15, 4)
t(d, (8, 262), "Only for someone who can hold on.", 15)
save(im, "fa_four_hand_seat")

im, d = new("BLANKET STRETCHER")
for k, (x0, lab) in enumerate(((10, "1. pole at 1/3"), (170, "2. fold over"), (330, "3. 2nd pole, fold"))):
    cy = 140
    if k == 0:
        L(d, [(x0, cy), (x0 + 140, cy)], 4)
        C(d, (x0 + 50, cy - 8), 8, 4, fill=G)
    elif k == 1:
        L(d, [(x0 + 40, cy), (x0 + 140, cy)], 4)
        d.arc([x0 + 34, cy - 16, x0 + 54, cy + 4], 90, 270, fill=G, width=4)
        L(d, [(x0 + 44, cy - 16), (x0 + 130, cy - 16)], 4)
        C(d, (x0 + 44, cy - 8), 8, 4, fill=G)
    else:
        L(d, [(x0 + 30, cy), (x0 + 110, cy)], 4)
        C(d, (x0 + 30, cy - 8), 8, 4, fill=G)
        C(d, (x0 + 100, cy - 24), 8, 4, fill=G)
        L(d, [(x0 + 30, cy - 16), (x0 + 110, cy - 16)], 4)
        L(d, [(x0 + 22, cy - 32), (x0 + 130, cy - 32)], 4)
    t(d, (x0 + 70, 180), lab, 14, "ma")
    if k < 2:
        arrow(d, (x0 + 140, 100), (x0 + 168, 100), 3, 10)
t(d, (240, 40), "End view: blanket folded in thirds round two poles", 14, "ma")
t(d, (8, 220), "Body weight holds the folds shut.", 15)
t(d, (8, 244), "Test with a healthy person first.", 15)
t(d, (8, 264), "Feet first on the flat; head uphill on slopes.", 14)
save(im, "fa_stretcher")

im, d = new("TRIAGE: SORT IN UNDER A MINUTE")
rows = [("Can walk?", "YES", "GREEN"),
        ("Breathing after", "NO", "BLACK"),
        ("Breaths over 30/min?", "YES", "RED"),
        ("No wrist pulse, or", "YES", "RED"),
        ("Cannot obey simple", "YES", "RED"),
        ("All the rest", "", "YELLOW")]
sub = {1: "airway opened?", 3: "refill over 2 s?", 4: "commands?"}
for k, (q, ans, out) in enumerate(rows):
    y = 38 + k * 38
    t(d, (12, y + 2), q, 15)
    if k in sub:
        t(d, (12, y + 19), sub[k], 13)
    if ans:
        t(d, (262, y + 10), ans, 14, "mm")
        arrow(d, (284, y + 10), (330, y + 10), 3, 9)
    else:
        arrow(d, (200, y + 10), (330, y + 10), 3, 9)
    d.rounded_rectangle([336, y - 2, 470, y + 24], 6, outline=G, width=4 if out == "RED" else 2,
                        fill=G if out == "RED" else None)
    d.text((403, y + 11), out, fill=K if out == "RED" else G, font=f(16), anchor="mm")
    if k < 5:
        t(d, (240, y + 29), "no" if k != 1 else "yes", 12, "mm")
t(d, (8, 278), "Stop only to open airways and press on bleeding.", 13, "ld")
save(im, "fa_triage")

im, d = new("OBSERVATIONS CHART")
cols = [("Time", 58), ("Temp", 60), ("Pulse", 62), ("Breaths", 76), ("Drinks", 70), ("Pee", 64), ("Alert?", 74)]
x = 8
y0, rh = 40, 34
xs = [x]
for name, w in cols:
    x += w
    xs.append(x)
for i in range(6):
    L(d, [(8, y0 + i * rh), (xs[-1], y0 + i * rh)], 2 if i else 3)
for xx in xs:
    L(d, [(xx, y0), (xx, y0 + 5 * rh)], 2)
for (name, w), xx in zip(cols, xs):
    t(d, (xx + w / 2, y0 + rh / 2), name, 14, "mm")
data = [("08:00", "37.8", "92", "18", "300 ml", "pale", "yes"),
        ("12:00", "38.6", "104", "22", "200 ml", "dark", "yes"),
        ("16:00", "39.2", "118", "26!", "100 ml", "none", "muddled")]
for r, row in enumerate(data):
    for (name, w), xx, val in zip(cols, xs, row):
        t(d, (xx + w / 2, y0 + (r + 1.5) * rh), val, 14, "mm")
t(d, (8, 220), "Every 4 hours, more often if worse. Write it down.", 15)
t(d, (8, 244), "Getting worse like the 16:00 row: get help NOW.", 15)
save(im, "fa_obs_chart")

# ======================= HUNTING & FISHING =======================
im, d = new("WHERE FISH LIE IN A RIVER")
# river banks, flowing left to right, with a bend
top = [(0, 60), (120, 54), (220, 70), (320, 50), (480, 64)]
bot = [(0, 200), (120, 206), (220, 236), (320, 214), (480, 222)]
d.line(top, fill=G, width=5, joint="curve")
d.line(bot, fill=G, width=5, joint="curve")
arrow(d, (20, 130), (80, 130), 3)
t(d, (20, 110), "flow", 14)
# rock and the slack water behind it
E(d, [120, 104, 160, 140], 4, fill=G)
fish(d, 190, 122, 0.8)
t(d, (140, 146), "behind rocks", 14, "ma")
# deep pool
dashed(d, (250, 120), (330, 120), 2); dashed(d, (250, 170), (330, 170), 2)
dashed(d, (250, 120), (250, 170), 2); dashed(d, (330, 120), (330, 170), 2)
fish(d, 294, 145, 0.8)
t(d, (290, 176), "deep pool", 14, "ma")
# undercut bank top right
for x in range(360, 470, 16):
    L(d, [(x, 60), (x + 8, 74)], 2)
fish(d, 418, 88, 0.8)
t(d, (414, 100), "undercut bank", 14, "ma")
# inside of bend, bottom
fish(d, 220, 214, 0.7)
t(d, (220, 244), "inside of bends:", 14, "ma")
t(d, (220, 262), "slow water", 14, "ma")
t(d, (8, 270), "dawn and dusk best", 14, "ld")
save(im, "hf_where_fish")

im, d = new("HANDLINE RIG")
WATER = 104
L(d, [(110, WATER), (470, WATER)], 3)
for x in range(120, 470, 30):
    d.arc([x, WATER - 4, x + 16, WATER + 4], 0, 180, fill=G, width=2)
# bank and stick reel
d.polygon([(0, 80), (100, 80), (110, 284), (0, 284)], outline=G, width=3)
d.rectangle([34, 40, 50, 92], outline=G, width=4)
for y in range(46, 88, 6):
    L(d, [(34, y), (50, y + 3)], 2)
t(d, (8, 20 + 76), "", 14)
t(d, (42, 100), "stick", 14, "ma"); t(d, (42, 116), "reel", 14, "ma")
# line
d.line([(50, 50), (200, 50), (250, 92)], fill=G, width=2)
# float
E(d, [242, 86, 258, 116], 3, fill=G)
L(d, [(250, 116), (250, 236)], 2)
# weight
E(d, [243, 176, 257, 190], 3, fill=G)
# hook with worm
d.arc([236, 230, 260, 258], 0, 200, fill=G, width=4)
d.line([(238, 244), (246, 236), (252, 248), (258, 238)], fill=G, width=3)
t(d, (266, 78), "float", 15, "lm")
t(d, (266, 183), "weight", 15, "lm")
L(d, [(226, 184), (226, 240)], 2); L(d, [(220, 184), (232, 184)], 2); L(d, [(220, 240), (232, 240)], 2)
t(d, (220, 212), "20-30 cm", 14, "rm")
t(d, (270, 246), "hook, point hidden", 15, "lm")
t(d, (300, 130), "Bites: wait for a", 15); t(d, (300, 150), "firm pull, then a", 15); t(d, (300, 170), "short sharp tug.", 15)
save(im, "hf_handline")

im, d = new("GUT A FISH")
# big fish, head on the right
E(d, [40, 70, 350, 200], 5)
d.polygon([(48, 135), (8, 90), (8, 180)], outline=G, width=5)   # tail at left
C(d, (304, 118), 9, 4)                                           # eye
d.arc([226, 80, 286, 190], 300, 60, fill=G, width=4)            # gill cover line
dot(d, (120, 186), 6)                                            # vent near the tail
t(d, (120, 214), "vent", 15, "ma")
dashed(d, (124, 194), (264, 194), 4, 10, 6)
arrow(d, (150, 236), (270, 236), 3)
t(d, (210, 246), "cut forward", 15, "ma")
t(d, (290, 214), "gills out", 15, "ma")
dashed(d, (100, 132), (260, 132), 2, 6, 6)
t(d, (180, 110), "blood line: scrape out", 14, "ma")
lines(d, 366, 50, ["Kill:", "2 blows", "above eyes", "", "Shallow", "cut: do", "not burst", "the guts"], 15, 4)
save(im, "hf_gut_fish")

im, d = new("SKIN AND OPEN A RABBIT")
divider(d, 240)
# 1: skin pulled apart from a slit across the back (top view, head left)
t(d, (120, 34), "1. SKIN", 16, "ma")
d.rounded_rectangle([66, 100, 186, 170], 30, outline=G, width=4)    # body
C(d, (50, 135), 18, 4)                                              # head
E(d, [20, 104, 50, 116], 3); E(d, [20, 154, 50, 166], 3)            # ears laid back
dashed(d, (126, 104), (126, 166), 4, 8, 5)                          # slit across the back
arrow(d, (114, 135), (78, 135), 4, 10)
arrow(d, (138, 135), (174, 135), 4, 10)
t(d, (126, 180), "slit the back,", 14, "ma")
t(d, (126, 198), "pull both ways", 14, "ma")
t(d, (126, 216), "like a jumper", 14, "ma")
# 2: belly, cut from pelvis to ribs, fingers under the blade
t(d, (360, 34), "2. OPEN BELLY", 16, "ma")
d.rounded_rectangle([310, 60, 410, 196], 34, outline=G, width=4)
t(d, (360, 76), "ribs", 14, "ma"); t(d, (360, 178), "pelvis", 14, "ma")
dashed(d, (360, 96), (360, 172), 4, 8, 5)
arrow(d, (430, 170), (430, 96), 3)
t(d, (446, 120), "cut", 14, "lm"); t(d, (446, 138), "up", 14, "lm")
lines(d, 360, 206, ["Lift the wall with", "two fingers. Do not", "cut gut or bladder."], 14, 3, "ma")
save(im, "hf_rabbit")

# ======================= COOKING =======================
im, d = new("ROCKET STOVE (cut through)")
# insulation either side of the chimney
hatch(d, (152, 92, 188, 198), 12, 2); hatch(d, (252, 92, 288, 254), 12, 2)
L(d, [(150, 90), (150, 200)], 4); L(d, [(290, 90), (290, 256)], 4)        # outer walls
L(d, [(150, 90), (190, 90)], 4); L(d, [(250, 90), (290, 90)], 4)
L(d, [(190, 90), (190, 200)], 5); L(d, [(250, 90), (250, 256)], 5)        # chimney walls
L(d, [(40, 200), (190, 200)], 5)                                          # tunnel roof
L(d, [(40, 256), (290, 256)], 5)                                          # floor
L(d, [(56, 232), (210, 232)], 3)                                          # fuel shelf
for y in (214, 222):
    L(d, [(14, y), (176, y)], 4)                                          # sticks on the shelf
flame(d, 214, 230, 30, 12)
for x in (206, 220, 234):
    arrow(d, (x, 186), (x, 100), 2, 8)
arrow(d, (14, 246), (70, 246), 2, 8)
# pot on stones
C(d, (198, 82), 5, 3, fill=G); C(d, (242, 82), 5, 3, fill=G)
d.rounded_rectangle([160, 34, 280, 76], 8, outline=G, width=4)
t(d, (220, 55), "POT", 15, "mm")
t(d, (300, 52), "2-3 cm gap", 14)
t(d, (300, 120), "insulation:", 14); t(d, (300, 138), "soil, ash", 14)
t(d, (300, 172), "chimney", 14); t(d, (300, 190), "30-40 cm", 14)
t(d, (8, 140), "feed sticks", 14); t(d, (8, 158), "in sideways", 14)
t(d, (8, 266), "air under the shelf", 13)
save(im, "ck_rocket_stove")

im, d = new("HAYBOX COOKER")
d.rectangle([30, 50, 270, 260], outline=G, width=5)
dots(d, (36, 56, 264, 254), 14, 2)
d.rectangle([60, 40, 240, 76], outline=G, width=4, fill=K)          # cushion lid
t(d, (150, 58), "cushion", 14, "mm")
d.rounded_rectangle([90, 120, 210, 220], 10, outline=G, width=5, fill=K)  # pot
L(d, [(80, 120), (220, 120)], 5)
t(d, (150, 170), "POT", 16, "mm")
d.rectangle([96, 228, 204, 248], fill=K)
t(d, (150, 238), "hay all round", 14, "mm")
lines(d, 288, 50, ["1. Boil, lid on:", "   5-15 min", "2. Into the box", "   fast, no gaps", "3. Leave:", "   rice 1-2 h", "   stew 3-4 h", "   beans 4-6 h", "4. Cooled? Boil", "   again to eat"], 15, 4)
save(im, "ck_haybox")

im, d = new("SAUERKRAUT: KEEP IT UNDER BRINE")
# jar
L(d, [(60, 70), (60, 250), (240, 250), (240, 70)], 5)
L(d, [(48, 62), (252, 62)], 4)
# cloth draped on top
d.line([(40, 54), (80, 46), (150, 50), (220, 44), (260, 54)], fill=G, width=3, joint="curve")
# brine line
L(d, [(64, 128), (236, 128)], 2)
for x in range(70, 236, 18):
    d.arc([x, 124, x + 12, 132], 0, 180, fill=G, width=2)
# small weight jar
d.rounded_rectangle([110, 90, 190, 150], 8, outline=G, width=4)
t(d, (150, 112), "weight", 14, "mm")
# shredded cabbage below
for y in range(160, 246, 12):
    for x in range(72, 230, 22):
        L(d, [(x, y), (x + 14, y - 5 + (x % 3) * 3)], 3)
t(d, (250, 130), "brine above", 14, "lm")
lines(d, 272, 168, ["20 g salt per", "1 kg cabbage (2%)", "18-24°C:", "3-4 weeks"], 15, 4)
save(im, "ck_sauerkraut")

im, d = new("WATER-BATH CANNING")
# pot
L(d, [(20, 60), (20, 260), (300, 260), (300, 60)], 5)
L(d, [(10, 60), (310, 60)], 4)
L(d, [(30, 240), (290, 240)], 4)                          # rack
for x in range(40, 290, 30):
    L(d, [(x, 240), (x, 252)], 2)
# jars
for x in (36, 120, 204):
    d.rounded_rectangle([x, 130, x + 62, 238], 10, outline=G, width=4)
    d.rectangle([x + 6, 118, x + 56, 130], fill=G)        # lid
# water level
WL = 92
for x in range(26, 290, 26):
    d.arc([x, WL - 5, x + 20, WL + 5], 180, 360, fill=G, width=3)
L(d, [(280, WL), (280, 118)], 2); L(d, [(274, WL), (286, WL)], 2); L(d, [(274, 118), (286, 118)], 2)
t(d, (316, 92), "2.5 cm of", 15); t(d, (316, 110), "water over", 15); t(d, (316, 128), "the lids", 15)
lines(d, 316, 160, ["Rolling boil", "all the time.", "HIGH-ACID", "food only."], 15, 4)
for x in (67, 151, 235):
    C(d, (x, 230), 3, 2)
save(im, "ck_water_bath")

im, d = new("POTATO CLAMP (cut through)")
GND = 220
L(d, [(0, GND), (480, GND)], 3)
# ditches
d.arc([20, GND - 20, 70, GND + 24], 0, 180, fill=G, width=4)
d.arc([410, GND - 20, 460, GND + 24], 0, 180, fill=G, width=4)
# soil outer mound
d.polygon([(80, GND), (240, 60), (400, GND)], outline=G, width=5)
# straw layer
d.polygon([(110, GND), (240, 92), (370, GND)], outline=G, width=3)
# roots inside
d.polygon([(140, GND - 4), (240, 124), (340, GND - 4)], outline=G, width=2)
for (x, y) in ((200, 200), (240, 200), (280, 200), (220, 176), (260, 176), (240, 152)):
    E(d, [x - 14, y - 9, x + 14, y + 9], 3, fill=G)
# straw base
L(d, [(110, GND - 2), (370, GND - 2)], 3)
# straw vent at the top
L(d, [(236, 40), (236, 124)], 3); L(d, [(244, 40), (244, 124)], 3)
t(d, (256, 36), "straw vent", 14)
t(d, (380, 96), "15 cm soil", 14); arrow(d, (376, 104), (330, 132), 2, 8)
t(d, (30, 96), "20 cm straw", 14); arrow(d, (120, 106), (168, 150), 2, 8)
t(d, (45, 248), "ditch", 14, "ma"); t(d, (435, 248), "ditch", 14, "ma")
t(d, (240, 262), "Well-drained spot. Sound, dry, unwashed roots.", 14, "ma")
save(im, "ck_clamp")

# ======================= ANIMALS =======================
im, d = new("HEN HOUSE AND RUN")
GND = 214
d.polygon([(30, 74), (130, 36), (230, 74)], outline=G, width=5)
d.rectangle([40, 74, 220, GND], outline=G, width=5)
for x in (60, 90, 170, 200):
    d.rectangle([x - 6, 82, x + 6, 90], fill=G)       # high vents
t(d, (130, 96), "vents high up", 13, "ma")
L(d, [(140, 128), (210, 128)], 6)                    # perch, high
t(d, (175, 136), "perch", 14, "ma")
d.rectangle([48, 160, 100, 200], outline=G, width=4)  # nest box, low
t(d, (74, 144), "nest", 14, "ma")
d.rectangle([150, 180, 178, GND], outline=G, width=3) # pop-hole
L(d, [(178, GND), (226, GND - 22)], 4)                # ramp
# run with mesh
L(d, [(220, 100), (460, 100)], 3); L(d, [(460, 100), (460, GND)], 3)
for x in range(230, 460, 16):
    L(d, [(x, 100), (x, GND)], 1)
for y in range(110, GND, 16):
    L(d, [(220, y), (460, y)], 1)
L(d, [(10, GND), (470, GND)], 4)                      # ground
# mesh carried 30 cm below ground
for x in range(230, 470, 16):
    L(d, [(x, GND), (x, GND + 36)], 1)
L(d, [(220, GND + 36), (470, GND + 36)], 2)
t(d, (340, GND + 48), "mesh buried 30 cm (or a skirt)", 13, "ma")
t(d, (12, 236), "Mesh, not chicken", 14); t(d, (12, 254), "wire. Shut in at dusk.", 14)
save(im, "an_coop")

im, d = new("QUICK DOG MUZZLE")
for k, (cx, lab) in enumerate(((80, "1. loop over nose"), (240, "2. cross under jaw"), (400, "3. tie behind ears"))):
    C(d, (cx - 24, 120), 30, 4)                                   # head
    d.rounded_rectangle([cx, 108, cx + 58, 136], 10, outline=G, width=4)   # snout
    dot(d, (cx + 54, 114), 5)                                     # nose
    d.polygon([(cx - 46, 100), (cx - 38, 70), (cx - 24, 92)], outline=G, width=3)  # ear
    d.rounded_rectangle([cx + 22, 100, cx + 34, 144], 4, outline=G, width=4)       # the loop
    if k == 0:
        arrow(d, (cx + 28, 62), (cx + 28, 96), 3, 9)
    elif k == 1:
        L(d, [(cx + 22, 144), (cx + 42, 170)], 4); L(d, [(cx + 34, 144), (cx + 14, 170)], 4)
    else:
        d.line([(cx + 28, 144), (cx - 10, 156), (cx - 52, 106)], fill=G, width=4)
        C(d, (cx - 54, 102), 6, 3, fill=G)
    t(d, (cx, 196), lab, 14, "ma")
t(d, (240, 236), "Use a soft bandage or tie. Not if it is", 15, "ma")
t(d, (240, 256), "vomiting or struggling to breathe.", 15, "ma")
save(im, "an_muzzle")

# ======================= REPAIRS =======================
im, d = new("SHARPEN AN AXE")
divider(d, 240)
# left: axe head side view with the file stroke direction
d.polygon([(40, 80), (150, 70), (210, 50), (220, 160), (150, 150), (40, 150)], outline=G, width=5)
d.rectangle([40, 90, 70, 140], outline=G, width=3)                 # eye
dashed(d, (170, 60), (182, 156), 2)
for y in (80, 110, 140):
    arrow(d, (214, y), (176, y + 4), 3, 9)
t(d, (120, 180), "push the file from", 14, "ma")
t(d, (120, 198), "the edge INTO the steel", 14, "ma")
t(d, (120, 222), "push stroke only", 14, "ma")
# right: edge cross-section, slightly convex
pts_l, pts_r = [], []
for k in range(21):
    u = k / 20
    y = 60 + 190 * u
    w = 46 * (1 - u) ** 0.6
    pts_l.append((360 - w, y)); pts_r.append((360 + w, y))
d.line(pts_l, fill=G, width=5, joint="curve"); d.line(pts_r, fill=G, width=5, joint="curve")
t(d, (360, 36), "edge, end view", 14, "ma")
t(d, (412, 160), "gently", 14, "lm"); t(d, (412, 178), "curved", 14, "lm"); t(d, (412, 196), "sides", 14, "lm")
t(d, (360, 262), "about 25-30°", 14, "ma")
save(im, "rp_axe")

im, d = new("FIX A PUNCTURE")
for k, (cx, lab) in enumerate(((80, "1. lever off"), (240, "2. find hole"), (400, "3. patch"))):
    t(d, (cx, 220), lab, 15, "ma")
# 1: rim arc with two levers
d.arc([10, 60, 150, 200], 180, 360, fill=G, width=8)
d.arc([24, 74, 136, 186], 180, 360, fill=G, width=3)
L(d, [(60, 70), (40, 30)], 6); L(d, [(100, 70), (124, 30)], 6)
# 2: tube with hole and bubbles
d.rounded_rectangle([170, 110, 310, 150], 20, outline=G, width=5)
C(d, (240, 110), 5, 3, fill=G)
for (x, y, r) in ((236, 92, 5), (248, 76, 6), (238, 58, 4)):
    C(d, (x, y), r, 2)
t(d, (240, 170), "pump up, listen,", 13, "ma"); t(d, (240, 186), "or dip in water", 13, "ma")
# 3: patch pressed on
d.rounded_rectangle([330, 110, 470, 150], 20, outline=G, width=5)
d.rounded_rectangle([382, 104, 418, 156], 6, outline=G, width=3, fill=G)
arrow(d, (400, 60), (400, 98), 4)
t(d, (400, 170), "glue, wait till dull,", 13, "ma"); t(d, (400, 186), "press hard", 13, "ma")
t(d, (240, 252), "Then feel inside the tyre for the thorn!", 16, "ma")
save(im, "rp_puncture")

im, d = new("TAP PARTS (water OFF first)")
cx = 120
d.rounded_rectangle([cx - 50, 40, cx + 50, 64], 8, outline=G, width=4)        # handle
t(d, (cx + 70, 52), "handle", 15, "lm")
d.polygon([(cx - 30, 84), (cx + 30, 84), (cx + 36, 106), (cx - 36, 106)], outline=G, width=4)  # headgear nut
t(d, (cx + 70, 95), "headgear nut", 15, "lm")
L(d, [(cx, 106), (cx, 170)], 6)                                                 # spindle
d.rectangle([cx - 12, 126, cx + 12, 134], fill=G)                               # O-ring
t(d, (cx + 70, 130), "O-ring (leak at handle)", 15, "lm")
d.rectangle([cx - 22, 172, cx + 22, 184], fill=G)                               # washer
t(d, (cx + 70, 178), "washer (drip at spout)", 15, "lm")
# tap body
d.rounded_rectangle([cx - 40, 198, cx + 40, 246], 8, outline=G, width=4)
L(d, [(cx + 40, 222), (cx + 110, 222), (cx + 110, 256)], 5)
t(d, (cx + 126, 244), "spout", 15, "lm")
t(d, (8, 266), "Plug in the sink so parts cannot fall down.", 14)
save(im, "rp_tap")

im, d = new("CHARCOAL IN A TIN")
# fire bed
for x in range(30, 300, 24):
    flame(d, x, 250, 30, 10)
L(d, [(10, 252), (320, 252)], 4)
# tin, cut away to show wood
d.rectangle([90, 110, 240, 230], outline=G, width=5, fill=K)
L(d, [(84, 110), (246, 110)], 6)
for y in range(124, 228, 18):
    for x in range(100, 232, 30):
        d.rounded_rectangle([x, y, x + 24, y + 12], 5, outline=G, width=2)
# hole and gas jet
dot(d, (165, 110), 4)
flame(d, 165, 104, 40, 10)
t(d, (190, 68), "gas jet burns", 14)
lines(d, 330, 50, ["1. Dry hardwood,", "   tin, 1 small", "   hole in lid", "2. In the fire", "3. Jet stops:", "   pull it out", "4. Keep SHUT", "   until cold"], 15, 4)
t(d, (8, 266), "Outdoors only: carbon monoxide.", 14)
save(im, "rp_charcoal")

im, d = new("SIMPLE OIL LAMP")
# jar
L(d, [(80, 100), (80, 250), (220, 250), (220, 100)], 5)
L(d, [(70, 96), (230, 96)], 4)
# oil
L(d, [(84, 180), (216, 180)], 2)
for x in range(90, 216, 20):
    d.arc([x, 176, x + 14, 184], 0, 180, fill=G, width=2)
t(d, (150, 214), "vegetable oil", 15, "ma")
t(d, (150, 232), "2-3 cm", 15, "ma")
# wire holder resting on the rim, coil round the wick
L(d, [(70, 96), (140, 120)], 3); L(d, [(230, 96), (160, 120)], 3)
for y in range(110, 134, 6):
    E(d, [138, y, 162, y + 6], 2)
# wick
L(d, [(150, 100), (150, 196)], 5)
flame(d, 150, 98, 44, 14)
L(d, [(176, 98), (186, 98)], 2); L(d, [(176, 110), (186, 110)], 2); L(d, [(181, 98), (181, 110)], 2); L(d, [(186, 98), (196, 74)], 2)
t(d, (190, 64), "3-5 mm of wick", 14, "lm")
t(d, (60, 128), "wire", 14, "rm"); t(d, (60, 146), "holder", 14, "rm")
lines(d, 252, 140, ["Never petrol,", "paraffin or", "spirits.", "On a plate,", "away from cloth."], 15, 4)
save(im, "rp_oil_lamp")

# ======================= SANITATION =======================
im, d = new("HANDWASHING: 20 SECONDS")
steps = [("1", "WET"), ("2", "SOAP"), ("3", "PALM TO"), ("4", "BACKS OF"),
         ("5", "BETWEEN"), ("6", "KNUCKLES"), ("7", "THUMBS"), ("8", "FINGER-")]
sub2 = {"PALM TO": "PALM", "BACKS OF": "HANDS", "BETWEEN": "FINGERS", "KNUCKLES": "IN PALMS",
        "THUMBS": "TWIST", "FINGER-": "TIPS", "WET": "HANDS", "SOAP": "ALL OVER"}
for k, (n, s) in enumerate(steps):
    col, row = k % 4, k // 4
    x0, y0 = 10 + col * 117, 38 + row * 104
    d.rounded_rectangle([x0, y0, x0 + 109, y0 + 94], 10, outline=G, width=3)
    C(d, (x0 + 18, y0 + 18), 12, 3, fill=G)
    d.text((x0 + 18, y0 + 18), n, fill=K, font=f(15), anchor="mm")
    t(d, (x0 + 55, y0 + 52), s, 15, "mm")
    t(d, (x0 + 55, y0 + 72), sub2[s], 15, "mm")
t(d, (240, 262), "Then rinse under pouring water and dry.", 16, "ma")
save(im, "sn_handwash")

im, d = new("BLEACH MIXES (for 5% bleach)")
for k, (cx, ratio, ml, use1, use2) in enumerate(((120, "1 : 49", "20 ml", "surfaces, pots,", "toilets"),
                                                   (360, "1 : 9", "100 ml", "blood, vomit,", "poo, sick room"))):
    t(d, (cx, 40), "0.1%" if k == 0 else "0.5%", 22, "ma")
    # bottle of bleach + litre jug
    d.rounded_rectangle([cx - 90, 80, cx - 50, 150], 6, outline=G, width=4)
    d.rectangle([cx - 78, 70, cx - 62, 80], outline=G, width=3)
    t(d, (cx - 70, 116), "B", 18, "mm")
    t(d, (cx - 30, 116), "+", 22, "mm")
    d.polygon([(cx - 10, 76), (cx + 80, 76), (cx + 72, 150), (cx - 2, 150)], outline=G, width=4)
    t(d, (cx + 35, 116), "water", 15, "mm")
    t(d, (cx, 166), ml + " bleach", 17, "ma")
    t(d, (cx, 190), "to 1 litre (" + ratio.replace(" ", "") + ")", 15, "ma")
    t(d, (cx, 214), use1, 14, "ma"); t(d, (cx, 232), use2, 14, "ma")
divider(d, 240, 40, 240)
t(d, (240, 258), "Fresh daily. Gloves. Never mix with other cleaners.", 14, "ma")
save(im, "sn_bleach")

print("batch 6 diagrams written")
