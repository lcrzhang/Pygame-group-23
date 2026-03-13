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
        
        self.platforms = []
        self.doors = []
        self.projectiles = []
        self.timer = 0.0
        self.timer_started = False
        
        self.generate_level()

    def generate_level(self):
        self.platforms = []
        self.projectiles = []
        
        # Ground spawn platform (extends across the whole bottom)
        start_y = self.world_size.y - 40
        self.platforms.append(Platform(0, start_y, self.world_size.x, 40))
        
        # Only 1 exit door at the bottom-right
        self.doors = [Door(self.world_size.x - Door.width - 20, start_y - Door.height, False)]
        
        # Start generating blocks from the left corner
        current_x = 20
        current_y = start_y
        
        # Generate 4-6 ascending platforms
        num_platforms = random.randint(4, 6)
        for _ in range(num_platforms):
            # Move up by a reachable amount (max jump is ~150, but 100 is safer)
            next_y = current_y - random.randint(80, 130)
            
            # Ensure platforms don't generate above the ceiling (door is 80px tall, so keep y > 100)
            if next_y < 100:
                next_y = 100
            
            # Move left or right Randomly
            direction = random.choice([-1, 1])
            # Distance should be reachable horizontally 
            dist = random.randint(80, 200)
            next_x = current_x + direction * dist
            
            plat_w = random.randint(100, 150)
            
            # If it's the last platform, force it to be on the right side
            if _ == num_platforms - 1:
                next_x = random.randint(int(self.world_size.x // 2), int(self.world_size.x - plat_w - 20))
            else:
                # Clamp to screen to ensure it doesn't spawn out of bounds
                if next_x < 0:
                    next_x = random.randint(0, 50)
                elif next_x + plat_w > self.world_size.x:
                    next_x = self.world_size.x - plat_w - random.randint(0, 50)
                
            self.platforms.append(Platform(next_x, next_y, plat_w, 20))
            current_x = next_x
            current_y = next_y
            
        # Teleport all existing players to the left corner of the screen
        for unit in self.units:
            unit.position.x = 20
            unit.position.y = start_y - Player.height - 5
            unit.speed.y = 0

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
                # Trigger a new random level and teleport everyone
                self.generate_level()
                break
                
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
