"""Bottom-centre HUD bar: item slots + a heart health bar.

One artwork (``inventory_example_with_slots_2.png``, 304x96) provides six 32x32
item slots and five 15x14 empty heart sockets. A full heart (from
``Inventory_Herat_Spritesheet.png`` at 0,2) is overlaid on each socket the player
still has. The bar is drawn bottom-centre, scaled to the screen.

Runtime-only (needs a display): surfaces are built once and cached per scale.
"""
import pygame

from . import config as C
from . import fonts
from .tiles import res_path

_UI = "./assets/textures/emojis-free/emoji style ui/"
_BAR = _UI + "inventory_example_with_slots_2.png"
_HEARTS = _UI + "Inventory_Herat_Spritesheet.png"
_HEART_SRC = pygame.Rect(0, 2, 15, 14)          # full-heart frame
_HEART_SIZE = (15, 14)

# native positions inside the bar image
_SLOT_POS = [(15, 35), (63, 35), (111, 35), (159, 35), (207, 35), (255, 35)]
_SLOT_SIZE = 32
_HEART_POS = [(23, 8), (40, 8), (57, 8), (74, 8), (91, 8)]
_ICON_PAD = 4                                   # native inset of an icon in a slot

# item name -> (sheet, source rect); _SLOTS is the display order into the slots
_ICONS = {
    "carrot": ("./assets/textures/emojis-free/Emoji_Spritesheet_Free.png",
               pygame.Rect(128, 416, 32, 32)),
}
_SLOTS = ["carrot"]

_cache = {}     # native surfaces, loaded once
_scaled = {}    # (key, w, h) -> scaled surface


def _build():
    if _cache:
        return
    _cache["bar"] = pygame.image.load(res_path(_BAR)).convert_alpha()
    hearts = pygame.image.load(res_path(_HEARTS)).convert_alpha()
    _cache["heart"] = hearts.subsurface(_HEART_SRC).copy()
    _cache["icons"] = {}
    for name, (path, rect) in _ICONS.items():
        sheet = pygame.image.load(res_path(path)).convert_alpha()
        _cache["icons"][name] = sheet.subsurface(rect).copy()


def _scale(key, native, w, h):
    s = _scaled.get((key, w, h))
    if s is None:
        s = pygame.transform.scale(native, (max(1, w), max(1, h)))
        _scaled[(key, w, h)] = s
    return s


def draw(surface, screen_w, screen_h, counts, health):
    """Draw the HUD bar bottom-centre: item counts in the slots and ``health``
    full hearts over the heart sockets."""
    _build()
    scale = max(2, screen_h // 360)
    bar = _cache["bar"]
    bw, bh = bar.get_width() * scale, bar.get_height() * scale
    ox = (screen_w - bw) // 2
    oy = screen_h - bh - max(4, screen_h // 100)
    surface.blit(_scale("bar", bar, bw, bh), (ox, oy))

    # hearts: ``health`` is fractional, so each heart drains top-down by whole
    # texture-pixel rows (the red recedes, the empty socket shows above it).
    hwn, hhn = _HEART_SIZE  # native heart size
    heart_native = _cache["heart"]
    for i, (hx, hy) in enumerate(_HEART_POS):
        fill = max(0.0, min(1.0, health - i))
        rows = round(hhn * fill)
        if rows <= 0:
            continue
        sub = heart_native.subsurface(pygame.Rect(0, hhn - rows, hwn, rows))
        surface.blit(pygame.transform.scale(sub, (hwn * scale, rows * scale)),
                     (ox + hx * scale, oy + (hy + hhn - rows) * scale))

    # item slots: icon (inset) + count bottom-right
    inner = (_SLOT_SIZE - 2 * _ICON_PAD) * scale
    slot_px = _SLOT_SIZE * scale
    font = fonts.get(max(10, int(_SLOT_SIZE * scale * 0.3)))
    for name, (sx, sy) in zip(_SLOTS, _SLOT_POS):
        px, py = ox + sx * scale, oy + sy * scale
        icon = _scale(name, _cache["icons"][name], inner, inner)
        surface.blit(icon, (px + _ICON_PAD * scale, py + _ICON_PAD * scale))
        label = str(counts.get(name, 0))
        tw, th = font.size(label)
        tx = px + slot_px - tw - 3 * scale
        ty = py + slot_px - th - 2 * scale
        surface.blit(font.render(label, False, C.HUD_SHADOW), (tx + 2, ty + 2))
        surface.blit(font.render(label, False, C.HUD_COLOR), (tx, ty))
