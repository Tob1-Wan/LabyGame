"""Runtime tunables for the game (window, movement, hitbox, look).

Generation/style lives in res/data/lvl.json; this file is only the live
gameplay/render feel.
"""

# --- window / scaling ------------------------------------------------------
WINDOWED_SIZE = (1280, 720)
VISIBLE_TILES_V = 16     # exactly this many tiles fit vertically -> tile_px = H/16
FPS = 144

# --- movement --------------------------------------------------------------
SPEED_TILES = 4.5        # player speed, tiles/s

# --- health & bleeding -----------------------------------------------------
MAX_HEALTH = 5           # full hearts (health is a float; hearts drain by pixels)
# A trap costs half a heart instantly, then opens a wound that bleeds out *slowly*
# and does NOT clot -- it only stops at death or when the goal is reached (the
# next level resets it). Each extra trap raises Game.bleeding, so you bleed out
# faster. A future bandage item would lower bleeding.
TRAP_DAMAGE = 0.5        # hearts lost instantly when caught in an armed trap
TRAP_BLEED = 1.0         # bleeding added per trap (intensity, never decays)
BLEED_DAMAGE = 0.05      # hearts lost per second per unit of bleeding (slow)

# --- blood trail -----------------------------------------------------------
# While bleeding, a splatter is dropped every BLOOD_SPACING/bleeding tiles walked,
# so stronger bleeding -> a denser trail.
BLOOD_SPACING = 1.4      # tiles walked per splatter at bleeding == 1
BLOOD_MAX = 1500         # cap on stored splatters per level

# Feet-only hitbox (tile units): a small flat box at the lower body so the upper
# body can overlap walls without the player getting stuck everywhere.
FEET_DY = 0.30           # how far below the sprite centre the feet sit
FEET_HX = 0.26           # half width
FEET_HY = 0.12           # half height
# Wall textures (3D top / thin walls) don't fill the whole cell, so shrink the
# solid area of a wall cell to match what the player actually sees.
WALL_INSET = 0.12

# --- rendering -------------------------------------------------------------
CHUNK_TILES = 8          # size of the repeating outer-background chunk
# Walls below this line (fraction of a tile under the sprite centre) are re-drawn
# over the player, so only a wall bumped *from above* clips the lower body.
GROUND_CLIP = 0.34
BG_FRAME_DUR = 0.18      # seconds per animated-background frame

BG_COLOR = (12, 12, 16)
HUD_COLOR = (240, 240, 240)
HUD_SHADOW = (0, 0, 0)
