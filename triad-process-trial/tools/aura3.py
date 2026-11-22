"""v7 renderer: aura-first spirits, subtle faces, orbiting orbs, attack/hit/death, any scale.

Everything is evaluated in "body space" (the original 32x48 skeleton coordinates) and
rasterised natively at any scale SC, so near/far sprites stay crisp pixel art.
"""
import math, random
import numpy as np
from PIL import Image
from gen import ELEMENTS, SHADOW, hexc, body_sdf, smin, sd_capsule, sd_circle

TAU = 2 * math.pi
PAL = {el: [hexc(c) for c in cs] for el, cs in ELEMENTS.items()}
OUTLINE = (16, 10, 26, 255)
ORDER = ['fire', 'water', 'wind', 'light', 'dark']

# ------------------------------------------------------------------ noise
class Flow:
    """Sum of travelling sine waves; integer temporal freqs => seamless over t in [0,1)."""
    def __init__(self, seed, n=6, kx=(-0.5, 0.5), ky=(-0.5, 0.5), f=(1, 2)):
        r = random.Random(seed)
        self.w = [(r.uniform(*kx) * (1 + i * .4), r.uniform(*ky) * (1 + i * .4),
                   r.randint(*f), r.uniform(0, TAU), 1 / (1 + i * .5)) for i in range(n)]
        self.norm = sum(w[-1] for w in self.w)
    def __call__(self, x, y, t):
        return sum(a * np.sin(kx * x + ky * y + TAU * f * t + ph) for kx, ky, f, ph, a in self.w) / self.norm

def noises(el):
    s = ORDER.index(el) * 100
    up = (0.25, 0.6)
    return {
        'w1': Flow(s + 1, kx=(-.4, .4), ky=(-.4, .4)),
        'w2': Flow(s + 2, kx=(-.4, .4), ky=(-.4, .4)),
        'j': Flow(s + 3, kx=(-.9, .9), ky=(-.9, .9)),
        # fire flows UP (ky>0), dark flows DOWN (ky<0)
        'a': Flow(s + 4, kx=(-.9, .9), ky=up, f=(1, 2)),
        'b': Flow(s + 5, kx=(-.3, .3), ky=(-.6, .6), f=(1, 1)),
    }

# ------------------------------------------------------------------ body + aura fields
def elem_body(el, X, Y, t):
    br = math.sin(TAU * t)
    B = body_sdf(X, Y, br, legs=(el != 'wind'))
    if el == 'fire':
        B = smin(B, sd_capsule(X, Y, 16, 10, 16 + 1.5 * math.sin(TAU * t), 1.5, 3.4, 0.3), 2.0)
        B = B + np.clip((Y - 36) / 5, 0, None) * 1.4
    elif el == 'water':
        B = smin(B, sd_capsule(X, Y, 17, 8, 22.5 + 0.8 * br, 15, 2.2, 0.8), 1.5)
        B = smin(B, sd_capsule(X, Y, 11, 42, 21, 42, 1.4, 1.4), 3.0)
    elif el == 'wind':
        B = smin(B, sd_capsule(X, Y, 16 + 1.5 * math.sin(TAU * t), 29, 16 - 2 * math.sin(TAU * t), 42, 4.0, 0.7), 2.0)
    elif el == 'light':
        B = B + np.clip((Y - 37) / 4, 0, None) * 1.3
    elif el == 'dark':
        for s_ in (-1, 1):
            B = smin(B, sd_capsule(X, Y, 16 + s_ * 2.5, 9, 16 + s_ * (5.5 + .5 * br), 3.5, 1.4, 0.4), 1.0)
    return B

