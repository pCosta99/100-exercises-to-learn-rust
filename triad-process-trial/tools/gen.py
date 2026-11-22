"""Base skeleton + shape helpers (signed-distance body) and the original v4 32x48 generator.
The current renderer (aura3.py) imports body_sdf, smin, sd_capsule, ELEMENTS, SHADOW, hexc from here.

Original notes:

LOCKED SPEC (shared by every element):
  canvas   : 32 x 48 px, transparent background
  anchor   : feet/ground point at (16, 44); ground shadow ellipse centered there
  body     : same humanoid skeleton for every element (head, torso, arms, legs)
  palette  : exactly 5 tones per element (rim, dark, mid, light, core) + 1 shared shadow
  frames   : 6-frame seamless idle loop, 10 fps
  view     : front / slight 3-4 view, light from above
"""
import math, random, sys
import numpy as np
from PIL import Image

W, H, FRAMES = 32, 48, 6
GROUND = (16, 44)
SHADOW = (12, 8, 24, 110)

def hexc(s):
    s = s.lstrip('#'); return tuple(int(s[i:i+2], 16) for i in (0, 2, 4)) + (255,)

ELEMENTS = {
    #          rim        dark       mid        light      core
    'fire':  ['#6b1a12', '#b8321a', '#ee6c1e', '#ffb83c', '#fff2a8'],
    'water': ['#10285e', '#1a5aa8', '#2d9bd8', '#86d8f2', '#e8fbff'],
    'wind':  ['#1b4a48', '#2e8a76', '#5ec79c', '#b4efc8', '#f2fff4'],
    'light': ['#7a5418', '#c4932c', '#f0cf52', '#fff1a2', '#ffffff'],
    'dark':  ['#120a1e', '#2c1244', '#56226f', '#9446b6', '#e2b2ff'],
}

# ---------------------------------------------------------------- shape
def sd_circle(x, y, cx, cy, r):
    return np.hypot(x - cx, y - cy) - r

def sd_capsule(x, y, ax, ay, bx, by, ra, rb):
    """Tapered capsule from a (radius ra) to b (radius rb)."""
    px, py = x - ax, y - ay
    vx, vy = bx - ax, by - ay
    h = np.clip((px * vx + py * vy) / (vx * vx + vy * vy), 0, 1)
    return np.hypot(px - vx * h, py - vy * h) - (ra + (rb - ra) * h)

def smin(a, b, k=2.0):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)

def body_sdf(x, y, breathe=0.0, legs=True):
    d = sd_circle(x, y, 16, 12 - breathe * 0.5, 4.6)
    d = smin(d, sd_capsule(x, y, 16, 19, 16, 30, 5.6 + breathe * 0.3, 3.8), 2.5)
    for s in (-1, 1):
        d = smin(d, sd_capsule(x, y, 16 + s * 5, 20, 16 + s * 8.2, 30 + breathe * 0.4, 2.2, 1.6), 1.5)
        if legs:
            d = smin(d, sd_capsule(x, y, 16 + s * 2.2, 30, 16 + s * 3.0, 41, 2.3, 1.4), 1.5)
    if not legs:
        d = smin(d, sd_capsule(x, y, 16, 29, 16, 42, 4.2, 0.8), 2.0)
    return d

# ---------------------------------------------------------------- noise (seamless in time)
class LoopNoise:
    def __init__(self, seed, n=7, scale=0.35):
        r = random.Random(seed)
        self.waves = [(r.uniform(-1, 1) * scale * (1 + i * 0.5), r.uniform(-1, 1) * scale * (1 + i * 0.5),
                       r.choice([1, 1, 2]), r.uniform(0, 6.283), 1 / (1 + i * 0.6)) for i in range(n)]
        self.norm = sum(w[4] for w in self.waves)
    def __call__(self, x, y, t, flow=(0.0, 0.0)):
        out = 0
        for kx, ky, f, ph, a in self.waves:
            # flow: drift pattern along a direction, one whole cycle per loop -> seamless
            out = out + a * np.sin(kx * x + ky * y + 6.2832 * f * t + ph)
        return out / self.norm

