# A reproducible process for making game art with an AI

This is the deliverable. Everything else in this folder (sprites, the boss, the city, the style tests)
is **experimental sample output** made while testing the process. None of it is a design decision for
the game.

---

## 1. The problem this solves

When an AI is asked to make pixel art directly (writing pixel grids, or prompting an image model), it
usually goes wrong in three ways:

1. **It can't see its own output.** It places pixels blind, so mistakes pile up.
2. **Nothing is pinned down.** Size, palette and proportions drift between sprites and between sessions.
3. **Results are one-offs.** A good result can't be regenerated, resized or adjusted. You can only ask
   again and hope, and every fix risks breaking something that worked.

The result is slow progress and no reproducibility. The process below fixes all three.

---

## 2. The five rules

### Rule 1: Lock a spec before making anything
Write down the constraints every asset must meet: canvas size or scale, palette (an exact list of
colours), frame count, frame rate, anchor point (e.g. the ground under the feet) and light direction.
Change the spec only on purpose, with a stated reason, and then re-render everything against it.

*Why:* consistency across a set comes from shared rules, not from carefully matching sprites one by one.

### Rule 2: Art is code, not pixels
Describe each asset as a **program**, never as hand-placed pixels:
- **Shape:** maths shapes (signed-distance functions: circles, boxes, capsules) blended together.
- **Motion:** parameters over time (noise that flows upward = flames, distance rings = ripples, etc.).
- **Colour:** mapped from the shape (e.g. how deep a pixel sits inside it) onto the locked palette.

