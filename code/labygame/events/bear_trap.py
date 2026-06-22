"""Bear-trap event tile.

An armed bear trap is walkable but dangerous: stepping onto it springs it and opens
a bleeding wound (adds TRAP_BLEED to Game.bleeding, draining hearts over time). The
safe way past is to throw an item: stand on the tile directly in front of the trap,
face towards it, and press E. The trap snaps shut on the item (used up and gone for
good) and is then harmless to walk over.

bear_trap.png is a 64x16 strip of four 16x16 frames:
  0 armed (open jaws, idle)  |  1-3 snapping shut (3 = sprung/safe)

Items are per-play, so a trap re-arms whenever the level is (re)loaded.
"""
import pygame

from .base import EventTile, register
from ..tiles import TILE, res_path

_SNAP_DUR = 0.10    # seconds per snap frame (1 -> 2 -> 3)
_SNAP_FRAMES = 3    # frames 1, 2, 3 make up the snap animation

_CACHE = {}  # display-dependent surfaces, loaded once


def _frames():
    if not _CACHE:
        sheet = pygame.image.load(
            res_path("./assets/textures/bear_trap.png")).convert_alpha()
        _CACHE["frames"] = [
            sheet.subsurface(pygame.Rect(i * TILE, 0, TILE, TILE)).copy()
            for i in range(sheet.get_width() // TILE)]
    return _CACHE["frames"]


@register("bear_trap")
class BearTrap(EventTile):
    def __init__(self, data, assets):
        super().__init__(data, assets)
        self.frames = _frames()
        self.armed = True          # always armed on (re)load -- items are per-play
        self.snap_t = 0.0          # advances through the snap once disarmed

    def disarm(self, game):
        """Trick the trap with a thrown item. Returns a HUD message."""
        if not self.armed:
            return None
        self.armed = False
        self.snap_t = 0.0
        return "Trap sprung!"

    def update(self, dt):
        if not self.armed and self.snap_t < _SNAP_FRAMES * _SNAP_DUR:
            self.snap_t += dt

    def _frame_index(self):
        if self.armed:
            return 0  # idle: just the open jaws, no animation
        return min(3, 1 + int(self.snap_t / _SNAP_DUR))  # snap: 1 -> 2 -> 3

    def draw(self, surface, screen_pos, tile_px):
        frame = self.frames[self._frame_index()]
        surface.blit(pygame.transform.scale(frame, (tile_px, tile_px)), screen_pos)
