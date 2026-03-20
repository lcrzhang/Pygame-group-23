import pygame
import random
import time

from entities.Player import Player
from entities.Platform import Platform

from entities.Door import Door
from entities.Projectile import Projectile, ProjectileWarning
from levels.Levels import LEVELS, AVAILABLE_MODIFIERS, LOBBY_LEVEL
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

        # Game over state
        self.game_over = False
        self.game_over_achieved_levels = 0
        
        self.levels_played = 0
        self.current_level_index = -1
        self.difficulty = DifficultySettings(0)
        self.active_modifier = None  # LevelModifier | None

        # track time between spawn_units ticks for countdown
        self._last_tick_ms = time.time() * 1000.0

        self.in_lobby = True
        self.load_level(is_lobby=True)

    def load_level(self, index=None, is_lobby=False):
        """Load a hand-crafted level. Pass an index, or None for random."""
        if is_lobby:
            self.current_level_index = -1
            level = LOBBY_LEVEL
            self.levels_played = 0
            self.in_lobby = True
        else:
            if index is None:
                if self.levels_played < len(LEVELS):
                    # Pick sequentially for the first playthrough
                    index = self.levels_played
                else:
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
        if not getattr(self, "in_lobby", False):
            self.levels_played += 1
        self.difficulty = DifficultySettings(self.levels_played)

        # Reset and START the countdown at 1 minute (60 seconds) when entering a level
        self.timer = 60.0
        self.timer_started = not getattr(self, "in_lobby", False)
        # reset last-tick so the first tick doesn't consume a large delta
        self._last_tick_ms = time.time() * 1000.0

        # Spawn door immediately if we are in the lobby
        if getattr(self, "in_lobby", False):
            self.doors = [Door(level.door[0], level.door[1], False)]

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
        # If game over and player pressed Start, restart the run and reset level counter
        if action.is_start_game() and self.game_over:
            # reset players health and state
            for p in self.players.values():
                p.health = Player.max_health
                p.is_ready = False
            # reset progression / counters backwards to lobby
            self.game_over = False
            self.game_over_achieved_levels = 0
            self.levels_played = 0
            self.current_level_index = -1
            self.difficulty = DifficultySettings(0)
            self.active_modifier = None
            self.in_lobby = True
            self.load_level(is_lobby=True)
            return

        if action.is_start_game():
            # start_game signal is used elsewhere; do not auto-start the level timer here
            pass

        # if game is over ignore most inputs
        if self.game_over:
            return

        name = action.get_name()
        if not name in self.players: # if the name is not seen before
            player = Player(self.world_size, name) # create a new player
            player.is_ready = False
            if not getattr(self, "in_lobby", False):
                # Joined mid-game -> start as spectator
                player.health = 0
            self.units.append(player)              # add to units
            self.players[name] = player            # add to players too for fast lookup by name 
        player = self.players[name]
        
        # Don't apply actions if in lobby and marked as ready
        if getattr(player, "is_ready", False) and getattr(self, "in_lobby", False):
            return

        player.apply_action(action, self.current_modifiers)
        player.update(self.platforms, self.world_size, self.current_modifiers)
        
        # Spectators don't interact with the world, but can move as ghosts
        if player.health <= 0 and not getattr(self, "in_lobby", False):
            return
        
        # Check door collisions
        player_rect = pygame.Rect(player.position.x, player.position.y, Player.width, Player.height)
        for door in self.doors:
            if player_rect.colliderect(door.rect):
                if getattr(self, "in_lobby", False):
                    player.is_ready = True
                    player.position.y = -1000 # Teleport away visually
                    player.speed.y = 0
                    
                    # Check if everyone is ready (all active players connected have is_ready)
                    if all(p.is_ready for p in self.players.values()):
                        self.in_lobby = False
                        for p in self.players.values():
                            p.is_ready = False
                            p.health = Player.max_health # revive mid-lobby spectators if needed
                        self.load_level(index=0)
                else:
                    # Trigger a new sequential/random level and teleport everyone
                    self.load_level()
                break
                
        hurt_player = False

        # Check kill zone collisions
        if hasattr(self.current_level, "kill_zones") and self.current_level.kill_zones:
            for kz in self.current_level.kill_zones:
                if player_rect.colliderect(pygame.Rect(*kz)):
                    hurt_player = True
                    break
                
        # Check projectile collisions
        if not hurt_player:
            for proj in list(self.projectiles):
                if player_rect.colliderect(proj.get_rect()):
                    # Hit by a projectile: remove the projectile
                    try:
                        self.projectiles.remove(proj)
                    except ValueError:
                        pass
                    hurt_player = True
                    break

        if hurt_player:
            player.take_damage(1)

            if player.health <= 0:
                # Player died. Check if *everyone* is dead.
                if all(p.health <= 0 for p in self.players.values()):
                    self.game_over = True
                    # record how many levels the player completed (at least 1)
                    self.game_over_achieved_levels = max(1, self.levels_played)
                    # stop hazards/timer
                    self.timer_started = False
                    self.projectiles.clear()
                    self.warnings.clear()
            else:
                # Respawn at the current level's spawn point (fallback to center)
                try:
                    sx, sy = self.current_level.spawn
                except Exception:
                    # fallback positions if no current level set
                    sx = int(self.world_size.x // 2) if hasattr(self.world_size, "x") else int(self.world_size[0] // 2)
                    sy = 50
                player.position.x = int(sx)
                player.position.y = int(sy)
                player.speed.y = 0

    def spawn_units(self):
        """Called regularly by server tick; update projectiles and warnings."""
        now_ms = time.time() * 1000.0
        delta_ms = now_ms - getattr(self, "_last_tick_ms", now_ms)
        self._last_tick_ms = now_ms
        delta_s = max(0.0, delta_ms / 1000.0)

        if getattr(self, "in_lobby", False):
            return

        # Update existing projectiles
        for proj in list(self.projectiles):
            proj.update(self.world_size)
        self.projectiles = [p for p in self.projectiles if not p.is_off_screen(self.world_size)]

        # Spawn pending projectile warnings
        for w in list(self.warnings):
            w.update(delta_s)
            if w.is_expired():
                self.projectiles.append(w.spawn_projectile(speed_mult=self.difficulty.projectile_speed_mult))
                self.warnings.remove(w)

        # random projectiles (warnings) based on time and difficulty
        chance_this_tick = self.difficulty.spawn_rate_per_sec * delta_s
        if random.random() < chance_this_tick:
            # Scale projectile size relative to the map width (2% to 6%)
            min_size = max(10, int(self.world_size.x * 0.02))
            max_size = max(min_size, int(self.world_size.x * 0.06))
            size = random.randint(min_size, max_size)
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
            
            warning = ProjectileWarning(
                spawn_pos=(x, y),
                base_speed=(speed_x, speed_y),
                size=size,
                warning_time=self.difficulty.warning_time,
                projectile_images=getattr(self.current_level, "projectile_images", None)
            )
            self.warnings.append(warning)

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

        # ── Lobby Instructions Text ───────────────────────────────────────────
        if getattr(self, "current_level", None) and hasattr(self.current_level, "instructions") and self.current_level.instructions:
            font = pygame.font.SysFont("Comic Sans MS", 28)
            for i, line in enumerate(self.current_level.instructions):
                text_surf = font.render(line, True, (255, 255, 255))
                x = (surface.get_width() - text_surf.get_width()) // 2
                y = 120 + i * 45
                surface.blit(text_surf, (x, y))

        # ── Level Name Popup and Modifier HUD badge ───────────────────────────
        # Fading logic: show fully for 2 seconds, fade out over 1.5 seconds
        time_elapsed = 60.0 - self.timer
        if time_elapsed < 2.0:
            fade_alpha = 255
        elif time_elapsed < 3.5:
            fade_alpha = int(255 * (1.0 - (time_elapsed - 2.0) / 1.5))
        else:
            fade_alpha = 0

        if getattr(self, "current_level", None) and fade_alpha > 0:
            self._draw_level_name_popup(surface, self.current_level.name, fade_alpha)

        if self.active_modifier is not None and fade_alpha > 0:
            self._draw_modifier_badge(surface, self.active_modifier, fade_alpha)

        # ── Level counter (top-right) ───────────────────────────────────────
        try:
            font = pygame.font.SysFont("Comic Sans MS", 24)
            if getattr(self, "current_level", None) is None:
                level_text = "Welcome"
            else:
                # show played level number starting at 1
                # use levels_played so the counter always starts at 1 for the first entered level
                level_text = f"Level {max(1, self.levels_played)}"
            txt_surf = font.render(level_text, True, (255, 255, 255))
            margin = 10
            x = surface.get_width() - txt_surf.get_width() - margin
            y = margin
            surface.blit(txt_surf, (x, y))
        except Exception:
            pass

        # ── Health hearts (top-right, below level counter) ───────────────────
        try:
            if name in self.players:
                p = self.players[name]
                hearts_total = Player.max_health
                hearts_current = getattr(p, "health", hearts_total)

                # heart drawing helper
                def _draw_heart(surf, cx, cy, size, color=(220, 30, 30)):
                    r = size // 4
                    # two circles
                    pygame.draw.circle(surf, color, (int(cx - r), int(cy - r)), r)
                    pygame.draw.circle(surf, color, (int(cx + r), int(cy - r)), r)
                    # bottom triangle / polygon
                    points = [
                        (int(cx - size // 2), int(cy - r)),
                        (int(cx + size // 2), int(cy - r)),
                        (int(cx), int(cy + size // 2))
                    ]
                    pygame.draw.polygon(surf, color, points)

                heart_size = 14
                gap = 6
                # start drawing under the level text
                start_x = surface.get_width() - margin
                start_y = y + txt_surf.get_height() + 8
                # draw hearts right-to-left
                for i in range(hearts_total):
                    hx = start_x - (i * (heart_size + gap)) - heart_size
                    hy = start_y
                    if i < hearts_current:
                        _draw_heart(surface, hx + heart_size/2, hy + heart_size/2, heart_size, (220,30,30))
                    else:
                        # draw dimmed heart
                        _draw_heart(surface, hx + heart_size/2, hy + heart_size/2, heart_size, (80,80,80))
        except Exception:
            pass

    def _draw_level_name_popup(self, surface, name, fade_alpha=255):
        if fade_alpha <= 0: return

        font = pygame.font.SysFont("Comic Sans MS", 36, bold=True)
        text_surf = font.render(name, True, (255, 255, 255))
        
        padding = 20
        popup_w = text_surf.get_width() + padding * 2
        popup_h = text_surf.get_height() + padding * 2
        
        popup_surf = pygame.Surface((popup_w, popup_h), pygame.SRCALPHA)
        popup_surf.fill((0, 0, 0, 180)) # Dark semitransparent background
        pygame.draw.rect(popup_surf, (255, 255, 255), popup_surf.get_rect(), 2) # White border
        
        popup_surf.blit(text_surf, (padding, padding))
        
        if fade_alpha < 255:
            popup_surf.set_alpha(fade_alpha)
            
        x = (surface.get_width() - popup_w) // 2
        y = 40
        surface.blit(popup_surf, (x, y))

    def _draw_modifier_badge(self, surface, modifier, fade_alpha=255):
        """Draw a small coloured badge in the top-left corner showing the active modifier."""
        if fade_alpha <= 0: return
        
        padding   = 8
        badge_x   = 10
        badge_y   = 10

        font_big   = pygame.font.SysFont("Comic Sans MS", 18)
        font_small = pygame.font.SysFont("Comic Sans MS", 13)

        label_surf = font_big.render(modifier.name, True, (255, 255, 255))
        desc_surf  = font_small.render(modifier.description, True, (220, 220, 220))

        badge_w = max(label_surf.get_width(), desc_surf.get_width()) + padding * 2
        badge_h = label_surf.get_height() + desc_surf.get_height() + padding * 2 + 4

        badge_surf = pygame.Surface((badge_w, badge_h), pygame.SRCALPHA)
        # Background fill with the modifier's colour (keep at 200/255 opacity max for readability)
        badge_surf.fill((*modifier.color, 200))
        # Thin white border
        pygame.draw.rect(badge_surf, (255, 255, 255), badge_surf.get_rect(), 1)

        # Text
        badge_surf.blit(label_surf, (padding, padding))
        badge_surf.blit(desc_surf,  (padding, padding + label_surf.get_height() + 4))

        if fade_alpha < 255:
            badge_surf.set_alpha(fade_alpha)

        surface.blit(badge_surf, (badge_x, badge_y))
