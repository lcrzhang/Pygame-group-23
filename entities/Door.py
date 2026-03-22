import pygame

class Door:
    """
    Represents the exit door in a level.
    Uses a globally cached texture to avoid reloading the image multiple times.
    """
    color = (0, 255, 0)
    width = 50
    height = 80

    # Class-level cached texture
    _cached_texture = None
    _cached_texture_path = None

    @classmethod
    def preload_texture(cls, path):
        """Call this after pygame.display.set_mode()"""
        cls._cached_texture_path = path
        try:
            img = pygame.image.load(path).convert_alpha()
            img = pygame.transform.scale(img, (cls.width, cls.height))
            cls._cached_texture = img
        except Exception as e:
            print(f"Failed to load door texture: {path} ({e})")
            cls._cached_texture = None

    def __init__(self, x, y, is_left_door):
        """Initializes the door at the specified position. is_left_door determines texture flip."""
        self.rect = pygame.Rect(x, y, Door.width, Door.height)
        self.is_left_door = is_left_door

    def draw(self, surface):
        """Draws the door texture if cached, otherwise falls back to a green outline."""
        if Door._cached_texture:
            img = Door._cached_texture
            if self.is_left_door:
                img = pygame.transform.flip(img, True, False)
            surface.blit(img, self.rect.topleft)
        else:
            pygame.draw.rect(surface, Door.color, self.rect, 2)