# ---------------------------------------------------------------- per-element field
def field(el, x, y, t, nz, nz2):
    br = math.sin(6.2832 * t)  # breathing
    if el == 'fire':
        # tongues lick upward from the whole upper contour (head, shoulders, arms)
        n = nz(x * 2.2, y * 0.35, t)
        lift = np.clip(n, 0, None) * 9.0
        d = np.minimum(body_sdf(x, y, br), body_sdf(x, y + lift, br) + 0.4)
        sway = 1.6 * math.sin(6.2832 * t)
        d = smin(d, sd_capsule(x, y, 16, 10, 16 + sway, 0.5, 3.6, 0.3), 2.0)
        d += 0.35 * nz2(x, y, t)
        d += np.clip((y - 35) / 5, 0, None) * 1.4  # legs burn away near ground
    elif el == 'water':
        wx = 0.7 * np.sin(y * 0.45 + 6.2832 * t)
        d = body_sdf(x + wx, y, br) + 0.25 * nz2(x, y, t)
        # flowing crest off the back of the head, like a wave
        d = smin(d, sd_capsule(x, y, 17, 8, 23 + 0.8 * br, 16, 2.4, 0.9), 1.5)
        # drips from the hands
        for s_ in (-1, 1):
            d = np.minimum(d, sd_capsule(x, y, 16 + s_ * 8.2, 30, 16 + s_ * 8.2, 33 + 1.5 * (1 + br), 1.0, 0.6))
        # pooling base
        d = smin(d, sd_capsule(x, y, 10, 42, 22, 42, 1.5, 1.5) + 0.3 * nz(x, y, t), 3.0)
    elif el == 'wind':
        sw = 1.6 * np.sin(y * 0.28 - 6.2832 * t) * np.clip((y - 10) / 30, 0, 1)
        d = body_sdf(x - sw, y, br, legs=False) + 0.3 * nz2(x * 1.5, y * 0.6, t)
        # carve diagonal gust streaks through the body
        gust = np.sin((y - 0.35 * x) * 1.0 + 6.2832 * t)
        d += np.clip(gust - 0.82, 0, None) * 8.0
        # swirl ribbon wrapping the tail
        rib = np.abs((y - 30) - 4 * np.sin((x - 16) * 0.5 + 6.2832 * t)) - 0.7
        d = np.minimum(d, np.where(np.abs(x - 16) < 8 - (y - 30) * 0.4, rib, 9))
    elif el == 'light':
        d = body_sdf(x, y, br) + 0.15 * nz2(x, y, t)
        d += np.clip((y - 37) / 4, 0, None) * 1.3  # floats: feet fade
    elif el == 'dark':
        # smoke drips downward; two horn-like wisps curl up from the head
        n = nz(x * 1.6, y * 0.4, t)
        drop = np.clip(n, 0, None) * 6.0
        d = np.minimum(body_sdf(x, y, br), body_sdf(x, y - drop, br) + 0.6)
        for s_ in (-1, 1):
            d = smin(d, sd_capsule(x, y, 16 + s_ * 3, 9, 16 + s_ * (7 + 0.6 * br), 2, 1.6, 0.5), 1.2)
        d += 0.3 * nz2(x, y, t)
    return -d  # positive = inside, value = depth in px

def bands(el, depth, x, y, t, nz):
    """Map depth -> palette index 0..4 (or -1 transparent)."""
    jitter = 0.35 * nz(x * 1.2, y * 1.2, t)
    v = depth + jitter
    if el == 'dark':
        # inverted: glowing violet rim, void-black interior
        idx = np.select([v < 0, v < 1.0, v < 2.0, v < 3.2], [-1, 3, 2, 1], 0)
    else:
        # brighter toward the vertical center line (inner flame)
        core_bias = np.clip(1.5 - np.abs(x - 16) * 0.12, 0, None)
        v = v + core_bias
        idx = np.select([v < 0, v < 1.0, v < 2.2, v < 3.6, v < 5.0], [-1, 0, 1, 2, 3], 4)
    return idx

# ---------------------------------------------------------------- particles & details
def particles(el, t, seed):
    r = random.Random(seed); pts = []
    if el == 'fire':
        for i in range(5):
            x0 = r.uniform(8, 24); ph = r.random(); y = 30 - ((t + ph) % 1) * 28
            pts.append((x0 + math.sin((t + ph) * 6.28) * 1.5, y, 3 if (t + ph) % 1 < .6 else 1))
    elif el == 'water':
        for i in range(4):
            x0 = r.choice([7, 9, 23, 25]) + r.uniform(-1, 1); ph = r.random()
            pts.append((x0, 30 + ((t + ph) % 1) * 12, 3))
    elif el == 'wind':
        for i in range(4):
            y0 = r.uniform(10, 38); ph = r.random(); x = 2 + ((t + ph) % 1) * 28
            for k in range(3):
                pts.append((x - k, y0 + math.sin(x * .4) * 1.2, 3 if k == 0 else 2))
    elif el == 'light':
        for i in range(4):
            ang = r.uniform(0, 6.28); ph = r.random()
            rad = 11 + 2 * math.sin((t + ph) * 6.28)
            pts.append((16 + math.cos(ang + t * 6.28 / 2) * rad, 24 + math.sin(ang + t * 6.28 / 2) * rad * 1.4, 4))
    elif el == 'dark':
        for i in range(5):
            x0 = r.uniform(8, 24); ph = r.random(); y = 26 + ((t + ph) % 1) * 18
            pts.append((x0 + math.sin((t + ph) * 6.28) * 2, y, 2))
    return pts