def fields(el, x, y, t, N, g=1.0, wg=1.0):
    """Returns body signed distance B (<0 inside) and aura level A (>0 inside aura)."""
    X = x + 0.7 * wg * N['w1'](x, y, t)
    Y = y + 0.7 * wg * N['w2'](x, y, t)
    B = elem_body(el, X, Y, t)
    if el == 'fire':
        n = N['a'](x * 0.8, y * 0.3, t)
        lift = np.clip(n + 0.25, 0, None) * 17 * g * np.clip((50 - y) / 40, 0.4, 1)
        side = 2.5 * g * N['b'](x * 0.5, y * 0.4, t)
        A = -elem_body(el, X + side, Y + lift, t) - 0.3
        A = np.maximum(A, (1.6 + 1.4 * N['j'](x * 0.9, y * 0.5, t)) * g - B)
    elif el == 'water':
        d = np.maximum(B, 0)
        rings = np.sin(d * 1.3 - TAU * t * 2 + 1.5 * N['b'](x, y, t))
        R = 6.5 * g
        A = np.where((B > 0) & (d < R) & (rings > 0.3), (R - d) * 0.8, -9.0)
        # glow skin hugging the body
        A = np.maximum(A, 1.2 - B)
    elif el == 'wind':
        dx, dy = x - 16, (y - 27) * 0.5
        r, th = np.hypot(dx, dy), np.arctan2(dy, dx)
        sp = np.sin(2 * th + 0.55 * r - TAU * t * 2 + 0.8 * N['b'](x, y, t))
        R = 8.5 * g
        A = np.where((B > 0) & (B < R) & (sp > 0.45), (R - B) * 0.6, -9.0)
        A = np.maximum(A, 0.8 - B)
    elif el == 'light':
        th = np.arctan2(y - 24, x - 16)
        spikes = np.clip(np.cos(8 * th + TAU * t), 0, None) ** 4 + 0.6 * np.clip(np.cos(8 * th + TAU * t + math.pi), 0, None) ** 6
        corona = 1.4 + 6.0 * g * spikes * (0.85 + 0.15 * math.sin(TAU * t * 2))
        A = corona - np.maximum(B, 0) + 0.2 * N['j'](x, y, t)
    elif el == 'dark':
        # violet flame around a void body (same flame field as fire, plus sideways tendrils)
        n = N['a'](x * 0.8, y * 0.3, t)
        lift = np.clip(n + 0.25, 0, None) * 17 * g * np.clip((50 - y) / 40, 0.4, 1)
        side = 3.5 * g * N['b'](x * 0.5, y * 0.4, t)
        A = -elem_body(el, X + side, Y + lift, t) - 0.3
        A = np.maximum(A, (1.6 + 1.4 * N['j'](x * 0.9, y * 0.5, t)) * g - B)
    return B, A

# ------------------------------------------------------------------ faces (small, low contrast)
FACES = {
    'fire':  (["E.....E", ".E...E."], 1),   # hot-headed glare
    'water': (["EE...EE"], 1),              # serene, eyes closed
    'wind':  ([".E...E.", ".E..E.E"], 1),   # trickster wink
    'light': ([".E...E.", ".E...E."], 1),   # wide-eyed, innocent
    'dark':  (["EE...EE"], 4),              # cold glowing stare
}

# ------------------------------------------------------------------ orbs
def orb_sprite(el, size=9):
    pal = PAL[el]
    c = (size - 1) / 2
    ys, xs = np.mgrid[0:size, 0:size].astype(float)
    x, y = xs - c, ys - c
    R = size / 2 - 0.4
    if el == 'fire':      # flame drop, tip curling up-right
        d = np.minimum(np.hypot(x, y - 1) - (R - 1.2), sd_capsule(x, y, 0, 0, 1.2, -R, R - 1.6, 0.2))
    elif el == 'water':   # droplet, symmetric tip up
        d = np.minimum(np.hypot(x, y - 1) - (R - 1.0), sd_capsule(x, y, 0, 0, 0, -R, R - 1.8, 0.2))
    elif el == 'wind':    # ball with a carved swirl
        d = np.hypot(x, y) - R
    elif el == 'light':   # 4-point star
        d = np.minimum(np.abs(x) * 0.45 + np.abs(y) - R * 0.95, np.abs(x) + np.abs(y) * 0.45 - R * 0.95)
        d = np.minimum(d, np.hypot(x, y) - R * 0.45)
    elif el == 'dark':    # crescent
        d = np.maximum(np.hypot(x, y) - R, -(np.hypot(x - R * 0.45, y + R * 0.35) - R * 0.72))
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0)); px = img.load()
    for j in range(size):
        for i in range(size):
            if d[j, i] <= 0:
                depth = -d[j, i]
                lit = depth - 0.35 * (x[j, i] + y[j, i])
                k = 0 if depth < 0.8 else 1 if lit < 1.0 else 2 if lit < 2.0 else 3
                if el == 'dark':
                    k = 3 if depth < 0.8 else 2 if lit < 1.2 else 1
                px[i, j] = pal[k]
    if el == 'wind':
        for (i, j) in [(int(c) + dx, int(c) + dy) for dx, dy in ((-1, 0), (0, -1), (1, -1), (1, 0), (1, 1), (0, 1))]:
            if 0 <= i < size and 0 <= j < size: px[i, j] = pal[0]
    hi = (int(c) - 1, int(c) - 1) if el != 'dark' else (int(c) - 2, int(c))
    if el != 'light' and px[hi][3]: px[hi] = pal[4]
    if el == 'light': px[int(c), int(c)] = pal[4]
    out = Image.new('RGBA', (size + 2, size + 2), (0, 0, 0, 0)); op = out.load()
    for j in range(size):
        for i in range(size):
            if px[i, j][3]:
                for ddx, ddy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    op[i + 1 + ddx, j + 1 + ddy] = OUTLINE
    out.alpha_composite(img, (1, 1))
    return out

