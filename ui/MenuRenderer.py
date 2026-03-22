import pygame

class MenuRenderer:
    """Handles drawing all UI menus to the screen."""
    
    def __init__(self, game_w, game_h, fonts):
        """Initializes the MenuRenderer with screen dimensions and a dictionary of pre-loaded fonts."""
        self.game_w = game_w
        self.game_h = game_h
        self.fonts = fonts  # e.g. {"title": font, "main": font, "small": font}

    def draw_main_menu(self, surface, start_logo, selected_index):
        """Draws the main menu with the game logo, title, and interactive options."""
        if start_logo:
            logo_w = 220
            logo_h = int(start_logo.get_height() * (logo_w / start_logo.get_width()))
            scaled_logo = pygame.transform.smoothscale(start_logo, (logo_w, logo_h))
            surface.blit(scaled_logo, (self.game_w // 2 - logo_w // 2, 50))
        
        title_f = self.fonts['title']
        main_f = self.fonts['main']

        # Draw "Dodge Box" title
        dodge_shadow = title_f.render("Dodge Box", True, (50, 50, 50))
        surface.blit(dodge_shadow, dodge_shadow.get_rect(center=(self.game_w // 2 + 8, 308)))
        
        dodge_title = title_f.render("Dodge Box", True, (255, 255, 255))
        surface.blit(dodge_title, dodge_title.get_rect(center=(self.game_w // 2, 300)))

        options = ["Start Game", "Customize Character", "Settings", "Credits", "Quit"]
        for i, opt in enumerate(options):
            bx, by = self.game_w // 2, 500 + i * 80
            color = (255, 255, 100) if i == selected_index else (255, 255, 255)
            opt_surf = main_f.render(opt, True, color)
            surface.blit(opt_surf, opt_surf.get_rect(center=(bx, by)))

    def draw_customize_menu(self, surface, character_color, selected_index):
        """Draws the character color customization screen, allowing players to select their avatar color."""
        small_f = self.fonts['small']
        main_f = self.fonts['main']

        title_surf = small_f.render("Select Character Color", True, (255, 255, 255))
        surface.blit(title_surf, title_surf.get_rect(center=(self.game_w // 2, 400)))
        
        colors = [
            ((255, 105, 180), "Pink"),
            ((255, 0, 0), "Red"),
            ((0, 0, 255), "Blue"),
            ((255, 255, 0), "Yellow"),
            ((0, 255, 0), "Green"),
            ((0, 0, 0), "Black"),
            ((255, 255, 255), "White")
        ]
        
        box_w, box_h = 100, 100
        gap = 30
        total_w = len(colors) * box_w + (len(colors) - 1) * gap
        start_x = self.game_w // 2 - total_w // 2
        start_y = 500
        
        for idx, (c_val, c_name) in enumerate(colors):
            bx = start_x + idx * (box_w + gap)
            rect = pygame.Rect(bx, start_y, box_w, box_h)
            pygame.draw.rect(surface, c_val, rect)
            if character_color == c_val:
                pygame.draw.rect(surface, (255, 255, 100), rect, 6) # highlight selected
            else:
                pygame.draw.rect(surface, (200, 200, 200), rect, 2)
                
        # Demo character preview
        prev_rect = pygame.Rect(self.game_w // 2 - 50, 680, 100, 100)
        pygame.draw.rect(surface, character_color, prev_rect, 8)
        
        color = (255, 255, 100) if 0 == selected_index else (255, 255, 255)
        opt_surf = main_f.render("Back", True, color)
        surface.blit(opt_surf, opt_surf.get_rect(center=(self.game_w // 2, self.game_h - 150)))

    def draw_settings_menu(self, surface, music_volume, jump_volume, selected_index):
        """Draws the settings screen with sliders for music and jump sound effects."""
        small_f = self.fonts['small']
        main_f = self.fonts['main']

        m_color = (255, 255, 100) if selected_index == 0 else (255, 255, 255)
        j_color = (255, 255, 100) if selected_index == 1 else (255, 255, 255)
        
        vol_text = small_f.render(f"Music Volume: {int(music_volume*100)}%", True, m_color)
        surface.blit(vol_text, vol_text.get_rect(center=(self.game_w // 2, self.game_h // 2 - 100)))
        
        slider_x = self.game_w // 2 - 300
        slider_y = self.game_h // 2 - 60
        slider_w = 600
        pygame.draw.line(surface, (100, 100, 100), (slider_x, slider_y), (slider_x + slider_w, slider_y), 12)
        filled_w = int(music_volume * slider_w)
        pygame.draw.line(surface, (200, 200, 200), (slider_x, slider_y), (slider_x + filled_w, slider_y), 12)
        pygame.draw.circle(surface, m_color, (slider_x + filled_w, slider_y), 20)

        j_vol_text = small_f.render(f"Jump Volume: {int(jump_volume*100)}%", True, j_color)
        surface.blit(j_vol_text, j_vol_text.get_rect(center=(self.game_w // 2, self.game_h // 2 + 20)))
        
        j_slider_y = self.game_h // 2 + 60
        pygame.draw.line(surface, (100, 100, 100), (slider_x, j_slider_y), (slider_x + slider_w, j_slider_y), 12)
        j_filled_w = int(jump_volume * slider_w)
        pygame.draw.line(surface, (200, 200, 200), (slider_x, j_slider_y), (slider_x + j_filled_w, j_slider_y), 12)
        pygame.draw.circle(surface, j_color, (slider_x + j_filled_w, j_slider_y), 20)

        b_color = (255, 255, 100) if selected_index == 2 else (255, 255, 255)
        opt_surf = main_f.render("Back", True, b_color)
        surface.blit(opt_surf, opt_surf.get_rect(center=(self.game_w // 2, self.game_h - 150)))

    def draw_credits_menu(self, surface, selected_index):
        """Draws the credits screen displaying the creators of the game."""
        main_f = self.fonts['main']
        title = main_f.render("Game made by:", True, (255, 255, 255))
        surface.blit(title, title.get_rect(center=(self.game_w // 2, self.game_h // 2 - 180)))

        names = ["Patrick Lira van de Meent", "Leo Zhang", "Luuk van der Duim", "Jelle Zegers", "soundtrack: Fun Time by Zambolino"]
        for i, n in enumerate(names):
            n_surf = main_f.render(n, True, (200, 200, 255))
            surface.blit(n_surf, n_surf.get_rect(center=(self.game_w // 2, self.game_h // 2 - 60 + i * 80)))
        
        color = (255, 255, 100) if 0 == selected_index else (255, 255, 255)
        opt_surf = main_f.render("Back", True, color)
        surface.blit(opt_surf, opt_surf.get_rect(center=(self.game_w // 2, self.game_h - 150)))

    def draw_pause_main(self, surface, selected_index, p_small):
        """Draws the main pause menu overlay during active gameplay."""
        options = ["Resume", "Settings", "Quit"]
        for i, opt in enumerate(options):
            color = (255, 255, 100) if i == selected_index else (200, 200, 200)
            opt_surf = p_small.render(opt, True, color)
            surface.blit(opt_surf, opt_surf.get_rect(center=(self.game_w // 2, self.game_h // 2 + i * 80 - 80)))

    def draw_pause_settings(self, surface, music_volume, jump_volume, selected_index, p_smaller, p_small):
        """Draws the settings menu overlay accessible from within the pause menu."""
        m_color = (255, 255, 100) if selected_index == 0 else (220, 220, 220)
        j_color = (255, 255, 100) if selected_index == 1 else (220, 220, 220)
        
        vol_text = p_smaller.render(f"Music Volume: {int(music_volume*100)}%", True, m_color)
        surface.blit(vol_text, vol_text.get_rect(center=(self.game_w // 2, self.game_h // 2 - 100)))
        
        # Draw Music Volume Slider
        slider_x = self.game_w // 2 - 225
        slider_y = self.game_h // 2 - 40
        slider_w = 450
        pygame.draw.line(surface, (100, 100, 100), (slider_x, slider_y), (slider_x + slider_w, slider_y), 12)
        filled_w = int(music_volume * slider_w)
        pygame.draw.line(surface, (200, 200, 200), (slider_x, slider_y), (slider_x + filled_w, slider_y), 12)
        pygame.draw.circle(surface, m_color, (slider_x + filled_w, slider_y), 18)

        j_vol_text = p_smaller.render(f"Jump Volume: {int(jump_volume*100)}%", True, j_color)
        surface.blit(j_vol_text, j_vol_text.get_rect(center=(self.game_w // 2, self.game_h // 2 + 20)))
        
        # Draw Jump Volume Slider
        j_slider_y = self.game_h // 2 + 80
        pygame.draw.line(surface, (100, 100, 100), (slider_x, j_slider_y), (slider_x + slider_w, j_slider_y), 12)
        j_filled_w = int(jump_volume * slider_w)
        pygame.draw.line(surface, (200, 200, 200), (slider_x, j_slider_y), (slider_x + j_filled_w, j_slider_y), 12)
        pygame.draw.circle(surface, j_color, (slider_x + j_filled_w, j_slider_y), 18)

        b_color = (255, 255, 100) if selected_index == 2 else (255, 255, 255)
        opt_surf = p_small.render("Back", True, b_color)
        surface.blit(opt_surf, opt_surf.get_rect(center=(self.game_w // 2, self.game_h - 150)))
