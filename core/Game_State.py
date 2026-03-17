import pygame
import random

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

        self.platforms = [Platform(x, y, w, h) for x, y, w, h in level.platforms]
        self.doors = [Door(level.door[0], level.door[1], False)]
        self.projectiles = []
        self.warnings = []
        self.current_modifiers = level.modifiers  # per-level physics

        # Increment difficulty
        self.levels_played += 1
        self.difficulty = DifficultySettings(self.levels_played)

        # Random level modifier (unlocked after MODIFIER_UNLOCK_LEVEL levels played)
        if self.levels_played > MODIFIER_UNLOCK_LEVEL and random.random() < MODIFIER_CHANCE:
            self.active_modifier = random.choice(AVAILABLE_MODIFIERS)
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
        if self.timer_started:
            self.timer += delta_time
        # Advance all warning countdowns
        for warning in self.warnings:
            warning.update(delta_time)

    def update(self, action):
        if action.is_start_game():
            self.timer_started = True

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
        diff = self.difficulty

        # ── Spawn new warnings ───────────────────────────────────────────────
        if random.random() < diff.spawn_chance:
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

            self.warnings.append(ProjectileWarning(
                spawn_pos    = (x, y),
                base_speed   = (speed_x, speed_y),
                size         = size,
                warning_time = diff.warning_time,
            ))

        # ── Promote expired warnings to real projectiles ──────────────────────
        still_waiting = []
        for warning in self.warnings:
            if warning.is_expired():
                self.projectiles.append(
                    warning.spawn_projectile(diff.projectile_speed_mult)
                )
            else:
                still_waiting.append(warning)
        self.warnings = still_waiting

        # ── Update active projectiles ─────────────────────────────────────────
        for proj in self.projectiles:
            proj.update(self.world_size)
        self.projectiles = [p for p in self.projectiles if not p.is_off_screen(self.world_size)]
            
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
