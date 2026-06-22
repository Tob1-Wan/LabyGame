"""Hidden-loot event tile.

A buried spot (a small plant/mound). Standing on it and pressing SPACE digs it
out: the loot pops, an item is auto-collected, and the tile is left bare (no
lingering hole/shadow). Drawn live (never baked) so it can animate the dig.
"""
import pygame

from .base import EventTile, register
from ..tiles import TILE, res_path

# item name -> column in "Simple Milk and grass item.png" (64x16 -> 4 tiles)
_ITEM_COLUMN = {"milk": 0, "bottle": 1, "grass": 2, "tool": 3, "plant": 2}

_CACHE = {}  # display-dependent surfaces, loaded once


def _assets():
    if not _CACHE:
        items = pygame.image.load(
            res_path("./assets/textures/Simple Milk and grass item.png")).convert_alpha()
        mound = pygame.image.load(
            res_path("./assets/textures/Basic Plants.png")).convert_alpha()
        _CACHE["items"] = items
        _CACHE["mound"] = mound.subsurface(pygame.Rect(0, 0, TILE, TILE)).copy()
    return _CACHE


@register("hidden_loot")
class HiddenLoot(EventTile):
    def __init__(self, data, assets):
        super().__init__(data, assets)
        a = _assets()
        self.mound = a["mound"]
        col = _ITEM_COLUMN.get(data.get("item", "milk"), 0)
        self.item_icon = a["items"].subsurface(pygame.Rect(col * TILE, 0, TILE, TILE)).copy()
        self.dig_anim = 0.0  # seconds since trigger, drives the pop

    def update(self, dt):
        if self.triggered and self.dig_anim < 1.0:
            self.dig_anim += dt

    def on_trigger(self, game):
        game.collect_item(self.data["item"])
        self.dig_anim = 0.0
        return f"Found {self.data['item']}!"

    def draw(self, surface, screen_pos, tile_px):
        sx, sy = screen_pos
        if not self.triggered:
            surface.blit(pygame.transform.scale(self.mound, (tile_px, tile_px)), (sx, sy))
            return
        # dug out: nothing lingers on the ground -- just the collected item
        # briefly popping up before it's gone for good.
        if self.dig_anim < 1.0:
            lift = int(tile_px * 0.6 * min(1.0, self.dig_anim * 2))
            surface.blit(pygame.transform.scale(self.item_icon, (tile_px, tile_px)), (sx, sy - lift))
