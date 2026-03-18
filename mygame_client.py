import sys
import zmq
import pygame

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
    display = pygame.display.set_mode((800, 600), pygame.RESIZABLE)
    pygame.display.set_caption('mygame')
    surface = pygame.display.get_surface()
    
    # Internal render target dimensions (will adjust to current level's world bounds)
    game_w, game_h = 800, 600
    game_surface = pygame.Surface((game_w, game_h))
    
    clock = pygame.time.Clock()
    background_color = (0,0,0)
    background_cache = {}   # cache loaded background images (store original surfaces)
    background_image = None 
    name_textures = Name_Textures()
    game_state = None
    started = False
    just_started = False
    font = pygame.font.SysFont('Comic Sans MS', 48)
    small_font = pygame.font.SysFont('Comic Sans MS', 24)
    
    running = True
    play_again_clicked = False
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if not started and event.type == pygame.KEYDOWN:
                started = True
                just_started = True
            # If game over, allow clicking the Play Again button (convert mouse to game coords)
            if event.type == pygame.MOUSEBUTTONDOWN and game_state and getattr(game_state, "game_over", False):
                mx, my = event.pos
                win_w, win_h = display.get_size()
                scale = min(win_w / game_w, win_h / game_h)
                scaled_w = int(game_w * scale)
                scaled_h = int(game_h * scale)
                offset_x = (win_w - scaled_w) // 2
                offset_y = (win_h - scaled_h) // 2
                if offset_x <= mx <= offset_x + scaled_w and offset_y <= my <= offset_y + scaled_h:
                    gx = int((mx - offset_x) / scale)
                    gy = int((my - offset_y) / scale)
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
        # This preserves aspect ratio and avoids stretching when the window is resized.
        game_surface.fill(background_color)

        if not started:
            # Draw start screen
            title = font.render('MyGame', False, (255, 255, 255))
            prompt = small_font.render('Press any key to start', False, (255, 255, 255))

            title_rect = title.get_rect(center=(game_w // 2, game_h // 2 - 40))
            prompt_rect = prompt.get_rect(center=(game_w // 2, game_h // 2 + 30))

            game_surface.blit(title, title_rect)
            game_surface.blit(prompt, prompt_rect)
        else:
            action = get_action(name, pygame.key.get_pressed(), start_game=just_started or play_again_clicked)
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
                    game_w, game_h = 800, 600
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

        # Scale the internal game surface to the window size with aspect ratio preserved.
        win_w, win_h = display.get_size()
        scale = min(win_w / game_w, win_h / game_h)
        scaled_w = int(game_w * scale)
        scaled_h = int(game_h * scale)
        scaled = pygame.transform.smoothscale(game_surface, (scaled_w, scaled_h))

        # Center the scaled view w/ letterboxing/pillarboxing
        surface.fill((0, 0, 0))
        surface.blit(scaled, ((win_w - scaled_w) // 2, (win_h - scaled_h) // 2))

        pygame.display.flip()
        clock.tick(60) # run at 60 frames per second

def get_action(name, keys, start_game=False):
    left = keys[pygame.K_LEFT] or keys[pygame.K_a]
    right = keys[pygame.K_RIGHT] or keys[pygame.K_d]
    jump = keys[pygame.K_UP] or keys[pygame.K_w] or keys[pygame.K_SPACE]
    down = keys[pygame.K_DOWN] or keys[pygame.K_s]
    return Action(name, left, right, jump, down, start_game)

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
