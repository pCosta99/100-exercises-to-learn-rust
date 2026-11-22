"""Preview GIFs of idle/attack/hit/death for all five spirits.

Usage: python3 tools/preview_actions.py OUT_DIR
"""
import sys
from PIL import Image
import aura3 as A
OUT, SC = sys.argv[1], 1.3
W, H = A.canvas_size(SC)
BG = (28, 26, 40, 255)

def timeline():
    seq = []
    for name, part in [('idle', A.tl_idle(12)), ('attack', A.tl_attack()), ('idle', A.tl_idle(6)),
                       ('hit', A.tl_hit()), ('idle', A.tl_idle(6)), ('death', A.tl_death())]:
        for k, a in enumerate(part):
            a = dict(a)
            if not (name == 'death' and k >= 3):
                a['orbs'] = None  # filled per element
                a['_orbs'] = True
            seq.append((name, a))
    return seq

def frames_for(el):
    N = A.noises(el); out = []
    for g, (name, a) in enumerate(timeline()):
        a = dict(a)
        if a.pop('_orbs', False): a['orbs'] = [el] * 5
        out.append(A.render(el, g / 12, SC, 'front', a, N))
    return out

def save_gif(frames, path, scale):
    seq = []
    for fr in frames:
        c = Image.new('RGBA', fr.size, BG); c.alpha_composite(fr)
        seq.append(c.resize((fr.width * scale, fr.height * scale), Image.NEAREST).convert('P', palette=Image.ADAPTIVE))
    seq[0].save(path, save_all=True, append_images=seq[1:], duration=100, loop=0, disposal=2)

allf = {el: frames_for(el) for el in A.ORDER}
for el, fr in allf.items():
    save_gif(fr, f'{OUT}/{el}_actions.gif', 5)
n = len(next(iter(allf.values())))
line = []
for i in range(n):
    c = Image.new('RGBA', (W * 5, H), (0, 0, 0, 0))
    for k, el in enumerate(A.ORDER): c.alpha_composite(allf[el][i], (k * W, 0))
    line.append(c)
save_gif(line, f'{OUT}/actions_lineup.gif', 3)
# key-frame sheet for review: attack 3,4,6 ; hit 0,2 ; death 5,9,13
keys = [12 + 3, 12 + 4, 12 + 6, 28 + 0, 28 + 2, 40 + 6, 40 + 10, 40 + 14]
S, pad = 4, 3
cs = Image.new('RGB', (pad + len(keys) * (W * S + pad), pad + 5 * (H * S + pad)), (14, 14, 20))
for r, el in enumerate(A.ORDER):
    for c, k in enumerate(keys):
        t = Image.new('RGBA', (W, H), BG); t.alpha_composite(allf[el][k])
        cs.paste(t.resize((W * S, H * S), Image.NEAREST), (pad + c * (W * S + pad), pad + r * (H * S + pad)))
cs.save(f'{OUT}/action_keys.png')
print(n, 'frames')