ORB = {(el, s): orb_sprite(el, s) for el in ORDER for s in (7, 9)}

# ------------------------------------------------------------------ particles (body space)
def particles(el, t, seed):
    r = random.Random(seed); out = []   # (ox, oy, palidx, front?)
    if el == 'fire':
        for i in range(7):
            ph, x0 = r.random(), r.uniform(7, 25); u = (t * r.choice([1, 2]) + ph) % 1
            if u > 0.8: continue
            x, y = x0 + 2 * math.sin(u * TAU * 1.5 + i), 40 - u * 44
            out += [(x, y, 4, i % 2), (x, y + 0.8, 3, i % 2), (x, y + 1.6, 1, i % 2)]
    elif el == 'water':
        for i in range(5):
            ph, x0 = r.random(), r.uniform(5, 27); u = (t + ph) % 1
            out.append((x0 + math.sin(u * TAU * 2) * 1.2, 44 - u * 36, 4, i % 2))
    elif el == 'wind':
        for i in range(4):
            ph, y0 = r.random(), r.uniform(8, 40); u = (t * 2 + ph) % 1
            x = -6 + u * 44
            for k in range(4):
                out.append((x - k * 0.8, y0 + math.sin(x * 0.4) * 1.0, 3 if k == 0 else 2, i % 2))
    elif el == 'light':
        for i in range(5):
            ph, ang = r.random(), r.uniform(0, TAU); u = (t * 2 + ph) % 1
            if u > 0.5: continue
            rad = 13 + r.uniform(-1, 2)
            out.append((16 + math.cos(ang) * rad, 24 + math.sin(ang) * rad * 1.3, 4, i % 2))
    elif el == 'dark':
        for i in range(5):
            ph, x0 = r.random(), r.uniform(8, 24); u = (t + ph) % 1
            out.append((x0 + math.sin(u * TAU) * 2, 28 + u * 16, 3, 0))
    return out

def burst(el, p, seed=7):
    """Radial element burst (attack). p in [0,1]."""
    r = random.Random(seed); out = []
    for i in range(14):
        a = TAU * i / 14 + r.uniform(-.2, .2)
        rad = 3 + p * r.uniform(16, 24)
        x, y = 16 + math.cos(a) * rad, 25 + math.sin(a) * rad * 0.8
        c = 4 if p < 0.4 else 3 if p < 0.7 else 1
        out += [(x, y, c, 1), (x - math.cos(a) * 1.2, y - math.sin(a), 2, 1)]
    return out

def rise(el, d, seed=11):
    """Death: motes rising out of the dissolving body."""
    r = random.Random(seed); out = []
    for i in range(22):
        x0, y0, sp = r.uniform(8, 24), r.uniform(8, 42), r.uniform(10, 30)
        st = r.uniform(0, 0.5)
        u = (d - st) / 0.5
        if 0 <= u <= 1:
            out.append((x0 + math.sin(u * 5 + i) * 2, y0 - u * sp, 4 if u < .5 else 2, 1))
    return out

# ------------------------------------------------------------------ render one sprite frame
def canvas_size(SC):
    return int(round(66 * SC)), int(round(74 * SC))

