"""Style exploration: the NULL MONARCH scene rebuilt in 3D (ray-marched signed distance fields),
then rendered as A) HD pixel art, B) graphic-novel comic, C) cinematic CGI.

Usage: python3 tools/styles.py OUT_DIR
"""
import math, os, random, sys
import numpy as np
from PIL import Image, ImageFilter, ImageDraw
import aura3 as A
import boss as B
from battle_ui import text, text_w

TAU = 2 * math.pi
W, H = 960, 540          # ray-march resolution
OW, OH = 1280, 720       # output resolution

# ------------------------------------------------------------------ 3D SDF primitives (p = tuple of arrays)
def length3(x, y, z): return np.sqrt(x * x + y * y + z * z)
def rbox(p, c, h, r):
    qx = np.abs(p[0] - c[0]) - (h[0] - r); qy = np.abs(p[1] - c[1]) - (h[1] - r); qz = np.abs(p[2] - c[2]) - (h[2] - r)
    return length3(np.maximum(qx, 0), np.maximum(qy, 0), np.maximum(qz, 0)) + np.minimum(np.maximum(qx, np.maximum(qy, qz)), 0) - r
def cap(p, a, b, ra, rb):
    pax, pay, paz = p[0] - a[0], p[1] - a[1], p[2] - a[2]
    bx, by, bz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    hh = np.clip((pax * bx + pay * by + paz * bz) / (bx * bx + by * by + bz * bz), 0, 1)
    return length3(pax - bx * hh, pay - by * hh, paz - bz * hh) - (ra + (rb - ra) * hh)
def torus(p, c, R, r):
    q = np.hypot(p[0] - c[0], p[2] - c[2]) - R
    return np.hypot(q, p[1] - c[1]) - r
def cyl_z(p, c, r, hl):
    dx = np.hypot(p[0] - c[0], p[1] - c[1]) - r; dz = np.abs(p[2] - c[2]) - hl
    return np.minimum(np.maximum(dx, dz), 0) + np.hypot(np.maximum(dx, 0), np.maximum(dz, 0))
def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)

T_NOW = 0.0
def scene(x, y, z, want_mat=False):
    t = T_NOW
    p = (x, y, z)
    head = smin(rbox(p, (0, 90, 0), (13, 15, 11), 5), rbox(p, (0, 76, 2), (9, 5, 8), 3), 2)
    fins = np.minimum(cap(p, (0, 103, -2), (0, 118, -4), 2.2, 0.4),
                      np.minimum(cap(p, (-8, 101, -2), (-14, 113, -4), 1.8, 0.4), cap(p, (8, 101, -2), (14, 113, -4), 1.8, 0.4)))
    headall = smin(head, fins, 1)
    visor = rbox((x, y - 0.22 * np.abs(x), z), (0, 89.5, 10.4), (11.5, 1.6, 1.4), 0.7)
    sw = 0.8 * math.sin(TAU * t + 1)
    cables = np.minimum(np.minimum(cap(p, (-5, 75, 0), (-7 + sw, 62, 2), 1.7, 1.7), cap(p, (5, 75, 0), (7 + sw, 62, 2), 1.7, 1.7)),
                        cap(p, (0, 74, -1), (sw, 62, 1), 1.5, 1.5))
    torso = smin(rbox(p, (0, 52, 0), (28, 12, 13), 6), rbox(p, (0, 31, 0), (19, 13, 11), 6), 4)
    torso = smin(torso, rbox(p, (0, -30, -2), (17, 52, 10), 5), 5)  # waist/legs going down into the street
    sh = np.minimum(rbox(p, (-31, 61, 0), (11, 9, 11), 4), rbox(p, (31, 61, 0), (11, 9, 11), 4))
    sh = np.minimum(sh, np.minimum(cap(p, (-35, 69, 0), (-41, 81, -2), 2.4, 0.4), cap(p, (35, 69, 0), (41, 81, -2), 2.4, 0.4)))
    body = smin(torso, sh, 2)
    arms = np.minimum(cap(p, (-33, 53, 4), (-44, 31, 19), 4.8, 3.6), cap(p, (33, 53, 4), (44, 31, 19), 4.8, 3.6))
    hands = None
    for s in (-1, 1):
        hx = 44 * s
        hd = rbox(p, (hx, 27, 22), (8.5, 4, 7.5), 3)
        for i in range(4):
            fx = hx - 6.3 + 4.2 * i
            hd = smin(hd, cap(p, (fx, 25, 27), (fx, 20.5, 32), 1.8, 1.5), 0.8)
            hd = np.minimum(hd, cap(p, (fx, 20.5, 32), (fx, 18.6, 36.5), 1.4, 0.3))
        hd = smin(hd, cap(p, (hx - s * 8, 26, 22), (hx - s * 11, 20, 27), 2.0, 1.4), 0.8)
        hands = hd if hands is None else np.minimum(hands, hd)
    metal = np.minimum.reduce([headall, cables, body, smin(arms, hands, 2)])
    core = cyl_z(p, (0, 47, 12.6), 6.0, 1.2)
    strips = np.minimum(rbox(p, (-31, 61, 11.1), (0.8, 6.5, 0.5), 0.2), rbox(p, (31, 61, 11.1), (0.8, 6.5, 0.5), 0.2))
    ang = np.arctan2(z, x)
    crown = torus((x, y - 0.12 * x, z), (0, 114, 0), 15, 0.9)
    crown = np.where(np.sin(5 * ang + TAU * t) > -0.5, crown, np.maximum(crown, 1.5))
    parts = [metal, visor, core, strips, crown]
    d = np.minimum.reduce(parts)
    if want_mat:
        return d, np.argmin(np.stack(parts), axis=0)
    return d

