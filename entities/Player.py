import pygame

class Player:
    width = 40
    height = 40
    max_health = 10
        
    def __init__(self, world_size, name):
        self.name = name
        self.color = (255, 255, 255)
        self.position = pygame.Vector2(world_size.x // 2, world_size.y // 2)
        self.speed = pygame.Vector2(0, 0)
        self.on_ground = False
        self.is_jumping_btn_held = False
        self.drop_through = False
        self.health = Player.max_health

    def __repr__(self):
        return f"position: {self.position} speed: {self.speed}"

    def get_position(self):
        return self.position
    
    def apply_action(self, action, modifiers=None):
        from levels.Levels import PlayerModifiers
        if modifiers is None:
            modifiers = PlayerModifiers()

        if action.is_left():
            self.speed.x -= modifiers.acceleration
        if action.is_right():
            self.speed.x += modifiers.acceleration
            
        self.is_jumping_btn_held = action.is_jump()
        if self.is_jumping_btn_held and self.on_ground:
            # increase jump impulse so jump height is higher
            self.speed.y = modifiers.jump_speed * 1.2
            self.on_ground = False

        # Drop through platforms when holding down while on a platform
        self.drop_through = action.is_down()
        if self.drop_through and self.on_ground:
            self.on_ground = False
            # Give a small downward push so we actually clear the platform
            self.speed.y = 4

    def update(self, platforms, world_size, modifiers=None):
        from levels.Levels import PlayerModifiers
        if modifiers is None:
            modifiers = PlayerModifiers()

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

    def draw(self, surface, name_textures):
        rect = pygame.Rect(self.position.x, self.position.y, Player.width, Player.height)
        pygame.draw.rect(surface, self.color, rect, 4)
        name_texture = name_textures.get_texture(self.name)
        text_offset = pygame.Vector2(name_texture.get_size())
        text_offset.x /= 2
        text_offset.x -= Player.width / 2
        text_offset.y += 10
        surface.blit(name_texture, self.position - text_offset)

    def take_damage(self, amount=1):
        self.health = max(0, self.health - amount)
