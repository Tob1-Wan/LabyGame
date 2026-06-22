"""Pure-data maze generation (no pygame).

Builds the semantic grid saved into a ``.lvl`` file plus the start/end positions
and the scattered event tiles. Everything that varies per level (size, events,
goal) is passed in from lvl.json via :mod:`levels`, so generation is fully
data-driven and head-less testable.
"""
import random
from collections import deque

from .tiles import WALL, PATH, START, END, EVENT


def _carve(w, h, rng):
    """Carve a perfect maze into a ``w x h`` grid with a randomized DFS.

    Cells sit on odd coordinates so coordinate 0 and the far edge stay walls --
    a solid wall ring around the maze. The result is a tree (one path between any
    two cells)."""
    grid = [[WALL] * w for _ in range(h)]
    hx, hy = w - 2, h - 2  # inclusive max cell coordinate per axis
    grid[1][1] = PATH
    stack = [(1, 1)]
    while stack:
        x, y = stack[-1]
        nbrs = []
        for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2)):
            nx, ny = x + dx, y + dy
            if 1 <= nx <= hx and 1 <= ny <= hy and grid[ny][nx] == WALL:
                nbrs.append((nx, ny, dx, dy))
        if not nbrs:
            stack.pop()
            continue
        nx, ny, dx, dy = rng.choice(nbrs)
        grid[y + dy // 2][x + dx // 2] = PATH  # knock down the wall between
        grid[ny][nx] = PATH
        stack.append((nx, ny))
    return grid


def _bfs_farthest(grid, w, h, source):
    """BFS over PATH cells; return (farthest_cell, distance_map)."""
    dist = {source: 0}
    q = deque([source])
    far = source
    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and grid[ny][nx] != WALL and (nx, ny) not in dist:
                dist[(nx, ny)] = dist[(x, y)] + 1
                if dist[(nx, ny)] > dist[far]:
                    far = (nx, ny)
                q.append((nx, ny))
    return far, dist


def _first_path(grid, w, h):
    return next((x, y) for y in range(h) for x in range(w) if grid[y][x] != WALL)


def _resolve_endpoints(grid, w, h, end):
    """Choose (start, end). ``"random"`` -> the two endpoints of the maze's
    longest path (max walking distance). An explicit ``[x, y]`` is honoured, with
    the start placed as far from it as possible."""
    if isinstance(end, (list, tuple)) and len(end) == 2:
        goal = (int(end[0]), int(end[1]))
        if grid[goal[1]][goal[0]] == WALL:           # snap a bad goal to a path
            goal, _ = _bfs_farthest(grid, w, h, _first_path(grid, w, h))
        start, _ = _bfs_farthest(grid, w, h, goal)
        return start, goal
    a, _ = _bfs_farthest(grid, w, h, _first_path(grid, w, h))  # double BFS =
    b, _ = _bfs_farthest(grid, w, h, a)                        # tree diameter
    return a, b


# event type-names that are traps (block the tile until tricked with an item)
TRAP_TYPES = {"bear_trap"}
_TRAP_CHANCE = 0.45  # how often an *eligible* cell becomes a trap vs an item


def _scatter_events(grid, w, h, start, end, rng, pool, items):
    """Place event tiles on path cells (never start/end); each gets a type from
    ``pool`` (the range's ``events`` list).

    Loot favours dead-ends (cells with a single non-wall neighbour) so it sits
    tucked away at the end of branches; other path cells top up the rest. The
    total is kept fairly sparse.

    Traps need an item to be tricked, so they are placed feasibly: cells are
    processed in order of distance from start while tracking ``surplus`` =
    (items so far) - (traps so far). A trap is only placed when surplus >= 1, so
    every trap has at least one earlier, collectable item to spend on it. This
    guarantees no trap at spawn, never two traps behind a single item, and traps
    never outnumber items."""
    if not pool:
        return []
    item_types = [t for t in pool if t not in TRAP_TYPES]
    trap_types = [t for t in pool if t in TRAP_TYPES]
    dead_ends, others = [], []
    for y in range(h):
        for x in range(w):
            if grid[y][x] != PATH or (x, y) in (start, end):
                continue
            nbrs = sum(1 for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                       if grid[y + dy][x + dx] != WALL)
            (dead_ends if nbrs == 1 else others).append((x, y))
    rng.shuffle(dead_ends)
    rng.shuffle(others)
    count = min(len(dead_ends) + len(others), max(2, (w + h) // 4))
    chosen = (dead_ends + others)[:count]
    # nearer cells first, so a trap is only ever reached after an earlier item.
    _, dist = _bfs_farthest(grid, w, h, start)
    chosen.sort(key=lambda c: dist.get(c, 0))

    events = []
    surplus = 0
    for (x, y) in chosen:
        if trap_types and item_types and surplus >= 1 and rng.random() < _TRAP_CHANCE:
            grid[y][x] = EVENT
            events.append({"type": rng.choice(trap_types), "x": x, "y": y,
                           "armed": True})
            surplus -= 1
        elif item_types:
            grid[y][x] = EVENT
            events.append({"type": rng.choice(item_types), "x": x, "y": y,
                           "item": rng.choice(items), "dug": False})
            surplus += 1
    return events


def generate(level, size, events=(), end="random", seed=None,
             items=("milk", "bottle", "tool", "plant")):
    """Generate a level. ``size`` is ``[w, h]`` in tiles, ``events`` the pool of
    event type-names, ``end`` either ``"random"`` or ``[x, y]``."""
    w, h = int(size[0]), int(size[1])
    rng = random.Random(seed if seed is not None else level)
    grid = _carve(w, h, rng)
    start, goal = _resolve_endpoints(grid, w, h, end)
    ev = _scatter_events(grid, w, h, start, goal, rng, list(events), list(items))
    grid[start[1]][start[0]] = START
    grid[goal[1]][goal[0]] = END
    return {"level": level, "size": [w, h], "grid": grid,
            "start": list(start), "end": list(goal), "events": ev}
