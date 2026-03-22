import pygame

class Player:
    """
    Represents a player entity in the game world. 
    Handles physics velocity, position, health, and applies input actions to movement.
    """
    width = 40
    height = 40
    max_health = 10
        
    def __init__(self, world_size, name):
        """Initializes a new player at the center of the world."""
        self.name = name
        self.color = (255, 255, 255)
        self.position = pygame.Vector2(world_size.x // 2, world_size.y // 2)
        self.speed = pygame.Vector2(0, 0)
        self.on_ground = False
        self.is_jumping_btn_held = False
        self.drop_through = False
        self.health = Player.max_health
        self.facing_right = True

    def __repr__(self):
        return f"position: {self.position} speed: {self.speed}"

    def get_position(self):
        """Returns the current absolute (x, y) Vector2 position of the player."""
        return self.position
    
    def apply_action(self, action, modifiers=None):
        """
        Parses a client Action object and applies horizontal and vertical impulses 
        to the player's speed vector, adhering to the active physics modifiers.
        """
        from levels.Levels import PlayerModifiers
        if modifiers is None:
            modifiers = PlayerModifiers()

        if self.health <= 0:
            if action.is_left(): 
                self.speed.x -= modifiers.acceleration
                self.facing_right = False
            if action.is_right(): 
                self.speed.x += modifiers.acceleration
                self.facing_right = True
            if action.is_jump(): self.speed.y -= modifiers.acceleration
            if action.is_down(): self.speed.y += modifiers.acceleration
            return

        if action.is_left():
            self.speed.x -= modifiers.acceleration
            self.facing_right = False
        if action.is_right():
            self.speed.x += modifiers.acceleration
            self.facing_right = True
            
        just_pressed_jump = action.is_jump() and not getattr(self, "prev_jump_held", False)
        self.prev_jump_held = action.is_jump()
        self.is_jumping_btn_held = action.is_jump()
        
        jumps_rem = getattr(self, "jumps_remaining", modifiers.max_jumps)
        if just_pressed_jump and jumps_rem > 0:
            # increase jump impulse so jump height is higher
            self.speed.y = modifiers.jump_speed * 1.2
            self.on_ground = False
            self.just_jumped = True
            self.jumps_remaining = jumps_rem - 1

        # Drop through platforms when holding down while on a platform
        self.drop_through = action.is_down()
        if self.drop_through and self.on_ground:
            self.on_ground = False
            # Give a small downward push so we actually clear the platform
            self.speed.y = 4

    def update(self, platforms, world_size, modifiers=None):
        """
        Applies gravity, friction, and calculates collisions against platforms and the 
        world boundaries to update the player's final position for the current tick.
        """
        from levels.Levels import PlayerModifiers
        if modifiers is None:
            modifiers = PlayerModifiers()

        if self.health <= 0:
            self.speed.x *= modifiers.friction
            self.speed.y *= modifiers.friction
            
            self.position.x += self.speed.x
            self.position.y += self.speed.y
            
            if self.position.x < 0:
                self.position.x = 0
                self.speed.x = 0
            elif self.position.x > world_size.x - Player.width:
                self.position.x = world_size.x - Player.width
                self.speed.x = 0
                
            if self.position.y < 0:
                self.position.y = 0
                self.speed.y = 0
            elif self.position.y > world_size.y - Player.height:
                self.position.y = world_size.y - Player.height
                self.speed.y = 0
            
            self.on_ground = (self.position.y >= world_size.y - Player.height)
            return

        # Apply gravity
        if self.speed.y < 0 and not self.is_jumping_btn_held:
            self.speed.y += modifiers.gravity_hold
        else:
            self.speed.y += modifiers.gravity
        
        # Apply friction
        self.speed.x *= modifiers.friction
        
        # Cap falling speed
        if self.speed.y > modifiers.max_fall_speed:
            self.speed.y = modifiers.max_fall_speed

        # Move X
        self.position.x += self.speed.x
        player_rect = pygame.Rect(self.position.x, self.position.y, Player.width, Player.height)
        
        # Check X collisions
        # First world boundaries
        if self.position.x < 0:
            self.position.x = 0
            self.speed.x = 0
            player_rect.x = 0
        elif self.position.x > world_size.x - Player.width:
            self.position.x = world_size.x - Player.width
            self.speed.x = 0
            player_rect.x = int(self.position.x)
 
        # Move Y (remember previous vertical position so we only land when coming from above)
        prev_bottom = player_rect.bottom
        self.position.y += self.speed.y
        player_rect.y = int(self.position.y)
        self.on_ground = False
        
        # Check Y collisions
        if self.position.y < 0:
            self.position.y = 0
            self.speed.y = 0
            player_rect.y = 0
        elif self.position.y > world_size.y - Player.height:
            self.position.y = world_size.y - Player.height
            self.speed.y = 0
            self.on_ground = True
            player_rect.y = int(self.position.y)

        # If we pressed down while on a platform, allow falling through for one tick
        drop_through = self.drop_through
        self.drop_through = False

        for platform in platforms:
            if player_rect.colliderect(platform.rect):
                # Treat the bottom-most platform (the “floor”) as solid even when holding down.
                is_floor = platform.rect.bottom >= world_size.y
                if self.speed.y > 0 and prev_bottom <= platform.rect.top and (not drop_through or is_floor): # Falling down
                    player_rect.bottom = platform.rect.top
                    self.position.y = player_rect.y
                    self.speed.y = 0
                    self.on_ground = True
                    self.jumps_remaining = modifiers.max_jumps

    def draw(self, surface, asset_cache, viewer_name=None, is_viewer_dead=False, active_modifier=None):
        if self.health <= 0:
            # Visible if it's the local player, or if the local player is also dead
            if self.name != viewer_name and not is_viewer_dead:
                return # Invisible to living players
                
            # If inverted controls are active, our movement direction/logic is flipped
            is_inverted = active_modifier and getattr(active_modifier, "inverted_controls", False)
            should_flip = (self.facing_right and not is_inverted) or (not self.facing_right and is_inverted)
            
            ghost_img = asset_cache.get_ghost_texture(self.color, should_flip)
            
            if ghost_img:
                # Offset by -10, -10 to center 60x60 sprite over 40x40 hitbox
                surface.blit(ghost_img, (int(self.position.x - 10), int(self.position.y - 10)))
            else:
                ghost_size = 60
                ghost_surf = pygame.Surface((ghost_size, ghost_size), pygame.SRCALPHA)
                pygame.draw.rect(ghost_surf, (*self.color, 255), (0, 0, ghost_size, ghost_size), 4)
                surface.blit(ghost_surf, (int(self.position.x - 10), int(self.position.y - 10)))
                
            name_texture = asset_cache.get_texture(self.name)
            name_surf = name_texture.copy()
            name_surf.set_alpha(128)
            text_offset = pygame.Vector2(name_texture.get_size())
            text_offset.x /= 2
            text_offset.x -= Player.width / 2
            text_offset.y += 10
            surface.blit(name_surf, self.position - text_offset)
            return

        rect = pygame.Rect(self.position.x, self.position.y, Player.width, Player.height)
        pygame.draw.rect(surface, self.color, rect, 4)
        name_texture = asset_cache.get_texture(self.name)
        text_offset = pygame.Vector2(name_texture.get_size())
        text_offset.x /= 2
        text_offset.x -= Player.width / 2
        text_offset.y += 10
        surface.blit(name_texture, self.position - text_offset)

    def take_damage(self, amount=1):
        self.health = max(0, self.health - amount)
