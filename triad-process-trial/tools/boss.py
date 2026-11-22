"""NULL MONARCH: cyberpunk boss renderer + its stage (rainy neon rooftop).

Same method as the spirits: the body is signed-distance shapes in a 100x120 "body space",
shaded into a locked palette, with animated parameters. Its "aura" is digital glitch.

Usage:
  python3 tools/boss.py OUT_DIR    -> boss previews + sprite sheet + stage still
"""
import math, random, sys, os, json
import numpy as np
from PIL import Image, ImageDraw
from gen import smin, sd_capsule

TAU = 2 * math.pi

# ------------------------------------------------------------------ locked boss palette (10 tones)
def hx(s): s = s.lstrip('#'); return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4)) + (255,)
BP = {
    'M0': hx('#0b0918'),  # outline / deepest metal
    'M1': hx('#1d1832'),  # dark metal, panel seams
    'M2': hx('#2e2850'),  # base metal
    'M3': hx('#4a4378'),  # lit metal
    'M4': hx('#7d78ad'),  # top highlight
    'MGd': hx('#8e1663'), # magenta dark
    'MG': hx('#ff2e97'),  # neon magenta
    'CYd': hx('#167f9c'), # cyan dark
    'CY': hx('#3df4ff'),  # neon cyan
    'W': hx('#fff2fb'),   # hot white
}
SCB = 2.3
BW, BH = int(100 * SCB), int(120 * SCB)

def sd_box(x, y, cx, cy, hw, hh, r):
    qx = np.abs(x - cx) - (hw - r)
    qy = np.abs(y - cy) - (hh - r)
    return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r

