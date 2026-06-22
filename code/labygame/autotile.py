"""Wall autotiling: pick a concrete tileset id for a wall from its neighbours.

A wall's look depends on which orthogonal neighbours are also walls. We build a
4-bit mask (N/S/E/W) and map it to a key in the ``wall_tiles`` table from
lvl.json. Out-of-bounds counts as OPEN (the maze has its own border ring), else
every edge/corner would render as a cross ("grid of plusses").
"""
from .tiles import WALL

N, S, E, W = 1, 2, 4, 8


def _is_wall(grid, w, h, x, y):
    if x < 0 or y < 0 or x >= w or y >= h:
        return False
    return grid[y][x] == WALL


def _mask(grid, w, h, x, y):
    m = 0
    if _is_wall(grid, w, h, x, y - 1): m |= N
    if _is_wall(grid, w, h, x, y + 1): m |= S
    if _is_wall(grid, w, h, x + 1, y): m |= E
    if _is_wall(grid, w, h, x - 1, y): m |= W
    return m


_MASK_TO_KEY = {
    0: "single",
    N: "end_down", S: "end_up", E: "end_left", W: "end_right",
    N | S: "vertical", E | W: "horizontal",
    S | E: "corner_tl", S | W: "corner_tr", N | E: "corner_bl", N | W: "corner_br",
    N | E | W: "t_up", S | E | W: "t_down", N | S | E: "t_left", N | S | W: "t_right",
    N | S | E | W: "cross",
}


def wall_tile_id(grid, w, h, x, y, wall_tiles):
    return wall_tiles[_MASK_TO_KEY[_mask(grid, w, h, x, y)]]
