import pygame

class Platform_jump:
    color = (127, 255, 255)

    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)

    def draw(self, surface):
        pygame.draw.rect(surface, Platform_jump.color, self.rect)