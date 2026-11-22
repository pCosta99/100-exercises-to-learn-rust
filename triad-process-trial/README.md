# Process trial: AI-made game art

**Read [PROCESS.md](PROCESS.md). The process is the deliverable.**

Everything else in this folder is **experimental sample output** from trying the process out:
elemental spirits, a boss, a city stage, battle mockups and style tests. None of it is a design or style
decision for the game. It's here only as worked examples of each step.

## What's in the folder

```
PROCESS.md     ← the process: rules, loop, checks, collaboration, pitfalls, recipe
tools/         the experiment scripts (Python + Pillow + numpy; ffmpeg for video)
assets/        exported sample sprite sheets + JSON metadata (shows the export format)
previews/      sample renders and videos from each round of the experiment
```

### Scripts, as examples of each technique

| Script | Shows |
|---|---|
| `tools/gen.py` | the first version: shapes as code, locked palette, render-and-check |
| `tools/aura3.py` | a scalable 2D renderer: shape + motion fields, timelines for actions |
| `tools/export.py` | sheet + JSON export with a palette assertion |
| `tools/preview_actions.py` | contact sheets / GIFs for review |
| `tools/battle_ui.py`, `tools/fight.py` | assembling a scene and a scripted sequence into a video |
| `tools/boss.py`, `tools/boss_fight.py` | a new asset type built with the same method |
| `tools/styles.py` | one 3D scene rendered to several styles |
| `tools/anim_style_a.py` | animating a pixelised render with a locked palette |

```bash
pip install -r requirements.txt
python3 tools/export.py out            # export sample sheets (also asserts the palette)
python3 tools/fight.py out             # sample sequence → GIF + MP4 (needs ffmpeg)
```

Running any script twice gives byte-identical output (see PROCESS.md, Rule 2 and the reproducibility check).
