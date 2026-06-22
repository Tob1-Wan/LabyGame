"""Game: window/scaling, input, the update loop, rendering and HUD.

The player stays centred; WASD scrolls the world the opposite way (vector
normalised so diagonals aren't faster). The view always shows VISIBLE_TILES_V
tiles vertically, so the tile scale is derived from the window height and
recomputed on resize/fullscreen.
"""
import math
import random

import pygame

from . import config as C
from . import fonts
from . import inventory
from .level import Level
from .player import Player
from .settings import load_settings, save_settings
from .tiles import TILE, res_path

# tile offset for the cell the player faces, by Player.direction
_DIR_OFFSETS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}


class Game:
    def __init__(self):
        pygame.init()
        try:  # audio is optional -- the game runs fine (silent) without it
            if not pygame.mixer.get_init():
                pygame.mixer.init()
        except pygame.error:
            pass
        self._sounds = {}
        self.settings = load_settings()
        self.fullscreen = bool(self.settings.get("fullscreen", True))
        pygame.display.set_caption("LabyGame")
        self.clock = pygame.time.Clock()

        self.items = 0
        self.item_counts = {}
        self.health = float(C.MAX_HEALTH)
        self.bleeding = 0.0
        self.banner = ""
        self.banner_timer = 0.0
        self.anim_time = 0.0

        self.screen = None
        self.screen_w = self.screen_h = 0
        self.tile_px = 0.0
        self.level = self.player = None
        self.char_path = res_path("./assets/textures/character.png")
        self.vignette = self.vignette_native = None

        # blood trail: splatters dropped on the floor as a wounded player walks
        self.blood = []          # (tile_x, tile_y, frame_idx)
        self.blood_accum = 0.0   # tiles walked since the last splatter
        self._blood_scaled = {}  # splatter px -> [scaled frames]

        self._apply_display()
        bsheet = pygame.image.load(res_path("./assets/textures/blood.png")).convert_alpha()
        bh = bsheet.get_height()
        self.blood_frames = [bsheet.subsurface(pygame.Rect(i * bh, 0, bh, bh)).copy()
                             for i in range(bsheet.get_width() // bh)]
        self.load_level(1)

    # -- display / scaling -------------------------------------------------
    def _apply_display(self):
        if self.fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode(C.WINDOWED_SIZE, pygame.RESIZABLE)
        self._on_resize()

    def _on_resize(self):
        self.screen_w, self.screen_h = self.screen.get_size()
        # Snap to a whole number of screen pixels per texture pixel (art is 16px
        # per tile) so every texture pixel is the same integer size on screen --
        # one uniform pixel grid for tiles, sprites, blood, everything. ~16 tiles
        # fit vertically; the exact count varies a little with the snap.
        ppt = max(1, round(self.screen_h / (C.VISIBLE_TILES_V * TILE)))
        self.tile_px = ppt * TILE
        self.font = fonts.get(max(14, self.screen_h // 32))
        self.big_font = fonts.get(max(24, self.screen_h // 18))
        if self.level:
            self.level.rescale(self.tile_px)
            self._reload_player()
        if self.vignette_native:
            self.vignette = pygame.transform.scale(self.vignette_native, (self.screen_w, self.screen_h))

    def _reload_player(self):
        mult = self.tile_px / TILE
        self.player = Player(self.char_path, TILE, walk_frames=2, idle_frames=2,
                             size_multiplier=mult)

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self.settings["fullscreen"] = self.fullscreen
        save_settings(self.settings)
        self._apply_display()

    # -- level management --------------------------------------------------
    def load_level(self, number):
        self.level = Level(number)
        self.level.rescale(self.tile_px)
        # items are per-level: a fresh (or re-entered) level starts empty and its
        # buried items are diggable again (see Level: dug state is never carried).
        self.items = 0
        self.item_counts = {}
        self.health = float(C.MAX_HEALTH)
        self.bleeding = 0.0
        self.blood.clear()
        self.blood_accum = 0.0
        self.char_path = res_path(self.level.style.get(
            "character", "./assets/textures/character.png"))
        self._reload_player()
        # player position is stored in TILE units (scale-independent)
        sx, sy = self.level.start
        self.ptx, self.pty = sx + 0.5, sy + 0.5

        if self.level.style.get("vignette"):
            self.vignette_native = pygame.image.load(
                res_path("./assets/textures/vignette.png")).convert_alpha()
            self.vignette = pygame.transform.scale(self.vignette_native, (self.screen_w, self.screen_h))
        else:
            self.vignette_native = self.vignette = None

        self.set_banner(f"Level {number}  -  {self.level.w}x{self.level.h}")

    def next_level(self):
        # dug state is intentionally NOT persisted -- items are per-play, so the
        # level is fully diggable again on a later visit / restart.
        self.load_level(self.level.number + 1)

    # -- callbacks used by event tiles ------------------------------------
    def collect_item(self, name):
        self.items += 1
        self.item_counts[name] = self.item_counts.get(name, 0) + 1

    def play_sound(self, rel_path):
        """Play a one-shot sound effect (cached by path). No-op if audio is
        unavailable, so headless/sound-less setups still work."""
        if not pygame.mixer.get_init():
            return
        snd = self._sounds.get(rel_path)
        if snd is None:
            try:
                snd = pygame.mixer.Sound(res_path(rel_path))
            except pygame.error:
                return
            self._sounds[rel_path] = snd
        snd.play()

    def set_banner(self, text, secs=2.0):
        self.banner, self.banner_timer = text, secs

    # -- collision (tile space) -------------------------------------------
    def _free(self, cx, cy):
        """True if the feet hitbox centred on sprite-centre (cx, cy) hits no
        blocker (wall or armed trap). Blockers are shrunk by WALL_INSET to match
        the visible art."""
        fx, fy = cx, cy + C.FEET_DY
        left, right = fx - C.FEET_HX, fx + C.FEET_HX
        top, bottom = fy - C.FEET_HY, fy + C.FEET_HY
        for ty in range(math.floor(top), math.floor(bottom) + 1):
            for tx in range(math.floor(left), math.floor(right) + 1):
                if self.level.is_blocked(tx, ty):
                    wl, wr = tx + C.WALL_INSET, tx + 1 - C.WALL_INSET
                    wt, wb = ty + C.WALL_INSET, ty + 1 - C.WALL_INSET
                    if right > wl and left < wr and bottom > wt and top < wb:
                        return False
        return True

    # -- main loop ---------------------------------------------------------
    def run(self):
        running = True
        while running:
            dt = self.clock.tick(C.FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.VIDEORESIZE and not self.fullscreen:
                    self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                    self._on_resize()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key in (pygame.K_F11, pygame.K_f):
                        self.toggle_fullscreen()
                    elif event.key == pygame.K_SPACE:
                        self.try_dig()
                    elif event.key == pygame.K_e:
                        self.try_throw()
            self.update(dt)
            self.draw()
        pygame.quit()

    def update(self, dt):
        keys = pygame.key.get_pressed()
        vx = keys[pygame.K_d] - keys[pygame.K_a]
        vy = keys[pygame.K_s] - keys[pygame.K_w]
        moving = bool(vx or vy)
        direction = None
        px0, py0 = self.ptx, self.pty
        if moving:
            length = math.hypot(vx, vy)  # normalise -> diagonals aren't faster
            ndx, ndy = vx / length, vy / length
            step = C.SPEED_TILES * dt
            if self._free(self.ptx + ndx * step, self.pty):
                self.ptx += ndx * step
            if self._free(self.ptx, self.pty + ndy * step):
                self.pty += ndy * step
            if abs(vx) >= abs(vy):
                direction = "right" if vx > 0 else "left"
            else:
                direction = "down" if vy > 0 else "up"
        moved = math.hypot(self.ptx - px0, self.pty - py0)

        self.anim_time += dt
        self.player.update(dt, moving, direction)
        for obj in self.level.events.values():
            obj.update(dt)
        if self.banner_timer > 0:
            self.banner_timer -= dt

        # stepping onto an armed trap springs it: half a heart now, then bleeds
        here = self.level.events.get(self.player_tile())
        if here is not None and getattr(here, "armed", False):
            here.disarm(self)
            self.health = max(0.0, self.health - C.TRAP_DAMAGE)
            self.bleeding += C.TRAP_BLEED
            self.set_banner("Caught in a trap!", 1.2)

        if self._update_bleeding(dt, moved):
            return  # bled out -> the level was reloaded, skip the rest

        if self.player_tile() == self.level.end:
            self.set_banner(f"Level {self.level.number} cleared!", 1.2)
            self.next_level()

    def _update_bleeding(self, dt, moved):
        """Apply active bleeding (``self.bleeding`` > 0): slowly drain health and
        drip a trail while moving. Bleeding never clots -- it only ends at death or
        when the goal is reached (next level resets it); stacking traps raise the
        intensity so you bleed out faster. Returns True if the player bled out (the
        level was reloaded)."""
        if self.bleeding <= 0:
            return False
        self.health = max(0.0, self.health - self.bleeding * C.BLEED_DAMAGE * dt)
        if moved > 0:
            spacing = C.BLOOD_SPACING / self.bleeding
            self.blood_accum += moved
            while self.blood_accum >= spacing:
                self.blood_accum -= spacing
                self._drop_splatter()
        if self.health <= 0:
            self.load_level(self.level.number)  # respawn: full reset of the level
            self.set_banner("You bled out!", 1.5)  # after load_level's own banner
            return True
        return False

    def _drop_splatter(self):
        """Add one blood splatter near the feet, snapped to the texture-pixel grid
        (stored as the splatter's top-left texture pixel in the world)."""
        cx = self.ptx + random.uniform(-0.3, 0.3)
        cy = self.pty + C.FEET_DY + random.uniform(-0.25, 0.25)
        half = self.blood_frames[0].get_width() // 2
        gx = round(cx * TILE) - half
        gy = round(cy * TILE) - half
        self.blood.append((gx, gy, random.randrange(len(self.blood_frames))))
        if len(self.blood) > C.BLOOD_MAX:
            self.blood.pop(0)

    def player_tile(self):
        # use the feet position (where the player visually stands / collides),
        # not the sprite centre, so events/end trigger anywhere on the tile.
        return (int(self.ptx), int(self.pty + C.FEET_DY))

    def try_dig(self):
        obj = self.level.events.get(self.player_tile())
        if obj and not obj.triggered:
            msg = obj.trigger(self)
            if msg:
                self.set_banner(msg, 1.5)

    def use_item(self):
        """Spend one collected item (for a throw). Returns True if one was used."""
        if self.items <= 0:
            return False
        self.items -= 1
        # prefer spending the visible inventory item (carrot), else anything
        for name in ("carrot", *self.item_counts):
            if self.item_counts.get(name, 0) > 0:
                self.item_counts[name] -= 1
                break
        return True

    def try_throw(self):
        """Throw an item at the trap on the tile the player faces (R). The player
        must stand directly in front of the trap and look towards it."""
        px, py = self.player_tile()
        dx, dy = _DIR_OFFSETS.get(self.player.direction, (0, 0))
        obj = self.level.events.get((px + dx, py + dy))
        if not (obj and getattr(obj, "armed", False)):
            return
        if not self.use_item():
            self.set_banner("No item to throw!", 1.2)
            return
        msg = obj.disarm(self)
        if msg:
            self.set_banner(msg, 1.5)

    # -- rendering ---------------------------------------------------------
    def draw(self):
        self.screen.fill(C.BG_COLOR)
        tp = self.tile_px
        ox = self.screen_w / 2 - self.ptx * tp
        oy = self.screen_h / 2 - self.pty * tp

        self._draw_outer(ox, oy)
        frame = int(self.anim_time / C.BG_FRAME_DUR)
        self.level.draw_background(self.screen, ox, oy, self.screen_w, self.screen_h, frame)

        # goal marker + event tiles: over the background, under the walls.
        self.level.draw_end(self.screen, ox, oy, self.screen_w, self.screen_h)
        for (tx, ty), obj in self.level.events.items():
            sx, sy = round(ox + tx * tp), round(oy + ty * tp)
            if -tp <= sx <= self.screen_w and -tp <= sy <= self.screen_h:
                obj.draw(self.screen, (sx, sy), round(tp))
        # blood is painted over the floor AND the event tiles (loot, carrots, traps)
        self._draw_blood(ox, oy, tp)

        self.level.draw_maze(self.screen, ox, oy, self.screen_w, self.screen_h)

        # player over the walls (overlaps walls above/beside)...
        cx, cy = self.screen_w // 2, self.screen_h // 2
        self.player.draw(self.screen, (cx, cy))

        # ...then re-draw walls below the foot line so a wall bumped from above
        # clips the lower body (2.5D look).
        cut = int(cy + C.GROUND_CLIP * tp)
        if cut < self.screen_h:
            prev = self.screen.get_clip()
            self.screen.set_clip(pygame.Rect(0, cut, self.screen_w, self.screen_h - cut))
            self.level.draw_maze(self.screen, ox, oy, self.screen_w, self.screen_h)
            self.screen.set_clip(prev)

        if self.vignette:
            self.screen.blit(self.vignette, (0, 0))
        self.draw_hud()
        pygame.display.flip()

    def _draw_blood(self, ox, oy, tp):
        """Draw the splatters at the world's integer texture-pixel scale, snapped
        to the same pixel grid as the tiles (positions are top-left tex pixels)."""
        if not self.blood:
            return
        ppt = max(1, round(tp / TILE))  # screen px per texture pixel (integer)
        frames = self._blood_scaled.get(ppt)
        if frames is None:
            frames = [pygame.transform.scale(f, (f.get_width() * ppt, f.get_height() * ppt))
                      for f in self.blood_frames]
            self._blood_scaled = {ppt: frames}  # only the current scale is kept
        fw = frames[0].get_width()
        for gx, gy, fi in self.blood:
            sx, sy = round(ox + gx * ppt), round(oy + gy * ppt)
            if -fw < sx < self.screen_w and -fw < sy < self.screen_h:
                self.screen.blit(frames[fi], (sx, sy))

    def _draw_outer(self, ox, oy):
        """Tile the darkened outer chunk across the whole screen, world-aligned."""
        chunk = self.level.outer_chunk
        cpx = chunk.get_width()
        if cpx <= 0:
            return
        start_x, start_y = int(ox % cpx) - cpx, int(oy % cpx) - cpx
        y = start_y
        while y < self.screen_h:
            x = start_x
            while x < self.screen_w:
                self.screen.blit(chunk, (x, y))
                x += cpx
            y += cpx

    def _text(self, text, pos, font=None):
        font = font or self.font
        self.screen.blit(font.render(text, False, C.HUD_SHADOW), (pos[0] + 2, pos[1] + 2))
        self.screen.blit(font.render(text, False, C.HUD_COLOR), pos)

    def draw_hud(self):
        self._text(f"Level {self.level.number}", (16, 12))
        self._text("WASD move   SPACE dig   E throw   F11 fullscreen   ESC quit",
                   (16, 12 + self.screen_h // 28))
        # item slots + hearts, bottom-centre
        inventory.draw(self.screen, self.screen_w, self.screen_h,
                       self.item_counts, self.health)
        if self.banner_timer > 0 and self.banner:
            surf = self.big_font.render(self.banner, False, C.HUD_COLOR)
            rect = surf.get_rect(center=(self.screen_w // 2, self.screen_h // 10))
            self.screen.blit(self.big_font.render(self.banner, False, C.HUD_SHADOW),
                             (rect.x + 2, rect.y + 2))
            self.screen.blit(surf, rect)