# ------------------------------------------------------------------ boss
def boss_render(t, act=None, seed_frame=0):
    act = act or {}
    rz, ch = act.get('raise', 0.0), act.get('charge', 0.0)
    gl = act.get('glitch', 0.0)
    appear = act.get('appear', 1.0)
    Ys, Xs = np.mgrid[0:BH, 0:BW].astype(float)
    bob = 1.2 * math.sin(TAU * t)
    x = (Xs + .5) / SCB
    y = (Ys + .5) / SCB - bob

    # parts
    head = smin(sd_box(x, y, 50, 30, 13, 15, 5), sd_box(x, y, 50, 44, 9, 5, 3), 2.0)
    fins = np.minimum(sd_capsule(x, y, 50, 17, 50, 3, 2.2, 0.4),
                      np.minimum(sd_capsule(x, y, 42, 19, 36, 7, 1.8, 0.4), sd_capsule(x, y, 58, 19, 64, 7, 1.8, 0.4)))
    headall = smin(head, fins, 1.0)
    sway = 0.8 * math.sin(TAU * t + 1)
    cables = np.minimum(np.minimum(sd_capsule(x, y, 45, 46, 43 + sway, 58, 1.7, 1.7),
                                   sd_capsule(x, y, 55, 46, 57 + sway, 58, 1.7, 1.7)),
                        sd_capsule(x, y, 50, 47, 50 + sway, 58, 1.5, 1.5))
    torso = smin(sd_box(x, y, 50, 68, 28, 12, 6), sd_box(x, y, 50, 89, 19, 13, 6), 4.0)
    shoulders = np.minimum(sd_box(x, y, 19, 59, 11, 9, 4), sd_box(x, y, 81, 59, 11, 9, 4))
    shoulders = np.minimum(shoulders, np.minimum(sd_capsule(x, y, 15, 51, 9, 40, 2.4, 0.4), sd_capsule(x, y, 85, 51, 91, 40, 2.4, 0.4)))
    body = smin(torso, shoulders, 2.0)
    hands = []
    for side in (-1, 1):
        hxp = 50 + side * (40 + 4 * rz)
        hyp = 84 - 16 * rz + 1.2 * math.sin(TAU * t + side)
        h = sd_box(x, y, hxp, hyp, 8.5, 7.5, 3)
        for i in range(4):
            fx0 = hxp - 6.3 + 4.2 * i
            curl = -side * 1.0 * (1 - rz)
            # two-segment clawed fingers
            h = smin(h, sd_capsule(x, y, fx0, hyp + 6, fx0 + curl, hyp + 12 - 3 * rz, 1.8, 1.5), 0.8)
            h = np.minimum(h, sd_capsule(x, y, fx0 + curl, hyp + 12 - 3 * rz, fx0 + curl * 1.6, hyp + 16 - 5 * rz, 1.4, 0.3))
        h = smin(h, sd_capsule(x, y, hxp - side * 8, hyp, hxp - side * 12, hyp + 6, 2.0, 1.4), 0.8)  # thumb
        hands.append((h, hxp, hyp))
    parts = [headall, cables, body, hands[0][0], hands[1][0]]
    allp = np.minimum.reduce(parts)
    mat = np.argmin(np.stack(parts), axis=0)   # 0 head 1 cable 2 body 3,4 hands

    inside = allp <= 0
    depth = -allp
    gy, gx = np.gradient(allp)
    nl = np.hypot(gx, gy) + 1e-6
    nx, ny = gx / nl, gy / nl
    lit = -(nx * -0.45 + ny * -0.89) * -1  # facing the top-left light

    out = np.full(allp.shape, '', dtype=object)
    # bevelled metal
    m = inside.copy()
    out[m] = 'M2'
    bevel = m & (depth < 3.0)
    out[bevel & (lit > 0.3)] = 'M3'
    out[bevel & (lit < -0.3)] = 'M1'
    rim = m & (depth < 1.0)
    out[rim] = 'M0'
    out[rim & (ny < -0.55)] = 'M4'
    out[rim & (nx < -0.4)] = 'MG'     # magenta rim light, left
    out[rim & (nx > 0.4)] = 'CY'      # cyan rim light, right

    # panel seams + neon strips
    seam = m & (depth >= 1.5) & (mat == 2) & ((np.abs(x - 50) < 0.45) & (y > 82) | (np.abs(y - 81) < 0.45))
    out[seam] = 'M1'
    pulse = 0.5 + 0.5 * math.sin(TAU * t * 2)
    for sx_, col in ((19, 'MG'), (81, 'CY')):
        strip = m & (mat == 2) & (np.abs(x - sx_) < 0.6) & (y > 53) & (y < 66)
        out[strip] = col if pulse > 0.3 else col + 'd'
    # shoulder vents + chest plates
    vents = m & (mat == 2) & ((np.abs(x - 19) < 6) | (np.abs(x - 81) < 6)) & (y > 61) & (y < 67) & (np.round(y) % 2 == 0)
    out[vents & (depth > 1.2)] = 'M1'
    plate = m & (mat == 2) & (depth > 1.5) & (np.abs(np.abs(x - 50) - 15) < 0.45) & (y > 58) & (y < 80)
    out[plate] = 'M1'
    plate_hi = m & (mat == 2) & (depth > 1.5) & (np.abs(np.abs(x - 50) - 14) < 0.45) & (y > 58) & (y < 80)
    out[plate_hi] = 'M3'
    # head side plates
    ears = m & (mat == 0) & (depth > 1.2) & (np.abs(np.abs(x - 50) - 10.5) < 0.5) & (y > 22) & (y < 38)
    out[ears] = 'M1'
    # jaw grill
    grill = m & (mat == 0) & (np.abs(x - 50) < 6) & (np.isin(np.round(y), [42, 44, 46]))
    out[grill] = 'M0'
    # visor
    vcy = 27.5 + 0.22 * np.abs(x - 50) * -1 + 2.6  # V-shaped slit, lowest in the middle
    vis = m & (mat == 0) & (np.abs(y - vcy) < 1.7) & (np.abs(x - 50) < 11.5)
    out[vis] = 'CYd'
    scan = 50 + 9.5 * math.sin(TAU * t)
    out[vis & (np.abs(x - scan) < 1.6)] = 'CY'
    out[vis & (np.abs(x - scan) < 0.6)] = 'W'
    if ch > 0:
        out[vis] = 'MG' if ch < 0.6 else 'W'
        out[vis & (np.abs(x - 50) > 11.5 - 12 * ch)] = 'MGd' if ch < 0.6 else 'MG'
    # cables with travelling light
    cab = m & (mat == 1)
    trav = (y - 46 - 12 * ((t * 2) % 1)) % 12
    out[cab & (depth >= 0.6)] = 'M1'
    out[cab & (depth >= 0.6) & (trav < 1.2)] = 'CY'
    # reactor core
    r = np.hypot(x - 50, y - 73)
    pr = 5.0 + 0.8 * math.sin(TAU * t * 2) + 3.5 * ch
    core = m & (mat == 2) & (r < pr + 1)
    out[core] = 'M0'
    out[core & (r < pr)] = 'MGd'
    out[core & (r < pr * 0.72)] = 'MG'
    out[core & (r < pr * 0.38)] = 'W'
    # hand fingertips glow when charging / raised
    if rz > 0.2:
        for _, hxp, hyp in hands:
            tip = m & (y > hyp + 13 - 5 * rz) & (y < hyp + 17 - 5 * rz) & (np.abs(x - hxp) < 9)
            out[tip] = 'CY'

    # hologram fade at the base: scanlines that thin out
    rows = np.floor(Ys).astype(int)
    rng = np.random.default_rng(7)
    noise = rng.random(allp.shape)
    fade = (y > 95) & m & (mat < 3)
    keep = (rows % 2 == 0) & (noise > np.clip((y - 95) / 16, 0, 1))
    out[fade & ~keep] = ''
    out[fade & keep & (out != 'MG') & (out != 'CY')] = 'CYd'
    # materialise (intro): reveal top-down with a bright scan front
    if appear < 1.0:
        front = appear * 125 - 5
        out[y > front] = ''
        out[m & (np.abs(y - front) < 1.2)] = 'W'
        out[m & (y < front) & (y > front - 6) & (rows % 2 == 1)] = ''
    # hologram crown: tilted dashed ring that rotates
    cr_x, cr_y = 50, 5.5 + 0.6 * math.sin(TAU * t)
    ang = np.arctan2((y - cr_y) / 0.28, x - cr_x)
    rad = np.hypot(x - cr_x, (y - cr_y) / 0.28)
    ring = (np.abs(rad - 15) < 1.5) & (np.sin(5 * ang + TAU * t) > -0.5) & (out == '')
    front = ring & (y > cr_y)
    out[ring] = 'MGd'
    out[front] = 'MG'
    out[ring & (np.sin(5 * ang + TAU * t) > 0.8)] = 'W'
    out[ring & ~front & (np.sin(5 * ang + TAU * t) > 0.3)] = 'MG'
    if appear < 1.0: out[(ring) & (y > appear * 125 - 5)] = ''
    if act.get('flash'):
        out[out != ''] = 'W'

    img = np.zeros((BH, BW, 4), dtype=np.uint8)
    for k, c in BP.items():
        img[out == k] = c

    # glitch aura: horizontal tears + magenta/cyan split
    r_ = random.Random(seed_frame * 7919 + 3)
    g = gl + (0.35 if seed_frame % 12 in (5, 6) else 0.0)
    if g > 0:
        for _ in range(int(1 + 5 * g)):
            y0 = r_.randrange(0, int(100 * SCB)); hgt = r_.randint(2, 6 + int(8 * g))
            sh = r_.choice([-1, 1]) * r_.randint(2, 3 + int(10 * g))
            band = img[y0:y0 + hgt].copy()
            band = np.roll(band, sh, axis=1)
            if sh > 0: band[:, :sh] = 0
            else: band[:, sh:] = 0
            a = band[..., 3] > 0
            left = a & ~np.roll(a, 1, axis=1); right = a & ~np.roll(a, -1, axis=1)
            band[left] = BP['MG']; band[right] = BP['CY']
            img[y0:y0 + hgt] = band
    im = Image.fromarray(img, 'RGBA').copy()
    # data bits drifting up (the boss's "aura particles")
    px = im.load()
    rr = random.Random(11)
    for i in range(26):
        x0 = rr.uniform(6, 94); ph = rr.random(); sp = rr.choice([1, 2])
        u = (t * sp + ph) % 1
        yy = (105 - u * 100 + bob) * SCB; xx = (x0 + 1.5 * math.sin(u * TAU + i)) * SCB
        col = BP[rr.choice(['CY', 'MG', 'CYd', 'W'])]
        if appear < 1 and yy / SCB > appear * 125: continue
        for k in range(rr.choice([1, 2, 3])):
            X, Y = int(xx), int(yy) + k
            if 0 <= X < BW and 0 <= Y < BH and px[X, Y][3] == 0: px[X, Y] = col
    return im

