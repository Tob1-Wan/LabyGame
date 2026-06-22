"""Shared tile constants and helpers.

The logical maze grid stores one semantic code per cell. A saved ``.lvl`` file is
the single source of truth for a level; the baked image and collision both derive
from this grid.
"""
import os

# --- Semantic cell codes (stored in the .lvl 2D array) ---------------------
WALL = 0   # blocks movement, drawn into the baked maze image
PATH = 1   # walkable, transparent in the baked image
START = 2  # walkable spawn point
END = 3    # walkable goal, drawn with the special end tile
EVENT = 4  # walkable, holds an event tile (drawn live, never baked)


def is_walkable(code):
    return code != WALL


# --- Pixel sizes -----------------------------------------------------------
TILE = 16  # native tile size in the source textures (px)

# This file lives in <root>/code/labygame/tiles.py
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RES = os.path.join(ROOT, "res")


def res_path(rel):
    """Resolve a path stored in lvl.json (e.g. ``./assets/textures/grass.png``)
    against the ``res`` directory."""
    rel = rel.lstrip("./").replace("/", os.sep)
    return os.path.join(RES, rel)


def get_tile(surface, tile_id):
    """Top-left pixel of ``tile_id`` inside a tileset ``surface``.

    Tile ids are linear, row-major (``id = row * cols + col``); ``cols`` comes
    from the surface width, so this works for any sheet (11-wide wall sheets,
    4-wide water, ...).
    """
    cols = surface.get_width() // TILE
    return (tile_id % cols) * TILE, (tile_id // cols) * TILE