# ------------------------------------------------------------------ camera
CAM = np.array([-38.0, 64.0, 190.0]); TGT = np.array([-2.0, 50.0, 0.0]); FOV = 44
fwd = TGT - CAM; fwd /= np.linalg.norm(fwd)
right = np.cross(fwd, [0, 1, 0]); right /= np.linalg.norm(right)
up = np.cross(right, fwd)
def project(P):
    """world points (N,3) -> screen (u,v) at W x H"""
    d = P - CAM
    zc = d @ fwd; xc = d @ right; yc = d @ up
    f = 0.5 * H / math.tan(math.radians(FOV / 2))
    return W / 2 + xc / zc * f, H / 2 - yc / zc * f

ROOF_Y, EDGE_Z = 18.0, 25.0
LIGHTS = [  # pos, colour, intensity
    (np.array([-90, 75, 70]), np.array([1.0, 0.16, 0.58]), 1.5),   # magenta neon left
    (np.array([95, 70, 70]), np.array([0.18, 0.92, 1.0]), 1.5),    # cyan neon right
    (np.array([0, 220, 120]), np.array([0.45, 0.42, 0.62]), 0.7),  # cool sky fill
    (np.array([-40, 30, 120]), np.array([1.0, 0.45, 0.12]), 0.6),  # warm bounce from the fire spirit
]

def sample(img, u, v):
    hh, ww = img.shape[:2]
    ui = np.clip(u.astype(int), 0, ww - 1); vi = np.clip(v.astype(int), 0, hh - 1)
    return img[vi, ui]

def march(ro, rd, tmax, steps=110):
    n = rd.shape[0]
    t = np.zeros(n); hit = np.zeros(n, bool)
    # AABB clip
    lo, hi = np.array([-62, -90, -22]), np.array([62, 125, 42])
    with np.errstate(divide='ignore', invalid='ignore'):
        t0 = (lo - ro) / rd; t1 = (hi - ro) / rd
    tn = np.nanmax(np.minimum(t0, t1), axis=1); tf = np.nanmin(np.maximum(t0, t1), axis=1)
    act = (tf > np.maximum(tn, 0)) & (tn < tmax)
    t = np.maximum(tn, 0) + 0.01
    idx = np.nonzero(act)[0]
    for _ in range(steps):
        if idx.size == 0: break
        p = ro[idx] + rd[idx] * t[idx, None]
        d = scene(p[:, 0], p[:, 1], p[:, 2])
        h = d < 0.015 * (1 + t[idx] / 200)
        hit[idx[h]] = True
        t[idx[~h]] += d[~h] * 0.85
        keep = ~h & (t[idx] < np.minimum(tf[idx], tmax[idx]))
        idx = idx[keep]
    return hit, t

