import pygame

class Door:
    color = (0, 255, 0)
    width = 20
    height = 80

    def __init__(self, x, y, is_left_door):
        self.rect = pygame.Rect(x, y, Door.width, Door.height)
        self.is_left_door = is_left_door

    def draw(self, surface):
        pygame.draw.rect(surface, Door.color, self.rect, 2)
