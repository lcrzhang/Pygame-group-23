import pygame
import random
import time

from entities.Player import Player
from entities.Platform import Platform

from entities.Door import Door
from entities.Projectile import Projectile, ProjectileWarning
from levels.Levels import LEVELS, AVAILABLE_MODIFIERS
from core.Difficulty import DifficultySettings, MODIFIER_UNLOCK_LEVEL, MODIFIER_CHANCE

class Game_State:
    def __init__(self, world_size):
        self.world_size = world_size
        self.players = {}
        self.units = []
        
        self.platforms = []
        self.doors = []
        self.projectiles = []
        self.warnings = []          # ProjectileWarning objects waiting to spawn
        self.timer = 0.0
        self.timer_started = False
        
        self.levels_played = 0
        self.current_level_index = -1
        self.difficulty = DifficultySettings(0)
        self.active_modifier = None  # LevelModifier | None

        # track time between spawn_units ticks for countdown
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
        self.current_level = level
        self.world_size = pygame.Vector2(level.world_size)

        self.platforms = [Platform(x, y, w, h) for x, y, w, h in level.platforms]
        # Do NOT create the door immediately — spawn it only after the timer runs out
        self.doors = []
        self.projectiles = []
        self.warnings = []
        self.current_modifiers = level.modifiers  # per-level physics

        # Increment difficulty
        self.levels_played += 1
        self.difficulty = DifficultySettings(self.levels_played)

        # Reset and START the countdown at 1 minute (60 seconds) when entering a level
        self.timer = 60.0
        self.timer_started = True
        # reset last-tick so the first tick doesn't consume a large delta
        self._last_tick_ms = pygame.time.get_ticks()

        # Random level modifier (unlocked after MODIFIER_UNLOCK_LEVEL levels played)
        if self.levels_played > MODIFIER_UNLOCK_LEVEL and random.random() < MODIFIER_CHANCE:
            # ...existing modifier apply logic...
            pass
        else:
            self.active_modifier = None

        # Teleport all existing players to the spawn point
        spawn_x, spawn_y = level.spawn
        for unit in self.units:
            unit.position.x = spawn_x
            unit.position.y = spawn_y
            unit.speed.y = 0

    def __repr__(self):
        return f"world_size: {self.world_size}\nunits: {self.units}"

    def tick_timer(self, delta_time):
        """Advance countdown timer (delta_time in seconds). Spawn door when timer reaches 0."""
        if not self.timer_started:
            return
        if self.timer <= 0.0:
            return
        self.timer -= delta_time
        if self.timer <= 0.0:
            self.timer = 0.0
            # spawn/show the door once when timer finishes
            if getattr(self, "current_level", None) and not self.doors:
                ld = self.current_level.door
                self.doors = [Door(ld[0], ld[1], False)]

    def update(self, action):
        if action.is_start_game():
            # start_game signal is used elsewhere; do not auto-start the level timer here
            pass

        name = action.get_name()
        if not name in self.players: # if the name is not seen before
            player = Player(self.world_size, name) # create a new player
            self.units.append(player)              # add to units
            self.players[name] = player            # add to players too for fast lookup by name 
        player = self.players[name]
        
        player.apply_action(action, self.current_modifiers)
        player.update(self.platforms, self.world_size, self.current_modifiers)
        
        # Check door collisions
        player_rect = pygame.Rect(player.position.x, player.position.y, Player.width, Player.height)
        for door in self.doors:
            if player_rect.colliderect(door.rect):
                # If we're in the welcome screen, entering the door should start the first level (index 0).
                if getattr(self, "in_welcome", False):
                    self.load_level(index=0)  # this will reset & start the 60s timer
                else:
                    # Trigger a new random level and teleport everyone; timer restarts in load_level
                    self.load_level()
                break
                
        # Check projectile collisions
        for proj in self.projectiles:
            if player_rect.colliderect(proj.get_rect()):
                # Hit by a projectile: reset position
                player.position.x = self.world_size.x // 2
                player.position.y = 50
                player.speed.y = 0

    def spawn_units(self):
        """Called regularly by server tick; update timers, projectiles and warnings."""
        now_ms = pygame.time.get_ticks()
        delta_ms = now_ms - getattr(self, "_last_tick_ms", now_ms)
        self._last_tick_ms = now_ms
        delta_s = max(0.0, delta_ms / 1000.0)

        # advance timer
        self.tick_timer(delta_s)

        # Update existing projectiles
        for proj in list(self.projectiles):
            proj.update(self.world_size)
        self.projectiles = [p for p in self.projectiles if not p.is_off_screen(self.world_size)]

        # Spawn pending projectile warnings
        for w in list(self.warnings):
            w.update(delta_s)
            if w.ready_to_spawn():
                self.projectiles.append(w.spawn_projectile())
                self.warnings.remove(w)

        # occasional random projectiles (keep existing behavior if used elsewhere)
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

        # Draw warning indicators on the screen edge
        for warning in self.warnings:
            warning.draw(surface, self.world_size)
            
        for proj in self.projectiles:
            proj.draw(surface)
            
        for unit in self.units:
            unit.draw(surface, name_textures)

        # ── Active modifier HUD badge ─────────────────────────────────────────
        if self.active_modifier is not None:
            self._draw_modifier_badge(surface, self.active_modifier)

    def _draw_modifier_badge(self, surface, modifier):
        """Draw a small coloured badge in the top-left corner showing the active modifier."""
        padding   = 8
        badge_x   = 10
        badge_y   = 10

        font_big   = pygame.font.SysFont("Comic Sans MS", 18)
        font_small = pygame.font.SysFont("Comic Sans MS", 13)

        label_surf = font_big.render(modifier.name, True, (255, 255, 255))
        desc_surf  = font_small.render(modifier.description, True, (220, 220, 220))

        badge_w = max(label_surf.get_width(), desc_surf.get_width()) + padding * 2
        badge_h = label_surf.get_height() + desc_surf.get_height() + padding * 2 + 4

        badge_rect = pygame.Rect(badge_x, badge_y, badge_w, badge_h)

        # Background fill with the modifier's colour
        bg_surf = pygame.Surface((badge_w, badge_h), pygame.SRCALPHA)
        bg_surf.fill((*modifier.color, 200))  # semi-transparent
        surface.blit(bg_surf, (badge_x, badge_y))

        # Thin white border
        pygame.draw.rect(surface, (255, 255, 255), badge_rect, 1)

        # Text
        surface.blit(label_surf, (badge_x + padding, badge_y + padding))
        surface.blit(desc_surf,  (badge_x + padding, badge_y + padding + label_surf.get_height() + 4))
