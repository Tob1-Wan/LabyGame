"""Runtime Level: loads a baked level and serves it to the renderer.

Holds native-resolution surfaces so it can be rescaled cheaply on window/scale
changes, draws the world background (static image or live-tiled animated frames),
and answers wall queries for collision.
"""
import math
import random

import pygame

from . import levels
from . import events as events_pkg
from .config import CHUNK_TILES
from .tiles import TILE, WALL, res_path, get_tile


class Level:
    def __init__(self, number):
        self.number = number
        self.data = levels.get_level(number)
        self.w, self.h = self.data["size"]
        self.grid = self.data["grid"]
        self.style = self.data["style"]
        self.start = tuple(self.data["start"])
        self.end = tuple(self.data["end"])
        self.bg_tiles = self.style["bg_tile_array"]
        self.animated = bool(self.style.get("animated_background", False))

        self.maze_native = pygame.image.load(self.data["_maze_png"]).convert_alpha()
        self.tilesets = [pygame.image.load(res_path(p)).convert_alpha()
                         for p in self.style["filenames"]]

        # the goal marker is drawn live (not baked) so the 2.5D wall pass never
        # paints it back over the player. Scaled copy is built in rescale().
        self.end_tile_native = self._tile_surface(*self.style["end_tile"])
        self.end_tile_img = None

        # background: a baked image (static) or per-frame tiles tiled live
        if self.animated:
            self.bg_native = None
            self.frames_native = self._build_bg_frames()
        else:
            self.bg_native = pygame.image.load(self.data["_bg_png"]).convert()
            self.frames_native = []
        self.outer_native = self._build_outer_chunk()

        # scaled surfaces (set by rescale). The maze/background are NOT
        # pre-scaled to the full world (that surface grows with the maze area
        # and blows up memory on huge levels); only screen-sized regions are
        # scaled live in draw_maze/draw_background. Chunks stay small + cached.
        self.tile_px = 0
        self.outer_chunk = None
        self.frames = []
        self.world_w = self.world_h = 0

        # live event objects. Items are per-play: every (re)load starts un-dug,
        # so revisiting/restarting a level makes its items collectable again.
        self.events = {}
        for ed in self.data["events"]:
            ed["dug"] = False
            obj = events_pkg.create(ed, None)
            if obj is not None:
                self.events[(ed["x"], ed["y"])] = obj

    # -- texture helpers ---------------------------------------------------
    def _tile_surface(self, ts_idx, tid):
        ts = self.tilesets[ts_idx]
        sx, sy = get_tile(ts, tid)
        return ts.subsurface(pygame.Rect(sx, sy, TILE, TILE)).copy()

    def _build_bg_frames(self):
        """One CHUNK-sized surface per animation frame (uniform tiling of one
        bg tile, e.g. animated water)."""
        px = CHUNK_TILES * TILE
        frames = []
        for ts_idx, tid in self.bg_tiles:
            tile = self._tile_surface(ts_idx, tid)
            chunk = pygame.Surface((px, px))
            for y in range(CHUNK_TILES):
                for x in range(CHUNK_TILES):
                    chunk.blit(tile, (x * TILE, y * TILE))
            frames.append(chunk)
        return frames

    def _build_outer_chunk(self):
        """A small, darkened background chunk repeated outside the level."""
        rng = random.Random(self.number * 99 + 7)
        px = CHUNK_TILES * TILE
        surf = pygame.Surface((px, px))
        for y in range(CHUNK_TILES):
            for x in range(CHUNK_TILES):
                surf.blit(self._tile_surface(*rng.choice(self.bg_tiles)), (x * TILE, y * TILE))
        dark = pygame.Surface((px, px), pygame.SRCALPHA)
        dark.fill((0, 0, 0, 95))
        surf.blit(dark, (0, 0))
        return surf

    # -- scaling -----------------------------------------------------------
    def rescale(self, tile_px):
        self.tile_px = tile_px
        self.world_w = max(1, round(self.w * tile_px))
        self.world_h = max(1, round(self.h * tile_px))
        cpx = max(1, round(CHUNK_TILES * tile_px))
        if self.animated:
            self.frames = [pygame.transform.scale(f, (cpx, cpx)) for f in self.frames_native]
        else:
            self.frames = []
        self.outer_chunk = pygame.transform.scale(self.outer_native, (cpx, cpx))
        tpx = max(1, round(tile_px))
        self.end_tile_img = pygame.transform.scale(self.end_tile_native, (tpx, tpx))

    # -- rendering ---------------------------------------------------------
    def _blit_region(self, screen, native, ox, oy, sw, sh):
        """Scale and blit only the on-screen slice of a native (16px/tile)
        surface. Cost scales with the viewport, not the maze, so huge levels
        stay cheap. ``(ox, oy)`` is the world's top-left in screen pixels."""
        scale = self.tile_px / TILE  # screen px per native px
        nat_w, nat_h = native.get_width(), native.get_height()
        nx0 = max(0, int(-ox / scale))
        ny0 = max(0, int(-oy / scale))
        nx1 = min(nat_w, int(math.ceil((sw - ox) / scale)) + 1)
        ny1 = min(nat_h, int(math.ceil((sh - oy) / scale)) + 1)
        nw, nh = nx1 - nx0, ny1 - ny0
        if nw <= 0 or nh <= 0:
            return
        sub = native.subsurface(pygame.Rect(nx0, ny0, nw, nh))
        scaled = pygame.transform.scale(sub, (max(1, round(nw * scale)),
                                              max(1, round(nh * scale))))
        screen.blit(scaled, (round(ox + nx0 * scale), round(oy + ny0 * scale)))

    def draw_maze(self, screen, ox, oy, sw, sh):
        """Draw the (transparent) wall layer over the visible viewport. Respects
        the screen's current clip, so the 2.5D foot-line re-draw still works."""
        self._blit_region(screen, self.maze_native, ox, oy, sw, sh)

    def draw_end(self, screen, ox, oy, sw, sh):
        """Draw the goal marker live (over the background, under walls/player)."""
        tp = self.tile_px
        sx, sy = ox + self.end[0] * tp, oy + self.end[1] * tp
        if -tp <= sx <= sw and -tp <= sy <= sh:
            screen.blit(self.end_tile_img, (round(sx), round(sy)))

    def draw_background(self, screen, ox, oy, sw, sh, frame_idx):
        """Draw the level's ground inside the world rect (static image, or the
        current animated frame tiled live)."""
        cl, ct = max(0, ox), max(0, oy)
        cr, cb = min(sw, ox + self.world_w), min(sh, oy + self.world_h)
        if cr <= cl or cb <= ct:
            return
        if not self.animated:
            self._blit_region(screen, self.bg_native, ox, oy, sw, sh)
            return
        chunk = self.frames[frame_idx % len(self.frames)]
        cpx = chunk.get_width()
        prev = screen.get_clip()
        screen.set_clip(pygame.Rect(cl, ct, cr - cl, cb - ct))
        start_x = ox + math.floor((cl - ox) / cpx) * cpx
        start_y = oy + math.floor((ct - oy) / cpx) * cpx
        y = start_y
        while y < cb:
            x = start_x
            while x < cr:
                screen.blit(chunk, (x, y))
                x += cpx
            y += cpx
        screen.set_clip(prev)

    # -- queries -----------------------------------------------------------
    def is_wall(self, tx, ty):
        if tx < 0 or ty < 0 or tx >= self.w or ty >= self.h:
            return True
        return self.grid[ty][tx] == WALL

    def is_blocked(self, tx, ty):
        """Movement blockers: walls and armed traps (events with ``solid``)."""
        if self.is_wall(tx, ty):
            return True
        obj = self.events.get((tx, ty))
        return bool(obj and getattr(obj, "solid", False))
