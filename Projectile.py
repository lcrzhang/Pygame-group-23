import pygame

class Projectile:
    color = (255, 0, 0)
    
    def __init__(self, position, speed, size):
        self.position = pygame.Vector2(position)
        self.speed = pygame.Vector2(speed)
        self.width = size
        self.height = size

    def update(self, world_size):
        self.position += self.speed

    def is_off_screen(self, world_size):
        if self.position.x + self.width < 0 and self.speed.x < 0:
            return True
        if self.position.x > world_size.x and self.speed.x > 0:
            return True
        if self.position.y + self.height < 0 and self.speed.y < 0:
            return True
        if self.position.y > world_size.y and self.speed.y > 0:
            return True
        return False

    def get_rect(self):
        return pygame.Rect(self.position.x, self.position.y, self.width, self.height)

    def draw(self, surface):
        rect = self.get_rect()
        pygame.draw.rect(surface, Projectile.color, rect)