def draw_frame(el, t, nz, nz2, nz3):
    pal = [hexc(c) for c in ELEMENTS[el]]
    ys, xs = np.mgrid[0:H, 0:W].astype(float)
    xs += 0.5; ys += 0.5
    depth = field(el, xs, ys, t, nz, nz2)
    idx = bands(el, depth, xs, ys, t, nz3)
    idx[44:, :] = -1  # nothing below ground line except shadow

    # cleanup: remove orphan pixels (no 4-neighbour of any colour)
    solid = idx >= 0
    nb = np.zeros_like(solid, dtype=int)
    nb[1:, :] += solid[:-1, :]; nb[:-1, :] += solid[1:, :]
    nb[:, 1:] += solid[:, :-1]; nb[:, :-1] += solid[:, 1:]
    idx[(solid) & (nb == 0)] = -1
    p = np.pad(idx, 1, constant_values=-1)
    up, dn, lf, rt = p[:-2, 1:-1], p[2:, 1:-1], p[1:-1, :-2], p[1:-1, 2:]
    agree = (up == dn) & (dn == lf) & (lf == rt) & (idx != up) & (idx >= 0) & (up >= 0)
    idx[agree] = up[agree]

    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    px = img.load()
    # ground shadow (2.5D anchor)
    cx, cy = GROUND
    for yy in range(H):
        for xx in range(W):
            if ((xx + .5 - cx) / 8.5) ** 2 + ((yy + .5 - cy) / 2.2) ** 2 <= 1:
                px[xx, yy] = SHADOW
    if el == 'light':
        # 8 fixed rays (straight + 45deg = clean pixel lines), alternating pulse
        cx0, cy0 = 16, 23
        for k, (dx, dy) in enumerate([(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1),(0,-1),(1,-1)]):
            if dy == 1: continue  # no rays into the ground
            pulse = 0.5 + 0.5 * math.sin(6.2832 * t + k * math.pi)
            r0 = 12 if dx and dy else 13
            for rr in range(r0, r0 + 1 + round(2 * pulse)):
                xx, yy = cx0 + dx * rr, cy0 + dy * rr
                if 0 <= xx < W and 0 <= yy < 43:
                    px[xx, yy] = pal[2] if rr == r0 else pal[1]
    for yy in range(H):
        for xx in range(W):
            i = idx[yy, xx]
            if i >= 0:
                px[xx, yy] = pal[i]
    if el == 'light':
        hb = 0 if math.sin(6.2832 * t) < 0.3 else -1
        HALO = ["..#######..",
                ".#.......#.",
                "..+++++++.."]
        for r_, row in enumerate(HALO):
            for c_, ch_ in enumerate(row):
                if ch_ != '.':
                    px[11 + c_, 1 + r_ + hb] = pal[4] if ch_ == '#' else pal[2]
    # eyes: fixed position, contrasting tone
    bob = 0 if math.sin(6.2832 * t) < 0.3 else -1
    eye = pal[0] if el in ('fire', 'light', 'water', 'wind') else pal[4]
    for ex in (14, 17):
        for ey in (12 + bob, 13 + bob):
            if ex in (14, 17) and ey == 12 + bob or el == 'dark':
                px[ex, ey] = eye
            else:
                px[ex, ey] = eye
    # particles
    for (x, y, c) in particles(el, t, sum(map(ord, el))):
        xi, yi = int(x), int(y)
        if 0 <= xi < W and 0 <= yi < 44:
            px[xi, yi] = pal[c]
            if el == 'light':  # little cross sparkle
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    if 0 <= xi + dx < W and 0 <= yi + dy < 44 and px[xi + dx, yi + dy][3] == 0:
                        px[xi + dx, yi + dy] = pal[2]
    return img

def build(out):
    sheets = {}
    for k, el in enumerate(ELEMENTS):
        nz, nz2, nz3 = LoopNoise(10 + k), LoopNoise(50 + k, scale=0.6), LoopNoise(90 + k, scale=0.9)
        frames = [draw_frame(el, f / FRAMES, nz, nz2, nz3) for f in range(FRAMES)]
        sheet = Image.new('RGBA', (W * FRAMES, H))
        for f, fr in enumerate(frames):
            sheet.paste(fr, (f * W, 0))
        sheet.save(f'{out}/{el}_sheet.png')
        sheets[el] = frames
    return sheets

if __name__ == '__main__':
    build(sys.argv[1] if len(sys.argv) > 1 else '.')
