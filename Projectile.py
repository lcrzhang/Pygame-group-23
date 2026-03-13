import pygame
import random

class Projectile:
    
    def __init__(self, position, speed, size):
        self.position = pygame.Vector2(position)
        self.speed = pygame.Vector2(speed)
        self.width = size
        self.height = size
        self.color = (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))
        self.shape = random.choice(['rect', 'circle', 'triangle'])

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
        if self.shape == 'rect':
            rect = self.get_rect()
            pygame.draw.rect(surface, self.color, rect)
        elif self.shape == 'circle':
            radius = self.width // 2
            center = (int(self.position.x + radius), int(self.position.y + radius))
            pygame.draw.circle(surface, self.color, center, radius)
        elif self.shape == 'triangle':
            points = [
                (self.position.x + self.width / 2, self.position.y),
                (self.position.x, self.position.y + self.height),
                (self.position.x + self.width, self.position.y + self.height)
            ]
            pygame.draw.polygon(surface, self.color, points)
