"""Export game-ready sprite sheets + metadata for every element and view.

Usage: python3 tools/export.py assets/
Output:
  assets/sprites/<element>/<view>.png   rows = animations, columns = frames (transparent)
  assets/sprites/<element>/<view>.json  frame size, ground anchor, fps, per-animation frame counts
  assets/orbs/<element>_<size>.png      orb icons (7px for far/small, 9px for near/UI), 1px outline included
  assets/palettes.json                  the locked 5-tone palettes
"""
import json, os, sys
from PIL import Image
import aura3 as A

VIEWS = {            # name: (render view, scale)  -- scale = pixels per skeleton unit
    'front': ('front', 1.3),   # showcase / portrait size
    'far':   ('front', 1.05),  # enemy in the battle scene
    'back':  ('back', 1.6),    # player in the battle scene (over-the-shoulder)
}
ANIMS = ['idle', 'attack', 'hit', 'death']

def timeline(anim, view):
    if anim == 'idle':   return A.tl_idle(12)
    if anim == 'attack': return A.tl_attack('back' if view == 'back' else 'front')
    if anim == 'hit':    return A.tl_hit()
    if anim == 'death':  return A.tl_death()

def export(out):
    allowed_extra = {A.SHADOW, (0, 0, 0, 0), (255, 255, 255, 255)}
    for el in A.ORDER:
        N = A.noises(el)
        allowed = set(A.PAL[el]) | allowed_extra
        os.makedirs(f'{out}/sprites/{el}', exist_ok=True)
        for vname, (view, SC) in VIEWS.items():
            W, H = A.canvas_size(SC)
            rows = {a: [A.render(el, f / 12, SC, view, act, N) for f, act in enumerate(timeline(a, view))] for a in ANIMS}
            cols = max(len(r) for r in rows.values())
            sheet = Image.new('RGBA', (W * cols, H * len(ANIMS)), (0, 0, 0, 0))
            for r, a in enumerate(ANIMS):
                for c, fr in enumerate(rows[a]):
                    bad = set(fr.get_flattened_data()) - allowed
                    assert not bad, (el, vname, a, c, bad)
                    sheet.paste(fr, (c * W, r * H))
            sheet.save(f'{out}/sprites/{el}/{vname}.png')
            meta = {
                'element': el, 'view': view, 'scale': SC,
                'frame_w': W, 'frame_h': H,
                'anchor': [W // 2, int(round(H - 3 * SC))],   # ground point under the feet
                'fps': 10,
                'animations': {a: {'row': i, 'frames': len(rows[a]), 'loop': a == 'idle'} for i, a in enumerate(ANIMS)},
                'notes': 'Idle loops seamlessly. Attack/hit return to idle pose. Death ends empty.',
            }
            json.dump(meta, open(f'{out}/sprites/{el}/{vname}.json', 'w'), indent=2)
        print('exported', el)
    os.makedirs(f'{out}/orbs', exist_ok=True)
    for (el, s), im in A.ORB.items():
        im.save(f'{out}/orbs/{el}_{s}.png')
    json.dump({el: ['#%02x%02x%02x' % c[:3] for c in A.PAL[el]] for el in A.ORDER} |
              {'_order': ['rim', 'dark', 'mid', 'light', 'core'], '_shadow_rgba': list(A.SHADOW), '_outline': list(A.OUTLINE)},
              open(f'{out}/palettes.json', 'w'), indent=2)

if __name__ == '__main__':
    export(sys.argv[1] if len(sys.argv) > 1 else 'assets')