def render(el, t, SC=1.3, view='front', act=None, N=None):
    act = act or {}
    N = N or noises(el)
    pal = PAL[el]
    Wc, Hc = canvas_size(SC)
    Gy = Hc - 3 * SC
    dx, dy = act.get('dx', 0), act.get('dy', 0)
    sx, sy, lean = act.get('sx', 1), act.get('sy', 1), act.get('lean', 0)
    g, wg, dis = act.get('g', 1), act.get('wg', 1), act.get('dissolve', 0)

    def to_body(X, Y):
        ox = (X + .5 - Wc / 2 - dx) / SC + 16
        oy = (Y + .5 - Gy - dy) / SC + 44
        ox = (ox - 16) / sx + 16
        oy = 44 - (44 - oy) / sy
        return ox - lean * (44 - oy) / 40, oy

    def to_canvas(px_, py_):
        ox2 = px_ + lean * (44 - py_) / 40
        oy = 44 - (44 - py_) * sy
        ox = (ox2 - 16) * sx + 16
        return (ox - 16) * SC + Wc / 2 + dx, (oy - 44) * SC + Gy + dy

    Ys, Xs = np.mgrid[0:Hc, 0:Wc].astype(float)
    x, y = to_body(Xs, Ys)
    if view == 'back':
        x = 32 - x  # mirror so asymmetric features (water crest) sit on the other side
    B, A = fields(el, x, y, t, N, g, wg)
    if dis > 0:
        nn = N['j'](x * 1.5, y * 1.5, t)
        B = B + dis * (9 + 4 * nn) + np.clip(dis * 1.5 - 0.2, 0, None) * (44 - y) * 0.0
        A = A - dis * (10 + 4 * nn)

    idx = -np.ones(B.shape, dtype=int)
    inside = B <= 0
    v = -B * SC + 0.4 * N['j'](x * 1.2, y * 1.2, t)
    aura = (~inside) & (A > 0)
    glow = (~inside) & (A <= 0) & (A > -1.4) & (((Xs + Ys) % 2) == 0)
    if el == 'dark':
        idx[glow] = 1
        idx[aura] = np.where(A[aura] > 1.8, 3, 2)
        vo = -B + 0.4 * N['j'](x * 1.2, y * 1.2, t)
        idx[inside] = np.select([vo[inside] < 0.7, vo[inside] < 1.7], [3, 1], 0)
    else:
        idx[glow] = 0
        idx[aura] = np.where(A[aura] > 3.5, 2, np.where(A[aura] > 1.3, 1, 0))
        vb = -B + 0.4 * N['j'](x * 1.2, y * 1.2, t) + np.clip(1.2 - np.abs(x - 16) * 0.12, 0, None)
        idx[inside] = np.select([vb[inside] < 0.9, vb[inside] < 2.4], [2, 3], 4)
    idx[Ys >= Gy + dy + 1] = -1
    # orphan removal + majority smoothing
    p = np.pad(idx, 1, constant_values=-1)
    up, dn, lf, rt = p[:-2, 1:-1], p[2:, 1:-1], p[1:-1, :-2], p[1:-1, 2:]
    nb = (up >= 0).astype(int) + (dn >= 0) + (lf >= 0) + (rt >= 0)
    idx[(idx >= 0) & (nb == 0) & ~glow] = -1
    agree = (up == dn) & (dn == lf) & (lf == rt) & (idx != up) & (idx >= 0) & (up >= 0)
    idx[agree] = up[agree]

    img = Image.new('RGBA', (Wc, Hc), (0, 0, 0, 0)); px = img.load()
    def put(bx, by, c):
        X, Y = to_canvas(32 - bx if view == 'back' else bx, by)
        X, Y = int(round(X)), int(round(Y))
        if 0 <= X < Wc and 0 <= Y < Hc: px[X, Y] = c

    # shadow
    sh = max(0.0, 1 - dis)
    if sh > 0:
        rx, ry = 9.5 * SC * sh * sx, 2.3 * SC * sh
        for Y in range(Hc):
            for X in range(Wc):
                if ((X + .5 - Wc / 2 - dx) / max(rx, .1)) ** 2 + ((Y + .5 - Gy) / max(ry, .1)) ** 2 <= 1:
                    px[X, Y] = SHADOW

    # orbs (orbit in body space; back half behind the spirit)
    orbs = act.get('orbs')
    orb_layers = ([], [])
    if orbs:
        sz = 9 if SC >= 1.4 else 7
        for i, oe in enumerate(orbs):
            a = TAU * (t + i / len(orbs))
            ox, oy = 16 + math.cos(a) * 17, 30 + math.sin(a) * 4.5 + 1.2 * math.sin(TAU * t * 2 + i)
            orb_layers[1 if math.sin(a) > 0 else 0].append((ox, oy, oe, sz))
    def draw_orbs(layer):
        for ox, oy, oe, sz in layer:
            X, Y = to_canvas(ox, oy)
            img.alpha_composite(ORB[(oe, sz)], (int(X - sz / 2), int(Y - sz / 2)))

    parts = particles(el, t, ORDER.index(el) * 31) if dis < 0.2 else []
    if act.get('burst') is not None: parts += burst(el, act['burst'])
    if dis > 0: parts += rise(el, dis)

    draw_orbs(orb_layers[0])
    for bx, by, c, f in parts:
        if not f: put(bx, by, pal[c])
    for Y in range(Hc):
        for X in range(Wc):
            k = idx[Y, X]
            if k >= 0: px[X, Y] = pal[k]
    if act.get('flash'):
        fc = pal[4] if el != 'light' else (255, 255, 255, 255)
        for Y in range(Hc):
            for X in range(Wc):
                if idx[Y, X] >= 0: px[X, Y] = fc
    # light's halo
    if el == 'light' and dis < 0.5:
        hx, hy = to_canvas(16, 4.2 - 0.4 * (math.sin(TAU * t) > 0.3))
        hw = int(round(5.5 * SC))
        for k in range(-hw, hw + 1):
            e = abs(k) / hw
            X = int(round(hx + k))
            if e > 0.75: px[X, int(round(hy))] = pal[4]
            elif 0 <= X < Wc:
                px[X, int(round(hy - 1))] = pal[4]; px[X, int(round(hy + 1))] = pal[2]
    # face (front only)
    if view == 'front' and act.get('face', True) and dis < 0.3 and not act.get('flash'):
        rows, ci = FACES[el]
        fx_, fy_ = to_canvas(16, 12.4 - 0.4 * (math.sin(TAU * t) > 0.3))
        for r_, row in enumerate(rows):
            for c_, ch in enumerate(row):
                if ch == 'E':
                    X, Y = int(round(fx_ - 3 + c_)), int(round(fy_ + r_))
                    if 0 <= X < Wc and 0 <= Y < Hc: px[X, Y] = pal[ci]
    for bx, by, c, f in parts:
        if f: put(bx, by, pal[c])
    draw_orbs(orb_layers[1])
    return img

