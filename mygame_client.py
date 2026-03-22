import sys
import zmq
import pygame
import os
import time
import math
from PIL import Image, ImageSequence
from SoundManager import SoundManager

from core.Action import Action
from core.Game_State import Game_State
from entities.Door import Door
from ui.MenuRenderer import MenuRenderer
from network.NetworkClient import NetworkClient

def main(name, port, host):
    # connect to server
    network_client = NetworkClient(host, port)

    # start pygame
    pygame.init()
    # Always open in 1920x1080 as requested
    display = pygame.display.set_mode((1920, 1080), pygame.RESIZABLE)
    pygame.display.set_caption('Dodge Box')
    surface = pygame.display.get_surface()
    Door.preload_texture("images/general (All levels)/door.jpg")
    
    # Internal render target dimensions
    game_w, game_h = 1920, 1080
    game_surface = pygame.Surface((game_w, game_h))
    
    clock = pygame.time.Clock()
    background_color = (0,0,0)
    background_cache = {}   # cache loaded background images (store original surfaces)
    
    class GIFPlayer:
        def __init__(self, filename):
            self.filename = filename
            self.frames = []
            self.durations = []
            self.last_frame_time = 0
            self.current_frame_idx = 0
            self._load_frames()

        def _load_frames(self):
            if not os.path.exists(self.filename):
                return
            with Image.open(self.filename) as img:
                for frame in ImageSequence.Iterator(img):
                    f = frame.convert('RGBA')
                    pygame_image = pygame.image.fromstring(f.tobytes(), f.size, f.mode)
                    self.frames.append(pygame_image)
                    self.durations.append(frame.info.get('duration', 100)) # ms

        def get_current_frame(self):
            if not self.frames:
                return None
            now = pygame.time.get_ticks()
            if now - self.last_frame_time > self.durations[self.current_frame_idx]:
                self.current_frame_idx = (self.current_frame_idx + 1) % len(self.frames)
                self.last_frame_time = now
            return self.frames[self.current_frame_idx]

    blackhole_player = None # Lazy load later
    background_image = None 
    asset_cache = AssetCache()
    
    # Font for black hole lore
    lore_font = pygame.font.SysFont("Comic Sans MS", 60, italic=True)
    
    # State for black hole menu
    black_hole_menu_active = False
    black_hole_selected_index = 0
    continue_playing_clicked = False
    
    game_state = Game_State(pygame.Vector2(game_w, game_h))
    started = False
    just_started = False
    prev_jumps = None
    music_volume = 0.5
    jump_volume = 0.3
    last_jump_test_time = 0
    MUSIC_VOL_STEP = 0.05

    font = pygame.font.SysFont('Comic Sans MS', 48)
    small_font = pygame.font.SysFont('Comic Sans MS', 24)
    timer_font = pygame.font.SysFont('Comic Sans MS', 72)
    
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
        jump_sound = pygame.mixer.Sound("sounds/sfx/lumora_studios-pixel-jump-319167.mp3")
        if jump_sound:
            jump_sound.set_volume(jump_volume)
    except Exception:
        sound_mgr = None
        jump_sound = None

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
    debug_command = None   # Set by F-key shortcuts each frame
    
    # Initialize MenuRenderer
    menu_fonts = {
        'title': title_font,
        'main': font,
        'small': small_font
    }
    menu_renderer = MenuRenderer(game_w, game_h, menu_fonts)

    running = True
    play_again_clicked = False
    in_pause_menu = False
    pause_menu_state = "main" # main, settings
    pause_selected_index = 0
    debug_command = None   # cleared each frame; set by F-key events
    debug_toast_text = ""   # short-lived on-screen notification (F4 modifier cycle)
    debug_toast_until = 0   # pygame ticks timestamp when toast expires
    while running:
        debug_command = None   # Reset each frame so it only fires once
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

                if black_hole_menu_active:
                    options = ["Continue Playing", "Main Menu"]
                    for i, opt in enumerate(options):
                        by = game_h // 2 + i * 80 - 80
                        if game_w // 2 - 200 <= gx <= game_w // 2 + 200 and by - 30 <= gy <= by + 30:
                            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                                if i == 0:
                                    continue_playing_clicked = True
                                elif i == 1:
                                    try:
                                        d_action = get_action(name, pygame.key.get_pressed(), disconnect=True)
                                        network_client.send_disconnect_action(d_action)
                                    except Exception: pass
                                    started = False
                                    just_started = False
                                    black_hole_menu_active = False
                                    game_state = None
                            elif event.type == pygame.MOUSEMOTION:
                                black_hole_selected_index = i
                    
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        continue # swallow clicks if menu is active
                
                if not started:
                    if main_menu_state == "main":
                        options = ["Start Game", "Customize Character", "Settings", "Credits", "Quit"]
                        for i, opt in enumerate(options):
                            # Adjusted for 1080p positioning
                            by = 500 + i * 80
                            if game_w // 2 - 300 <= gx <= game_w // 2 + 300 and by - 30 <= gy <= by + 30:
                                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                                    if i == 0:
                                        if not network_client.running:
                                            network_client = NetworkClient(host, port)
                                        started = True; just_started = True; play_bg_music()
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
                                by = game_h // 2 + i * 80 - 80
                                if game_w // 2 - 200 <= gx <= game_w // 2 + 200 and by - 30 <= gy <= by + 30:
                                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                                        if i == 0: in_pause_menu = False
                                        elif i == 1: pause_menu_state = "settings"; pause_selected_index = 0
                                        elif i == 2: 
                                            in_pause_menu = False
                                            try:
                                                d_action = get_action(name, pygame.key.get_pressed(), disconnect=True)
                                                network_client.send_disconnect_action(d_action)
                                            except Exception: pass
                                            started = False
                                            just_started = False
                                            game_state = None
                                    elif event.type == pygame.MOUSEMOTION:
                                        pause_selected_index = i
                        elif pause_menu_state == "settings":
                            by = game_h - 150
                            if game_w // 2 - 200 <= gx <= game_w // 2 + 200 and by - 30 <= gy <= by + 30:
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
                elif black_hole_menu_active:
                    options = ["Continue Playing", "Main Menu"]
                    if event.key in (pygame.K_UP, pygame.K_w):
                        black_hole_selected_index = (black_hole_selected_index - 1) % len(options)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        black_hole_selected_index = (black_hole_selected_index + 1) % len(options)
                    elif event.key == pygame.K_RETURN:
                        if black_hole_selected_index == 0:
                            continue_playing_clicked = True
                        elif black_hole_selected_index == 1:
                            try:
                                d_action = get_action(name, pygame.key.get_pressed(), disconnect=True)
                                network_client.send_disconnect_action(d_action)
                            except Exception: pass
                            started = False
                            just_started = False
                            black_hole_menu_active = False
                            game_state = None
                elif in_pause_menu:
                    if pause_menu_state == "main":
                        options = ["Resume", "Settings", "Quit"]
                    elif pause_menu_state == "settings":
                        options = ["Music Volume", "Jump Volume", "Back"]
                    else:
                        options = ["Back"]
                        
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
                                try:
                                    d_action = get_action(name, pygame.key.get_pressed(), disconnect=True)
                                    network_client.send_disconnect_action(d_action)
                                except Exception: pass
                                started = False
                                just_started = False
                                game_state = None
                        elif pause_menu_state == "settings":
                            # 0: Music, 1: Jump, 2: Back
                            if pause_selected_index == 2: # Back
                                pause_menu_state = "main"
                                pause_selected_index = 0
                            # Sliders are handled by arrows/mouse, so no action on Enter for them.

            # ── DEBUG shortcuts (F-keys, only while in-game) ────────────────
            if started and event.type == pygame.KEYDOWN and game_state and not getattr(game_state, "game_over", False) and not getattr(game_state, "in_lobby", False):
                if event.key == pygame.K_F1:
                    debug_command = "skip_timer"   # Spawn the door immediately
                elif event.key == pygame.K_F2:
                    debug_command = "next_level"   # Skip directly to the next level
                elif event.key == pygame.K_F3:
                    debug_command = "kill_player"  # Kill your own player (test game-over)
                elif event.key == pygame.K_F4:
                    # Cycle through modifiers
                    from levels.Levels import AVAILABLE_MODIFIERS
                    if not hasattr(main, "_dbg_mod_idx"):
                        main._dbg_mod_idx = 0
                    mod = AVAILABLE_MODIFIERS[main._dbg_mod_idx % len(AVAILABLE_MODIFIERS)]
                    debug_command = f"set_modifier:{mod.name}"
                    debug_toast_text = f"[DEBUG] Modifier set to: {mod.name}"
                    debug_toast_until = pygame.time.get_ticks() + 2500
                    main._dbg_mod_idx += 1
                else:
                    debug_command = None
            
            if not started and event.type == pygame.KEYDOWN:
                if main_menu_state == "main":
                    options = ["Start Game", "Customize Character", "Settings", "Credits", "Quit"]
                elif main_menu_state == "settings":
                    options = ["Music Volume", "Jump Volume", "Back"]
                else:
                    options = ["Back"]
                    
                if event.key in (pygame.K_UP, pygame.K_w):
                    main_selected_index = (main_selected_index - 1) % len(options)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    main_selected_index = (main_selected_index + 1) % len(options)
                elif event.key == pygame.K_RETURN:
                    if main_menu_state == "main":
                        if main_selected_index == 0:
                            if not network_client.running:
                                network_client = NetworkClient(host, port)
                            started = True; just_started = True; play_bg_music()
                        elif main_selected_index == 1: main_menu_state = "customize"; main_selected_index = 0
                        elif main_selected_index == 2: main_menu_state = "settings"; main_selected_index = 0
                        elif main_selected_index == 3: main_menu_state = "credits"; main_selected_index = 0
                        elif main_selected_index == 4: running = False
                    else:
                        if main_menu_state == "settings":
                            if main_selected_index == 2: # Back
                                main_menu_state = "main"; main_selected_index = 0
                        else:
                            if main_selected_index == 0: main_menu_state = "main"; main_selected_index = 0

            # volume controls (global, works on start screen and in-game)
            if event.type == pygame.KEYDOWN:
                try:
                    # Volume keys (+/-) affect whichever slider is "selected" or just music if not in settings
                    current_sel = -1
                    if main_menu_state == "settings": current_sel = main_selected_index
                    elif in_pause_menu and pause_menu_state == "settings": current_sel = pause_selected_index
                    
                    if event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                        if current_sel == 1: # Jump
                            jump_volume = max(0.0, jump_volume - MUSIC_VOL_STEP)
                        else: # Default/Music
                            music_volume = max(0.0, music_volume - MUSIC_VOL_STEP)
                    elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                        if current_sel == 1: # Jump
                            jump_volume = min(1.0, jump_volume + MUSIC_VOL_STEP)
                        else: # Music
                            music_volume = min(1.0, music_volume + MUSIC_VOL_STEP)
                    
                    # Apply to hardware
                    if sound_mgr: sound_mgr.set_music_volume(music_volume)
                    if jump_sound: jump_sound.set_volume(jump_volume)
                    
                    # Left/Right keys for sliders while in settings
                    if (main_menu_state == "settings" or (in_pause_menu and pause_menu_state == "settings")):
                        if event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                            delta = -0.05 if event.key == pygame.K_LEFT else 0.05
                            if (main_menu_state == "settings" and main_selected_index == 0) or (in_pause_menu and pause_selected_index == 0):
                                music_volume = max(0.0, min(1.0, music_volume + delta))
                                if sound_mgr: sound_mgr.set_music_volume(music_volume)
                            elif (main_menu_state == "settings" and main_selected_index == 1) or (in_pause_menu and pause_selected_index == 1):
                                jump_volume = max(0.0, min(1.0, jump_volume + delta))
                                if jump_sound: jump_sound.set_volume(jump_volume)
                                # Play test sound
                                if jump_sound: jump_sound.play()
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
                menu_renderer.draw_main_menu(game_surface, start_logo, main_selected_index)
            elif main_menu_state == "customize":
                menu_renderer.draw_customize_menu(game_surface, character_color, main_selected_index)
            elif main_menu_state == "settings":
                menu_renderer.draw_settings_menu(game_surface, music_volume, jump_volume, main_selected_index)
            elif main_menu_state == "credits":
                menu_renderer.draw_credits_menu(game_surface, main_selected_index)
            else:
                msg = font.render(f"{main_menu_state.capitalize()} - Coming Soon!", True, (255, 255, 255))
                game_surface.blit(msg, msg.get_rect(center=(game_w // 2, game_h // 2)))

                color = (255, 255, 100) if 0 == main_selected_index else (255, 255, 255)
                opt_surf = font.render("Back", True, color)
                game_surface.blit(opt_surf, opt_surf.get_rect(center=(game_w // 2, game_h - 150)))
        else:
            action = get_action(name, pygame.key.get_pressed(), start_game=just_started or play_again_clicked or continue_playing_clicked, set_pause=in_pause_menu, color=character_color, debug_command=debug_command)
            just_started = False
            continue_playing_clicked = False
            network_client.send_action(action) # send action
             
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
                game_state.draw(name, game_surface, asset_cache)

                # Draw timer
                minutes = int(game_state.timer) // 60
                seconds = int(game_state.timer) % 60
                time_str = f"{minutes:02d}:{seconds:02d}"
                time_text = timer_font.render(time_str, False, (255, 255, 255))
                time_rect = time_text.get_rect(midtop=(game_w // 2, 10))
                # Draw timer ONLY if black hole effect is NOT active
                if not getattr(game_state, "black_hole_active", False):
                    game_surface.blit(time_text, time_rect)
                else:
                    # Special Black Hole Effect for Level 5
                    elapsed = time.time() - game_state.black_hole_start_time
                    if elapsed < 4.0:
                        # Lore Phases (0-4 seconds): Growing Black Hole + Sequential Text
                        game_surface.fill((0, 0, 0))
                        
                        # 1. Draw the scaling Black Hole GIF (Lazy Load)
                        if blackhole_player is None:
                            blackhole_player = GIFPlayer("images/Level1/blackhole.gif")
                        bh_frame = blackhole_player.get_current_frame()
                        if bh_frame:
                            # Scale from 5% to 100% over the full 4 seconds
                            scale_factor = max(0.05, min(1.0, elapsed / 4.0))
                            new_size = (int(bh_frame.get_width() * scale_factor), int(bh_frame.get_height() * scale_factor))
                            scaled_bh = pygame.transform.scale(bh_frame, new_size)
                            f_rect = scaled_bh.get_rect(center=(game_w // 2, game_h // 2))
                            game_surface.blit(scaled_bh, f_rect)

                        # 2. Draw Lore Text based on sub-phase
                        if elapsed < 2.0:
                            txt = lore_font.render("What is happening?", True, (255, 255, 255))
                        else:
                            txt = lore_font.render("Is this a... Blackhole?", True, (255, 255, 255))
                        game_surface.blit(txt, txt.get_rect(center=(game_w // 2, game_h // 2 + 150)))
                    
                    else:
                        # Black hole GIF + Spiral Players phase (4s+)
                        game_surface.fill((0, 0, 0))
                        
                        # 1. Draw the Black Hole GIF at full size
                        if blackhole_player is None:
                            blackhole_player = GIFPlayer("images/Level1/blackhole.gif")
                        bh_frame = blackhole_player.get_current_frame()
                        if bh_frame:
                            f_rect = bh_frame.get_rect(center=(game_w // 2, game_h // 2))
                            game_surface.blit(bh_frame, f_rect)
                        
                        # 2. Draw Spiraling Players
                        # We use a radius that decreases over time
                        orbit_time = elapsed - 4.0 # Time since GIF started
                        players_remaining = 0
                        
                        for i, p_name in enumerate(game_state.players):
                            # Unique start radius and contraction speed for each player
                            start_r = 450 + (i * 40)
                            contract_speed = 80 + (i * 15)
                            r = start_r - (orbit_time * contract_speed)
                            
                            threshold = 20 # "Invisible circle" radius where they disappear
                            if r > threshold:
                                players_remaining += 1
                                # Unique orbital speed and phase
                                orb_speed = 1.0 + (i * 0.2)
                                angle = orbit_time * orb_speed + (i * (2 * math.pi / max(1, len(game_state.players))))
                                
                                # Orbit coordinates around the center
                                ox = (game_w // 2) + int(math.cos(angle) * r)
                                oy = (game_h // 2) + int(math.sin(angle) * r)
                                
                                # Draw player at orbital position (BORDER ONLY)
                                p_color = (255, 255, 255) # default
                                if p_name == name:
                                    p_color = (0, 255, 0) # Highlight current player
                                    
                                pygame.draw.rect(game_surface, p_color, (ox - 10, oy - 10, 20, 20), 2)
                                
                                # Draw name tag
                                n_txt = asset_cache.get_texture(p_name)
                                n_rect = n_txt.get_rect(midbottom=(ox, oy - 15))
                                game_surface.blit(n_txt, n_rect)
                        
                        # 3. Show Final Menu if all are gone
                        if players_remaining == 0:
                            black_hole_menu_active = True
                            
                            # Draw overlay
                            overlay = pygame.Surface((game_w, game_h), pygame.SRCALPHA)
                            overlay.fill((0, 0, 0, 180))
                            
                            bh_font = pygame.font.SysFont("Comic Sans MS", 72, bold=True)
                            title_surf = bh_font.render("YOU'VE COMPLETED THE GAME!", True, (255, 255, 255))
                            overlay.blit(title_surf, title_surf.get_rect(center=(game_w // 2, game_h // 4)))
                            
                            bh_small = pygame.font.SysFont("Comic Sans MS", 54)
                            ready_count = sum(1 for p in game_state.players.values() if getattr(p, "is_ready", False))
                            total_count = len(game_state.players) if game_state.players else 1
                            options = [f"Continue Playing ({ready_count}/{total_count})", "Main Menu"]
                            for i, opt in enumerate(options):
                                color = (255, 255, 100) if i == black_hole_selected_index else (200, 200, 200)
                                opt_surf = bh_small.render(opt, True, color)
                                overlay.blit(opt_surf, opt_surf.get_rect(center=(game_w // 2, game_h // 2 + i * 80 - 80)))

                            game_surface.blit(overlay, (0, 0))
            else:
                # no game state yet — clear to default
                game_surface.fill(background_color)

            # Receive latest game_state from the background network thread (non-blocking)
            state_data = network_client.receive_game_state()
            if state_data:
                try:
                    if game_state is None:
                        game_state = Game_State(pygame.Vector2(game_w, game_h))
                        
                    game_state.apply_compressed_state(state_data)
                except Exception:
                    # Corrupted state or unexpected issue
                    pass
                else:
                    if not getattr(game_state, "black_hole_active", False):
                        black_hole_menu_active = False

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

            if game_state and name in game_state.players:
                current_jumps = game_state.players[name].jumps_remaining
                if prev_jumps is not None and current_jumps < prev_jumps:
                    if jump_sound:
                        jump_sound.play()
                prev_jumps = current_jumps

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
                
                # Determine slider properties based on which menu is open
                if started: # Pause Menu
                    slider_x = game_w // 2 - 225
                    slider_y = game_h // 2 - 40
                    j_slider_y = game_h // 2 + 80
                    slider_w = 450
                else: # Main Menu
                    slider_x = game_w // 2 - 300
                    slider_y = game_h // 2 - 60
                    j_slider_y = game_h // 2 + 60
                    slider_w = 600
                    
                if slider_x - 30 <= gx <= slider_x + slider_w + 30:
                    fraction = (gx - slider_x) / slider_w
                    if slider_y - 60 <= gy <= slider_y + 60:
                        music_volume = max(0.0, min(1.0, fraction))
                        if main_menu_state == "settings": main_selected_index = 0
                        elif in_pause_menu and pause_menu_state == "settings": pause_selected_index = 0
                        try:
                            if sound_mgr is not None: sound_mgr.set_music_volume(music_volume)
                        except Exception:
                            pass
                    elif j_slider_y - 60 <= gy <= j_slider_y + 60:
                        new_vol = max(0.0, min(1.0, fraction))
                        if abs(new_vol - jump_volume) > 0.01:
                            if jump_sound and time.time() - last_jump_test_time > 0.15:
                                jump_sound.play()
                                last_jump_test_time = time.time()
                        jump_volume = new_vol
                        if main_menu_state == "settings": main_selected_index = 1
                        elif in_pause_menu and pause_menu_state == "settings": pause_selected_index = 1
                        if jump_sound:
                            jump_sound.set_volume(jump_volume)


        if in_pause_menu:
            pause_overlay = pygame.Surface((game_w, game_h), pygame.SRCALPHA)
            pause_overlay.fill((0, 0, 0, 200)) # Darker overlay
            
            p_font = pygame.font.SysFont("Comic Sans MS", 72, bold=True)
            p_small = pygame.font.SysFont("Comic Sans MS", 54)
            p_smaller = pygame.font.SysFont("Comic Sans MS", 42)
            
            title_text = "PAUSED" if pause_menu_state == "main" else "SETTINGS"
            title_surf = p_font.render(title_text, True, (255, 255, 255))
            pause_overlay.blit(title_surf, title_surf.get_rect(center=(game_w // 2, game_h // 4)))
            
            if pause_menu_state == "main":
                menu_renderer.draw_pause_main(pause_overlay, pause_selected_index, p_small)
            elif pause_menu_state == "settings":
                menu_renderer.draw_pause_settings(pause_overlay, music_volume, jump_volume, pause_selected_index, p_smaller, p_small)

            game_surface.blit(pause_overlay, (0, 0))

        # ── Debug toast notification ──────────────────────────────────────────
        if debug_toast_text and pygame.time.get_ticks() < debug_toast_until:
            toast_font = pygame.font.SysFont("Comic Sans MS", 20, bold=True)
            toast_surf = toast_font.render(debug_toast_text, True, (255, 240, 60))
            game_surface.blit(toast_surf, (game_w // 2 - toast_surf.get_width() // 2, game_h - 80))

        # Stretch the internal game surface to fill the entire window
        win_w, win_h = display.get_size()
        scaled = pygame.transform.smoothscale(game_surface, (win_w, win_h))
        surface.blit(scaled, (0, 0))

        pygame.display.flip()
        clock.tick(60) # run at 60 frames per second

def get_action(name, keys, start_game=False, set_pause=None, color=(255, 255, 255), debug_command=None, disconnect=False):
    if set_pause:
        return Action(name, False, False, False, False, start_game, set_pause, color, debug_command, disconnect)
    left = keys[pygame.K_LEFT] or keys[pygame.K_a]
    right = keys[pygame.K_RIGHT] or keys[pygame.K_d]
    jump = keys[pygame.K_UP] or keys[pygame.K_w] or keys[pygame.K_SPACE]
    down = keys[pygame.K_DOWN] or keys[pygame.K_s]
    return Action(name, left, right, jump, down, start_game, set_pause, color, debug_command, disconnect)

class AssetCache: # class to generate and store textures of user names and ghosts
    def __init__(self):
        self.asset_cache = {}
        self.ghost_textures = {} # Key: (color_tuple, facing_right)

    def get_texture(self, name):
        if not name in self.asset_cache:
            font = pygame.font.SysFont('Comic Sans MS', 24, bold=True)
            name_texture = font.render(name, False, (255, 255, 255))
            self.asset_cache[name] = name_texture
        return self.asset_cache[name]

    def get_ghost_texture(self, color, facing_right):
        key = (tuple(color), facing_right)
        if key not in self.ghost_textures:
            try:
                import os
                img_path = "images/general (All levels)/ghost.png"
                if not os.path.exists(img_path):
                    return None
                
                base_img = pygame.image.load(img_path).convert_alpha()
                ghost_size = (60, 60)
                base_img = pygame.transform.scale(base_img, ghost_size)
                
                # Flip before coloring if needed (base is assumed to face left)
                if facing_right:
                    base_img = pygame.transform.flip(base_img, True, False)

                # Coloring: Use BLEND_RGBA_MULT
                colored_ghost = base_img.copy()
                color_surf = pygame.Surface(ghost_size, pygame.SRCALPHA)
                color_surf.fill((*color, 255))
                colored_ghost.blit(color_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                
                self.ghost_textures[key] = colored_ghost
            except Exception:
                return None
        return self.ghost_textures[key]

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