# action timelines (dicts consumed per frame)
def btl_idle(n): return [{} for _ in range(n)]
def btl_attack():
    out = []
    for k in range(14):
        if k < 8:
            e = k / 7
            out.append({'raise': e, 'charge': e, 'glitch': 0.15 * e})
        elif k < 11:
            out.append({'raise': 1, 'charge': 1, 'glitch': 0.5, 'beam': True})
        else:
            e = (k - 10) / 3
            out.append({'raise': 1 - e, 'charge': 0.6 * (1 - e)})
    return out
def btl_hit():
    return [{'flash': k < 1, 'glitch': [1.0, 0.9, 0.6, 0.4, 0.2, 0.0][k]} for k in range(6)]
def btl_intro(n=24):
    return [{'appear': min(1, k / (n - 6)), 'glitch': 0.8 * (1 - k / n)} for k in range(n)]
def btl_enrage():
    return [{'glitch': 1.2 if k % 3 else 0.4, 'charge': 0.5 + 0.5 * (k % 2), 'raise': 0.4} for k in range(16)]

# boss placement in the 640x360 scene
BOSS_X, BOSS_TOP = 430, 12
def boss_point(bx, by):
    return BOSS_X - BW / 2 + bx * SCB, BOSS_TOP + by * SCB
VISOR = boss_point(50, 28)
CORE = boss_point(50, 73)

