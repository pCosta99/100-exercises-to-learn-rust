"""Full-exchange battle showcase: two player turns, one enemy turn, a finishing blow.

Usage: python3 tools/fight.py OUT_DIR   -> OUT_DIR/fight.gif, fight.mp4, fight_poster.png
"""
import math, random, subprocess, sys, os
from PIL import Image, ImageChops, ImageDraw
import aura3 as A
from battle_ui import (SW, SH, INK, UI_BG, TXT, DIM, text, text_w, background, platform, panel,
                    hp_bar, piles_ui, card, energy, intent, paste_sprite, PLAYER, ENEMY)

TAU = 2 * math.pi
CARDS = {
    'EMBER': ('fire', 1, ['fire'], 7),
    'BLAZE': ('fire', 2, ['fire', 'fire'], 12),
    'STOKE': ('fire', 0, [], 0),        # gain 2 fire orbs, next fire attack +5
    'TIDE':  ('water', 1, ['water'], 5),
    'SHIFT': ('wind', 1, ['wind'], 0),
}
SLOT_X = lambda i, n: 336 - (n * 50) // 2 + 60 + i * 50
HAND_Y = 294

class Fx:
    def __init__(self, kind, life, **kw):
        self.kind, self.life, self.age = kind, life, 0
        self.__dict__.update(kw)