def normal(p):
    e = 0.06
    k = [(1, -1, -1), (-1, -1, 1), (-1, 1, -1), (1, 1, 1)]
    n = np.zeros_like(p)
    for kx, ky, kz in k:
        d = scene(p[:, 0] + kx * e, p[:, 1] + ky * e, p[:, 2] + kz * e)
        n += np.array([kx, ky, kz]) * d[:, None]
    return n / (np.linalg.norm(n, axis=1, keepdims=True) + 1e-9)

def shade_boss(p, rd, tdist, env, charge=0.0):
    n = normal(p)
    _, mat = scene(p[:, 0], p[:, 1], p[:, 2], want_mat=True)
    V = -rd
    alb = np.array([0.035, 0.035, 0.05])
    col = np.tile(np.array([0.012, 0.01, 0.025]), (p.shape[0], 1))
    for pos, c, I in LIGHTS:
        L = pos - p; dist = np.linalg.norm(L, axis=1, keepdims=True); L /= dist
        att = I / (1 + (dist / 160) ** 2)
        diff = np.clip((n * L).sum(1, keepdims=True), 0, None)
        Hh = L + V; Hh /= np.linalg.norm(Hh, axis=1, keepdims=True)
        spec = np.clip((n * Hh).sum(1, keepdims=True), 0, None) ** 70
        col += (alb * diff + 1.3 * spec) * c * att
    # reactor light on the chest and hands
    L = np.array([0, 47, 20]) - p; dist = np.linalg.norm(L, axis=1, keepdims=True); L /= dist
    col += np.clip((n * L).sum(1, keepdims=True), 0, None) * np.array([1, 0.15, 0.5]) * (0.9 + 2 * charge) / (1 + (dist / 22) ** 2)
    # chrome: reflect the city
    R = rd - 2 * (rd * n).sum(1, keepdims=True) * n
    u, v = project(p + R * 600)
    fres = 0.25 + 0.75 * (1 - np.clip((n * V).sum(1, keepdims=True), 0, 1)) ** 4
    col += sample(env, u, v) * fres * 0.9
    # ambient occlusion
    ao = np.ones((p.shape[0], 1))
    for k in range(1, 5):
        dd = k * 1.1
        ao -= (dd - scene(*(p + n * dd).T))[:, None] / (2 ** k) * 0.35
    col *= np.clip(ao, 0.15, 1)
    # panel seams
    x, y, z = p.T
    seam = ((np.abs(x) < 0.3) & (y < 44) & (z > 8)) | ((np.abs(y - 42) < 0.3) & (z > 8)) | ((np.abs(np.abs(x) - 15) < 0.3) & (y > 40) & (y < 62) & (z > 10))
    col[seam] *= 0.35
    # emissives
    scan = 9.5 * math.sin(TAU * T_NOW)
    vis = mat == 1
    vc = np.array([0.25, 0.95, 1.0]) if charge < 0.5 else np.array([1.0, 0.2, 0.6])
    col[vis] = vc * 2.2 + np.exp(-((x[vis] - scan) / 1.6) ** 2)[:, None] * 3.0
    cr = mat == 2
    r = np.hypot(x[cr], y[cr] - 47)
    col[cr] = np.array([1, 0.12, 0.5]) * 2.4 + np.clip(1 - r / 2.8, 0, 1)[:, None] * 4.0
    st = mat == 3
    col[st] = np.where((x[st] < 0)[:, None], np.array([1, 0.15, 0.55]), np.array([0.2, 0.9, 1])) * (1.6 + 0.8 * math.sin(TAU * T_NOW * 2))
    col[mat == 4] = np.array([1, 0.2, 0.6]) * 2.6
    fog = 1 - np.exp(-tdist / 900)
    col = col * (1 - fog[:, None]) + np.array([0.22, 0.05, 0.2]) * fog[:, None]
    return col