# ------------------------------------------------------------------ the stage: neon rooftop
SW, SH = 640, 360
ROOF = 232
WIN = [(255, 196, 110), (110, 220, 255), (255, 92, 180), (190, 160, 255)]
SIGNS = ['OVERCLOCK', 'NEURO GRAFT', 'SYNTH NOODLE', 'VOID BANK', 'NO SIGNAL', 'WAKE UP']

class City:
    def __init__(self, font_text, font_w):
        self.text, self.tw = font_text, font_w
        r = random.Random(42)
        self.base = Image.new('RGBA', (SW, SH))
        d = ImageDraw.Draw(self.base)
        sky = [(12, 6, 28), (22, 10, 44), (40, 16, 66), (70, 24, 92), (118, 38, 118), (170, 60, 140)]
        for y in range(ROOF):  # smoggy sky, glowing magenta at the horizon
            k = (y / ROOF) ** 1.5 * (len(sky) - 1)
            i = min(int(k), len(sky) - 2); u = k - i
            c = tuple(int(sky[i][j] * (1 - u) + sky[i + 1][j] * u) for j in range(3))
            d.line([(0, y), (SW, y)], fill=c)
        self.windows, self.antennas, self.signs, self.bills = [], [], [], []
        # three building layers, far -> near
        layers = [  # (min w, max w, top range, body colour, rim colour, window step, window size, lit prob)
            (12, 26, (70, 160), (66, 34, 92), (96, 52, 120), (3, 3), (1, 1), 0.30),
            (18, 38, (36, 140), (36, 18, 60), (80, 36, 104), (4, 4), (2, 1), 0.22),
            (30, 60, (6, 110), (17, 10, 32), (90, 30, 96), (5, 6), (2, 2), 0.16),
        ]
        for layer, (wmin, wmax, (t0, t1), col, rimc, (sx_, sy_), (ww, wh), lit) in enumerate(layers):
            x = r.randint(-20, 0)
            while x < SW:
                w = r.randint(wmin, wmax); top = r.randint(t0, t1)
                if layer == 2 and 300 < x < 540: x = 540; continue  # gap so the boss reads
                if layer == 1 and 340 < x < 520: top = max(top, 120)
                d.rectangle([x, top, x + w, ROOF], fill=col)
                if r.random() < 0.5:
                    d.rectangle([x + 3, top - 6, x + w - 3, top], fill=col)
                d.line([(x, top), (x, ROOF)], fill=rimc)          # neon rim on the left edge
                d.line([(x, top), (x + w, top)], fill=rimc)
                # window grid with lit floors
                floors_lit = r.random()
                for wy in range(top + 4, ROOF - 3, sy_):
                    row_on = r.random() < 0.55 + 0.4 * floors_lit
                    for wx in range(x + 2, x + w - 2, sx_):
                        if row_on and r.random() < lit * 2.2 and 0 <= wx < SW - ww:
                            c = WIN[r.randrange(4)] if r.random() < .3 else (210, 150, 90)
                            dim = 0.5 + 0.22 * layer
                            cc = tuple(int(v * dim) for v in c) + (255,)
                            d.rectangle([wx, wy, wx + ww - 1, wy + wh - 1], fill=cc)
                            if r.random() < 0.04: self.windows.append((wx, wy, cc))
                if layer >= 1 and r.random() < 0.6:
                    ax = x + w // 2
                    d.line([(ax, top - 14), (ax, top)], fill=col)
                    if 1 <= ax < SW - 1 and top - 15 >= 0: self.antennas.append((ax, top - 15, r.random()))
                if layer >= 1 and r.random() < 0.4 and w >= 24:
                    self.bills.append((x + 2, top + r.randint(10, 30), w - 4, r.choice(SIGNS), r.choice(['MG', 'CY', 'Y']), r.random()))
                if layer == 2 and r.random() < 0.8:
                    self.signs.append((x + (w - 9 if r.random() < .5 else 3), top + 16, r.choice(['ZERO', 'NEON', 'HOTEL', 'BAR']), r.choice(['MG', 'CY']), r.random()))
                x += w + r.randint(-3, 5)
            haze = Image.new('RGBA', (SW, SH), (0, 0, 0, 0)); hd = ImageDraw.Draw(haze)
            for y in range(100, ROOF):
                a_ = int((60 if layer < 2 else 40) * ((y - 100) / (ROOF - 100)) ** 2)
                hd.line([(0, y), (SW, y)], fill=(190, 60, 140, a_))
            self.base.alpha_composite(haze)
        self.cars = [(r.uniform(0, SW), r.uniform(40, 190), r.choice([-1, 1]) * r.uniform(3, 9), r.choice(['MG', 'CY', 'W', 'R'])) for _ in range(9)]
        self.rain = [(r.uniform(-60, SW), r.uniform(0, SH), r.uniform(9, 15)) for _ in range(170)]
        # rooftop (drawn in front of the boss)
        self.roof = Image.new('RGBA', (SW, SH), (0, 0, 0, 0)); rd = ImageDraw.Draw(self.roof)
        for y in range(ROOF, SH):
            k = (y - ROOF) / (SH - ROOF)
            rd.line([(0, y), (SW, y)], fill=(int(30 - 12 * k), int(24 - 10 * k), int(46 - 16 * k), 255))
        VP = (320, ROOF - 40)
        for i in range(-16, 17):
            x1 = 320 + i * 60
            # clip lines to the roof
            for yy in range(ROOF + 2, SH, 1):
                u = (yy - VP[1]) / (SH - VP[1])
                xx = int(VP[0] + (x1 - VP[0]) * u)
                if 0 <= xx < SW and (yy + i) % 1 == 0: self.roof.putpixel((xx, yy), (44, 36, 70, 255))
        z = 1.0
        while True:
            yy = int(ROOF + (SH - ROOF) / z)
            if yy <= ROOF + 3: break
            rd.line([(0, yy), (SW, yy)], fill=(44, 36, 70)); z *= 1.5
        # railing with neon strip
        rd.rectangle([0, ROOF - 7, SW, ROOF - 6], fill=(40, 32, 60))
        for px_ in range(4, SW, 26):
            rd.line([(px_, ROOF - 7), (px_, ROOF)], fill=(40, 32, 60))
        rd.line([(0, ROOF), (SW, ROOF)], fill=BP['CY'][:3])
        rd.line([(0, ROOF + 1), (SW, ROOF + 1)], fill=BP['CYd'][:3])
        # props: water tank (right) and a neon sign mast (left)
        rd.rectangle([588, 150, 628, ROOF - 8], fill=(18, 12, 30)); rd.ellipse([586, 142, 630, 158], fill=(22, 16, 36))
        for i in range(588, 629, 6): rd.line([(i, 154), (i, ROOF - 8)], fill=(28, 22, 44))
        rd.line([(592, ROOF - 8), (586, ROOF + 6)], fill=(18, 12, 30), width=2); rd.line([(624, ROOF - 8), (630, ROOF + 6)], fill=(18, 12, 30), width=2)
        rd.line([(24, 96), (24, ROOF + 8)], fill=(18, 12, 30), width=3)
        rd.rectangle([8, 100, 40, 128], fill=(10, 6, 20), outline=BP['MG'][:3])
        rd.rectangle([10, 102, 38, 126], outline=BP['MGd'][:3])
        font_text(self.roof, 'LVL', 14, 106, BP['MG'], shadow=False); font_text(self.roof, '99', 18, 116, BP['CY'], shadow=False)
        # puddles: dithered reflection of the city
        self.puddles = [(110, 250, 52, 6), (560, 268, 46, 7), (330, 296, 34, 5), (450, 246, 44, 5)]
        # player pad
        cx, cy, rx, ry = 196, 306, 70, 13
        for yy in range(cy - ry - 2, cy + ry + 3):
            for xx in range(cx - rx - 2, cx + rx + 3):
                e = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2
                if e <= 1: self.roof.putpixel((xx, yy), (38, 30, 60, 255) if e < 0.85 else (60, 50, 92, 255))
                if 0.92 < e <= 1.0 and (xx // 3) % 2 == 0: self.roof.putpixel((xx, yy), BP['CY'])

    def sky_layer(self, f):
        im = self.base.copy(); px = im.load(); d = ImageDraw.Draw(im)
        r = random.Random(f // 3)
        for (wx, wy, c) in self.windows:  # blinking windows
            if r.random() < 0.3: px[wx, wy] = (14, 10, 26, 255)
        for (ax, ay, ph) in self.antennas:
            if ((f / 10 + ph) % 1) < 0.35:
                px[ax, ay] = (255, 60, 70, 255)
                if 0 < ax < SW - 1: px[ax - 1, ay] = px[ax + 1, ay] = (120, 30, 40, 255)
        for (bx, by, bw, s, col, ph) in self.bills:  # scrolling billboards
            c = {'MG': BP['MG'], 'CY': BP['CY'], 'Y': (255, 210, 90, 255)}[col]
            dark = tuple(v // 3 for v in c[:3]) + (255,)
            if r.random() < 0.06: continue  # flicker off
            d.rectangle([bx, by, bx + bw, by + 9], fill=(10, 6, 20), outline=dark)
            strip = Image.new('RGBA', (self.tw(s) + 2, 7), (0, 0, 0, 0))
            self.text(strip, s, 0, 1, c, shadow=False)
            off = (f * 1.5 + ph * 100) % (strip.width + bw)
            crop = Image.new('RGBA', (bw - 2, 7), (0, 0, 0, 0))
            crop.paste(strip, (int(bw - off), 0), strip)
            im.alpha_composite(crop, (bx + 1, by + 1))
        for (sx, sy, s, col, ph) in self.signs:  # vertical neon signs
            c = BP[col]
            on = not (((f / 7 + ph) % 1) < 0.08)
            d.rectangle([sx - 1, sy - 2, sx + 5, sy + len(s) * 6 + 1], fill=(10, 6, 20), outline=c if on else BP[col + 'd'])
            for i, ch in enumerate(s):
                self.text(im, ch, sx + 1, sy + i * 6, c if on else BP[col + 'd'], shadow=False)
        for (cx, cy, v, col) in self.cars:  # flying cars with light trails
            x = (cx + v * f) % (SW + 40) - 20
            c = {'MG': BP['MG'], 'CY': BP['CY'], 'W': (255, 240, 220, 255), 'R': (255, 70, 60, 255)}[col]
            for k in range(1, 12):
                xx = int(x - math.copysign(k, v))
                if 0 <= xx < SW: px[xx, int(cy)] = tuple(int(a * (1 - k / 13) + b * k / 13) for a, b in zip(c[:3], (40, 20, 60))) + (255,)
            if 0 <= int(x) < SW - 2:
                px[int(x), int(cy)] = c; px[int(x) + 1, int(cy)] = (30, 24, 44, 255); px[int(x) - 1, int(cy)] = (30, 24, 44, 255)
        return im

    def roof_layer(self, f, sky):
        im = self.roof.copy(); px = im.load(); spx = sky.load()
        for (cx, cy, rx, ry) in self.puddles:  # reflections of whatever is above the roof edge
            for yy in range(cy - ry, cy + ry + 1):
                for xx in range(cx - rx, cx + rx + 1):
                    if ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1 and 0 <= xx < SW:
                        src_y = ROOF - 1 - (yy - (cy - ry)) * 3 - (f % 3 if (xx + yy) % 5 == 0 else 0)
                        c = spx[xx, max(0, src_y)]
                        if (xx + yy) % 2 == 0: px[xx, yy] = (int(c[0] * .8) + 10, int(c[1] * .8) + 8, int(c[2] * .8) + 16, 255)
                        else: px[xx, yy] = (24, 20, 40, 255)
        return im

    def rain_layer(self, im, f):
        px = im.load()
        for (x0, y0, sp) in self.rain:
            y = (y0 + sp * f) % (SH + 20) - 10
            x = x0 + (y / SH) * 40
            for k in range(4):
                X, Y = int(x - k * 0.45), int(y - k)
                if 0 <= X < SW and 0 <= Y < SH:
                    a = px[X, Y]
                    px[X, Y] = tuple(min(255, int(a[i] * 0.55 + (150, 170, 220)[i] * 0.45)) for i in range(3)) + (255,)
            if y > ROOF + 4 and (y0 * 7 + f) % 9 == 0:  # splash
                X, Y = int(x), int(y)
                for dx_, dy_ in ((-1, -1), (1, -1)):
                    if 0 <= X + dx_ < SW and 0 <= Y + dy_ < SH: px[X + dx_, Y + dy_] = (150, 170, 220, 255)

def stage_frame(city, f, boss_img=None, boss_dx=0, boss_dy=0):
    sky = city.sky_layer(f)
    if boss_img is not None:
        sky.alpha_composite(boss_img, (int(BOSS_X - BW / 2 + boss_dx), int(BOSS_TOP + boss_dy)))
    roof = city.roof_layer(f, sky)
    sky.alpha_composite(roof)
    return sky

if __name__ == '__main__':
    from battle_ui import text, text_w
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    city = City(text, text_w)
    frames = []
    seq = btl_idle(24) + btl_attack() + btl_idle(6) + btl_hit() + btl_idle(8)
    for f, a in enumerate(seq):
        b = boss_render(f / 12, a, f)
        sc = stage_frame(city, f, b)
        if a.get('beam'):
            d = ImageDraw.Draw(sc)
            for w, c in ((9, BP['MGd']), (6, BP['MG']), (3, BP['W'])):
                d.line([VISOR, (196, 250)], fill=c, width=w)
        city.rain_layer(sc, f)
        frames.append(sc)
    frames[0].resize((SW * 2, SH * 2), Image.NEAREST).save(f'{out}/stage_still.png')
    # boss sprite sheet: rows idle(12) / attack(14) / hit(6) / intro(26), transparent
    rows = {'idle': btl_idle(12), 'attack': btl_attack(), 'hit': btl_hit(), 'intro': btl_intro(26)}
    cols = max(len(v) for v in rows.values())
    sheet = Image.new('RGBA', (BW * cols, BH * len(rows)), (0, 0, 0, 0))
    allowed = set(BP.values()) | {(0, 0, 0, 0)}
    for r_, (name, tl) in enumerate(rows.items()):
        for c_, a in enumerate(tl):
            im = boss_render(c_ / 12, a, c_ if name == 'idle' else c_ + 100)
            assert set(im.get_flattened_data()) <= allowed, name
            sheet.paste(im, (c_ * BW, r_ * BH))
    sheet.save(f'{out}/null_monarch.png')
    json.dump({'name': 'NULL MONARCH', 'frame_w': BW, 'frame_h': BH, 'fps': 10, 'scale': SCB,
               'scene_offset': [BOSS_X - BW // 2, BOSS_TOP], 'visor': list(VISOR), 'core': list(CORE),
               'palette': {k: '#%02x%02x%02x' % v[:3] for k, v in BP.items()},
               'animations': {n: {'row': i, 'frames': len(v), 'loop': n == 'idle'} for i, (n, v) in enumerate(rows.items())},
               'notes': "attack frames 8-10 fire the visor beam (drawn by the scene, see boss_fight.py)"},
              open(f'{out}/null_monarch.json', 'w'), indent=2)
    gif = [fr.resize((SW * 2, SH * 2), Image.NEAREST).convert('P', palette=Image.ADAPTIVE) for fr in frames]
    gif[0].save(f'{out}/stage.gif', save_all=True, append_images=gif[1:], duration=100, loop=0)
    print(len(frames), 'frames')
