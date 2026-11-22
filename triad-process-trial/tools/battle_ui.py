"""Battle-screen building blocks (background, pixel font, cards, piles, HP bars) + a one-turn mockup.

Usage: python3 tools/battle_ui.py OUT_DIR  -> battle.gif, battle_still.png
"""
import math, random, sys
from PIL import Image, ImageDraw
import aura3 as A

SW, SH = 640, 360
TAU = 2 * math.pi
INK = (16, 10, 26, 255)
UI_BG = (34, 28, 50, 255)
UI_HI = (70, 60, 96, 255)
TXT = (230, 224, 240, 255)
DIM = (140, 130, 165, 255)
RED = (214, 60, 70, 255)

# ------------------------------------------------------------------ 3x5 pixel font
F = {
 'A': '.#.#.#####.##.#',
 'B': '##.#.###.#.###.',
 'C': '.###..#..#...##',
 'D': '##.#.##.##.###.',
 'E': '####..##.#..###',
 'F': '####..##.#..#..',
 'G': '.###..#.##.#.##',
 'H': '#.##.#####.##.#',
 'I': '###.#..#..#.###',
 'J': '..#..#..##.#.#.',
 'K': '#.##.###.#.##.#',
 'L': '#..#..#..#..###',
 'M': '#.########.##.#',
 'N': '##.#.##.##.##.#',
 'O': '.#.#.##.##.#.#.',
 'P': '##.#.###.#..#..',
 'R': '##.#.###.#.##.#',
 'S': '.###...#...###.',
 'T': '###.#..#..#..#.',
 'U': '#.##.##.##.####',
 'V': '#.##.##.##.#.#.',
 'W': '#.##.########.#',
 'Y': '#.##.#.#..#..#.',
 'Z': '###..#.#.#..###',
 '0': '####.##.##.####',
 '1': '.#.##..#..#.###',
 '2': '##...#.#.#..###',
 '3': '##...#.#...###.',
 '4': '#.##.####..#..#',
 '5': '####..##...###.',
 '6': '.###..####.####',
 '7': '###..#.#..#..#.',
 '8': '####.#####.####',
 '9': '####.####..###.',
 '/': '..#..#.#.#..#..',
 '-': '......###......',
 '+': '....#.###.#....',
 'X': '#.##.#.#.#.##.#',
 'Q': '.#.#.##.##.#..#',
 ' ': '...............',
 ':': '....#.....#....',
}

def text(im, s, x, y, col=TXT, sc=1, shadow=True):
    px = im.load()
    for pass_ in ((1, INK), (0, col)) if shadow else ((0, col),):
        off, c = pass_
        cx = x
        for ch in s.upper():
            g = F.get(ch, F[' '])
            for i, b in enumerate(g):
                if b == '#':
                    gx, gy = i % 3, i // 3
                    for ax in range(sc):
                        for ay in range(sc):
                            X, Y = cx + gx * sc + ax + off, y + gy * sc + ay + off
                            if 0 <= X < SW and 0 <= Y < SH: px[X, Y] = c
            cx += 4 * sc
    return cx

def text_w(s, sc=1): return len(s) * 4 * sc - sc

# ------------------------------------------------------------------ background (static)
def background():
    im = Image.new('RGBA', (SW, SH)); d = ImageDraw.Draw(im)
    HZ = 150
    sky = [(18, 14, 34), (26, 19, 46), (38, 26, 60), (56, 34, 74), (84, 46, 86)]
    for y in range(HZ):
        k = min(len(sky) - 1, int((y / HZ) ** 1.6 * len(sky)))
        d.line([(0, y), (SW, y)], fill=sky[k])
    r = random.Random(3)
    for _ in range(70):
        x, y = r.randrange(SW), r.randrange(int(HZ * 0.7))
        im.putpixel((x, y), (200, 190, 230) if r.random() < .3 else (110, 100, 150))
    # big pale moon
    for y in range(-14, 15):
        for x in range(-14, 15):
            if x * x + y * y <= 196:
                c = (232, 214, 196) if (x + 4) ** 2 + (y - 3) ** 2 > 120 else (205, 186, 176)
                im.putpixel((520 + x, 44 + y), c)
    # mountain layers
    for layer, (base, amp, col, seed) in enumerate([(HZ - 30, 26, (44, 30, 66), 5), (HZ - 12, 16, (32, 22, 50), 9)]):
        rr = random.Random(seed); phs = [rr.uniform(0, TAU) for _ in range(4)]
        for x in range(SW):
            h = base - amp * (0.5 * math.sin(x * 0.011 + phs[0]) + 0.3 * math.sin(x * 0.029 + phs[1]) + 0.2 * math.sin(x * 0.07 + phs[2]))
            d.line([(x, int(h)), (x, HZ)], fill=col)
    # ground
    gcols = [(44, 34, 62), (38, 29, 54), (32, 25, 46), (27, 21, 40), (22, 17, 33)]
    for y in range(HZ, SH):
        k = min(len(gcols) - 1, int((y - HZ) / (SH - HZ) * len(gcols)))
        d.line([(0, y), (SW, y)], fill=gcols[k])
    d.line([(0, HZ), (SW, HZ)], fill=(120, 70, 110))
    VP = (320, HZ)
    for i in range(-14, 15):
        d.line([VP, (320 + i * 70, SH)], fill=(50, 40, 72))
    z = 1.0
    while True:
        y = HZ + int(18 / z * 1.0 * 6) if False else int(HZ + 210 / (z * 1.0) * 0 + (SH - HZ) / z)
        if y <= HZ + 3: break
        d.line([(0, y), (SW, y)], fill=(50, 40, 72)); z *= 1.45
    for _ in range(140):  # ground speckle
        x, y = r.randrange(SW), r.randrange(HZ + 4, SH)
        im.putpixel((x, y), (56, 44, 78))
    return im

