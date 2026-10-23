#!/usr/bin/env python3
"""
DOOMSDAY PI - boot splash for a 480x320 (3.5" SPI TFT, RGB565) cyberdeck.

Everything is drawn procedurally with pygame (no external assets).
The animation is a perfect loop of LOOP frames at FPS (default 100 @ 20 fps = 5 s).

Run live (e.g. on the Pi, fullscreen on the TFT framebuffer):
    python3 splash.py --fullscreen            # loops until a key / Ctrl-C
    python3 splash.py --fullscreen --seconds 8  # show for 8 s then exit (boot use)
Export demo files headlessly:
    SDL_VIDEODRIVER=dummy python3 splash.py --export OUT_DIR

Pi notes: on a fbtft/fbcp setup simply run fullscreen at 480x320; on a raw
framebuffer you can try SDL_VIDEODRIVER=kmsdrm (pygame 2) or SDL_FBDEV=/dev/fb1.
"""
import os
import sys
import math
import random
import argparse

import pygame

W, H = 480, 320
FPS = 20
LOOP = 100                 # frames per loop (5 s)
GROUND_Y = 272
TAU = math.pi * 2
INTRO_END = 20             # title intro (flicker / glitch / slam) frames

# ------------------------------------------------------------------ helpers

def clamp(v, a=0.0, b=1.0):
    return a if v < a else b if v > b else v


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_col(c1, c2, t):
    t = clamp(t)
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def grad(stops, t):
    """stops: list of (pos, colour) sorted by pos."""
    t = clamp(t)
    for i in range(len(stops) - 1):
        p0, c0 = stops[i]
        p1, c1 = stops[i + 1]
        if t <= p1:
            return lerp_col(c0, c1, (t - p0) / (p1 - p0) if p1 > p0 else 0)
    return stops[-1][1]


