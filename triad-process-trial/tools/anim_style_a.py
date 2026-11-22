"""Style A in motion: NULL MONARCH charges and fires its laser at the fire spirit.

3D render -> post -> pixelise with a palette LOCKED from frame 0 (no colour flicker between frames).
Usage: python3 tools/anim_style_a.py OUT_DIR   -> style_A_laser.gif / .mp4
"""
import math, os, random, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import styles as S

def pixelise(img, pal, w=640, h=360):
    small = np.asarray(Image.fromarray((img * 255).astype(np.uint8)).resize((w, h), Image.BOX)).astype(float)
    jj, ii = np.mgrid[0:h, 0:w]
    small = small + S.BAYER[jj % 4, ii % 4][..., None] * 22
    q = np.empty((h, w, 3), np.uint8)
    for r0 in range(0, h, 60):
        d = ((small[r0:r0 + 60, :, None, :] - pal[None, None]) ** 2).sum(-1)
        q[r0:r0 + 60] = pal[np.argmin(d, axis=-1)].astype(np.uint8)
    return Image.fromarray(q)

def lock_palette(img, colors=36):
    small = Image.fromarray((img * 255).astype(np.uint8)).resize((640, 360), Image.BOX)
    p = small.quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    pal = np.array(p.getpalette()[:colors * 3]).reshape(-1, 3).astype(float)
    return np.vstack([pal, S.ACCENTS])

def beam_layer(p0, p1, strength):
    lay = Image.new('L', (S.OW, S.OH), 0); d = ImageDraw.Draw(lay)
    d.line([p0, p1], fill=255, width=18)
    soft = np.asarray(lay.filter(ImageFilter.GaussianBlur(10))).astype(float) / 255
    core = Image.new('L', (S.OW, S.OH), 0); ImageDraw.Draw(core).line([p0, p1], fill=255, width=5)
    core = np.asarray(core.filter(ImageFilter.GaussianBlur(1.2))).astype(float) / 255
    return (soft[..., None] * np.array([1.0, 0.15, 0.6]) * 2.5 + core[..., None] * np.array([1.2, 1.1, 1.3]) * 6) * strength

def schedule(n=48):
    out = []
    for f in range(n):
        if f < 14:   a = dict(charge=0.0)
        elif f < 26: a = dict(charge=(f - 14) / 11)                       # visor + core charge
        elif f < 31: a = dict(charge=1.0, beam=1.0 - 0.12 * (f - 26))     # fire
        elif f < 37: a = dict(charge=0.4 * (37 - f) / 6, hit=f - 31)      # spirit hit
        else:        a = dict(charge=0.0)
        out.append(a)
    return out

if __name__ == '__main__':
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    tmp = f'{out}/_a'; os.makedirs(tmp, exist_ok=True)
    pal = None
    visor = np.array([[0.0, 89.5, 12.0]])
    for f, a in enumerate(schedule()):
        t = f / 12
        raw = S.build_frame(t=t, charge=a['charge'])
        big = np.asarray(Image.fromarray((np.clip(raw / 6, 0, 1) * 255).astype(np.uint8)).resize((S.OW, S.OH), Image.BICUBIC)).astype(float) / 255 * 6
        fx, fy = 300, 668
        hit = a.get('hit')
        if hit is not None and hit < 2:
            fx += random.Random(f).choice([-6, 6])
        big = S.composite_fire(big, t, fx, fy)
        if hit is not None and hit < 2:  # white-hot flash on the spirit
            jj, ii = np.mgrid[0:S.OH, 0:S.OW]
            m = np.exp(-(((ii - fx) / 60.0) ** 2 + ((jj - (fy - 90)) / 110.0) ** 2))
            big += m[..., None] * np.array([1.6, 1.4, 1.5]) * (2 - hit)
        if a.get('beam'):
            u, v = S.project(visor)
            p0 = (float(u[0]) * S.OW / S.W, float(v[0]) * S.OH / S.H)
            big += beam_layer(p0, (fx, fy - 90), a['beam'])
        img = S.post(big, rain_seed=1 + f % 3, grain=False)
        if hit is not None and hit < 3:  # camera shake
            img = np.roll(img, random.Random(f).choice([-8, -4, 4, 8]), axis=1)
        if pal is None: pal = lock_palette(img)
        px = pixelise(img, pal)
        px.resize((1280, 720), Image.NEAREST).save(f'{tmp}/{f:04d}.png')
        print('frame', f, flush=True)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', '12', '-i', f'{tmp}/%04d.png',
                    '-vf', 'scale=1920:1080:flags=neighbor', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '16',
                    '-r', '24', f'{out}/style_A_laser.mp4'], check=True)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', '12', '-i', f'{tmp}/%04d.png',
                    '-vf', 'split[a][b];[a]palettegen=max_colors=64:stats_mode=full[p];[b][p]paletteuse=dither=none',
                    f'{out}/style_A_laser.gif'], check=True)
    for f_ in os.listdir(tmp): os.remove(f'{tmp}/{f_}')
    os.rmdir(tmp)