# ------------------------------------------------------------------ backdrop (the city, photographic)
def city_backdrop(f=0):
    city = B.City(text, text_w)
    sky = city.sky_layer(f).convert('RGB')
    # crop above the roof, scale up smoothly, defocus, add bokeh from lights
    sky = sky.crop((0, 0, 640, B.ROOF))
    big = sky.resize((W, int(B.ROOF * W / 640)), Image.BICUBIC)
    arr = np.asarray(big).astype(float) / 255
    lum = arr.max(axis=2)
    bright = np.where(lum[..., None] > 0.45, arr, 0) * 255
    bimg = Image.fromarray(bright.astype(np.uint8))
    bok = np.asarray(bimg.filter(ImageFilter.GaussianBlur(4))).astype(float) / 255 * 1.6 \
        + np.asarray(bimg.filter(ImageFilter.GaussianBlur(12))).astype(float) / 255 * 1.2
    soft = np.asarray(big.filter(ImageFilter.GaussianBlur(2.2))).astype(float) / 255
    out = soft * 0.85 + bok
    # linearise-ish
    return out ** 1.6 * 1.3

def build_frame(t=0.0, charge=0.0):
    global T_NOW
    T_NOW = t
    back = city_backdrop(int(t * 12))
    # align city horizon (its roof row) to the projected roof edge
    eu, ev = project(np.array([[0.0, ROOF_Y, EDGE_Z]]))
    edge_row = int(ev[0])
    env = np.zeros((H, W, 3))
    bh = back.shape[0]
    top = edge_row - bh
    src0 = max(0, -top)
    env[max(0, top):edge_row] = back[src0:bh]
    if top > 0: env[:top] = back[0][None] * np.linspace(0.6, 1.0, top)[:, None, None]
    env[edge_row:] = back[-1] * 0.5
    rows = np.arange(H)[:, None, None]
    env += np.clip(1 - np.abs(rows - edge_row + 40) / 170, 0, 1) ** 2 * np.array([0.45, 0.08, 0.32])
    beams = Image.new('L', (W, H), 0); bd = ImageDraw.Draw(beams)
    for bx, ang, wdt in ((180, -0.35, 26), (760, 0.42, 22), (520, -0.12, 16)):
        bd.polygon([(bx - 3, edge_row - 60), (bx + 3, edge_row - 60), (bx + 900 * math.sin(ang) + wdt * 4, -50), (bx + 900 * math.sin(ang) - wdt * 4, -50)], fill=70)
    bm = np.asarray(beams.filter(ImageFilter.GaussianBlur(14))).astype(float)[..., None] / 255
    env += bm * np.array([0.55, 0.5, 0.75])
    envb = np.asarray(Image.fromarray((np.clip(env, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(5))).astype(float) / 255
    envb = envb ** 1.0

    jj, ii = np.mgrid[0:H, 0:W].astype(float)
    f_ = 0.5 * H / math.tan(math.radians(FOV / 2))
    rd = (fwd[None, None, :] * f_ + right[None, None, :] * (ii - W / 2)[..., None] - up[None, None, :] * (jj - H / 2)[..., None])
    rd = rd.reshape(-1, 3); rd /= np.linalg.norm(rd, axis=1, keepdims=True)
    ro = np.tile(CAM, (rd.shape[0], 1))
    # roof plane
    with np.errstate(divide='ignore', invalid='ignore'):
        tfl = (ROOF_Y - CAM[1]) / rd[:, 1]
    zf = CAM[2] + rd[:, 2] * tfl
    floor = (rd[:, 1] < 0) & (zf > EDGE_Z)
    tfl = np.where(floor, tfl, 1e9)
    hit, tt = march(ro, rd, tfl)
    img = env.reshape(-1, 3).copy()
    ph = ro[hit] + rd[hit] * tt[hit, None]
    img[hit] = shade_boss(ph, rd[hit], tt[hit], envb, charge)
    # wet roof: reflections with ripples + railing neon + fire light pool
    fl = floor & ~hit
    P = ro[fl] + rd[fl] * tfl[fl, None]
    rr = rd[fl].copy(); rr[:, 1] *= -1
    rip = 0.004 * np.sin(P[:, 0] * 0.9 + P[:, 2] * 0.35) + 0.003 * np.sin(P[:, 2] * 1.7 + P[:, 0] * 0.4) + 0.003 * np.sin(P[:, 0] * 2.3 - P[:, 2] * 1.1)
    rr[:, 0] += rip; rr[:, 1] += rip * 0.5
    rr /= np.linalg.norm(rr, axis=1, keepdims=True)
    h2, t2 = march(P, rr, np.full(P.shape[0], 1e9), steps=70)
    refl = np.zeros_like(P)
    u, v = project(P + rr * 800)
    refl[:] = sample(envb, u, v)
    if h2.any():
        q = P[h2] + rr[h2] * t2[h2, None]
        refl[h2] = shade_boss(q, rr[h2], t2[h2], envb, charge)
    fres = 0.08 + 0.92 * (1 - np.abs(rd[fl, 1])) ** 5
    puddle = (np.sin(P[:, 0] * 0.07) * np.sin(P[:, 2] * 0.11 + 1) > -0.2).astype(float)
    base = np.array([0.018, 0.016, 0.03])
    col = base + refl * (0.25 + 0.7 * fres[:, None]) * (0.45 + 0.55 * puddle[:, None])
    rail = np.abs(P[:, 2] - EDGE_Z - 0.6) < 0.55
    col[rail] = np.array([0.25, 0.95, 1.0]) * 2.0
    # grid seams in the concrete
    g = (np.abs((P[:, 0] + 1000) % 22 - 11) > 10.7) | (np.abs((P[:, 2]) % 22 - 11) > 10.7)
    col[g] *= 0.6
    img[fl] = col
    img = img.reshape(H, W, 3)
    return img

# ------------------------------------------------------------------ the fire spirit (smooth emissive version)
def fire_spirit(t, SC=4.4):
    N = A.noises('fire')
    Wc, Hc = int(66 * SC), int(74 * SC)
    Gy = Hc - 3 * SC
    Ys, Xs = np.mgrid[0:Hc, 0:Wc].astype(float)
    x = 32 - ((Xs + .5 - Wc / 2) / SC + 16)
    y = (Ys + .5 - Gy) / SC + 44
    Bd, Ad = A.fields('fire', x, y, t, N)
    I = np.clip(Ad / 6, 0, 1) * 0.75 + np.clip(-Bd / 3, 0, 1) * 0.6
    I = np.clip(I, 0, 1.2)
    stops = [(0.0, (0, 0, 0)), (0.15, (0.35, 0.03, 0.01)), (0.4, (1.0, 0.28, 0.04)), (0.7, (1.0, 0.62, 0.18)), (0.95, (1.0, 0.92, 0.6)), (1.2, (1.4, 1.3, 1.1))]
    col = np.zeros(I.shape + (3,))
    for (a, ca), (b, cb) in zip(stops, stops[1:]):
        m = (I >= a) & (I < b)
        u = ((I - a) / (b - a))[m][:, None]
        col[m] = np.array(ca) * (1 - u) + np.array(cb) * u
    col[I >= 1.2] = stops[-1][1]
    return col * 1.6, I, Gy

def composite_fire(img, t, ax, ay):
    col, I, Gy = fire_spirit(t)
    h, w = I.shape
    x0, y0 = int(ax - w / 2), int(ay - Gy)
    a = np.clip(I * 3, 0, 1)[..., None]
    sub = img[y0:y0 + h, x0:x0 + w]
    img[y0:y0 + h, x0:x0 + w] = sub * (1 - a * 0.6) + col * a
    # reflection on the wet roof (flipped, dimmer)
    ry = int(ay + 2)
    rh = min(h, img.shape[0] - ry)
    fl = col[::-1][:rh] * 0.35
    img[ry:ry + rh, x0:x0 + w] += fl * np.linspace(1, 0, rh)[:, None, None]
    # warm light pool
    jj, ii = np.mgrid[0:img.shape[0], 0:img.shape[1]]
    e = ((ii - ax) / 190.0) ** 2 + ((jj - ay) / 34.0) ** 2
    img += np.clip(1 - e, 0, 1)[..., None] ** 2 * np.array([1.0, 0.4, 0.1]) * 0.35
    return img

# ------------------------------------------------------------------ post: bloom, grade, lens
def post(img, rain_seed=1, grain=True):
    img = np.clip(img, 0, 8)
    lum = img.max(axis=2, keepdims=True)
    bright = np.clip(img - 0.75, 0, None)
    b8 = (np.clip(bright / 4, 0, 1) * 255).astype(np.uint8)
    bi = Image.fromarray(b8)
    bloom = (np.asarray(bi.filter(ImageFilter.GaussianBlur(6))).astype(float) * 0.9 +
             np.asarray(bi.filter(ImageFilter.GaussianBlur(22))).astype(float) * 1.4) / 255 * 4
    img = img + bloom * 0.6
    # ACES-ish tonemap
    a, b, c, d, e = 2.51, 0.03, 2.43, 0.59, 0.14
    img = np.clip((img * (a * img + b)) / (img * (c * img + d) + e), 0, 1)
    # grade: teal shadows, magenta highlights
    l = img.mean(axis=2, keepdims=True)
    img = img + (1 - l) * np.array([-0.01, 0.015, 0.03]) + l * np.array([0.03, -0.01, 0.02])
    img = np.clip(img, 0, 1) ** (1 / 1.05)
    h, w = img.shape[:2]
    # rain streaks
    r = random.Random(rain_seed)
    rain = Image.new('L', (w, h), 0); dr = ImageDraw.Draw(rain)
    for _ in range(420):
        x, y, L = r.uniform(-100, w), r.uniform(-50, h), r.uniform(18, 60)
        dr.line([(x, y), (x + L * 0.25, y + L)], fill=r.randint(25, 70), width=1)
    for _ in range(14):  # a few big out-of-focus drops in the foreground
        x, y, L = r.uniform(0, w), r.uniform(0, h), r.uniform(80, 160)
        dr.line([(x, y), (x + L * 0.25, y + L)], fill=r.randint(20, 40), width=3)
    rn = np.asarray(rain.filter(ImageFilter.GaussianBlur(0.6))).astype(float)[..., None] / 255
    img = img + rn * np.array([0.7, 0.8, 1.0]) * 0.9
    # chromatic aberration toward the edges
    out = img.copy()
    out[..., 0] = np.roll(img[..., 0], 2, axis=1)
    out[..., 2] = np.roll(img[..., 2], -2, axis=1)
    jj, ii = np.mgrid[0:h, 0:w]
    rr = np.hypot((ii - w / 2) / (w / 2), (jj - h / 2) / (h / 2))
    mix = np.clip(rr - 0.4, 0, 1)[..., None]
    img = img * (1 - mix) + out * mix
    img *= (1 - 0.45 * np.clip(rr - 0.35, 0, 1) ** 1.6)[..., None]  # vignette
    if grain:
        img += np.random.default_rng(rain_seed).normal(0, 0.018, img.shape)
    return np.clip(img, 0, 1)

# ------------------------------------------------------------------ style A: HD pixel art from the render
BAYER = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) + 0.5) / 16 - 0.5

