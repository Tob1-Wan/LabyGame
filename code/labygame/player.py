"""Animated player sprite.

Reads a sprite sheet laid out as rows = directions (down, up, left, right) and
columns = idle frames then walk frames. Frames are scaled by ``size_multiplier``
at load so the sprite matches the current tile size.
"""
import pygame


class Player(pygame.sprite.Sprite):
    def __init__(self, sprite_sheet_path, frame_size, walk_frames, idle_frames,
                 size_multiplier):
        super().__init__()
        sheet = pygame.image.load(sprite_sheet_path).convert_alpha()
        self.frame_size = frame_size
        scaled = round(frame_size * size_multiplier)
        self.directions = ["down", "up", "left", "right"]  # sheet row order
        self.walk_frames = walk_frames
        self.idle_frames = idle_frames

        # frames[direction] = {"walk": [...], "idle": [...]}
        self.frames = {}
        for row, direction in enumerate(self.directions):
            idle, walk = [], []
            for col in range(idle_frames):
                idle.append(self._cut(sheet, col, row, scaled))
            for col in range(walk_frames):
                walk.append(self._cut(sheet, idle_frames + col, row, scaled))
            self.frames[direction] = {"walk": walk, "idle": idle}

        self.direction = "down"
        self.is_moving = False
        self.anim_timer = 0
        self.anim_speed = 0.15  # seconds per frame
        self.frame_idx = 0

    def _cut(self, sheet, col, row, scaled):
        rect = pygame.Rect(col * self.frame_size, row * self.frame_size,
                           self.frame_size, self.frame_size)
        return pygame.transform.scale(sheet.subsurface(rect), (scaled, scaled))

    def update(self, dt, moving, direction, animation_speed=0.15):
        self.anim_speed = animation_speed
        if direction:
            self.direction = direction
        self.is_moving = moving
        self.anim_timer += dt
        if self.anim_timer >= self.anim_speed:
            self.anim_timer = 0
            n = self.walk_frames if self.is_moving else self.idle_frames
            self.frame_idx = (self.frame_idx + 1) % n

    def draw(self, surface, center_pos):
        kind = "walk" if self.is_moving else "idle"
        frame = self.frames[self.direction][kind][self.frame_idx]
        surface.blit(frame, frame.get_rect(center=center_pos))