# ------------------------------------------------------------------ action timelines
def tl_idle(n):
    return [{} for _ in range(n)]

def tl_attack(view='front'):
    out = []
    for k in range(10):
        if k < 4:
            e = k / 3
            a = {'sx': 1 - .07 * e, 'sy': 1 - .1 * e, 'g': 1 - .45 * e, 'lean': -.15 * e}
        else:
            e = (k - 4) / 5
            s = 1 + .2 * (1 - e) ** 2
            a = {'sx': s, 'sy': s, 'g': 1 + 1.1 * (1 - e), 'burst': e if e < 1 else None}
            if view == 'back':
                a.update({'sx': 2 - s, 'sy': 2 - s, 'dy': -10 * (1 - e) ** 2})
        out.append(a)
    return out

def tl_hit():
    js = [3, -3, 2, -1, 0, 0]
    return [{'flash': k < 2, 'dx': js[k], 'sx': .92 + .016 * k, 'sy': .92 + .016 * k,
             'wg': 3.2 - .45 * k, 'g': .5 + .1 * k} for k in range(6)]

def tl_death():
    out = [{'flash': True, 'wg': 3}, {'dx': 3, 'wg': 3.5}, {'dx': -3, 'wg': 3.5, 'g': 1.6}]
    for k in range(13):
        d = k / 12
        out.append({'dissolve': d, 'g': 1.6 * (1 - d), 'wg': 2 + 2 * d, 'face': d < .25})
    return out + [{'dissolve': 1.2} for _ in range(4)]
