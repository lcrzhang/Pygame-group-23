import pygame
import random

from Player import Player
from Platform import Platform
from Door import Door
from Projectile import Projectile

class Game_State:

    def __init__(self, world_size):
        self.world_size = world_size
        self.players = {}
        self.units = []
        
        self.platforms = [
            Platform(200, 400, 150, 20),
            Platform(500, 300, 150, 20)
        ]
        
        self.doors = [
            Door(0, world_size.y - Door.height - 20, True),
            Door(world_size.x - Door.width, world_size.y - Door.height - 20, False)
        ]
        
        self.projectiles = []
        self.timer = 0.0
        self.timer_started = False

    def __repr__(self):
        return f"world_size: {self.world_size}\nunits: {self.units}"

    def tick_timer(self, delta_time):
        if self.timer_started:
            self.timer += delta_time

    def update(self, action):
        if action.is_start_game():
            self.timer_started = True

        name = action.get_name()
        if not name in self.players: # if the name is not seen before
            player = Player(self.world_size, name) # create a new player
            self.units.append(player)              # add to units
            self.players[name] = player            # add to players too for fast lookup by name 
        player = self.players[name]
        
        player.apply_action(action)
        player.update(self.platforms, self.world_size)
        
        # Check door collisions
        player_rect = pygame.Rect(player.position.x, player.position.y, Player.width, Player.height)
        for door in self.doors:
            if player_rect.colliderect(door.rect):
                # Teleport to the top middle
                player.position.x = self.world_size.x // 2
                player.position.y = 50
                player.speed.y = 0
                
        # Check projectile collisions
        for proj in self.projectiles:
            if player_rect.colliderect(proj.get_rect()):
                # Hit by a projectile: reset position
                player.position.x = self.world_size.x // 2
                player.position.y = 50
                player.speed.y = 0

    def spawn_units(self):
        # Update existing projectiles
        for proj in self.projectiles:
            proj.update(self.world_size)
            
        self.projectiles = [p for p in self.projectiles if not p.is_off_screen(self.world_size)]
            
        # Spawn projectiles occasionally
        if random.random() < 0.03:
            size = random.randint(10, 40)
            edge = random.choice(["top", "left", "right"])
            if edge == "top":
                x = random.randint(0, int(self.world_size.x))
                y = -size - 5
                speed_x = random.uniform(-4, 4)
                speed_y = random.uniform(2, 6)
            elif edge == "left":
                x = -size - 5
                y = random.randint(0, int(self.world_size.y) // 2)
                speed_x = random.uniform(2, 6)
                speed_y = random.uniform(1, 4)
            else:
                x = self.world_size.x + 5
                y = random.randint(0, int(self.world_size.y) // 2)
                speed_x = random.uniform(-6, -2)
                speed_y = random.uniform(1, 4)
            self.projectiles.append(Projectile((x, y), (speed_x, speed_y), size))
        
    def draw(self, name, surface, name_textures):
        rect = pygame.Rect(pygame.Vector2(0, 0), self.world_size)
        white = (255, 255, 255)
        pygame.draw.rect(surface, white, rect, 2)
        
        for platform in self.platforms:
            platform.draw(surface)
            
        for door in self.doors:
            door.draw(surface)
            
        for proj in self.projectiles:
            proj.draw(surface)
            
        for unit in self.units:
            unit.draw(surface, name_textures)
