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
        self.is_paused = False

        # Game over state
        self.game_over = False
        self.game_over_achieved_levels = 0
        
        self.levels_played = 0
        self.current_level_index = -1
        self.difficulty = DifficultySettings(0)
        self.active_modifier = None  # LevelModifier | None

        # Black hole effect state
        self.black_hole_active = False
        self.black_hole_start_time = 0.0

        # track time between spawn_units ticks for countdown
        self._last_tick_ms = time.time() * 1000.0

        self.in_lobby = True
        self.load_level(is_lobby=True)

    def get_compressed_state(self):
        """Returns a minimal serializable dictionary of the dynamic game state."""
        # Dynamic players state
        p_state = {}
        for name, p in self.players.items():
            p_state[name] = {
                'pos': (p.position.x, p.position.y),
                'speed': (p.speed.x, p.speed.y),
                'hp': p.health,
                'color': p.color,
                'facing': p.facing_right,
                'jumps': getattr(p, 'jumps_remaining', 0),
                'og': p.on_ground
            }

        # Dynamic projectiles
        projs = []
        for pr in self.projectiles:
            projs.append({
                'pos': (pr.position.x, pr.position.y),
                'speed': (pr.speed.x, pr.speed.y),
                'sz': pr.width,
                'img': pr.image_path,
                'col': pr.color,
                'sh': pr.shape
            })

        # Dynamic warnings
        warns = []
        for w in self.warnings:
            warns.append({
                'sp': (w.spawn_pos.x, w.spawn_pos.y),
                'bs': (w.base_speed.x, w.base_speed.y),
                'sz': w.size,
                'tr': w.time_remaining,
                'tw': w.warning_time,
                'img': w.chosen_image
            })

        # Dynamic doors
        ds = []
        for door in self.doors:
            ds.append({'pos': (door.rect.x, door.rect.y)})

        return {
            't': self.timer,
            'ts': self.timer_started,
            'p': p_state,
            'j': projs,
            'w': warns,
            'd': ds,
            'mod': self.active_modifier.name if self.active_modifier else None,
            'li': self.current_level_index,
            'lp': self.levels_played,
            'go': self.game_over,
            'goa': self.game_over_achieved_levels,
            'bh': self.black_hole_active,
            'bhs': self.black_hole_start_time,
            'il': self.in_lobby,
            'pa': self.is_paused,
            'ws': (self.world_size.x, self.world_size.y)
        }

    def apply_compressed_state(self, s):
        """Updates this Game_State instance from a compressed state dictionary."""
        # Level change sync
        if s['li'] != self.current_level_index or (s['il'] != self.in_lobby):
            self.load_level(index=s['li'] if s['li'] >= 0 else None, is_lobby=s['il'])
        
        self.timer = s['t']
        self.timer_started = s['ts']
        self.levels_played = s['lp']
        self.game_over = s['go']
        self.game_over_achieved_levels = s['goa']
        self.black_hole_active = s['bh']
        self.black_hole_start_time = s['bhs']
        self.is_paused = s['pa']
        self.world_size = pygame.Vector2(s['ws'])

        # Sync Active Modifier
        if s['mod'] is None:
            self.active_modifier = None
        elif not self.active_modifier or self.active_modifier.name != s['mod']:
            for m in AVAILABLE_MODIFIERS:
                if m.name == s['mod']:
                    self.active_modifier = m
                    break

        # Sync Players
        current_names = set(s['p'].keys())
        # Remove players no longer in the state
        to_remove = [n for n in self.players if n not in current_names]
        for n in to_remove:
            p = self.players.pop(n)
            if p in self.units: self.units.remove(p)

        for name, data in s['p'].items():
            if name not in self.players:
                p = Player(self.world_size, name)
                self.players[name] = p
                self.units.append(p)
            else:
                p = self.players[name]
            
            p.position = pygame.Vector2(data['pos'])
            p.speed = pygame.Vector2(data['speed'])
            p.health = data['hp']
            p.color = data['color']
            p.facing_right = data['facing']
            p.jumps_remaining = data['jumps']
            p.on_ground = data.get('og', False)

        # Sync Projectiles (simpler to just recreate from info list)
        self.projectiles = []
        for pr_data in s['j']:
            pr = Projectile(pr_data['pos'], pr_data['speed'], pr_data['sz'], pr_data['img'])
            pr.color = pr_data['col']
            pr.shape = pr_data['sh']
            self.projectiles.append(pr)

        # Sync Warnings
        self.warnings = []
        for w_data in s['w']:
            w = ProjectileWarning(w_data['sp'], w_data['bs'], w_data['sz'], w_data['tw'])
            w.time_remaining = w_data['tr']
            w.chosen_image = w_data['img']
            self.warnings.append(w)

        # Sync Doors
        if len(self.doors) != len(s['d']):
            self.doors = []
            for d_data in s['d']:
                self.doors.append(Door(d_data['pos'][0], d_data['pos'][1]))
        else:
            for i, d_data in enumerate(s['d']):
                self.doors[i].rect.x, self.doors[i].rect.y = d_data['pos']

    def load_level(self, index=None, is_lobby=False):
        """Load a hand-crafted level. Pass an index, or None for random."""
        if is_lobby:
            self.current_level_index = -1
            level = LOBBY_LEVEL
            self.levels_played = 0
            self.in_lobby = True
        else:
            if index is None:
                # For the first 5 levels, pick sequentially
                if self.levels_played < 5:
                    index = self.levels_played
                else:
                    # After level 5, pick randomly from all levels, avoiding repetition
                    choices = [i for i in range(len(LEVELS)) if i != self.current_level_index]
                    index = random.choice(choices) if choices else 0
            self.current_level_index = index
            level = LEVELS[index]
        self.current_level = level
        self.world_size = pygame.Vector2(level.world_size)

        tex = getattr(level, "platform_image", None)
        self.platforms = [Platform(x, y, w, h, texture_path=tex) for x, y, w, h in level.platforms]
        # Do NOT create the door immediately — spawn it only after the timer runs out
        self.doors = []
        self.projectiles = []
        self.warnings = []
        self.current_modifiers = level.modifiers  # per-level physics
        self.black_hole_active = False # Reset on level load
        self.black_hole_start_time = 0.0

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
        # ── Spawn door immediately if we are in the lobby
        if getattr(self, "in_lobby", False):
            ld = level.door
            # Use a texture for the door
            self.doors = [Door(ld[0], ld[1], False)]

        # Random level modifier (unlocked after MODIFIER_UNLOCK_LEVEL levels played)
        if not is_lobby and self.levels_played >= MODIFIER_UNLOCK_LEVEL and random.random() < MODIFIER_CHANCE:
            eligible_modifiers = [
                m for m in AVAILABLE_MODIFIERS
                if not (m.name == "Ice Skates" and self.current_level_index == 3)
            ]
            self.active_modifier = random.choice(eligible_modifiers)
            basis = level.modifiers
            from levels.Levels import PlayerModifiers
            self.current_modifiers = PlayerModifiers(
                gravity=basis.gravity * self.active_modifier.gravity_mult,
                gravity_hold=basis.gravity_hold * self.active_modifier.gravity_mult,
                friction=basis.friction * self.active_modifier.friction_mult,
                acceleration=basis.acceleration * self.active_modifier.speed_mult,
                max_fall_speed=basis.max_fall_speed,
                jump_speed=basis.jump_speed,
                max_jumps=basis.max_jumps + self.active_modifier.extra_jumps,
            )
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
        if not self.timer_started or getattr(self, "is_paused", False) or self.game_over:
            return
            
        if self.timer_started and self.timer > 0:
            self.timer -= delta_time
        
        # Check if timer reached 0
        if self.timer <= 0:
            self.timer = 0.0
            # spawn/show the door once when timer finishes
            # ── Spawn door when timer reaches 0
            if getattr(self, "current_level", None) and not self.doors:
                if self.levels_played == 5 and not getattr(self, "in_lobby", False):
                    if not self.black_hole_active:
                        self.black_hole_active = True
                        self.black_hole_start_time = time.time()
                else:
                    ld = self.current_level.door
                    # Spawn door with texture
                    self.doors = [Door(ld[0], ld[1], False)]

    def update(self, action):
        name = action.get_name()
        
        if getattr(action, 'disconnect', False):
            self._handle_disconnect(name)
            return

        if action.is_start_game():
            self._handle_game_start(name)
            return

        # ── Debug shortcuts (only when game is running, not in lobby) ──────────
        self._handle_debug_commands(action, name)

        if action.get_set_pause() is not None:
            self.is_paused = action.get_set_pause() if len(self.players) <= 1 else False

        # If game is over or paused, ignore movement inputs
        if self.game_over or getattr(self, "is_paused", False):
            return

        player = self._sync_player_state(action, name)
        
        if getattr(player, "is_ready", False) and getattr(self, "in_lobby", False):
            return

        # Core Movement
        player.apply_action(action, self.current_modifiers)
        if self.active_modifier and getattr(self.active_modifier, "inverted_controls", False):
            player.speed.x -= 2 * (action.is_right() - action.is_left()) * self.current_modifiers.acceleration
        player.update(self.platforms, self.world_size, self.current_modifiers)
        
        # Spectators don't interact with the world
        if player.health <= 0 and not getattr(self, "in_lobby", False):
            return
        
        player_rect = pygame.Rect(player.position.x, player.position.y, Player.width, Player.height)
        
        # Doors & Progressions
        if self._check_door_collisions(player, player_rect):
            return
            
        # Hazards
        if self._check_hazard_collisions(player_rect):
            player.take_damage(1)
            self._handle_player_death_or_respawn(player)

    def _handle_disconnect(self, name):
        """Processes a player disconnecting from the server, cleaning up their entity."""
        if name in self.players:
            p = self.players.pop(name)
            if p in self.units:
                self.units.remove(p)
                
            if not self.players:
                self._full_reset()
                return
                
            if getattr(self, "black_hole_active", False) and self.players:
                if all(p.is_ready for p in self.players.values()):
                    if self.levels_played < 10:
                        self.black_hole_active = False
                        self.black_hole_start_time = 0.0
                        for px in self.players.values(): px.is_ready = False
                        self.load_level(index=None)
                    else:
                        self._full_reset()

    def _handle_game_start(self, name):
        """Processes a player pressing the start/ready button."""
        if getattr(self, "black_hole_active", False):
            if name in self.players:
                self.players[name].is_ready = True
            
            if self.players and all(p.is_ready for p in self.players.values()):
                if self.levels_played < 10:
                    self.black_hole_active = False
                    self.black_hole_start_time = 0.0
                    for px in self.players.values(): px.is_ready = False
                    self.load_level(index=None)
                else:
                    self._full_reset()
        elif getattr(self, "game_over", False):
            self._full_reset()

    def _handle_debug_commands(self, action, name):
        """Processes debugging inputs like skipping levels or triggering modifiers."""
        debug_cmd = getattr(action, "debug_command", None)
        if debug_cmd and not getattr(self, "in_lobby", False):
            if debug_cmd == "skip_timer":
                self.timer = 0.01
            elif debug_cmd == "next_level":
                self.load_level()
            elif debug_cmd == "kill_player":
                if name in self.players:
                    self.players[name].health = 0
            elif debug_cmd.startswith("set_modifier:"):
                mod_name = debug_cmd[len("set_modifier:"):]
                from levels.Levels import AVAILABLE_MODIFIERS
                for m in AVAILABLE_MODIFIERS:
                    if m.name == mod_name:
                        self.active_modifier = m
                        basis = self.current_level.modifiers
                        from levels.Levels import PlayerModifiers
                        self.current_modifiers = PlayerModifiers(
                            gravity=basis.gravity * m.gravity_mult,
                            gravity_hold=basis.gravity_hold * m.gravity_mult,
                            friction=basis.friction * m.friction_mult,
                            acceleration=basis.acceleration * m.speed_mult,
                            max_fall_speed=basis.max_fall_speed,
                            jump_speed=basis.jump_speed,
                            max_jumps=basis.max_jumps + m.extra_jumps,
                        )
                        break

    def _sync_player_state(self, action, name):
        """Ensures the player exists and syncs basic state like color."""
        if not name in self.players:
            player = Player(self.world_size, name)
            player.is_ready = False
            if not getattr(self, "in_lobby", False):
                player.health = 0  # Mid-game joins are spectators
            self.units.append(player)
            self.players[name] = player
        
        player = self.players[name]
        player.color = action.get_color()
        return player

    def _check_door_collisions(self, player, player_rect):
        """Evaluates if a player has reached the exit door to progress the level."""
        for door in self.doors:
            if player_rect.colliderect(door.rect):
                if getattr(self, "in_lobby", False):
                    player.is_ready = True
                    player.position.y = -1000 
                    player.speed.y = 0
                    
                    if all(p.is_ready for p in self.players.values()):
                        self.in_lobby = False
                        for p in self.players.values():
                            p.is_ready = False
                            p.health = Player.max_health
                        self.load_level(index=0)
                else:
                    self.load_level()
                return True
        return False

    def _check_hazard_collisions(self, player_rect):
        """Evaluates if a player's hitbox overlaps with any kill zones or projectiles."""
        if hasattr(self.current_level, "kill_zones") and self.current_level.kill_zones:
            for kz in self.current_level.kill_zones:
                if player_rect.colliderect(pygame.Rect(*kz)):
                    return True
                
        for proj in list(self.projectiles):
            if player_rect.colliderect(proj.get_rect()):
                try: self.projectiles.remove(proj)
                except ValueError: pass
                return True
        return False

    def _handle_player_death_or_respawn(self, player):
        """Evaluates if the entire team is dead (Game Over) or respawns the player."""
        if player.health <= 0:
            if all(p.health <= 0 for p in self.players.values()):
                self.game_over = True
                self.game_over_achieved_levels = max(1, self.levels_played)
                self.timer_started = False
                self.projectiles.clear()
                self.warnings.clear()
        else:
            try: sx, sy = self.current_level.spawn
            except Exception:
                sx = int(self.world_size.x // 2) if hasattr(self.world_size, "x") else int(self.world_size[0] // 2)
                sy = 50
            player.position.x = int(sx)
            player.position.y = int(sy)
            player.speed.y = 0

    def _full_reset(self):
        # reset players health and state
        for p in self.players.values():
            p.health = Player.max_health
            p.is_ready = False
        # reset progression / counters backwards to lobby
        self.game_over = False
        self.black_hole_active = False
        self.game_over_achieved_levels = 0
        self.levels_played = 0
        self.current_level_index = -1
        self.difficulty = DifficultySettings(0)
        self.active_modifier = None
        self.in_lobby = True
        self.load_level(is_lobby=True)

    def spawn_units(self):
        """Called regularly by server tick; update projectiles and warnings."""
        now_ms = time.time() * 1000.0
        delta_ms = now_ms - getattr(self, "_last_tick_ms", now_ms)
        self._last_tick_ms = now_ms
        if getattr(self, "is_paused", False):
            return
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
            
            # Apply modifier overrides
            size_mult = getattr(self.active_modifier, "projectile_size_mult", 1.0) if self.active_modifier else 1.0
            size = max(5, int(size * size_mult))
            
            restrict_edge = getattr(self.active_modifier, "restrict_spawn_edge", None) if self.active_modifier else None
            if restrict_edge == "top":
                edge_choices = ["top"]
            elif restrict_edge == "sides":
                edge_choices = ["left", "right"]
            else:
                edge_choices = ["top", "left", "right"]
            edge = random.choice(edge_choices)
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
            
            # Apply projectile speed modifier
            p_speed_mult = getattr(self.active_modifier, "projectile_speed_mult", 1.0) if self.active_modifier else 1.0
            speed_x *= p_speed_mult
            speed_y *= p_speed_mult

            warning = ProjectileWarning(
                spawn_pos=(x, y),
                base_speed=(speed_x, speed_y),
                size=size,
                warning_time=self.difficulty.warning_time,
                projectile_images=getattr(self.current_level, "projectile_images", None)
            )
            self.warnings.append(warning)

    def draw(self, name, surface, asset_cache):
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
            
        is_viewer_dead = False
        if name in self.players:
            is_viewer_dead = self.players[name].health <= 0
            
        for unit in self.units:
            unit.draw(surface, asset_cache, name, is_viewer_dead, self.active_modifier)

        self._draw_kill_zones(surface)
        self._draw_lobby_instructions(surface)
        
        time_elapsed = 60.0 - self.timer
        fade_alpha = 255 if time_elapsed < 2.0 else int(255 * (1.0 - (time_elapsed - 2.0) / 1.5)) if time_elapsed < 3.5 else 0
        self._draw_level_hud(surface, name, fade_alpha)

    def _draw_kill_zones(self, surface):
        """Draws lava/spikes/kill zones to the surface."""
        if hasattr(self, "current_level") and self.current_level and self.current_level.kill_zones:
            is_ice = getattr(self.current_level, "theme", "") == "ice"
            for (kx, ky, kw, kh) in self.current_level.kill_zones:
                if is_ice:
                    spike_w = 40
                    spike_h = min(kh, 60)
                    spike_color_dark  = (40, 100, 200)   # darker outline
                    num_spikes = kw // spike_w + 1

                    platform_tex_path = getattr(self.current_level, "platform_image", None)
                    spike_tex = self.platforms[0]._load_texture(platform_tex_path) if (platform_tex_path and self.platforms) else None

                    if spike_tex is not None:
                        tw, th = spike_tex.get_size()
                        tiled_surf = pygame.Surface((kw, kh), pygame.SRCALPHA)
                        for ty in range(0, kh, th):
                            for tx in range(0, kw, tw):
                                tiled_surf.blit(spike_tex, (tx, ty))
                        
                        mask_surf = pygame.Surface((kw, kh), pygame.SRCALPHA)
                        mask_surf.fill((0, 0, 0, 0))
                        for i in range(num_spikes):
                            sx = i * spike_w
                            pygame.draw.polygon(mask_surf, (255, 255, 255, 255), [
                                (sx, spike_h), (sx + spike_w // 2, 0), (sx + spike_w, spike_h),
                            ])
                            
                        tiled_surf.blit(mask_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                        surface.blit(tiled_surf, (kx, ky))
                        
                        for i in range(num_spikes):
                            sx = kx + i * spike_w
                            pygame.draw.polygon(surface, spike_color_dark, [
                                (sx, ky + spike_h), (sx + spike_w // 2, ky), (sx + spike_w, ky + spike_h),
                            ], 2)
                    else:
                        spike_color = (80, 160, 255)
                        for i in range(num_spikes):
                            sx = kx + i * spike_w
                            tip_x = sx + spike_w // 2
                            tip_y = ky
                            bl = (sx, ky + spike_h)
                            br = (sx + spike_w, ky + spike_h)
                            pygame.draw.polygon(surface, spike_color, [bl, (tip_x, tip_y), br])
                            pygame.draw.polygon(surface, spike_color_dark, [bl, (tip_x, tip_y), br], 2)
                else:
                    pygame.draw.rect(surface, (220, 50, 50), (kx, ky, kw, kh), 3)

    def _draw_lobby_instructions(self, surface):
        """Draws the instructional text presented in the lobby."""
        if getattr(self, "current_level", None) and hasattr(self.current_level, "instructions") and self.current_level.instructions:
            font = pygame.font.SysFont("Comic Sans MS", 28)
            for i, line in enumerate(self.current_level.instructions):
                text_surf = font.render(line, True, (255, 255, 255))
                x = (surface.get_width() - text_surf.get_width()) // 2
                y = 220 + i * 45
                surface.blit(text_surf, (x, y))

    def _draw_level_hud(self, surface, name, fade_alpha):
        """Draws the level counter, health hearts, and modifier badges."""
        if getattr(self, "current_level", None) and fade_alpha > 0:
            self._draw_level_name_popup(surface, self.current_level.name, fade_alpha)

        if self.active_modifier is not None and fade_alpha > 0:
            self._draw_modifier_badge(surface, self.active_modifier, fade_alpha)

        try:
            font = pygame.font.SysFont("Comic Sans MS", 32)
            if getattr(self, "current_level", None) is None:
                level_text = "Welcome"
            else:
                level_text = f"Level {max(1, self.levels_played)}"
            txt_surf = font.render(level_text, True, (255, 255, 255))
            margin = 10
            x = surface.get_width() - txt_surf.get_width() - margin
            y = margin
            surface.blit(txt_surf, (x, y))
        except Exception:
            pass

        try:
            if name in self.players:
                p = self.players[name]
                hearts_total = Player.max_health
                hearts_current = getattr(p, "health", hearts_total)

                def _draw_heart(surf, cx, cy, size, color=(220, 30, 30)):
                    r = size // 4
                    pygame.draw.circle(surf, color, (int(cx - r), int(cy - r)), r)
                    pygame.draw.circle(surf, color, (int(cx + r), int(cy - r)), r)
                    points = [
                        (int(cx - size // 2), int(cy - r)),
                        (int(cx + size // 2), int(cy - r)),
                        (int(cx), int(cy + size // 2))
                    ]
                    pygame.draw.polygon(surf, color, points)

                heart_size = 24
                gap = 10
                start_x = surface.get_width() - margin
                start_y = y + txt_surf.get_height() + 12
                for i in range(hearts_total):
                    hx = start_x - (i * (heart_size + gap)) - heart_size
                    hy = start_y
                    if i < hearts_current:
                        _draw_heart(surface, hx + heart_size/2, hy + heart_size/2, heart_size, (220,30,30))
                    else:
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
        y = 110
        surface.blit(popup_surf, (x, y))

    def _draw_modifier_badge(self, surface, modifier, fade_alpha=255):
        """Draw a small badge in the top-left corner showing the active modifier."""
        if fade_alpha <= 0: return
        
        padding   = 12
        badge_x   = 12
        badge_y   = 12

        font_big = pygame.font.SysFont("Comic Sans MS", 28, bold=True)
        label_surf = font_big.render(f"⚠ {modifier.name}", True, (255, 255, 255))

        badge_w = label_surf.get_width() + padding * 2
        badge_h = label_surf.get_height() + padding * 2

        badge_surf = pygame.Surface((badge_w, badge_h), pygame.SRCALPHA)
        badge_surf.fill((180, 30, 30, 200))
        pygame.draw.rect(badge_surf, (255, 255, 255), badge_surf.get_rect(), 1)
        badge_surf.blit(label_surf, (padding, padding))

        if fade_alpha < 255:
            badge_surf.set_alpha(fade_alpha)

        surface.blit(badge_surf, (badge_x, badge_y))
