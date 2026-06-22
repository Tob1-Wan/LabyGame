"""Carrot event tile.

A buried carrot (frame 0). Standing on it and pressing SPACE digs it out: the two
middle frames play as a short dig animation, a carrot is collected, and the last
frame stays behind as a leftover hole -- it never clears, so it doubles as a
breadcrumb marking cells the player has already visited. Drawn live (never baked).

carrots.png is a 64x16 strip of four 16x16 frames:
  0 buried carrot  |  1-2 digging  |  3 leftover hole
"""
import pygame

from .base import EventTile, register
from ..tiles import TILE, res_path

_DIG_FRAME_DUR = 0.18           # seconds per dig frame
_DIG_TIME = 2 * _DIG_FRAME_DUR  # frames 1 and 2, then settle on the hole

_CACHE = {}  # display-dependent surfaces, loaded once


def _frames():
    if not _CACHE:
        sheet = pygame.image.load(
            res_path("./assets/textures/carrots.png")).convert_alpha()
        _CACHE["frames"] = [
            sheet.subsurface(pygame.Rect(i * TILE, 0, TILE, TILE)).copy()
            for i in range(sheet.get_width() // TILE)]
    return _CACHE["frames"]


@register("carrot")
class Carrot(EventTile):
    def __init__(self, data, assets):
        super().__init__(data, assets)
        self.frames = _frames()
        # already-dug carrots (loaded from a saved level) skip straight to the
        # leftover hole instead of replaying the dig animation.
        self.dig_anim = _DIG_TIME if self.triggered else 0.0

    def update(self, dt):
        if self.triggered and self.dig_anim < _DIG_TIME:
            self.dig_anim += dt

    def on_trigger(self, game):
        game.collect_item("carrot")
        game.play_sound("./assets/sounds/digging.mp3")
        self.dig_anim = 0.0
        return "Dug up a carrot!"

    def _frame_index(self):
        if not self.triggered:
            return 0
        if self.dig_anim < _DIG_FRAME_DUR:
            return 1
        if self.dig_anim < _DIG_TIME:
            return 2
        return 3  # leftover hole, stays for orientation

    def draw(self, surface, screen_pos, tile_px):
        frame = self.frames[self._frame_index()]
        surface.blit(pygame.transform.scale(frame, (tile_px, tile_px)), screen_pos)
