import pygame

class AnimatedTile(pygame.sprite.Sprite):
    def __init__(self, sprite_sheet, tile_size, frame_coords, anim_speed=0.2):
        """
        sprite_sheet: already loaded pygame.Surface
        tile_size: size of each tile (width and height)
        frame_coords: list of (x, y) tuples (in tiles, not pixels) for the animation sequence
        anim_speed: seconds per frame (float)
        """
        super().__init__()
        self.sprite_sheet = sprite_sheet
        self.tile_size = tile_size
        self.frame_coords = frame_coords
        self.anim_speed = anim_speed
        self.frames = self._extract_frames()
        self.frame_idx = 0
        self.anim_timer = 0
        self.is_animating = True  # Default: animation runs

    def _extract_frames(self):
        frames = []
        for (tx, ty) in self.frame_coords:
            rect = pygame.Rect(tx * self.tile_size, ty * self.tile_size, self.tile_size, self.tile_size)
            frame = self.sprite_sheet.subsurface(rect).copy()
            frames.append(frame)
        return frames

    def update(self, dt):
        if self.is_animating and len(self.frames) > 1:
            self.anim_timer += dt
            if self.anim_timer >= self.anim_speed:
                self.anim_timer = 0
                self.frame_idx = (self.frame_idx + 1) % len(self.frames)

    def draw(self, surface, pos, animate=True):
        """
        surface: pygame.Surface to draw on
        pos: (x, y) tuple in pixels
        animate: if False, always show first frame; if True, animate
        """
        self.is_animating = animate
        frame = self.frames[self.frame_idx] if animate else self.frames[0]
        surface.blit(frame, pos)

# Example usage:
# sheet = pygame.image.load("assets/tiles/animated_water.png").convert_alpha()
# animated_tile = AnimatedTile(
#     sprite_sheet=sheet,
#     tile_size=32,
#     frame_coords=[(0,0), (1,0), (2,0), (3,0)],
#     anim_speed=0.1
# )
# In your game loop:
# animated_tile.update(dt)
# animated_tile.draw(screen, (tile_x, tile_y), animate=True)