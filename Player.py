import pygame

class Player:
    width = 40
    height = 40
    color = (255, 255, 255)
        
    def __init__(self, world_size, name):
        self.name = name
        self.position = pygame.Vector2(world_size.x // 2, world_size.y // 2)
        self.speed = pygame.Vector2(0, 0)
        self.on_ground = False
        self.is_jumping_btn_held = False

    def __repr__(self):
        return f"position: {self.position} speed: {self.speed}"

    def get_position(self):
        return self.position
    
    def apply_action(self, action):
        accel = 1.0
        if action.is_left():
            self.speed.x -= accel
        if action.is_right():
            self.speed.x += accel
            
        self.is_jumping_btn_held = action.is_jump()
        if self.is_jumping_btn_held and self.on_ground:
            self.speed.y = -12
            self.on_ground = False

    def update(self, platforms, world_size):
        # Apply gravity
        if self.speed.y < 0 and not self.is_jumping_btn_held:
            self.speed.y += 1.5
        else:
            self.speed.y += 0.5
        
        # Apply friction
        self.speed.x *= 0.85
        
        # Cap falling speed
        if self.speed.y > 15:
            self.speed.y = 15

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
            
        for platform in platforms:
            if player_rect.colliderect(platform.rect):
                if self.speed.x > 0: # Moving right
                    player_rect.right = platform.rect.left
                    self.position.x = player_rect.x
                    self.speed.x = 0
                elif self.speed.x < 0: # Moving left
                    player_rect.left = platform.rect.right
                    self.position.x = player_rect.x
                    self.speed.x = 0

        # Move Y
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

        for platform in platforms:
            if player_rect.colliderect(platform.rect):
                if self.speed.y > 0: # Falling down
                    player_rect.bottom = platform.rect.top
                    self.position.y = player_rect.y
                    self.speed.y = 0
                    self.on_ground = True
                elif self.speed.y < 0: # Jumping up
                    player_rect.top = platform.rect.bottom
                    self.position.y = player_rect.y
                    self.speed.y = 0

    def draw(self, surface, name_textures):
        rect = pygame.Rect(self.position.x, self.position.y, Player.width, Player.height)
        pygame.draw.rect(surface, Player.color, rect, 4)
        name_texture = name_textures.get_texture(self.name)
        text_offset = pygame.Vector2(name_texture.get_size())
        text_offset.x /= 2
        text_offset.x -= Player.width / 2
        text_offset.y += 10
        surface.blit(name_texture, self.position - text_offset)
