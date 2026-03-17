import pygame

class Platform:
    color = (150, 150, 150)

    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)

    def draw(self, surface):
        pygame.draw.rect(surface, Platform.color, self.rect)
