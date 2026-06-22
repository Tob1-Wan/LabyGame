"""Bake a semantic grid to PNGs at native (16px/tile) resolution.

  * ``<name>.png``     maze walls with transparent paths (drawn over the
                       background; transparency also documents collisions).
  * ``<name>_bg.png``  opaque ground, random tile per cell -- only for *static*
                       backgrounds. Animated backgrounds are tiled live at
                       runtime (cheap, no giant per-frame images), so no bg file.

Event tiles are never baked (they animate). Runs head-less: tilesets are loaded
without ``convert`` so no display is needed.
"""
import os
import random

import pygame

from .tiles import TILE, WALL, RES, get_tile
from .autotile import wall_tile_id


def _load(path_rel):
    rel = path_rel.lstrip("./").replace("/", os.sep)
    return pygame.image.load(os.path.join(RES, rel))


def bake(level_data, style, out_dir, name):
    """Write ``<name>.png`` and, for static backgrounds, ``<name>_bg.png``.
    Returns ``(maze_path, bg_path_or_None)``."""
    grid = level_data["grid"]
    w, h = level_data["size"]
    rng = random.Random(level_data["level"])

    tilesets = [_load(p) for p in style["filenames"]]
    wall_set = tilesets[0]                 # walls always come from filenames[0]
    wall_tiles = style["wall_tiles"]
    bg_tiles = style["bg_tile_array"]      # list of [tileset_idx, tile_id]
    animated = style.get("animated_background", False)

    # --- maze layer (transparent) ------------------------------------------
    # Only walls are baked. The end tile is drawn live (like event tiles) so it
    # never gets re-drawn over the player by the 2.5D foot-line wall pass.
    maze = pygame.Surface((w * TILE, h * TILE), pygame.SRCALPHA)
    for y in range(h):
        for x in range(w):
            if grid[y][x] == WALL:
                sx, sy = get_tile(wall_set, wall_tile_id(grid, w, h, x, y, wall_tiles))
                maze.blit(wall_set, (x * TILE, y * TILE), pygame.Rect(sx, sy, TILE, TILE))

    os.makedirs(out_dir, exist_ok=True)
    maze_path = os.path.join(out_dir, f"{name}.png")
    pygame.image.save(maze, maze_path)
    if animated:
        return maze_path, None

    # --- static background layer (opaque) ----------------------------------
    bg = pygame.Surface((w * TILE, h * TILE))
    for y in range(h):
        for x in range(w):
            ts_idx, tid = rng.choice(bg_tiles)
            ts = tilesets[ts_idx]
            sx, sy = get_tile(ts, tid)
            bg.blit(ts, (x * TILE, y * TILE), pygame.Rect(sx, sy, TILE, TILE))
    bg_path = os.path.join(out_dir, f"{name}_bg.png")
    pygame.image.save(bg, bg_path)
    return maze_path, bg_path
