import pygame

class AnimatedBackground(pygame.sprite.Sprite):
    def __init__(self, images, pos=(0, 0), frame_rate=144, size_multiplier=1.0):
        super().__init__()
        # Lade und skaliere die Bilder
        self.images = []
        for image in images:
            if size_multiplier != 1.0:
                w, h = image.get_size()
                img = pygame.transform.scale(image, (int(w * size_multiplier), int(h * size_multiplier)))
            self.images.append(img)
        self.index = 0
        self.image = self.images[self.index]
        self.rect = self.image.get_rect(topleft=pos)
        self.frame_rate = frame_rate
        self.animation_speed = 50.0 / self.frame_rate  # Sekunden pro Frame
        self.time_accumulator = 0.0

    def update(self, dt, animation_speed=0.5):
        self.animation_speed = animation_speed
        # dt sollte in Sekunden übergeben werden (z.B. clock.tick()/1000.0)
        self.time_accumulator += dt
        while self.time_accumulator >= self.animation_speed:
            self.index = (self.index + 1) % len(self.images)
            self.image = self.images[self.index]
            self.time_accumulator -= self.animation_speed

    def draw(self, surface, pos=None):
        """Zeichnet den aktuellen Frame auf die angegebene Oberfläche.
        Optional kann eine Position übergeben werden."""
        if pos is not None:
            self.rect.topleft = pos
        surface.blit(self.image, self.rect)