class Battle:
    def __init__(self):
        self.bg = background()
        platform(self.bg, ENEMY['ax'], ENEMY['ay'] + 1, 52, 10, (66, 52, 88), (90, 74, 116))
        platform(self.bg, PLAYER['ax'], PLAYER['ay'] + 2, 78, 15, (62, 48, 84), (86, 70, 112))
        self.Np, self.Ne = A.noises(PLAYER['el']), A.noises(ENEMY['el'])
        self.f = 0
        self.piles = [['fire', 'fire', 'water'], ['fire', 'fire'], ['fire', 'light'], ['fire'], ['fire', 'wind', 'wind']]
        self.hand = ['EMBER', 'BLAZE', 'TIDE', 'SHIFT']
        self.hx = {}            # card -> current x (for sliding)
        self.hy = {}            # card -> current y
        self.php, self.ehp, self.en = 48, 34, 3
        self.pq, self.eq = [], []   # per-frame action queues
        self.fx = []
        self.banner = None
        self.shake = 0
        self.enemy_dead = False
        self.intent = 9
        self.end_btn = 0
        self.frames = []
        self.bonus = 0
        self.tx, self.ty = ENEMY['ax'], ENEMY['ay'] - 32   # where player attacks land
        self.dmg_xy = (ENEMY['ax'] + 26, ENEMY['ay'] - 70)
        self.lift = None

    # ---------------------------------------------------------- helpers
    def slot_center(self, c, k):
        x0, y0 = 8, 262
        return x0 + 6 + c * 17 + 6, y0 + 68 - k * 13 + 6

    def spend(self, orbs):
        for el in orbs:
            for c in reversed(range(5)):
                if self.piles[c] and self.piles[c][-1] == el:
                    cx, cy = self.slot_center(c, len(self.piles[c]) - 1)
                    self.fx.append(Fx('pop', 6, x=cx, y=cy, el=el))
                    self.piles[c].pop(); break

    def gain(self, el, n):
        for _ in range(n):
            c = min(range(5), key=lambda i: len(self.piles[i]))
            self.piles[c].append(el)
            cx, cy = self.slot_center(c, len(self.piles[c]) - 1)
            self.fx.append(Fx('pop', 8, x=cx, y=cy, el=el))

    def run(self, n):
        for _ in range(n):
            self.render(); self.f += 1

    # ---------------------------------------------------------- beats
    def show_banner(self, s, n=16):
        self.banner = [s, 0]
        self.run(n)
        self.banner = None

    def deal(self, cards):
        for c in cards:
            self.hand.append(c)
            self.hy[c] = SH + 10
        self.run(8)

    def play(self, name):
        el, cost, orbs, dmg = CARDS[name]
        dmg += self.bonus if dmg else 0
        if dmg: self.bonus = 0
        # lift
        self.lift = name
        self.run(4)
        # card flies to centre and bursts
        i = self.hand.index(name)
        sx, sy = self.hx[name], self.hy[name]
        self.hand.remove(name); self.lift = None
        self.fx.append(Fx('flycard', 6, name=name, x0=sx, y0=sy, x1=SW // 2 - 23, y1=150))
        self.en -= cost
        self.spend(orbs)
        if name == 'STOKE':
            self.run(6)
            self.gain('fire', 2); self.bonus = 5
            self.pq += [{'g': 1.6, 'burst': u / 5} for u in range(6)]
            self.run(14)
            return
        self.run(3)
        # attack
        self.pq += A.tl_attack('back')
        self.run(4)
        big = dmg >= 12
        flight = 8
        self.fx.append(Fx('proj', flight, el=el, r=6 if big else 4,
                          p0=(PLAYER['ax'], PLAYER['ay'] - 56), p1=(self.tx, self.ty), arc=34))
        self.run(flight)
        self.hit_enemy(el, dmg, big)

    def hit_enemy(self, el, dmg, big):
        self.fx.append(Fx('impact', 9, el=el, x=self.tx, y=self.ty, big=big))
        self.fx.append(Fx('dmg', 16, s=f'-{dmg}', x=self.dmg_xy[0], y=self.dmg_xy[1]))
        self.shake = 5 if big else 3
        self.ehp = max(0, self.ehp - dmg)
        if self.ehp == 0:
            self.enemy_dead = True
            self.eq = self.enemy_death_tl()
            self.run(len(self.eq) + 2)
        else:
            self.eq = self.enemy_hit_tl()
            self.run(10)

    def enemy_hit_tl(self): return A.tl_hit()
    def enemy_death_tl(self): return A.tl_death()

    def enemy_turn(self):
        self.show_banner('ENEMY TURN', 14)
        self.eq += A.tl_attack('front')
        self.run(5)
        self.fx.append(Fx('proj', 8, el='dark', r=5, p0=(ENEMY['ax'], ENEMY['ay'] - 32),
                          p1=(PLAYER['ax'] + 4, PLAYER['ay'] - 58), arc=26))
        self.run(8)
        self.fx.append(Fx('impact', 9, el='dark', x=PLAYER['ax'] + 4, y=PLAYER['ay'] - 58, big=True))
        self.fx.append(Fx('dmg', 16, s=f'-{self.intent}', x=PLAYER['ax'] + 44, y=PLAYER['ay'] - 100))
        self.php -= self.intent
        self.shake = 5
        self.pq = A.tl_hit()
        self.run(12)
        self.intent = 11

    # ---------------------------------------------------------- drawing
    def draw_fx(self, sc, layer):
        px = sc.load()
        def put(x, y, c):
            x, y = int(round(x)), int(round(y))
            if 0 <= x < SW and 0 <= y < SH: px[x, y] = c
        for e in self.fx:
            u = e.age / max(1, e.life - 1)
            pal = A.PAL.get(getattr(e, 'el', 'fire'))
            if e.kind == 'proj' and layer == 'world':
                (x0, y0), (x1, y1) = e.p0, e.p1
                pos = lambda uu: (x0 + (x1 - x0) * uu, y0 + (y1 - y0) * uu - e.arc * math.sin(math.pi * uu))
                for k in range(10, 0, -1):  # trail
                    uu = u - k * 0.035
                    if uu < 0: continue
                    x, y = pos(uu)
                    c = pal[3] if k < 3 else pal[2] if k < 6 else pal[1]
                    rr = max(0, e.r - 1 - k // 2)
                    for dy in range(-rr, rr + 1):
                        for dx in range(-rr, rr + 1):
                            if dx * dx + dy * dy <= rr * rr: put(x + dx, y + dy, c)
                x, y = pos(u)
                r = e.r - (1 if u > 0.6 and e.p1[1] < e.p0[1] else 0)  # shrinks with distance
                for dy in range(-r - 1, r + 2):
                    for dx in range(-r - 1, r + 2):
                        d = math.hypot(dx, dy)
                        if d <= r + 0.5:
                            if e.el == 'dark':
                                c = pal[0] if d < r * 0.5 else pal[3] if d < r * 0.85 else pal[4]
                            else:
                                c = pal[4] if d < r * 0.45 else pal[3] if d < r * 0.75 else pal[2] if d < r else pal[0]
                            put(x + dx, y + dy, c)
            elif e.kind == 'impact' and layer == 'world':
                rad = 3 + e.age * (4 if e.big else 3)
                if e.age < 4:
                    for a in range(0, 360, 6):
                        put(e.x + math.cos(math.radians(a)) * rad, e.y + math.sin(math.radians(a)) * rad * 0.8,
                            pal[4] if e.age < 2 else pal[3])
                rnd = random.Random(e.x)
                for i in range(18 if e.big else 12):
                    a = rnd.uniform(0, TAU); sp = rnd.uniform(2, 4.5)
                    x, y = e.x + math.cos(a) * sp * e.age * 1.4, e.y + math.sin(a) * sp * e.age - 0.25 * e.age ** 2 * -1
                    c = pal[4] if u < .3 else pal[3] if u < .6 else pal[1]
                    put(x, y, c); put(x + 1, y, c)
            elif e.kind == 'dmg' and layer == 'ui':
                text(sc, e.s, e.x, int(e.y - e.age * 1.6), (255, 236, 190) if e.age < 12 else (190, 170, 150), sc=2)
            elif e.kind == 'pop' and layer == 'ui':
                rr = 5 + e.age
                for a in range(0, 360, 20):
                    put(e.x + math.cos(math.radians(a)) * rr, e.y + math.sin(math.radians(a)) * rr, pal[4] if e.age < 4 else pal[2])
            elif e.kind == 'flycard' and layer == 'ui':
                k = min(1.0, u * 1.4)
                ease = 1 - (1 - k) ** 3
                x = e.x0 + (e.x1 - e.x0) * ease; y = e.y0 + (e.y1 - e.y0) * ease
                if e.age < e.life - 2:
                    el, cost, orbs, _ = CARDS[e.name]
                    card(sc, int(x), int(y), e.name, el, cost, orbs, hi=True)
                else:  # burst into sparkles
                    pal = A.PAL[CARDS[e.name][0]]
                    rnd = random.Random(3)
                    for i in range(24):
                        put(x + 23 + rnd.uniform(-30, 30), y + 31 + rnd.uniform(-36, 36), pal[rnd.choice([2, 3, 4])])

    def render(self):
        t = self.f / 12
        pa = self.pq.pop(0) if self.pq else {}
        ea = self.eq.pop(0) if self.eq else ({'dissolve': 1.3} if self.enemy_dead else {})
        pa = dict(pa); ea = dict(ea)
        pa['orbs'] = [p[-1] for p in self.piles if p]
        if not self.enemy_dead: ea['orbs'] = ['dark'] * 5

        world = self.bg.copy()
        paste_sprite(world, A.render(ENEMY['el'], t, ENEMY['SC'], 'front', ea, self.Ne), ENEMY['ax'], ENEMY['ay'], ENEMY['SC'])
        self.draw_fx(world, 'world')
        paste_sprite(world, A.render(PLAYER['el'], t, PLAYER['SC'], 'back', pa, self.Np), PLAYER['ax'], PLAYER['ay'], PLAYER['SC'])
        if self.shake:
            r = random.Random(self.f)
            world = ImageChops.offset(world, r.choice([-2, -1, 1, 2]), r.choice([-1, 1]))
            self.shake -= 1
        sc = world

        # UI
        if not self.enemy_dead:
            hp_bar(sc, ENEMY['ax'] - 36, ENEMY['ay'] + 14, 72, self.ehp, 50)
            text(sc, 'HOLLOW', ENEMY['ax'] - text_w('HOLLOW') // 2, ENEMY['ay'] + 23, DIM)
            if not self.eq: intent(sc, ENEMY['ax'] - 8, ENEMY['ay'] - 82, self.intent)
        panel(sc, 8, 8, 150, 26)
        text(sc, 'EMBERLING', 14, 12, TXT)
        hp_bar(sc, 14, 18, 130, self.php, 60)
        text(sc, 'FLOOR 3', SW - 8 - text_w('FLOOR 3'), 10, DIM)
        piles_ui(sc, self.piles, 8, 262)
        energy(sc, 262, 326, self.en, 3)
        n = len(self.hand)
        for i, name in enumerate(self.hand):
            tx = SLOT_X(i, n); ty = HAND_Y - (10 if getattr(self, 'lift', None) == name else 0)
            cx = self.hx.get(name, tx); cy = self.hy.get(name, ty)
            cx += (tx - cx) * 0.45; cy += (ty - cy) * 0.45
            self.hx[name], self.hy[name] = cx, cy
            el, cost, orbs, _ = CARDS[name]
            card(sc, int(round(cx)), int(round(cy)), name, el, cost, orbs, hi=(getattr(self, 'lift', None) == name))
        btn = (120, 64, 48, 255) if self.end_btn else (80, 46, 40, 255)
        panel(sc, 548, 322, 630, 346, fill=btn)
        text(sc, 'END TURN', 589 - text_w('END TURN') // 2, 332, TXT)
        text(sc, f'DRAW {7 - 0}', 556, 304, DIM); text(sc, 'DISCARD 2', 556, 312, DIM)
        self.draw_fx(sc, 'ui')
        if self.banner:
            s, k = self.banner
            band = Image.new('RGBA', (SW, 34), (12, 8, 22, 190))
            sc.alpha_composite(band, (0, 62))
            w = text_w(s, 3)
            slide = max(0, 6 - k) * 30
            text(sc, s, SW // 2 - w // 2 + slide, 71, (250, 236, 210), sc=3)
            self.banner[1] += 1
        if self.end_btn: self.end_btn -= 1
        for e in self.fx: e.age += 1
        self.fx = [e for e in self.fx if e.age < e.life]
        self.frames.append(sc)

def script(b):
    b.run(6)
    b.show_banner('YOUR TURN')
    b.run(4)
    b.play('EMBER'); b.run(3)
    b.play('BLAZE'); b.run(6)
    b.end_btn = 4; b.run(4)
    b.enemy_turn()
    b.show_banner('YOUR TURN')
    b.en = 3; b.deal(['STOKE', 'BLAZE']); b.run(3)
    b.play('STOKE'); b.run(2)
    b.play('BLAZE')
    b.run(4)
    b.show_banner('VICTORY', 26)
    b.run(6)

if __name__ == '__main__':
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    b = Battle(); script(b)
    fr = b.frames
    print(len(fr), 'frames')
    S = 2
    fr[0].resize((SW * S, SH * S), Image.NEAREST).save(f'{out}/fight_poster.png')
    # MP4 (sharp pixels: nearest-neighbour upscale x3 to 1920x1080)
    tmp = f'{out}/_frames'; os.makedirs(tmp, exist_ok=True)
    for i, im in enumerate(fr):
        im.convert('RGB').save(f'{tmp}/{i:04d}.png')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', '10', '-i', f'{tmp}/%04d.png',
                    '-vf', 'scale=1920:1080:flags=neighbor', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                    '-crf', '16', '-r', '30', f'{out}/fight.mp4'], check=True)
    # GIF via ffmpeg palettegen (much smaller than PIL for long clips)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', '10', '-i', f'{tmp}/%04d.png',
                    '-vf', 'scale=1280:720:flags=neighbor,split[a][b];[a]palettegen=max_colors=128:stats_mode=full[p];[b][p]paletteuse=dither=none',
                    f'{out}/fight.gif'], check=True)
    for f_ in os.listdir(tmp): os.remove(f'{tmp}/{f_}')
    os.rmdir(tmp)