def ease_out(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def alpha_circle(surf, col, alpha, pos, r):
    r = int(r)
    if r <= 0 or alpha <= 0:
        return
    s = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
    pygame.draw.circle(s, (*col, int(clamp(alpha, 0, 255))), (r + 1, r + 1), r)
    surf.blit(s, (int(pos[0]) - r - 1, int(pos[1]) - r - 1))


# ------------------------------------------------------------------ 5x7 pixel font
FONT = {
    'A': [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    'B': ["####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."],
    'C': [".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."],
    'D': ["####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."],
    'E': ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
    'F': ["#####", "#....", "#....", "####.", "#....", "#....", "#...."],
    'G': [".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".####"],
    'H': ["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    'I': [".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."],
    'J': ["..###", "...#.", "...#.", "...#.", "#..#.", "#..#.", ".##.."],
    'K': ["#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"],
    'L': ["#....", "#....", "#....", "#....", "#....", "#....", "#####"],
    'M': ["#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"],
    'N': ["#...#", "#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#"],
    'O': [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    'P': ["####.", "#...#", "#...#", "####.", "#....", "#....", "#...."],
    'Q': [".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"],
    'R': ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
    'S': [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
    'T': ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    'U': ["#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    'V': ["#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."],
    'W': ["#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"],
    'X': ["#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"],
    'Y': ["#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."],
    'Z': ["#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"],
    '0': [".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."],
    '1': ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."],
    '2': [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"],
    '3': ["####.", "....#", "....#", ".###.", "....#", "....#", "####."],
    '4': ["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."],
    '5': ["#####", "#....", "####.", "....#", "....#", "#...#", ".###."],
    '6': [".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."],
    '7': ["#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."],
    '8': [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."],
    '9': [".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."],
    '.': [".....", ".....", ".....", ".....", ".....", ".##..", ".##.."],
    ':': [".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."],
    '%': ["##..#", "##..#", "...#.", "..#..", ".#...", "#..##", "#..##"],
    '-': [".....", ".....", ".....", "#####", ".....", ".....", "....."],
    '/': ["....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."],
    '[': [".###.", ".#...", ".#...", ".#...", ".#...", ".#...", ".###."],
    ']': [".###.", "...#.", "...#.", "...#.", "...#.", "...#.", ".###."],
    '_': [".....", ".....", ".....", ".....", ".....", ".....", "#####"],
    ' ': ["....."] * 7,
}


def text_surface(text, scale, color, outline=(0, 0, 0), spacing=1):
    """Pixel-font text with a 1-scale-pixel outline. Returns SRCALPHA surface."""
    cw = (5 + spacing) * scale
    w = len(text) * cw - spacing * scale + 2 * scale
    h = 7 * scale + 2 * scale
    face = pygame.Surface((w, h), pygame.SRCALPHA)
    for i, ch in enumerate(text.upper()):
        g = FONT.get(ch, FONT[' '])
        for r, row in enumerate(g):
            for c, bit in enumerate(row):
                if bit == '#':
                    face.fill((*color, 255), (scale + i * cw + c * scale, scale + r * scale, scale, scale))
    if outline is None:
        return face
    out = pygame.Surface((w, h), pygame.SRCALPHA)
    m = pygame.mask.from_surface(face).to_surface(setcolor=(*outline, 255), unsetcolor=(0, 0, 0, 0))
    o = max(1, scale // 2 + (1 if scale >= 2 else 0))
    for dx in (-o, 0, o):
        for dy in (-o, 0, o):
            out.blit(m, (dx, dy))
    out.blit(face, (0, 0))
    return out


# ------------------------------------------------------------------ the splash
class Splash:
    def __init__(self):
        rng = random.Random(1337)
        self.rng = rng
        self._make_background(rng)
        self._make_title()
        self.subtitle_text = "[ PI ] OFFLINE SURVIVAL DECK"
        self.sub_full = text_surface(self.subtitle_text, 2, (255, 205, 130), (40, 0, 0))
        self.sub_pos = ((W - self.sub_full.get_width()) // 2, 150)
        self.char_w = 12
        self.overlay = pygame.Surface((W, H))
        # particle tables (deterministic)
        self.lava = [dict(k=rng.choice((2, 3, 3, 4)), p=rng.random(), vx=rng.uniform(-40, 40),
                          hp=rng.uniform(16, 36), sz=rng.choice((2, 3, 3, 4))) for _ in range(64)]
        self.smoke = [dict(p=i / 9.0, w=rng.random()) for i in range(9)]
        self.embers = [dict(x=rng.uniform(0, W), k=rng.choice((1, 1, 2)), p=rng.random(),
                            amp=rng.uniform(4, 14)) for _ in range(34)]
        self.ash = [dict(x=rng.uniform(0, W), p=rng.random(), amp=rng.uniform(3, 10)) for _ in range(20)]
        self.rain = [dict(x=rng.uniform(26, 112), p=rng.random()) for _ in range(26)]
        self.debris = [dict(a=rng.uniform(-1.1, 1.1), d=rng.uniform(22, 48), sz=rng.choice((2, 2, 3)))
                       for _ in range(14)]
        self.spray = [dict(dx=rng.uniform(-14, 22), p=rng.random(), h=rng.uniform(6, 16)) for _ in range(14)]
        self.rock = [(math.cos(a) * r, math.sin(a) * r) for a, r in
                     [(i / 9 * TAU, rng.uniform(6.0, 8.5)) for i in range(9)]]
        self._make_globe(rng)

    # ---------------- static art
    def _make_background(self, rng):
        bg = pygame.Surface((W, H))
        stops = [(0.0, (16, 3, 24)), (0.40, (62, 6, 20)), (0.75, (150, 30, 16)), (1.0, (240, 100, 28))]
        for y in range(GROUND_Y):
            bg.fill(grad(stops, y / GROUND_Y), (0, y, W, 1))
        # dim stars in the upper sky
        for _ in range(40):
            x, y = rng.randrange(W), rng.randrange(0, 90)
            c = rng.choice(((90, 70, 110), (130, 100, 140), (70, 50, 90)))
            bg.set_at((x, y), c)
        # big dying sun on the horizon
        pygame.draw.circle(bg, (205, 70, 25), (240, GROUND_Y), 46)
        pygame.draw.circle(bg, (225, 95, 30), (240, GROUND_Y), 38)
        # jagged distant ridge
        pts = [(0, GROUND_Y)]
        x = 0
        while x <= W:
            pts.append((x, GROUND_Y - rng.randint(6, 22)))
            x += rng.randint(10, 22)
        pts += [(W, GROUND_Y)]
        pygame.draw.polygon(bg, (58, 14, 20), pts)
        # ruined skyline silhouettes behind the bay
        for bx in range(160, 350, 14):
            bh = rng.randint(6, 20)
            bw = rng.randint(7, 12)
            pygame.draw.rect(bg, (40, 10, 16), (bx, GROUND_Y - 12 - bh, bw, bh + 12))
            if rng.random() < 0.5:  # broken top
                pygame.draw.polygon(bg, (58, 14, 20) if False else grad(stops, (GROUND_Y - 12 - bh) / GROUND_Y),
                                    [(bx, GROUND_Y - 12 - bh), (bx + bw, GROUND_Y - 12 - bh),
                                     (bx + bw, GROUND_Y - 12 - bh + 5)])
        # ground
        bg.fill((30, 10, 12), (0, GROUND_Y, W, H - GROUND_Y))
        bg.fill((70, 22, 18), (0, GROUND_Y, W, 2))
        # bay of water between volcano and blast
        bg.fill((22, 58, 110), (140, GROUND_Y - 12, 222, 14))
        for i in range(10):
            yy = GROUND_Y - 10 + (i % 3) * 4
            xx = 150 + i * 21
            bg.fill((70, 120, 180), (xx, yy, 8, 1))
        self.bg = bg

    def _make_title(self):
        S, GAP, pad = 9, 7, 6
        word = "DOOMSDAY"
        tw = len(word) * 5 * S + (len(word) - 1) * GAP
        th = 7 * S
        rows = [(255, 248, 150), (255, 222, 60), (255, 182, 30), (255, 140, 20),
                (250, 95, 15), (228, 52, 12), (185, 24, 12)]
        face = pygame.Surface((tw + pad * 2, th + pad * 2), pygame.SRCALPHA)
        for li, ch in enumerate(word):
            for r, row in enumerate(FONT[ch]):
                for c, bit in enumerate(row):
                    if bit != '#':
                        continue
                    x = pad + li * (5 * S + GAP) + c * S
                    y = pad + r * S
                    col = rows[r]
                    hi = lerp_col(col, (255, 255, 230), 0.45)
                    lo = lerp_col(col, (60, 0, 0), 0.45)
                    face.fill(col, (x, y, S, S))
                    face.fill(hi, (x, y, S, 1))
                    face.fill(hi, (x, y, 1, S))
                    face.fill(lo, (x, y + S - 1, S, 1))
                    face.fill(lo, (x + S - 1, y, 1, S))
        mask = pygame.mask.from_surface(face)
        black = mask.to_surface(setcolor=(0, 0, 0, 255), unsetcolor=(0, 0, 0, 0))
        shadow = mask.to_surface(setcolor=(75, 0, 8, 255), unsetcolor=(0, 0, 0, 0))
        title = pygame.Surface(face.get_size(), pygame.SRCALPHA)
        title.blit(shadow, (5, 5))
        title.blit(black, (6, 6))
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                if dx * dx + dy * dy <= 10:
                    title.blit(black, (dx, dy))
        title.blit(face, (0, 0))
        self.title = title
        self.title_pos = ((W - title.get_width()) // 2, 72)
        self.title_red = mask.to_surface(setcolor=(255, 0, 70, 170), unsetcolor=(0, 0, 0, 0))
        self.title_cyan = mask.to_surface(setcolor=(0, 230, 255, 170), unsetcolor=(0, 0, 0, 0))
        self.title_white = mask.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
        # glow: blurred orange silhouette, pre-scaled to a few intensity levels (cheap on a Pi)
        gp = 22
        g = pygame.Surface((face.get_width() + gp * 2, face.get_height() + gp * 2))
        g.fill((0, 0, 0))
        g.blit(mask.to_surface(setcolor=(255, 110, 10, 255), unsetcolor=(0, 0, 0, 0)), (gp, gp))
        gw, gh = g.get_size()
        for _ in range(2):
            small = pygame.transform.smoothscale(g, (gw // 7, gh // 7))
            g = pygame.transform.smoothscale(small, (gw, gh))
        self.glow_levels = []
        for k in range(12):
            s = g.copy()
            v = int(255 * (0.25 + 0.75 * k / 11))
            s.fill((v, v, v), special_flags=pygame.BLEND_MULT)
            self.glow_levels.append(s)
        self.glow_off = gp

    def _make_globe(self, rng):
        R = 24
        self.globe_c = (440, 47)
        self.globe_r = R
        D = R * 2
        tex = pygame.Surface((D * 2, D))
        tex.fill((30, 95, 205))
        blobs = [(rng.uniform(0, D * 2), rng.uniform(6, D - 6), rng.uniform(6, 13), rng.uniform(4, 9))
                 for _ in range(9)]
        for bx, by, bw, bh in blobs:
            for off in (-D * 2, 0, D * 2):
                pygame.draw.ellipse(tex, (60, 170, 70), (bx + off - bw, by - bh, bw * 2, bh * 2))
                pygame.draw.ellipse(tex, (110, 200, 90), (bx + off - bw * 0.5, by - bh * 0.6, bw, bh * 0.7))
        self.globe_tex = tex
        m = pygame.Surface((D, D), pygame.SRCALPHA)
        pygame.draw.circle(m, (255, 255, 255, 255), (R, R), R)
        self.globe_mask = m
        shade = pygame.Surface((D, D), pygame.SRCALPHA)
        pygame.draw.circle(shade, (0, 0, 30, 110), (R + 9, R + 9), R)
        pygame.draw.circle(shade, (0, 0, 0, 0), (R - 6, R - 6), R - 4)
        self.globe_shade = shade

    # ---------------- animated elements
    def draw_particles_bg(self, s, t):
        # fallout ash drifting down
        for a in self.ash:
            u = (t + a['p']) % 1.0
            y = -4 + u * (GROUND_Y + 4)
            x = (a['x'] + a['amp'] * math.sin(TAU * (u * 2 + a['p']))) % W
            s.fill((150, 135, 135), (int(x), int(y), 2, 2))
        # embers rising
        for e in self.embers:
            u = (t * e['k'] + e['p']) % 1.0
            y = GROUND_Y - u * (GROUND_Y + 8)
            x = (e['x'] + e['amp'] * math.sin(TAU * (u * 3 + e['p']))) % W
            col = grad([(0, (255, 240, 120)), (0.5, (255, 130, 20)), (1, (170, 30, 10))], u)
            sz = 2 if u < 0.6 else 1
            s.fill(col, (int(x), int(y), sz, sz))

    def cone_y(self, x):
        if x < 63:
            return 272 - (x - 2) / 61 * 65 if x >= 2 else 999
        if x > 91:
            return 207 + (x - 91) / 59 * 65 if x <= 150 else 999
        return 207

    def draw_volcano(self, s, t):
        cx, cy = 77, 207
        # smoke (behind the cone)
        for i, p in enumerate(self.smoke):
            u = (t * 2 + p['p']) % 1.0
            y = cy - 8 - u * 62
            x = cx - 4 - u * 48 + 4 * math.sin(TAU * (u * 1.5 + p['w']))
            r = 7 + u * 16
            a = 250 * (1 - u) ** 0.8 * min(1.0, u * 10)
            col = lerp_col((80, 62, 60), (150, 132, 128), u)
            alpha_circle(s, col, a, (x, y), r)
            alpha_circle(s, lerp_col(col, (200, 185, 175), 0.45), a * 0.8, (x - r * 0.3, y - r * 0.3), r * 0.55)
        # cone
        body = [(2, 272), (30, 241), (50, 221), (63, 207), (91, 207), (104, 221), (126, 246), (150, 272)]
        pygame.draw.polygon(s, (92, 40, 32), body)
        pygame.draw.polygon(s, (62, 24, 24), [(77, 207), (91, 207), (104, 221), (126, 246), (150, 272), (84, 272)])
        pygame.draw.polygon(s, (20, 6, 8), body, 2)
        for (rx, ry) in [(40, 250), (58, 236), (30, 262), (112, 252), (96, 238), (70, 258)]:
            pygame.draw.circle(s, (50, 18, 18), (rx, ry), 2)
        # lava rivers with flowing bright pulses
        rivers = [[(68, 209), (61, 222), (66, 235), (54, 251), (58, 271)],
                  [(87, 209), (93, 224), (88, 239), (101, 257), (99, 271)]]
        for ri, rv in enumerate(rivers):
            pygame.draw.lines(s, (200, 50, 10), False, rv, 6)
            pygame.draw.lines(s, (255, 120, 20), False, rv, 4)
            n = 0
            for j in range(len(rv) - 1):
                (x0, y0), (x1, y1) = rv[j], rv[j + 1]
                for k in range(6):
                    f = k / 6
                    b = 0.5 + 0.5 * math.sin(TAU * (n / 7.0 - t * 4 + ri * 0.3))
                    n += 1
                    if b > 0.55:
                        s.fill(lerp_col((255, 170, 30), (255, 250, 170), b),
                               (int(lerp(x0, x1, f)) - 1, int(lerp(y0, y1, f)) - 1, 3, 3))
        # crater glow
        pulse = 0.5 + 0.5 * math.sin(TAU * t * 5)
        pygame.draw.ellipse(s, (255, 110, 20), (cx - 16, cy - 4, 32, 9))
        pygame.draw.ellipse(s, lerp_col((255, 200, 60), (255, 250, 190), pulse), (cx - 10, cy - 3, 20, 6))
        # lava fountain
        for p in self.lava:
            a = (t * p['k'] + p['p']) % 1.0
            u = a * 1.35
            y = cy - 2 - 4 * p['hp'] * u * (1 - u)
            x = cx + p['vx'] * u
            if u > 0.5 and y > self.cone_y(x):
                continue
            col = grad([(0, (255, 250, 170)), (0.35, (255, 200, 40)), (0.8, (255, 100, 15)), (1.35, (200, 30, 10))], u / 1.35)
            sz = p['sz'] if u < 0.8 else max(2, p['sz'] - 1)
            s.fill((60, 10, 0), (int(x) - 1, int(y) - 1, sz + 2, sz + 2))
            s.fill(col, (int(x), int(y), sz, sz))

    def draw_storm(self, s, t, f):
        flash = f % LOOP in (8, 9, 11, 47, 48, 55, 56, 78, 79, 81)
        bob = 3 * math.sin(TAU * t)
        cx, cy = 66 + bob, 30
        # rain
        for d in self.rain:
            u = (t * 5 + d['p']) % 1.0
            y = 46 + u * 20
            x = d['x'] + bob - u * 4
            pygame.draw.line(s, (130, 150, 220), (int(x), int(y)), (int(x) - 2, int(y) + 5), 1)
        if flash:
            bolts = [[(58, 46), (48, 58), (55, 61), (38, 74), (45, 76), (26, 88), (32, 89), (14, 102)],
                     [(96, 46), (106, 56), (100, 59), (114, 66), (108, 68), (124, 72)]]
            b = bolts[0] if (f % 2 == 0) else bolts[1]
            if f % LOOP == 55:
                b = bolts[0]
            b = [(x + bob, y) for x, y in b]
            pygame.draw.lines(s, (120, 90, 255), False, b, 6)
            pygame.draw.lines(s, (255, 250, 150), False, b, 3)
            pygame.draw.lines(s, (255, 255, 255), False, b, 1)
        puffs = [(-38, 6, 13), (-20, -4, 17), (2, -10, 19), (24, -3, 16), (42, 6, 12),
                 (0, 8, 15), (-24, 10, 12), (24, 10, 12)]
        dark, mid, hi = ((95, 85, 130), (150, 140, 190), (210, 205, 240)) if flash else \
                        ((45, 40, 62), (78, 72, 100), (115, 108, 140))
        for dx, dy, r in puffs:
            pygame.draw.circle(s, (15, 10, 25), (int(cx + dx), int(cy + dy)), r + 2)
        for dx, dy, r in puffs:
            pygame.draw.circle(s, dark, (int(cx + dx), int(cy + dy + 2)), r)
        for dx, dy, r in puffs:
            pygame.draw.circle(s, mid, (int(cx + dx - 1), int(cy + dy - 1)), r - 3)
        for dx, dy, r in puffs[:5]:
            pygame.draw.circle(s, hi, (int(cx + dx - 3), int(cy + dy - 4)), max(2, r - 10))
        return flash

    def draw_globe(self, s, t):
        gx, gy = self.globe_c
        R = self.globe_r
        D = R * 2
        # atmosphere glow
        alpha_circle(s, (90, 160, 255), 60, (gx, gy), R + 5)
        g = pygame.Surface((D, D), pygame.SRCALPHA)
        off = int(t * D * 2) % (D * 2)
        g.blit(self.globe_tex, (-off, 0))
        g.blit(self.globe_tex, (-off + D * 2, 0))
        g.blit(self.globe_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        g.blit(self.globe_shade, (0, 0))
        s.blit(g, (gx - R, gy - R))
        pygame.draw.circle(s, (10, 10, 30), (gx, gy), R, 2)
        pygame.draw.circle(s, (230, 240, 255), (gx - 9, gy - 10), 3)

    def asteroid_geom(self):
        gx, gy = self.globe_c
        sx, sy = 165, -25
        dx, dy = gx - sx, gy - sy
        L = math.hypot(dx, dy)
        ux, uy = dx / L, dy / L
        ix, iy = gx - ux * (self.globe_r - 2), gy - uy * (self.globe_r - 2)
        return (sx, sy), (ix, iy), (ux, uy)

    def draw_asteroid(self, s, t, f):
        (sx, sy), (ix, iy), (ux, uy) = self.asteroid_geom()
        t0, t1 = 0.35, 0.62
        # tiny background shooting stars
        for (a0, a1, p0, p1) in [(0.04, 0.11, (310, 8), (230, 36)), (0.80, 0.86, (340, 28), (262, 56))]:
            if a0 <= t <= a1:
                k = (t - a0) / (a1 - a0)
                x, y = lerp(p0[0], p1[0], k), lerp(p0[1], p1[1], k)
                tx, ty = x + (p0[0] - p1[0]) * 0.25, y + (p0[1] - p1[1]) * 0.25
                pygame.draw.line(s, (255, 180, 120), (int(tx), int(ty)), (int(x), int(y)), 1)
                s.fill((255, 255, 220), (int(x), int(y), 2, 2))
        if t0 <= t < t1:
            k = (t - t0) / (t1 - t0)
            L = math.hypot(ix - sx, iy - sy)
            x, y = lerp(sx, ix, k), lerp(sy, iy, k)
            # fire trail: circles going back along the path
            for j in range(16, 0, -1):
                d = j * 4.5
                tx, ty = x - ux * d, y - uy * d
                wob = 1.5 * math.sin(f * 1.7 + j)
                tx += -uy * wob
                ty += ux * wob
                r = max(1, 8 - j * 0.45)
                col = grad([(0, (255, 250, 180)), (0.3, (255, 200, 40)), (0.65, (255, 100, 20)), (1, (150, 30, 20))], j / 16)
                pygame.draw.circle(s, col, (int(tx), int(ty)), int(r))
            alpha_circle(s, (255, 160, 40), 110, (x, y), 12)
            ang = f * 0.5
            ca, sa = math.cos(ang), math.sin(ang)
            pts = [(x + px * ca - py * sa, y + px * sa + py * ca) for px, py in self.rock]
            pygame.draw.polygon(s, (20, 10, 10), pts)
            pygame.draw.polygon(s, (125, 100, 88), [(lerp(x, px, 0.82), lerp(y, py, 0.82)) for px, py in pts])
            pygame.draw.circle(s, (80, 62, 56), (int(x - 2 * ca), int(y + 2 * sa)), 2)
            pygame.draw.circle(s, (80, 62, 56), (int(x + 3 * sa), int(y + 3 * ca)), 1)
            pygame.draw.circle(s, (255, 220, 140), (int(x + ux * 4), int(y + uy * 4)), 2)
        if t >= t1:
            ph = (t - t1) / (1 - t1)          # 0..1 over the rest of the loop
            gx, gy = self.globe_c
            # impact flash + starburst
            if ph < 0.35:
                k = ph / 0.35
                r = 5 + k * 26
                alpha_circle(s, (255, 230, 120), 230 * (1 - k), (ix, iy), r)
                alpha_circle(s, (255, 255, 255), 255 * (1 - k) ** 2, (ix, iy), r * 0.55)
                if k < 0.6:
                    for i in range(8):
                        a = i / 8 * TAU + 0.2
                        l0, l1 = r * 0.6, r * 1.25
                        pygame.draw.line(s, (255, 250, 200),
                                         (int(ix + math.cos(a) * l0), int(iy + math.sin(a) * l0)),
                                         (int(ix + math.cos(a) * l1), int(iy + math.sin(a) * l1)), 2)
                base = math.atan2(-uy, -ux)
                for d in self.debris:
                    a = base + d['a']
                    dist = d['d'] * ease_out(k)
                    px, py = ix + math.cos(a) * dist, iy + math.sin(a) * dist + 10 * k * k
                    col = lerp_col((255, 220, 90), (160, 50, 20), k)
                    s.fill(col, (int(px), int(py), d['sz'], d['sz']))
            # burning crater on the globe
            fire = 1 - clamp((ph - 0.55) / 0.45)
            if fire > 0:
                fl = 0.5 + 0.5 * math.sin(f * 2.3)
                alpha_circle(s, (255, 90, 20), 200 * fire, (ix + 2, iy + 2), 5 + fl * 2)
                alpha_circle(s, (255, 230, 100), 230 * fire, (ix + 2, iy + 2), 2 + fl)
                for i in range(3):
                    u = (ph * 3 + i / 3) % 1
                    alpha_circle(s, (90, 80, 85), 170 * fire * (1 - u), (ix - 4 - u * 14, iy - 4 - u * 16), 3 + u * 6)

    def draw_nuke(self, s, t, f):
        ph = (t - 0.18) % 1.0
        gx, gy = 410, GROUND_Y
        flash = 0.0
        if ph < 0.06:
            k = ph / 0.06
            flash = 1 - k
            alpha_circle(s, (255, 250, 220), 255 * (1 - k * 0.5), (gx, gy - 10), 10 + k * 46)
        g = ease_out(ph / 0.4)
        fade = 1 - clamp((ph - 0.78) / 0.2)
        if fade <= 0:
            return flash
        temp = 1 - clamp(ph / 0.95) ** 1.3
        ox, oy = gx - 75, gy - 130
        L = pygame.Surface((150, 145), pygame.SRCALPHA)

        def C(x, y, r, col):
            pygame.draw.circle(L, col, (int(x - ox), int(y - oy)), max(1, int(r)))

        hi = lerp_col((215, 175, 150), (255, 248, 170), temp)
        mid = lerp_col((165, 105, 85), (255, 165, 40), temp)
        lo = lerp_col((100, 50, 45), (215, 60, 20), temp)
        ol = (35, 12, 12)
        cy = gy - 14 - 56 * g
        R = 6 + 26 * g
        wob = lambda i: 1 + 0.07 * math.sin(TAU * (t * 4 + i * 0.37))
        # ground skirt
        sw, sh = 18 + 72 * g, 6 + 9 * g
        skirt = [(-0.45, 0.2, 0.32), (0.45, 0.2, 0.32), (-0.2, -0.1, 0.38), (0.2, -0.1, 0.38), (0, 0.1, 0.42)]
        stem_top = cy + 0.35 * R
        stem_w0, stem_w1 = 5 + 9 * g, 4 + 5 * g
        cap_dome = [(-0.6, 0.0, 0.55), (0.6, 0.0, 0.55), (0.0, -0.42, 0.6), (-0.32, -0.3, 0.5), (0.32, -0.3, 0.5)]
        cap_roll = [(-0.8, 0.35, 0.32), (-0.3, 0.46, 0.33), (0.3, 0.46, 0.33), (0.8, 0.35, 0.32)]
        # outline pass
        for i, (a, b, r) in enumerate(skirt):
            C(gx + a * sw, gy - 4 + b * sh, r * sw * 0.55 * wob(i) + 2, ol)
        pygame.draw.polygon(L, ol, [(gx - stem_w0 - 2 - ox, gy - oy), (gx + stem_w0 + 2 - ox, gy - oy),
                                    (gx + stem_w1 + 2 - ox, stem_top - oy), (gx - stem_w1 - 2 - ox, stem_top - oy)])
        for i, (a, b, r) in enumerate(cap_dome + cap_roll):
            C(gx + a * R, cy + b * R, r * R * wob(i) + 2, ol)
        # fill pass
        for i, (a, b, r) in enumerate(skirt):
            C(gx + a * sw, gy - 4 + b * sh, r * sw * 0.55 * wob(i), lo)
            C(gx + a * sw - 2, gy - 6 + b * sh, r * sw * 0.38 * wob(i), mid)
        pygame.draw.polygon(L, lo, [(gx - stem_w0 - ox, gy - oy), (gx + stem_w0 - ox, gy - oy),
                                    (gx + stem_w1 - ox, stem_top - oy), (gx - stem_w1 - ox, stem_top - oy)])
        pygame.draw.polygon(L, mid, [(gx - stem_w0 * 0.6 - ox, gy - oy), (gx + stem_w0 * 0.1 - ox, gy - oy),
                                     (gx + stem_w1 * 0.1 - ox, stem_top - oy), (gx - stem_w1 * 0.6 - ox, stem_top - oy)])
        # rising stem puffs
        for i in range(4):
            u = (t * 3 + i / 4) % 1
            yy = lerp(gy - 6, stem_top, u)
            C(gx + 1.5 * math.sin(TAU * (u + i * 0.25)), yy, stem_w1 * 0.9 + 1, mid)
        if g > 0.55:   # condensation ring
            rk = (g - 0.55) / 0.45
            ry = lerp(gy, stem_top, 0.55)
            rw = R * (0.6 + 0.8 * rk)
            pygame.draw.ellipse(L, (*lerp_col(hi, (255, 255, 255), 0.3), int(200 * rk)),
                                (gx - rw - ox, ry - 4 - oy, rw * 2, 8), 2)
        for i, (a, b, r) in enumerate(cap_roll):
            C(gx + a * R, cy + b * R, r * R * wob(i + 5), lo)
        for i, (a, b, r) in enumerate(cap_dome):
            C(gx + a * R, cy + b * R, r * R * wob(i), mid)
        for i, (a, b, r) in enumerate(cap_dome):
            C(gx + a * R - R * 0.12, cy + b * R - R * 0.14, r * R * 0.6 * wob(i), hi)
        if temp > 0.15:   # glowing core
            C(gx, cy - R * 0.1, R * 0.35 * temp, (255, 255, 220))
        L.set_alpha(int(255 * fade))
        s.blit(L, (ox, oy))
        return flash

    def draw_wave(self, s, t):
        p = t
        h = 56 * math.sin(math.pi * p) ** 0.8
        if h < 4:
            return
        cx = 178 + 118 * p
        B = GROUND_Y - 8
        s.set_clip(pygame.Rect(140, 150, 222, GROUND_Y + 2 - 150))
        body = [(cx - 95, B + 8), (cx - 70, B - 0.08 * h), (cx - 45, B - 0.35 * h), (cx - 25, B - 0.7 * h),
                (cx - 10, B - 0.93 * h), (cx + 5, B - h), (cx + 20, B - 0.9 * h), (cx + 29, B - 0.68 * h),
                (cx + 26, B - 0.5 * h), (cx + 18, B - 0.48 * h), (cx + 13, B - 0.58 * h),
                (cx + 8, B - 0.42 * h), (cx + 12, B - 0.18 * h), (cx + 28, B + 8)]
        pygame.draw.polygon(s, (8, 20, 50), [(x, y) for x, y in body], 0)
        pygame.draw.polygon(s, (30, 110, 205), body)
        # lighter back highlight band
        pygame.draw.polygon(s, (60, 150, 230), [(cx - 70, B - 0.08 * h), (cx - 45, B - 0.35 * h),
                                                (cx - 25, B - 0.7 * h), (cx - 10, B - 0.93 * h),
                                                (cx - 14, B - 0.7 * h), (cx - 32, B - 0.4 * h),
                                                (cx - 52, B - 0.12 * h)])
        # dark tube inside the curl
        pygame.draw.polygon(s, (15, 60, 140), [(cx + 8, B - 0.42 * h), (cx + 13, B - 0.58 * h),
                                               (cx + 18, B - 0.48 * h), (cx + 16, B - 0.2 * h),
                                               (cx + 12, B - 0.18 * h)])
        pygame.draw.lines(s, (5, 15, 40), False, body[:-1], 2)
        # foam on the crest and lip
        for i in range(9):
            k = i / 8
            fx = lerp(cx - 14, cx + 28, k)
            fy = B - h * (0.92 - 0.25 * k * k) - 1
            r = 3 + 2 * math.sin(TAU * (t * 6 + i * 0.4)) ** 2
            pygame.draw.circle(s, (240, 250, 255), (int(fx), int(fy)), int(r))
        # spray droplets
        for d in self.spray:
            u = (t * 4 + d['p']) % 1
            sx = cx + d['dx'] + u * 10
            sy = B - h - d['h'] * math.sin(math.pi * u) + 2
            s.fill((220, 240, 255), (int(sx), int(sy), 2, 2))
        # foam at the base
        for i in range(6):
            pygame.draw.circle(s, (220, 235, 250), (int(cx + 12 + i * 4), int(B + 3 - (i % 2) * 2)), 3)
        s.set_clip(None)

    def draw_trefoil(self, s, cx, cy, r, ang):
        pygame.draw.circle(s, (0, 0, 0), (cx, cy), r + 2)
        pygame.draw.circle(s, (255, 215, 0), (cx, cy), r)
        for k in range(3):
            a0 = ang + k * TAU / 3 - math.pi / 6
            a1 = a0 + math.pi / 3
            pts = []
            for j in range(7):
                a = lerp(a0, a1, j / 6)
                pts.append((cx + math.cos(a) * r * 0.86, cy + math.sin(a) * r * 0.86))
            for j in range(6, -1, -1):
                a = lerp(a0, a1, j / 6)
                pts.append((cx + math.cos(a) * r * 0.3, cy + math.sin(a) * r * 0.3))
            pygame.draw.polygon(s, (0, 0, 0), pts)
        pygame.draw.circle(s, (0, 0, 0), (cx, cy), max(2, int(r * 0.18)))

    def draw_loader(self, s, t, f):
        x0, y0, w, h = 150, 284, 250, 11
        progress = (f % LOOP + 1) / LOOP
        pygame.draw.rect(s, (0, 0, 0), (x0 - 2, y0 - 2, w + 4, h + 4))
        pygame.draw.rect(s, (255, 170, 60), (x0 - 2, y0 - 2, w + 4, h + 4), 1)
        n = 25
        bw = (w - 2) / n
        filled = int(progress * n + 0.001)
        for i in range(filled):
            col = grad([(0, (255, 230, 60)), (0.5, (255, 140, 20)), (1, (235, 40, 15))], i / (n - 1))
            if i == filled - 1 and (f // 2) % 2:
                col = (255, 255, 200)
            s.fill(col, (int(x0 + 1 + i * bw), y0 + 1, int(bw) - 1, h - 2))
        dots = "." * ((f // 4) % 4)
        txt = text_surface("BOOTING" + dots, 2, (255, 205, 130), (30, 0, 0))
        s.blit(txt, (x0 - 2, 300))
        pct = text_surface("%d%%" % int(progress * 100), 2, (255, 205, 130), (30, 0, 0))
        s.blit(pct, (x0 + w + 2 - pct.get_width(), 300))
        self.draw_trefoil(s, 126, 296, 13, t * TAU)
        self.draw_trefoil(s, 424, 296, 13, -t * TAU)

    def draw_title(self, s, f, intro=True):
        tx, ty = self.title_pos
        lf = f % LOOP if intro else INTRO_END + f
        rnd = random.Random(lf * 7919 + 3)
        if lf < INTRO_END:
            on = [0, 0, 0, 1, 0, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 1, 1, 1, 1, 1][lf]
            if not on:
                return
            if lf < 14:   # glitchy flicker: RGB split + sliced offsets
                for img, dx in ((self.title_red, -4), (self.title_cyan, 4)):
                    s.blit(img, (tx + dx + rnd.randint(-2, 2), ty))
                th = self.title.get_height()
                y = 0
                while y < th:
                    sh = rnd.randint(4, 12)
                    off = rnd.choice((0, 0, rnd.randint(-14, 14)))
                    s.blit(self.title, (tx + off, ty + y), pygame.Rect(0, y, self.title.get_width(), sh))
                    y += sh
                return
            if lf == 14:   # slam: white-hot frame
                s.blit(self.glow_levels[-1], (tx - self.glow_off, ty - self.glow_off), special_flags=pygame.BLEND_ADD)
                s.blit(self.title_white, (tx, ty))
                return
        # steady: pulsing glow
        pulse = 0.5 + 0.5 * math.sin(TAU * (lf / LOOP) * 2.5)
        lvl = int(pulse * (len(self.glow_levels) - 1))
        s.blit(self.glow_levels[lvl], (tx - self.glow_off, ty - self.glow_off), special_flags=pygame.BLEND_ADD)
        if lf in (70, 71):   # tiny periodic glitch
            th = self.title.get_height()
            for y in range(0, th, 8):
                off = rnd.choice((0, 0, 0, rnd.randint(-6, 6)))
                s.blit(self.title, (tx + off, ty + y), pygame.Rect(0, y, self.title.get_width(), 8))
            s.blit(self.title_cyan, (tx + 3, ty), special_flags=0) if lf == 70 else None
        else:
            s.blit(self.title, (tx, ty))

    def draw_subtitle(self, s, f, intro=True):
        lf = f % LOOP if intro else INTRO_END + 40
        start, dur = 18, 22
        if lf < start:
            return
        n = len(self.subtitle_text)
        shown = n if lf >= start + dur else int((lf - start) / dur * n)
        x, y = self.sub_pos
        wpx = min(self.sub_full.get_width(), shown * self.char_w + 2)
        s.blit(self.sub_full, (x, y), pygame.Rect(0, 0, wpx, self.sub_full.get_height()))
        if shown < n or (lf // 5) % 2 == 0:
            cxp = x + 2 + shown * self.char_w
            if shown >= n:
                cxp += 2
            s.fill((255, 205, 130), (cxp, y + 2, 10, 14))

    # ---------------- frame
    def render(self, canvas, screen, f, intro=True):
        t = (f % LOOP) / LOOP
        c = canvas
        c.blit(self.bg, (0, 0))
        self.draw_particles_bg(c, t)
        self.draw_globe(c, t)
        self.draw_asteroid(c, t, f)
        lightning = self.draw_storm(c, t, f)
        self.draw_wave(c, t)
        self.draw_volcano(c, t)
        nflash = self.draw_nuke(c, t, f)
        self.draw_title(c, f, intro)
        self.draw_subtitle(c, f, intro)
        self.draw_loader(c, t, f)
        if nflash > 0:
            self.overlay.fill((255, 230, 180))
            self.overlay.set_alpha(int(110 * nflash))
            c.blit(self.overlay, (0, 0))
        if lightning:
            self.overlay.fill((180, 170, 255))
            self.overlay.set_alpha(22)
            c.blit(self.overlay, (0, 0))
        # screen shake on the title slam and the nuke shockwave
        lf = f % LOOP if intro else INTRO_END + f
        amp = 0
        if 14 <= lf < 21:
            amp = 6 * (1 - (lf - 14) / 7)
        ph = (t - 0.18) % 1.0
        if ph < 0.1:
            amp = max(amp, 3 * (1 - ph / 0.1))
        dx = dy = 0
        if amp > 0.5:
            r = random.Random(f * 31 + 7)
            dx, dy = r.randint(-int(amp), int(amp)), r.randint(-int(amp), int(amp))
        screen.fill((0, 0, 0))
        screen.blit(c, (dx, dy))


# ------------------------------------------------------------------ entry points

def run_live(args):
    flags = pygame.FULLSCREEN if args.fullscreen else 0
    screen = pygame.display.set_mode((W, H), flags)
    pygame.display.set_caption("DOOMSDAY PI")
    pygame.mouse.set_visible(False)
    canvas = pygame.Surface((W, H)).convert()
    sp = Splash()
    clock = pygame.time.Clock()
    f = 0
    end = args.seconds * FPS if args.seconds else None
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT or ev.type == pygame.KEYDOWN:
                return
        # intro plays only on the first loop when running live
        sp.render(canvas, screen, f, intro=(f < LOOP) or args.repeat_intro)
        pygame.display.flip()
        clock.tick(FPS)
        f += 1
        if end and f >= end:
            return


def surf_to_pil(surf, rgb565=True):
    from PIL import Image
    img = Image.frombytes("RGB", surf.get_size(), pygame.image.tobytes(surf, "RGB"))
    if rgb565:   # emulate the TFT's 16-bit colour depth
        lut = [v & 0xF8 for v in range(256)] + [v & 0xFC for v in range(256)] + [v & 0xF8 for v in range(256)]
        img = img.point(lut)
    return img


def export(args):
    import subprocess
    import shutil
    from PIL import Image
    out = args.export
    os.makedirs(out, exist_ok=True)
    screen = pygame.display.set_mode((W, H))
    canvas = pygame.Surface((W, H))
    sp = Splash()
    frames = []
    for f in range(LOOP):
        sp.render(canvas, screen, f, intro=True)
        frames.append(surf_to_pil(screen, not args.no565))
    if args.frames_dir:
        os.makedirs(args.frames_dir, exist_ok=True)
        for i, im in enumerate(frames):
            im.save(os.path.join(args.frames_dir, "f%03d.png" % i))
    frames[args.still].save(os.path.join(out, "splash_still.png"))
    # GIF with one shared palette (no dithering -> crisp pixels, no shimmer)
    sample = Image.new("RGB", (W, H * 10))
    for i in range(10):
        sample.paste(frames[i * LOOP // 10 + 5], (0, H * i))
    pal = sample.quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    gif = [im.quantize(palette=pal, dither=Image.Dither.NONE) for im in frames]
    gif[0].save(os.path.join(out, "splash_demo.gif"), save_all=True, append_images=gif[1:],
                duration=int(1000 / FPS), loop=0, optimize=False, disposal=1)
    # MP4, 2x nearest-neighbour, 3 loops
    ff = shutil.which("ffmpeg")
    if ff:
        cmd = [ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H),
               "-r", str(FPS), "-i", "-", "-vf", "scale=%d:%d:flags=neighbor" % (W * 2, H * 2),
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", "-preset", "slow",
               "-movflags", "+faststart", os.path.join(out, "splash_demo.mp4")]
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for _ in range(args.mp4_loops):
            for im in frames:
                p.stdin.write(im.tobytes())
        p.stdin.close()
        rc = p.wait()
        print("ffmpeg exit code", rc)
    else:
        print("ffmpeg not found; MP4 skipped")
    print("exported to", out)


def main():
    ap = argparse.ArgumentParser(description="DOOMSDAY PI boot splash")
    ap.add_argument("--fullscreen", action="store_true")
    ap.add_argument("--seconds", type=float, default=0, help="exit after N seconds (0 = run until key)")
    ap.add_argument("--repeat-intro", action="store_true", help="replay title intro every loop")
    ap.add_argument("--export", metavar="DIR", help="render GIF/MP4/PNG headlessly into DIR")
    ap.add_argument("--frames-dir", help="also dump every frame as PNG here")
    ap.add_argument("--still", type=int, default=55, help="frame index for splash_still.png")
    ap.add_argument("--mp4-loops", type=int, default=3)
    ap.add_argument("--no565", action="store_true", help="don't emulate RGB565 in exports")
    args = ap.parse_args()
    if args.export:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    try:
        export(args) if args.export else run_live(args)
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
