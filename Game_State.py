import pygame
import random

from Player import Player
from Platform import Platform

from Door import Door
from Projectile import Projectile
from Levels import LEVELS

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
        
        self.current_level_index = -1
        self.current_level = None
        # Track time between ticks so we can countdown even though update() doesn't get delta_time
        self._last_tick_ms = pygame.time.get_ticks()
        self.load_level()

    def load_level(self, index=None):
        """Load a hand-crafted level. Pass an index, or None for random."""
        if index is None:
            # Pick randomly, but avoid repeating the same level twice in a row
            choices = [i for i in range(len(LEVELS)) if i != self.current_level_index]
            index = random.choice(choices) if choices else 0
        self.current_level_index = index
        level = LEVELS[index]

        self.platforms = [Platform(x, y, w, h) for x, y, w, h in level.platforms]
        # Do NOT create the door immediately — spawn it only after the timer runs out
        self.doors = []
        self.projectiles = []

        # Remember the current level data so we can spawn the door later
        self.current_level = level

        # Reset and start the countdown at 3 minutes (180 seconds)
        self.timer = 180.0
        self.timer_started = True

        # Teleport all existing players to the spawn point
        spawn_x, spawn_y = level.spawn
        for unit in self.units:
            unit.position.x = spawn_x
            unit.position.y = spawn_y
            unit.speed.y = 0

    def __repr__(self):
        return f"world_size: {self.world_size}\nunits: {self.units}"

    def tick_timer(self, delta_time):
        # delta_time is seconds; count DOWN from timer when started
        if self.timer_started and self.timer > 0.0:
            self.timer -= delta_time
            if self.timer <= 0.0:
                self.timer = 0.0
                # Timer reached zero: spawn/show the door (only once)
                if self.current_level and not self.doors:
                    self.doors = [Door(self.current_level.door[0], self.current_level.door[1], False)]

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
                self.load_level()  # load next (random) hand-crafted level
                break
                
        # Check projectile collisions
        for proj in self.projectiles:
            if player_rect.colliderect(proj.get_rect()):
                # Hit by a projectile: reset position
                player.position.x = self.world_size.x // 2
                player.position.y = 50
                player.speed.y = 0

    def spawn_units(self):
        # Update timer using real time delta (spawn_units is called every tick)
        now_ms = pygame.time.get_ticks()
        delta_ms = now_ms - getattr(self, "_last_tick_ms", now_ms)
        self._last_tick_ms = now_ms
        self.tick_timer(delta_ms / 1000.0)

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
