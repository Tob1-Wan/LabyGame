"""Shared pixel font used for all in-game text.

One TTF (Sprout Lands, 8x14 pixel font) at any size, cached. Render text with
antialias=False so the pixels stay crisp and match the pixel-art look.
"""
import pygame

from .tiles import res_path

_PATH = "./assets/fonts/pixelFont-7-8x14-sproutLands.ttf"
_cache = {}


def get(size):
    """Return the pixel font at ``size`` px (cached). Needs pygame.font ready."""
    size = max(1, int(size))
    f = _cache.get(size)
    if f is None:
        f = pygame.font.Font(res_path(_PATH), size)
        _cache[size] = f
    return f