What you get:
- **Reproducible:** same script → byte-identical output, on any machine, every run. Every "random"
  choice uses a fixed seed. Never use anything that changes between runs (e.g. Python's `hash()`).
- **Any size:** the same description renders natively at any scale, so it never gets resized and blurry.
- **Cheap fixes:** a change is a parameter edit that applies to every frame, view and animation at once.
- **Seamless loops by construction:** build animation noise from waves whose time frequencies are whole
  numbers, so the last frame always flows into the first.

Use small hand-made patterns ("stamps") only where maths looks worse, e.g. a halo or a 3-pixel face.

### Rule 3: Render, look, fix (the core loop)
After **every** change:
1. **Render a contact sheet:** all variants × several frames, zoomed 4-6×, on more than one background.
2. **Look at it.** The AI can view images. Name concrete defects, not vibes:
   "speckle noise inside the body", "these eyes + this mouth read as an owl", "the smoke is the same
   brightness as the background", "the effect is clipped by the canvas edge".
3. **Zoom in with a crop** when a detail is too small to judge. Faces and icons need it.
4. **Make one targeted fix per defect**, re-render, look again.

*Why:* almost every quality jump came from looking. The defects were invisible in the code and
obvious in the image.

### Rule 4: Automate the checks that must never break
Next to the visual check, add assertions that fail the export:
- every pixel belongs to the locked palette,
- frame size and anchor are correct,
- bounding boxes per frame (to catch drift or clipping),
- **reproducibility:** export twice (even with different hash seeds) and compare checksums.

Also add cheap clean-up passes, e.g. removing stray single pixels.

### Rule 5: Keep every version
Write each round to its own folder (v1, v2, …). You can always compare, roll back, or point at
"the first draft had the better balance".

---

## 3. How to split the work between you and the AI

| You (direction) | The AI (execution) |
|---|---|
| Say what it should *feel* like, in plain words | Turn it into concrete parameter changes |
| Judge whether it's good | Render, inspect and fix the specific defects |
| Pick between options | Make options cheap to produce |
| Change the spec on purpose | Re-render everything against the new spec |

The feedback that moved things furthest was all about design and in plain language:
"each one should have a personality", "the faces take too much attention", "the aura should be the
core of the movement", "it should face into the screen, like Pokémon", "less toyish".
You never needed to talk about individual pixels.

**Ask the AI to:**
- state its plan and what it's unsure about before building,
- show you renders, not descriptions of renders,
- tell you honestly what is still weak after each round,
- verify claims (e.g. "it's reproducible") with an actual check, not assume them.

---

## 4. Techniques discovered along the way (reusable, not decisions)

- **Pseudo-3D in 2D:** shade 2D shapes using their distance field as a height map. You get bevels,
  rim lights and depth without a 3D engine.
- **Depth layers sell scale and space:** far layers lighter and hazier, near layers darker; the
  foreground drawn *over* a huge character so it rises from behind it.
- **One scene, many styles:** build a scene once (even in real 3D via ray-marched distance fields), then
  render it to pixel art, comic or cinematic looks with post-processing. Changing style is cheap, and
  the scene stays the single source of truth.
- **Rendering to pixel art from a lit scene:** downscale → palette (median-cut + fixed accent colours
  so key hues survive) → ordered (Bayer) dithering. **Lock the palette from one reference frame** and
  reuse it, or animation flickers.
- **Video for sharing:** export MP4 with nearest-neighbour upscaling so pixels stay sharp; GIFs via
  ffmpeg's palette generation.
- **Clean pixel lines:** stick to 0° and 45°. Rotated lines look jagged at low resolution.

---

## 5. Pitfalls we actually hit (and the fix)

| Symptom seen in the render | Cause | Fix |
|---|---|---|
| Passed every automatic check but looked noisy | checks don't measure taste | always look, too |
| All variants looked the same | one shared shape, no signature per variant | add one distinct silhouette feature each |
| Face became all you see | too many high-contrast pixels | 2-3 low-contrast pixels; personality from motion |
| Effect invisible | same brightness as the background | push its values brighter; contrast beats hue |
| Background filled with pattern | "no effect" value fell inside the effect's range | use a clearly out-of-range default |
| Neon signs floating in space | buildings matched the sky colour | separate depth layers by brightness |
| Object vanished during an animation | an effect meant for one part also hit another | limit the effect to the right parts |
| Metal looked like plastic | coloured lights too strong, reflections too weak | darker base, sharper highlights, more reflection |
| Key colour lost in pixel art | palette reduction dropped a rare hue | always include fixed accent colours |
| Colours flickered in animation | palette recomputed per frame | lock the palette once |
| Labels rendered wrong | tiny bitmap font with mistyped glyphs | define glyphs row by row; render a test sheet |
| "Reproducible" claim was false in old code | Python's randomised `hash()` used as a seed | stable seeds only; checksum-compare two runs |

---

## 6. Recipe for any new asset

1. **Spec line:** size/scale, palette, frames, fps, anchor, light.
2. **Describe the shape** as maths shapes and the **motion** as parameters over time.
3. **Render a zoomed contact sheet.** Look. List the defects.
4. **Fix one defect at a time**, re-rendering after each.
5. **Add an assertion** for anything that must never break.
6. **Export** sheets + metadata (frame size, anchor, fps, frames per animation). Save the version.
7. **Verify reproducibility:** export twice, compare checksums.

---

## 7. Limits

- The AI judges small details reliably only when zoomed in. Insist on crops.
- "Is this good?" stays a human call. The process makes iterating cheap, not taste automatic.
- Code-built art has a ceiling: simple shapes look simple, and realism exposes it.
  Photorealism needs detailed 3D models or AI image models, which give up reproducibility.

---

## Appendix: how the experiment went (for reference)

Each row is one render-look-fix round. The outputs are in `previews/` and `assets/`. They are samples,
not game decisions.

| Round | What was tried | What looking at it revealed |
|---|---|---|
| 1 | five elemental "aura" spirits, shared skeleton, locked 5-colour palettes | passed the checks; noisy, near-identical silhouettes |
| 2-4 | smoothing, a signature shape per element, hand-made halo stamp, 0°/45° rays | rotating lines jagged; halo hidden behind the head |
| 5-6 | bigger canvas, personality faces, particle effects | one face read as an owl; eyes vanished on a bright head |
| 7 | aura-first rewrite at any scale, orbs, attack/hit/death, battle mockup | background-fill bug; dark aura invisible (4 rounds to fix) |
| 8 | full fight video, export pipeline, reproducibility check | the check caught a non-deterministic seed in old code |
| 9 | boss + cyberpunk city stage, same method | signs floating in space; hands vanishing; crown too faint |
| 10 | same scene in 3D, rendered as pixel / comic / cinematic styles | plastic metal, floating torso, lost hues, palette flicker |
