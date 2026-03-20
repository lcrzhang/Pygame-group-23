import sys
import zmq
import pygame
import os
from SoundManager import SoundManager

from core.Action import Action
from core.Game_State import Game_State

def main(name, port, host):
    # connect to server
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect(f"tcp://{host}:{port}")
    print(f"Connecting to port '{port}' of host '{host}'.")

    # start pygame
    pygame.init()
    # Always open in 1920x1080 as requested
    display = pygame.display.set_mode((1920, 1080), pygame.RESIZABLE)
    pygame.display.set_caption('Dodge Box')
    surface = pygame.display.get_surface()
    
    # Internal render target dimensions
    game_w, game_h = 1920, 1080
    game_surface = pygame.Surface((game_w, game_h))
    
    clock = pygame.time.Clock()
    background_color = (0,0,0)
    background_cache = {}   # cache loaded background images (store original surfaces)
    background_image = None 
    name_textures = Name_Textures()
    game_state = None
    started = False
    just_started = False
    music_volume = 0.5
    MUSIC_VOL_STEP = 0.05

    font = pygame.font.SysFont('Comic Sans MS', 48)
    small_font = pygame.font.SysFont('Comic Sans MS', 24)
    
    # Load Dodge Box specific font
    try:
        title_font = pygame.font.Font(os.path.join("Fonts", "TypefaceMarioWorldPixelFilledRegular-rgVMx.ttf"), 140)
    except Exception:
        title_font = pygame.font.SysFont('Comic Sans MS', 140, bold=True)
    
    try:
        wooden_plate = pygame.image.load(os.path.join("images", "startscreen", "wooden_plate.png")).convert()
        wooden_plate.set_colorkey((255, 255, 255))
    except Exception:
        wooden_plate = None
    
    # sound manager (optional)
    try:
        sound_mgr = SoundManager()
    except Exception:
        sound_mgr = None

    def _find_first_music(folder):
        try:
            for ext in (".ogg", ".mp3", ".wav", ".flac"):
                for f in os.listdir(folder):
                    if f.lower().endswith(ext):
                        return os.path.join(folder, f)
        except Exception:
            return None
        return None

    def play_bg_music():
        # play background music from the sounds folder when game starts
        try:
            if sound_mgr is not None:
                music_path = _find_first_music(sound_mgr.sounds_dir)
                if music_path:
                    sound_mgr.play_music(music_path, loops=-1, volume=music_volume)
        except Exception:
            pass

    try:
        start_bg = pygame.image.load(os.path.join("images", "startscreen", "background.png")).convert()
    except Exception:
        start_bg = None
    try:
        start_logo = pygame.image.load(os.path.join("images", "startscreen", "logo.png")).convert_alpha()
    except Exception:
        start_logo = None
        
    main_menu_state = "main" # main, customize, settings, credits, language
    main_selected_index = 0
    character_color = (255, 255, 255)

    running = True
    play_again_clicked = False
    in_pause_menu = False
    pause_menu_state = "main" # main, settings
    pause_selected_index = 0
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Handle Mouse Clicks & Hovers
            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION):
                mx, my = event.pos
                win_w, win_h = display.get_size()
                # Stretch scaling calculation (independent X and Y)
                scale_x = win_w / game_w
                scale_y = win_h / game_h
                
                gx = int(mx / scale_x)
                gy = int(my / scale_y)

                if gx < 0: gx = 0
                if gx >= game_w: gx = game_w - 1
                if gy < 0: gy = 0
                if gy >= game_h: gy = game_h - 1

                if not started:
                    if main_menu_state == "main":
                        options = ["Start Game", "Customize Character", "Settings", "Credits", "Quit"]
                        for i, opt in enumerate(options):
                            # Adjusted for 1080p positioning
                            by = 500 + i * 80
                            if game_w // 2 - 300 <= gx <= game_w // 2 + 300 and by - 30 <= gy <= by + 30:
                                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                                    if i == 0: started = True; just_started = True; play_bg_music()
                                    elif i == 1: main_menu_state = "customize"; main_selected_index = 0
                                    elif i == 2: main_menu_state = "settings"; main_selected_index = 0
                                    elif i == 3: main_menu_state = "credits"; main_selected_index = 0
                                    elif i == 4: running = False
                                elif event.type == pygame.MOUSEMOTION:
                                    main_selected_index = i
                    elif main_menu_state in ("settings", "customize", "credits", "language"):
                        by = game_h - 150
                        if game_w // 2 - 200 <= gx <= game_w // 2 + 200 and by - 40 <= gy <= by + 40:
                            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                                main_menu_state = "main"; main_selected_index = 0
                            elif event.type == pygame.MOUSEMOTION:
                                main_selected_index = 0
                        
                        if main_menu_state == "customize" and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                            colors = [
                                (255, 105, 180), (255, 0, 0), (0, 0, 255),
                                (255, 255, 0), (0, 255, 0), (0, 0, 0), (255, 255, 255)
                            ]
                            box_w, box_h = 100, 100
                            gap = 30
                            total_w = len(colors) * box_w + (len(colors) - 1) * gap
                            start_x = game_w // 2 - total_w // 2
                            start_y = 500
                            for idx, c_val in enumerate(colors):
                                bx = start_x + idx * (box_w + gap)
                                if bx <= gx < bx + box_w and start_y <= gy < start_y + box_h:
                                    character_color = c_val

                elif started and game_state and not getattr(game_state, "game_over", False):
                    if not in_pause_menu:
                        pass
                    else:
                        if pause_menu_state == "main":
                            for i, opt in enumerate(["Resume", "Settings", "Quit"]):
                                by = game_h // 2 + i * 50 - 50
                                if game_w // 2 - 120 <= gx <= game_w // 2 + 120 and by - 20 <= gy <= by + 20:
                                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                                        if i == 0: in_pause_menu = False
                                        elif i == 1: pause_menu_state = "settings"; pause_selected_index = 0
                                        elif i == 2: in_pause_menu = False; started = False; just_started = False; game_state = None
                                    elif event.type == pygame.MOUSEMOTION:
                                        pause_selected_index = i
                        elif pause_menu_state == "settings":
                            by = game_h // 2 + 70
                            if game_w // 2 - 120 <= gx <= game_w // 2 + 120 and by - 20 <= gy <= by + 20:
                                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                                    pause_menu_state = "main"; pause_selected_index = 0
                                elif event.type == pygame.MOUSEMOTION:
                                    pause_selected_index = 0

            # Handle Keyboard Input
            if started and event.type == pygame.KEYDOWN and game_state and not getattr(game_state, "game_over", False):
                if event.key == pygame.K_ESCAPE:
                    if in_pause_menu:
                        if pause_menu_state == "settings":
                            pause_menu_state = "main"
                            pause_selected_index = 0
                        else:
                            in_pause_menu = False
                    else:
                        in_pause_menu = True
                        pause_menu_state = "main"
                        pause_selected_index = 0
                elif in_pause_menu:
                    options = ["Resume", "Settings", "Quit"] if pause_menu_state == "main" else ["Back"]
                    if event.key in (pygame.K_UP, pygame.K_w):
                        pause_selected_index = (pause_selected_index - 1) % len(options)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        pause_selected_index = (pause_selected_index + 1) % len(options)
                    elif event.key == pygame.K_RETURN:
                        if pause_menu_state == "main":
                            if pause_selected_index == 0: # Resume
                                in_pause_menu = False
                            elif pause_selected_index == 1: # Settings
                                pause_menu_state = "settings"
                                pause_selected_index = 0
                            elif pause_selected_index == 2: # Quit
                                in_pause_menu = False
                                started = False
                                just_started = False
                                game_state = None
                        elif pause_menu_state == "settings":
                            if pause_selected_index == 0: # Back
                                pause_menu_state = "main"
                                pause_selected_index = 0

            if not started and event.type == pygame.KEYDOWN:
                options = ["Start Game", "Customize Character", "Settings", "Credits", "Quit"] if main_menu_state == "main" else ["Back"]
                if event.key in (pygame.K_UP, pygame.K_w):
                    main_selected_index = (main_selected_index - 1) % len(options)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    main_selected_index = (main_selected_index + 1) % len(options)
                elif event.key == pygame.K_RETURN:
                    if main_menu_state == "main":
                        if main_selected_index == 0: started = True; just_started = True; play_bg_music()
                        elif main_selected_index == 1: main_menu_state = "customize"; main_selected_index = 0
                        elif main_selected_index == 2: main_menu_state = "settings"; main_selected_index = 0
                        elif main_selected_index == 3: main_menu_state = "credits"; main_selected_index = 0
                        elif main_selected_index == 4: running = False
                    else:
                        if main_selected_index == 0: main_menu_state = "main"; main_selected_index = 0

            # volume controls (global, works on start screen and in-game)
            if event.type == pygame.KEYDOWN:
                try:
                    if event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                        music_volume = max(0.0, music_volume - MUSIC_VOL_STEP)
                        if sound_mgr is not None:
                            sound_mgr.set_music_volume(music_volume)
                    elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                        music_volume = min(1.0, music_volume + MUSIC_VOL_STEP)
                        if sound_mgr is not None:
                            sound_mgr.set_music_volume(music_volume)
                except Exception:
                    pass
            # If game over, allow clicking the Play Again button (stretch scaling)
            if event.type == pygame.MOUSEBUTTONDOWN and game_state and getattr(game_state, "game_over", False):
                mx, my = event.pos
                win_w, win_h = display.get_size()
                scale_x = win_w / game_w
                scale_y = win_h / game_h
                if scale_x > 0 and scale_y > 0:
                    gx = int(mx / scale_x)
                    gy = int(my / scale_y)
                    # button location (must match drawing below)
                    btn_w, btn_h = 240, 50
                    btn_x = (game_w - btn_w) // 2
                    btn_y = (game_h // 2) + 40
                    if btn_x <= gx <= btn_x + btn_w and btn_y <= gy <= btn_y + btn_h:
                        play_again_clicked = True

        # Update internal resolution if we have a game_state with a larger/different world
        if game_state:
            gw, gh = int(game_state.world_size.x), int(game_state.world_size.y)
            if gw != game_w or gh != game_h:
                game_w, game_h = gw, gh
                game_surface = pygame.Surface((game_w, game_h))

        # Always render to the internal surface, then scale to the current window size.
        # This will fill the entire window (stretching if necessary) to remove black borders.
        game_surface.fill(background_color)

        if not started:
            if start_bg:
                scaled_bg = pygame.transform.scale(start_bg, (game_w, game_h))
                game_surface.blit(scaled_bg, (0, 0))
            else:
                game_surface.fill((20, 20, 40))

            overlay = pygame.Surface((game_w, game_h), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 100))
            game_surface.blit(overlay, (0, 0))

            if main_menu_state == "main":
                if start_logo:
                    logo_w = 220
                    logo_h = int(start_logo.get_height() * (logo_w / start_logo.get_width()))
                    scaled_logo = pygame.transform.smoothscale(start_logo, (logo_w, logo_h))
                    game_surface.blit(scaled_logo, (game_w // 2 - logo_w // 2, 50))
                
                # Draw "Dodge Box" title
                dodge_shadow = title_font.render("Dodge Box", True, (50, 50, 50))
                game_surface.blit(dodge_shadow, dodge_shadow.get_rect(center=(game_w // 2 + 8, 308)))
                
                dodge_title = title_font.render("Dodge Box", True, (255, 255, 255))
                game_surface.blit(dodge_title, dodge_title.get_rect(center=(game_w // 2, 300)))

                options = ["Start Game", "Customize Character", "Settings", "Credits", "Quit"]
                for i, opt in enumerate(options):
                    bx, by = game_w // 2, 500 + i * 80
                    color = (255, 255, 100) if i == main_selected_index else (255, 255, 255)
                    opt_surf = font.render(opt, True, color)
                    game_surface.blit(opt_surf, opt_surf.get_rect(center=(bx, by)))
            elif main_menu_state == "customize":
                title_surf = small_font.render("Select Character Color", True, (255, 255, 255))
                game_surface.blit(title_surf, title_surf.get_rect(center=(game_w // 2, 400)))
                
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
                start_x = game_w // 2 - total_w // 2
                start_y = 500
                
                for idx, (c_val, c_name) in enumerate(colors):
                    bx = start_x + idx * (box_w + gap)
                    rect = pygame.Rect(bx, start_y, box_w, box_h)
                    pygame.draw.rect(game_surface, c_val, rect)
                    if character_color == c_val:
                        pygame.draw.rect(game_surface, (255, 255, 100), rect, 6) # highlight selected
                    else:
                        pygame.draw.rect(game_surface, (200, 200, 200), rect, 2)
                        
                # Demo character preview
                prev_rect = pygame.Rect(game_w // 2 - 50, 680, 100, 100)
                pygame.draw.rect(game_surface, character_color, prev_rect, 8)
                
                color = (255, 255, 100) if 0 == main_selected_index else (255, 255, 255)
                opt_surf = font.render("Back", True, color)
                game_surface.blit(opt_surf, opt_surf.get_rect(center=(game_w // 2, game_h - 150)))

            elif main_menu_state == "settings":
                vol_text2 = pygame.font.SysFont("Comic Sans MS", 28).render(f"Music Volume: {int(music_volume*100)}%", True, (220, 220, 220))
                game_surface.blit(vol_text2, vol_text2.get_rect(center=(game_w // 2, game_h // 2 - 40)))
                
                slider_x = game_w // 2 - 300
                slider_y = game_h // 2
                slider_w = 600
                pygame.draw.line(game_surface, (100, 100, 100), (slider_x, slider_y), (slider_x + slider_w, slider_y), 12)
                filled_w = int(music_volume * slider_w)
                pygame.draw.line(game_surface, (200, 200, 200), (slider_x, slider_y), (slider_x + filled_w, slider_y), 12)
                pygame.draw.circle(game_surface, (255, 255, 100), (slider_x + filled_w, slider_y), 20)

                color = (255, 255, 100) if 0 == main_selected_index else (255, 255, 255)
                opt_surf = font.render("Back", True, color)
                game_surface.blit(opt_surf, opt_surf.get_rect(center=(game_w // 2, game_h - 150)))
            else:
                msg = font.render(f"{main_menu_state.capitalize()} - Coming Soon!", True, (255, 255, 255))
                game_surface.blit(msg, msg.get_rect(center=(game_w // 2, game_h // 2)))

                color = (255, 255, 100) if 0 == main_selected_index else (255, 255, 255)
                opt_surf = font.render("Back", True, color)
                game_surface.blit(opt_surf, opt_surf.get_rect(center=(game_w // 2, game_h - 150)))
        else:
            action = get_action(name, pygame.key.get_pressed(), start_game=just_started or play_again_clicked, set_pause=in_pause_menu, color=character_color)
            just_started = False
            socket.send_pyobj(action) # send action
             
            # Draw background based on last received game_state (if any)
            if game_state and getattr(game_state, "current_level", None):
                lvl_bg = getattr(game_state.current_level, "background", None)
                if isinstance(lvl_bg, (tuple, list)) and len(lvl_bg) == 3:
                    # plain RGB background
                    background_color = tuple(lvl_bg)
                    game_surface.fill(background_color)
                elif isinstance(lvl_bg, str):
                    # image path: load once and scale to game surface size each frame
                    try:
                        if lvl_bg not in background_cache:
                            background_cache[lvl_bg] = pygame.image.load(lvl_bg).convert()
                        bg_orig = background_cache[lvl_bg]
                        bg_scaled = pygame.transform.scale(bg_orig, (game_w, game_h))
                        game_surface.blit(bg_scaled, (0, 0))
                    except Exception:
                        game_surface.fill(background_color)
                else:
                    game_surface.fill(background_color)

                # draw last game_state on top of background
                game_state.draw(name, game_surface, name_textures)

                # Draw timer
                minutes = int(game_state.timer) // 60
                seconds = int(game_state.timer) % 60
                time_str = f"{minutes:02d}:{seconds:02d}"
                time_text = font.render(time_str, False, (255, 255, 255))
                time_rect = time_text.get_rect(midtop=(game_w // 2, 10))
                game_surface.blit(time_text, time_rect)
            else:
                # no game state yet — clear to default
                game_surface.fill(background_color)

            # Receive new game_state from server (blocking until reply)
            try:
                game_state = socket.recv_pyobj()
            except Exception:
                # If receive fails, stop running
                running = False
            else:
                # If we requested "Play Again", server should have reset state.
                # Return client to the start screen and clear local UI state so the player
                # sees the welcome screen again (fully reset).
                if play_again_clicked:
                    # clear UI / caches
                    started = False
                    just_started = False
                    play_again_clicked = False
                    background_cache.clear()
                    background_image = None
                    # reset internal render target to default
                    game_w, game_h = 1920, 1080
                    game_surface = pygame.Surface((game_w, game_h))
                    # drop server state locally so start screen shows
                    game_state = None

        # If server reports game over, draw overlay + Play Again button on the internal game_surface
        if game_state and getattr(game_state, "game_over", False):
            overlay = pygame.Surface((game_w, game_h), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            go_font = pygame.font.SysFont("Comic Sans MS", 48, bold=True)
            small = pygame.font.SysFont("Comic Sans MS", 28)
            txt = go_font.render("GAME OVER", True, (255, 200, 200))
            txt_rect = txt.get_rect(center=(game_w // 2, game_h // 2 - 40))
            overlay.blit(txt, txt_rect)
            achieved = getattr(game_state, "game_over_achieved_levels", 0)
            lvl_msg = f"You reached level {achieved}"
            lvl_txt = small.render(lvl_msg, True, (255, 255, 255))
            lvl_rect = lvl_txt.get_rect(center=(game_w // 2, game_h // 2))
            overlay.blit(lvl_txt, lvl_rect)
            # Play Again button
            btn_w, btn_h = 240, 50
            btn_x = (game_w - btn_w) // 2
            btn_y = (game_h // 2) + 40
            pygame.draw.rect(overlay, (40, 160, 40), (btn_x, btn_y, btn_w, btn_h), border_radius=6)
            pygame.draw.rect(overlay, (255, 255, 255), (btn_x, btn_y, btn_w, btn_h), 2, border_radius=6)
            btn_txt = small.render("Play Again", True, (255, 255, 255))
            btn_rect = btn_txt.get_rect(center=(btn_x + btn_w // 2, btn_y + btn_h // 2))
            overlay.blit(btn_txt, btn_rect)
            # blit overlay onto game_surface (on top) BEFORE scaling so it becomes visible
            game_surface.blit(overlay, (0, 0))



        # Handle Slider Dragging for full screen fill
        is_settings_open = (started and in_pause_menu and pause_menu_state == "settings") or (not started and main_menu_state == "settings")
        if is_settings_open and pygame.mouse.get_pressed()[0]:
            mx, my = pygame.mouse.get_pos()
            win_w, win_h = display.get_size()
            scale_x = win_w / game_w
            scale_y = win_h / game_h
            if scale_x > 0 and scale_y > 0:
                gx = int(mx / scale_x)
                gy = int(my / scale_y)
                slider_x = game_w // 2 - 300
                slider_y = game_h // 2
                slider_w = 600
                if slider_x - 30 <= gx <= slider_x + slider_w + 30 and slider_y - 40 <= gy <= slider_y + 40:
                    fraction = (gx - slider_x) / slider_w
                    music_volume = max(0.0, min(1.0, fraction))
                    try:
                        if sound_mgr is not None: sound_mgr.set_music_volume(music_volume)
                    except Exception:
                        pass


        if in_pause_menu:
            pause_overlay = pygame.Surface((game_w, game_h), pygame.SRCALPHA)
            pause_overlay.fill((0, 0, 0, 200)) # Darker overlay
            
            p_font = pygame.font.SysFont("Comic Sans MS", 48, bold=True)
            p_small = pygame.font.SysFont("Comic Sans MS", 36)
            p_smaller = pygame.font.SysFont("Comic Sans MS", 28)
            
            title_text = "PAUSED" if pause_menu_state == "main" else "SETTINGS"
            title_surf = p_font.render(title_text, True, (255, 255, 255))
            pause_overlay.blit(title_surf, title_surf.get_rect(center=(game_w // 2, game_h // 4)))
            
            if pause_menu_state == "main":
                options = ["Resume", "Settings", "Quit"]
                for i, opt in enumerate(options):
                    color = (255, 255, 100) if i == pause_selected_index else (200, 200, 200)
                    opt_surf = p_small.render(opt, True, color)
                    pause_overlay.blit(opt_surf, opt_surf.get_rect(center=(game_w // 2, game_h // 2 + i * 50 - 50)))
            elif pause_menu_state == "settings":
                vol_text2 = p_smaller.render(f"Music Volume: {int(music_volume*100)}%", True, (220, 220, 220))
                pause_overlay.blit(vol_text2, vol_text2.get_rect(center=(game_w // 2, game_h // 2 - 40)))
                
                # Draw Volume Slider
                slider_x = game_w // 2 - 150
                slider_y = game_h // 2
                slider_w = 300
                pygame.draw.line(pause_overlay, (100, 100, 100), (slider_x, slider_y), (slider_x + slider_w, slider_y), 8)
                filled_w = int(music_volume * slider_w)
                pygame.draw.line(pause_overlay, (200, 200, 200), (slider_x, slider_y), (slider_x + filled_w, slider_y), 8)
                pygame.draw.circle(pause_overlay, (255, 255, 100), (slider_x + filled_w, slider_y), 12)

                color = (255, 255, 100) if 0 == pause_selected_index else (200, 200, 200)
                opt_surf = p_small.render("Back", True, color)
                pause_overlay.blit(opt_surf, opt_surf.get_rect(center=(game_w // 2, game_h // 2 + 70)))

            game_surface.blit(pause_overlay, (0, 0))

        # Stretch the internal game surface to fill the entire window as requested
        win_w, win_h = display.get_size()
        scaled = pygame.transform.smoothscale(game_surface, (win_w, win_h))
        surface.blit(scaled, (0, 0))

        pygame.display.flip()
        clock.tick(60) # run at 60 frames per second

def get_action(name, keys, start_game=False, set_pause=None, color=(255, 255, 255)):
    if set_pause:
        return Action(name, False, False, False, False, start_game, set_pause, color)
    left = keys[pygame.K_LEFT] or keys[pygame.K_a]
    right = keys[pygame.K_RIGHT] or keys[pygame.K_d]
    jump = keys[pygame.K_UP] or keys[pygame.K_w] or keys[pygame.K_SPACE]
    down = keys[pygame.K_DOWN] or keys[pygame.K_s]
    return Action(name, left, right, jump, down, start_game, set_pause, color)

class Name_Textures: # class to generate and store textures of user names

    def __init__(self):
        self.name_textures={}

    def get_texture(self, name):
        if not name in self.name_textures:
            font = pygame.font.SysFont('Comic Sans MS', 20)
            name_texture = font.render(name, False, (255,255,255))
            self.name_textures[name] = name_texture
        return self.name_textures[name]
        
if __name__ == "__main__":
    name = "_"
    port = 2345
    host = "127.0.0.1"
    if len(sys.argv) > 1:
        name = sys.argv[1][:20]
    if len(sys.argv) > 2:
        port = int(sys.argv[2])
    if len(sys.argv)>3:
        host = sys.argv[3]
    main(name, port, host)
