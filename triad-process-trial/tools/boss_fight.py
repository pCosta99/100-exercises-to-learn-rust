"""Boss fight showcase: EMBERLING vs NULL MONARCH on the neon rooftop.

Usage: python3 tools/boss_fight.py OUT_DIR  -> boss_fight.gif, boss_fight.mp4, boss_fight_poster.png
"""
import math, os, random, subprocess, sys
from PIL import Image, ImageChops, ImageDraw
import aura3 as A
import boss as B
import fight
from fight import Battle, Fx, SW, SH, text, text_w, panel, hp_bar, piles_ui, energy, card, PLAYER, CARDS, SLOT_X, HAND_Y
from battle_ui import TXT, DIM, INK

BOSS_HP = 220

class BossBattle(Battle):
    def __init__(self):
        super().__init__()
        self.city = B.City(text, text_w)
        self.ehp = BOSS_HP
        self.tx, self.ty = int(B.CORE[0]), int(B.CORE[1])
        self.dmg_xy = (self.tx + 40, self.ty - 30)
        self.intent = 18
        self.beam = 0
        self.eq = B.btl_intro(26)
        self.name_show = 0

    def enemy_hit_tl(self): return B.btl_hit()

    def enemy_turn(self):
        self.show_banner('ENEMY TURN', 14)
        self.eq += B.btl_attack()
        self.run(8)
        self.run(3)  # beam frames are handled in render via the 'beam' flag
        self.fx.append(Fx('impact', 10, el='light', x=PLAYER['ax'] + 2, y=PLAYER['ay'] - 60, big=True))
        self.fx.append(Fx('dmg', 18, s=f'-{self.intent}', x=PLAYER['ax'] + 44, y=PLAYER['ay'] - 104))
        self.php -= self.intent
        self.shake = 7
        self.pq = A.tl_hit()
        self.run(12)
        self.intent = 24

    def render(self):
        f = self.f; t = f / 12
        pa = self.pq.pop(0) if self.pq else {}
        ea = self.eq.pop(0) if self.eq else {}
        pa = dict(pa); pa['orbs'] = [p[-1] for p in self.piles if p]

        bimg = B.boss_render(t, ea, f)
        world = B.stage_frame(self.city, f, bimg)
        self.draw_fx(world, 'world')
        if ea.get('beam'):
            d = ImageDraw.Draw(world)
            tgt = (PLAYER['ax'] + 2, PLAYER['ay'] - 60)
            j = random.Random(f)
            for w, c in ((13, B.BP['MGd']), (9, B.BP['MG']), (5, B.BP['CY']), (2, B.BP['W'])):
                d.line([B.VISOR, tgt], fill=c[:3], width=w + j.choice([-1, 0, 1]))
            for k in range(14):  # crackle along the beam
                u = j.random()
                x = B.VISOR[0] + (tgt[0] - B.VISOR[0]) * u + j.randint(-9, 9)
                y = B.VISOR[1] + (tgt[1] - B.VISOR[1]) * u + j.randint(-9, 9)
                world.putpixel((int(x), int(y)), B.BP[j.choice(['CY', 'MG', 'W'])])
        A_spr = A.render(PLAYER['el'], t, PLAYER['SC'], 'back', pa, self.Np)
        fight.paste_sprite(world, A_spr, PLAYER['ax'], PLAYER['ay'], PLAYER['SC'])
        self.city.rain_layer(world, f)
        if self.shake:
            r = random.Random(f)
            world = ImageChops.offset(world, r.choice([-3, -2, 2, 3]), r.choice([-2, -1, 1, 2]))
            self.shake -= 1
        sc = world

        # boss bar (top centre)
        panel(sc, 170, 6, 470, 30, fill=(30, 18, 44, 255))
        text(sc, 'NULL MONARCH', 176, 10, B.BP['MG'])
        text(sc, 'BOSS', 470 - 6 - text_w('BOSS'), 10, DIM)
        hp_bar(sc, 176, 18, 288, self.ehp, BOSS_HP)
        if not self.eq:
            fight.intent(sc, 478, 12, self.intent)
        panel(sc, 8, 8, 150, 26)
        text(sc, 'EMBERLING', 14, 12, TXT)
        hp_bar(sc, 14, 18, 130, self.php, 60)
        text(sc, 'FLOOR 9', SW - 8 - text_w('FLOOR 9'), 10, DIM)
        piles_ui(sc, self.piles, 8, 262)
        energy(sc, 262, 326, self.en, 3)
        n = len(self.hand)
        for i, name in enumerate(self.hand):
            tx = SLOT_X(i, n); ty = HAND_Y - (10 if self.lift == name else 0)
            cx = self.hx.get(name, tx); cy = self.hy.get(name, ty)
            cx += (tx - cx) * 0.45; cy += (ty - cy) * 0.45
            self.hx[name], self.hy[name] = cx, cy
            el, cost, orbs, _ = CARDS[name]
            card(sc, int(round(cx)), int(round(cy)), name, el, cost, orbs, hi=(self.lift == name))
        btn = (120, 64, 48, 255) if self.end_btn else (80, 46, 40, 255)
        panel(sc, 548, 322, 630, 346, fill=btn)
        text(sc, 'END TURN', 589 - text_w('END TURN') // 2, 332, TXT)
        text(sc, 'DRAW 7', 556, 304, DIM); text(sc, 'DISCARD 2', 556, 312, DIM)
        self.draw_fx(sc, 'ui')
        if self.banner:
            s, k = self.banner
            warn = s.startswith('WARNING') or s.startswith('PHASE')
            band = Image.new('RGBA', (SW, 34), (60, 6, 30, 210) if warn else (12, 8, 22, 190))
            sc.alpha_composite(band, (0, 62))
            if warn and (k // 3) % 2 == 0:
                for xx in range(0, SW, 12):  # hazard stripes
                    ImageDraw.Draw(sc).line([(xx, 62), (xx + 6, 62)], fill=B.BP['MG'][:3])
                    ImageDraw.Draw(sc).line([(xx + 6, 95), (xx + 12, 95)], fill=B.BP['MG'][:3])
            w = text_w(s, 3)
            slide = max(0, 6 - k) * 30
            text(sc, s, SW // 2 - w // 2 + slide, 71, (255, 220, 236) if warn else (250, 236, 210), sc=3)
            self.banner[1] += 1
        if self.end_btn: self.end_btn -= 1
        for e in self.fx: e.age += 1
        self.fx = [e for e in self.fx if e.age < e.life]
        self.frames.append(sc)

def script(b):
    b.run(8)                       # boss materialises out of the rain
    b.run(14)
    b.show_banner('WARNING', 18)
    b.show_banner('YOUR TURN')
    b.play('EMBER'); b.run(3)
    b.play('BLAZE'); b.run(6)
    b.end_btn = 4; b.run(4)
    b.enemy_turn()
    b.show_banner('YOUR TURN')
    b.en = 3; b.deal(['STOKE', 'BLAZE']); b.run(3)
    b.play('STOKE'); b.run(2)
    b.play('BLAZE'); b.run(6)
    b.eq = B.btl_enrage()
    b.shake = 10
    b.show_banner('PHASE 2', 22)
    b.run(10)

if __name__ == '__main__':
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    b = BossBattle(); script(b)
    fr = b.frames; print(len(fr), 'frames')
    fr[40].resize((SW * 2, SH * 2), Image.NEAREST).save(f'{out}/boss_fight_poster.png')
    tmp = f'{out}/_frames'; os.makedirs(tmp, exist_ok=True)
    for i, im in enumerate(fr): im.convert('RGB').save(f'{tmp}/{i:04d}.png')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', '10', '-i', f'{tmp}/%04d.png',
                    '-vf', 'scale=1920:1080:flags=neighbor', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                    '-crf', '16', '-r', '30', f'{out}/boss_fight.mp4'], check=True)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', '10', '-i', f'{tmp}/%04d.png',
                    '-vf', 'scale=1280:720:flags=neighbor,split[a][b];[a]palettegen=max_colors=200:stats_mode=full[p];[b][p]paletteuse=dither=none',
                    f'{out}/boss_fight.gif'], check=True)
    for f_ in os.listdir(tmp): os.remove(f'{tmp}/{f_}')
    os.rmdir(tmp)
