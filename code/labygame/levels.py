"""Create-or-load a level, resolving its style from res/data/lvl.json.

lvl.json is a list of range blocks::

    {"lvls": [1, 3], "size": [11, 11], "events": ["hidden_loot"],
     "vignette": false, "end": "random", "end_tile": [0, 58],
     "character": "./assets/textures/character.png",
     "filenames": ["./assets/textures/grass.png"],
     "animated_background": false,
     "bg_tile_array": [[0, 55], [0, 56], [0, 57]], "wall_tiles": { ... }}

``lvls`` is an inclusive range so one block configures many levels. Tiles are
``[tileset_index, tile_id]`` (row-major, 11 per row on the 77-tile wall sheets).
Past the last range the last block is reused and its size keeps growing by
``+round(size*0.1)`` per level, so the game is endless.

On disk a level is ``<n>.lvl`` (JSON grid + style), ``<n>.png`` (maze) and, for
static backgrounds, ``<n>_bg.png``. Matching files are loaded as-is; otherwise
the level is regenerated.
"""
import json
import os

from . import maze
from . import baking
from .tiles import RES

LVL_DIR = os.path.join(RES, "lvls")
DATA_DIR = os.path.join(RES, "data")

# Bump when generation/baking changes so stale levels on disk are rebuilt.
BAKE_VERSION = 8

_STYLE_FIELDS = ("filenames", "wall_tiles", "bg_tile_array", "end_tile",
                 "vignette", "character", "animated_background", "events", "end")
_DEFAULTS = {"vignette": False, "character": "./assets/textures/character.png",
             "animated_background": False, "events": [], "end": "random"}

# Style fields that are pure runtime cosmetics: they affect neither the baked
# image nor the grid, so edits to lvl.json should take effect on already-baked
# levels without forcing a rebuild.
_RUNTIME_STYLE_FIELDS = ("vignette", "character")


def _load_styles():
    with open(os.path.join(DATA_DIR, "lvl.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def _grow(size, steps):
    w, h = int(size[0]), int(size[1])
    for _ in range(max(0, steps)):
        w += round(w * 0.1)
        h += round(h * 0.1)
    return [w, h]


def style_for_level(level, styles=None):
    """Resolve the full style block for ``level`` (grows size past the table)."""
    styles = styles or _load_styles()
    chosen, steps = styles[-1], 0
    for s in styles:
        lo, hi = s["lvls"]
        if lo <= level <= hi:
            chosen, steps = s, 0
            break
    else:
        steps = max(0, level - styles[-1]["lvls"][1])
    style = {f: chosen.get(f, _DEFAULTS.get(f)) for f in _STYLE_FIELDS}
    style["size"] = _grow(chosen["size"], steps)
    return style


def lvl_paths(level):
    name = str(level)
    return (os.path.join(LVL_DIR, f"{name}.lvl"),
            os.path.join(LVL_DIR, f"{name}.png"),
            os.path.join(LVL_DIR, f"{name}_bg.png"))


def exists(level, animated=False):
    """True if the files this level needs are present (animated levels need no
    baked background)."""
    lvl_file, maze_png, bg_png = lvl_paths(level)
    needed = [lvl_file, maze_png] + ([] if animated else [bg_png])
    return all(os.path.isfile(p) for p in needed)


def save(level_data):
    lvl_file, _, _ = lvl_paths(level_data["level"])
    os.makedirs(LVL_DIR, exist_ok=True)
    with open(lvl_file, "w", encoding="utf-8") as f:
        json.dump(level_data, f)


def load(level):
    lvl_file, maze_png, bg_png = lvl_paths(level)
    with open(lvl_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["_maze_png"] = maze_png
    data["_bg_png"] = bg_png
    return data


def get_level(level, force=False):
    """Return level data, generating + baking + saving on first use (or when the
    on-disk bake version is older than the engine)."""
    style = style_for_level(level)
    animated = style.get("animated_background", False)
    if not force and exists(level, animated):
        data = load(level)
        if data.get("bake_version") == BAKE_VERSION:
            # Refresh runtime-only cosmetics from the current lvl.json so edits
            # (e.g. toggling the vignette) apply without rebaking the level.
            saved_style = data.setdefault("style", style)
            for f in _RUNTIME_STYLE_FIELDS:
                saved_style[f] = style.get(f)
            return data

    data = maze.generate(level, size=style["size"],
                         events=style["events"], end=style["end"])
    data["style"] = style
    data["bake_version"] = BAKE_VERSION
    baking.bake(data, style, LVL_DIR, str(level))
    save(data)
    return load(level)