def platform(im, cx, cy, rx, ry, col_top, col_rim):
    px = im.load()
    for y in range(cy - ry - 1, cy + ry + 3):
        for x in range(cx - rx - 1, cx + rx + 2):
            e = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
            e2 = ((x - cx) / rx) ** 2 + ((y - cy - 2) / ry) ** 2
            if e <= 1: px[x, y] = col_top if e < 0.82 else col_rim
            elif e2 <= 1: px[x, y] = INK

# ------------------------------------------------------------------ UI pieces
def panel(im, x0, y0, x1, y1, fill=UI_BG):
    d = ImageDraw.Draw(im)
    d.rectangle([x0, y0, x1, y1], fill=INK)
    d.rectangle([x0 + 1, y0 + 1, x1 - 1, y1 - 1], fill=fill)
    d.line([(x0 + 2, y0 + 1), (x1 - 2, y0 + 1)], fill=UI_HI)

def hp_bar(im, x, y, w, hp, mx, label=True):
    d = ImageDraw.Draw(im)
    d.rectangle([x, y, x + w, y + 6], fill=INK)
    d.rectangle([x + 1, y + 1, x + w - 1, y + 5], fill=(60, 24, 36))
    fw = int((w - 2) * hp / mx)
    if fw > 0:
        d.rectangle([x + 1, y + 1, x + fw, y + 5], fill=RED)
        d.line([(x + 1, y + 1), (x + fw, y + 1)], fill=(240, 120, 120))
    if label:
        s = f'{hp}/{mx}'
        text(im, s, x + w // 2 - text_w(s) // 2, y + 1, TXT)

def piles_ui(im, piles, x0, y0):
    panel(im, x0, y0, x0 + 92, y0 + 86)
    text(im, 'PILES', x0 + 5, y0 + 5, DIM)
    for c, pile in enumerate(piles):
        cx = x0 + 6 + c * 17
        ImageDraw.Draw(im).rectangle([cx - 1, y0 + 14, cx + 13, y0 + 80], fill=(26, 21, 40))
        for k in range(5):  # empty slots
            sy = y0 + 68 - k * 13
            ImageDraw.Draw(im).rectangle([cx + 3, sy + 4, cx + 9, sy + 8], outline=(48, 40, 68))
        for k, el in enumerate(pile):
            sy = y0 + 68 - k * 13
            im.alpha_composite(A.ORB[(el, 9)], (cx + 1, sy + 1))
        text(im, str(len(pile)), cx + 5, y0 + 81 - 0, DIM, shadow=False) if False else None

CARDS = [('EMBER', 'fire', 1, ['fire']), ('STOKE', 'fire', 0, []), ('BLAZE', 'fire', 2, ['fire', 'fire']),
         ('TIDE', 'water', 1, ['water']), ('SHIFT', 'wind', 1, ['wind'])]

def card(im, x, y, name, el, cost, orbs, hi=False):
    pal = A.PAL[el]
    d = ImageDraw.Draw(im)
    w, h = 46, 62
    d.rectangle([x, y, x + w - 1, y + h - 1], fill=INK)
    d.rectangle([x + 1, y + 1, x + w - 2, y + h - 2], fill=pal[1] if not hi else pal[2])
    d.rectangle([x + 3, y + 3, x + w - 4, y + h - 4], fill=(40, 33, 58))
    d.rectangle([x + 3, y + 3, x + w - 4, y + 11], fill=pal[0])
    text(im, name, x + w // 2 - text_w(name) // 2 + 2, y + 5, TXT)
    # art window with the orbs this card spends
    d.rectangle([x + 5, y + 14, x + w - 6, y + 36], fill=(24, 19, 36))
    if orbs:
        tw = len(orbs) * 12 - 1
        for i, oe in enumerate(orbs):
            im.alpha_composite(A.ORB[(oe, 9)], (x + w // 2 - tw // 2 + i * 12, y + 20))
    else:
        for i in range(3):
            d.point((x + 15 + i * 8, y + 25), fill=pal[3])
    for i, ww in enumerate([30, 34, 22]):  # fake rules text
        d.line([(x + 7, y + 42 + i * 5), (x + 7 + ww, y + 42 + i * 5)], fill=(110, 100, 140))
    # cost gem
    for yy in range(-5, 6):
        for xx in range(-5, 6):
            if xx * xx + yy * yy <= 25:
                im.putpixel((x + 2 + xx, y + 2 + yy), INK if xx * xx + yy * yy > 16 else (250, 196, 70))
    text(im, str(cost), x + 1, y, INK, shadow=False)

def energy(im, cx, cy, e, mx):
    for yy in range(-13, 14):
        for xx in range(-13, 14):
            r2 = xx * xx + yy * yy
            if r2 <= 169:
                c = INK if r2 > 144 else (250, 196, 70) if r2 > 100 else (220, 120, 40) if (xx + yy) > 4 else (250, 170, 60)
                im.putpixel((cx + xx, cy + yy), c)
    s = f'{e}/{mx}'
    text(im, s, cx - text_w(s) // 2, cy - 2, TXT)

def intent(im, cx, cy, dmg):
    # little sword icon + damage number
    pts = [(0, 0), (1, 1), (2, 2), (3, 3), (4, 4), (5, 5)]
    px = im.load()
    for x, y in pts:
        for dx, dy in ((0, 0), (1, 0), (0, 1)):
            px[cx + x + dx, cy + y + dy] = (230, 230, 240)
    for k in range(-2, 3):
        px[cx + 4 + k, cy + 6 - k] = (200, 150, 80)
    px[cx + 6, cy + 6] = (200, 150, 80); px[cx + 7, cy + 7] = (200, 150, 80)
    text(im, str(dmg), cx + 10, cy + 2, TXT)

def paste_sprite(scene, spr, ax, ay, SC):
    Wc, Hc = spr.size
    Gy = Hc - 3 * SC
    scene.alpha_composite(spr, (int(round(ax - Wc / 2)), int(round(ay - Gy))))

# ------------------------------------------------------------------ scene + timeline
PLAYER = dict(el='fire', SC=1.6, ax=196, ay=304)
ENEMY = dict(el='dark', SC=1.05, ax=446, ay=196)

def build(out, scale=2):
    bg = background()
    platform(bg, ENEMY['ax'], ENEMY['ay'] + 1, 52, 10, (66, 52, 88), (90, 74, 116))
    platform(bg, PLAYER['ax'], PLAYER['ay'] + 2, 78, 15, (62, 48, 84), (86, 70, 112))
    Np, Ne = A.noises(PLAYER['el']), A.noises(ENEMY['el'])
    piles0 = [['fire', 'fire', 'water'], ['fire', 'fire'], ['fire', 'fire', 'fire', 'light'], ['fire'], ['fire', 'wind', 'wind']]
    piles1 = [['fire', 'fire', 'water'], ['fire', 'fire'], ['fire', 'fire'], ['fire'], ['fire', 'wind', 'wind']]  # BLAZE spends 2 fire... from pile 3 top? (illustrative)
    piles1[2] = ['fire', 'fire']
    seq = []
    patk, ehit, eatk, phit = A.tl_attack('back'), A.tl_hit(), A.tl_attack('front'), A.tl_hit()
    T = 64
    frames = []
    for f in range(T):
        t = f / 12
        pa, ea = {}, {}
        hand = list(range(5)); raise_ = [0] * 5; played = False
        piles = piles0; ehp, php = 34, 48; e_cur = 3
        proj = None; dmg = None
        if 12 <= f < 16: raise_[2] = (f - 11) * 3
        if f >= 16:
            hand = [0, 1, 3, 4]; piles = piles1; e_cur = 1
        if 16 <= f < 26: pa = dict(patk[f - 16])
        if 20 <= f < 26:
            u = (f - 20) / 5
            proj = ('fire', u, (PLAYER['ax'], PLAYER['ay'] - 50), (ENEMY['ax'], ENEMY['ay'] - 30))
        if 26 <= f < 32: ea = dict(ehit[f - 26])
        if f >= 26: ehp = 22
        if 26 <= f < 36: dmg = ('-12', ENEMY['ax'] + 24, ENEMY['ay'] - 60 - (f - 26) * 2)
        if 38 <= f < 48: ea = dict(eatk[f - 38])
        if 42 <= f < 48:
            u = (f - 42) / 5
            proj = ('dark', u, (ENEMY['ax'], ENEMY['ay'] - 30), (PLAYER['ax'] + 6, PLAYER['ay'] - 50))
        if 48 <= f < 54: pa = dict(phit[f - 48])
        if f >= 48: php = 39
        if 48 <= f < 58: dmg = ('-9', PLAYER['ax'] + 40, PLAYER['ay'] - 96 - (f - 48) * 2)
        tops = [p[-1] for p in piles]
        pa['orbs'] = tops
        ea['orbs'] = ['dark'] * 5

        sc = bg.copy()
        espr = A.render(ENEMY['el'], t, ENEMY['SC'], 'front', ea, Ne)
        paste_sprite(sc, espr, ENEMY['ax'], ENEMY['ay'], ENEMY['SC'])
        # projectile (drawn between enemy and player for depth)
        if proj:
            pel, u, (x0, y0), (x1, y1) = proj
            for k in range(6):
                uu = max(0, u - k * 0.05)
                x = x0 + (x1 - x0) * uu; y = y0 + (y1 - y0) * uu - 30 * math.sin(math.pi * uu)
                spr = A.ORB[(pel, 9 if (pel == 'fire') == (uu < 0.5) else 7)] if k == 0 else None
                if spr: sc.alpha_composite(spr, (int(x) - spr.width // 2, int(y) - spr.height // 2))
                else:
                    c = A.PAL[pel][4 - min(k, 3)]
                    sc.putpixel((int(x), int(y)), c); sc.putpixel((int(x) + 1, int(y)), c)
        pspr = A.render(PLAYER['el'], t, PLAYER['SC'], 'back', pa, Np)
        paste_sprite(sc, pspr, PLAYER['ax'], PLAYER['ay'], PLAYER['SC'])

        # --- UI
        hp_bar(sc, ENEMY['ax'] - 36, ENEMY['ay'] + 14, 72, ehp, 50)
        text(sc, 'HOLLOW', ENEMY['ax'] - text_w('HOLLOW') // 2, ENEMY['ay'] + 23, DIM)
        if f < 38: intent(sc, ENEMY['ax'] - 8, ENEMY['ay'] - 82, 9)
        panel(sc, 8, 8, 150, 26)
        text(sc, 'EMBERLING', 14, 12, TXT)
        hp_bar(sc, 14, 18, 130, php, 60)
        text(sc, 'FLOOR 3', SW - 8 - text_w('FLOOR 3'), 10, DIM)
        piles_ui(sc, piles, 8, 262)
        energy(sc, 262, 326, e_cur, 3)
        xs = 286
        for i in hand:
            name, el, cost, orbs = CARDS[i]
            card(sc, xs, 294 - raise_[i], name, el, cost, orbs, hi=raise_[i] > 0)
            xs += 50
        panel(sc, 548, 322, 630, 346, fill=(80, 46, 40, 255) if f < 38 else UI_BG)
        text(sc, 'END TURN', 589 - text_w('END TURN') // 2, 332, TXT)
        text(sc, 'DRAW 7', 556, 304, DIM); text(sc, 'DISCARD 2', 556, 312, DIM)
        if dmg:
            s, x, y = dmg
            text(sc, s, x, y, (255, 240, 200), sc=2)
        frames.append(sc)

    frames[0].resize((SW * scale, SH * scale), Image.NEAREST).save(f'{out}/battle_still.png')
    frames[22].resize((SW * scale, SH * scale), Image.NEAREST).save(f'{out}/battle_attack.png')
    gif = [fr.resize((SW * scale, SH * scale), Image.NEAREST).convert('P', palette=Image.ADAPTIVE, colors=255) for fr in frames]
    gif[0].save(f'{out}/battle.gif', save_all=True, append_images=gif[1:], duration=100, loop=0, disposal=2)

if __name__ == '__main__':
    build(sys.argv[1])
