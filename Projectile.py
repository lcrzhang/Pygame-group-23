import pygame

class Projectile:
    width = 10
    height = 10
    color = (255, 0, 0)
    
    def __init__(self, position, speed):
        self.position = pygame.Vector2(position)
        self.speed = pygame.Vector2(speed)

    def update(self, world_size):
        self.position += self.speed
        
        # Bounce off walls
        if self.position.x < 0 or self.position.x > world_size.x - Projectile.width:
            self.speed.x = -self.speed.x
        if self.position.y < 0 or self.position.y > world_size.y - Projectile.height:
            self.speed.y = -self.speed.y

    def get_rect(self):
        return pygame.Rect(self.position.x, self.position.y, Projectile.width, Projectile.height)

    def draw(self, surface):
        rect = self.get_rect()
        pygame.draw.rect(surface, Projectile.color, rect)