ACCENTS = np.array([  # always kept in the pixel palette so key hues survive quantisation
    (64, 10, 6), (150, 30, 8), (240, 90, 20), (255, 170, 60), (255, 236, 170),     # fire ramp
    (20, 120, 150), (70, 235, 255), (150, 20, 90), (255, 50, 160), (255, 245, 252),  # neon + white
    (8, 6, 16), (24, 18, 40)], float)

def to_pixel(img, w=640, h=360, colors=36):
    small = Image.fromarray((img * 255).astype(np.uint8)).resize((w, h), Image.BOX)
    arr = np.asarray(small).astype(float)
    pal_img = small.quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    pal = np.array(pal_img.getpalette()[:colors * 3]).reshape(-1, 3).astype(float)
    pal = np.vstack([pal, ACCENTS])
    jj, ii = np.mgrid[0:h, 0:w]
    arr = arr + BAYER[jj % 4, ii % 4][..., None] * 22
    q = np.empty((h, w, 3), np.uint8)
    for r0 in range(0, h, 60):  # chunked nearest-colour search
        d = ((arr[r0:r0 + 60, :, None, :] - pal[None, None]) ** 2).sum(-1)
        q[r0:r0 + 60] = pal[np.argmin(d, axis=-1)].astype(np.uint8)
    im = Image.fromarray(q)
    return im.resize((w * 2, h * 2), Image.NEAREST), im

# ------------------------------------------------------------------ style B: graphic novel / comic
def comic(img):
    im = Image.fromarray((img * 255).astype(np.uint8)).filter(ImageFilter.MedianFilter(5))
    hsv = np.asarray(im.convert('HSV')).astype(float) / 255
    v = hsv[..., 2]
    levels = np.array([0.06, 0.22, 0.45, 0.72, 1.0])
    vq = levels[np.clip(np.digitize(v, [0.12, 0.33, 0.6, 0.86]), 0, 4)]
    hsv[..., 1] = np.clip(hsv[..., 1] * 1.2, 0, 1)
    hsv[..., 2] = vq
    flat = np.asarray(Image.fromarray((hsv * 255).astype(np.uint8), 'HSV').convert('RGB')).astype(float) / 255
    # ink lines from luminance edges
    lum = np.asarray(im.convert('L')).astype(float) / 255
    gx = np.abs(np.roll(lum, -1, 1) - np.roll(lum, 1, 1)); gy = np.abs(np.roll(lum, -1, 0) - np.roll(lum, 1, 0))
    edge = ((gx + gy) > 0.16).astype(np.uint8) * 255
    edge = np.asarray(Image.fromarray(edge).filter(ImageFilter.MaxFilter(3))) > 0
    # halftone dots in the shadows
    h, w = lum.shape
    jj, ii = np.mgrid[0:h, 0:w]
    cell = 7
    cx = (ii % cell) - cell / 2 + 0.5; cy = (jj % cell) - cell / 2 + 0.5
    dark = np.clip((0.35 - v) / 0.35, 0, 1)
    dots = np.hypot(cx, cy) < dark * cell * 0.55
    out = flat.copy()
    out[dots] *= 0.45
    out[edge] = np.array([0.05, 0.03, 0.09])
    rng = np.random.default_rng(5)
    tex = Image.fromarray((rng.random((h // 2, w // 2)) * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
    out = out * (0.94 + 0.06 * np.asarray(tex)[..., None] / 255)
    return np.clip(out, 0, 1)

def label(im, s):
    im = im.convert('RGB'); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, len(s) * 13 + 22, 34], fill=(10, 8, 18))
    big = Image.new('RGBA', (len(s) * 4 + 4, 9), (0, 0, 0, 0))
    text(big, s, 1, 1, (255, 240, 250, 255), shadow=False)
    im.paste(big.resize((big.width * 3, big.height * 3), Image.NEAREST), (10, 6), big.resize((big.width * 3, big.height * 3), Image.NEAREST))
    return im

if __name__ == '__main__':
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    raw = build_frame(t=0.15)
    big = np.asarray(Image.fromarray((np.clip(raw / 6, 0, 1) * 255).astype(np.uint8)).resize((OW, OH), Image.BICUBIC)).astype(float) / 255 * 6
    big = composite_fire(big, 0.15, 300, 668)
    np.save(f'{out}/_hdr.npy', big.astype(np.float32))
    cgi = post(big)
    Image.fromarray((cgi * 255).astype(np.uint8)).save(f'{out}/style_C_cgi.png')
    pix_big, pix_small = to_pixel(post(big, grain=False))
    pix_big.save(f'{out}/style_A_hd_pixel.png'); pix_small.save(f'{out}/style_A_hd_pixel_1x.png')
    cm = comic(post(big, grain=False))
    Image.fromarray((cm * 255).astype(np.uint8)).save(f'{out}/style_B_comic.png')
    print('done')
