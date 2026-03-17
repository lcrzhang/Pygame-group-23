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
    game_surface = pygame.Surface((800, 600))  # fixed internal render target
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
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if not started and event.type == pygame.KEYDOWN:
                started = True
                just_started = True

        # Always render to a fixed 800x600 surface, then scale to the current window size.
        # This preserves aspect ratio and avoids stretching when the window is resized.
        game_surface.fill(background_color)

        if not started:
            # Draw start screen
            title = font.render('MyGame', False, (255, 255, 255))
            prompt = small_font.render('Press Enter to start', False, (255, 255, 255))

            title_rect = title.get_rect(center=(800 // 2, 600 // 2 - 40))
            prompt_rect = prompt.get_rect(center=(800 // 2, 600 // 2 + 30))

            game_surface.blit(title, title_rect)
            game_surface.blit(prompt, prompt_rect)
        else:
            action = get_action(name, pygame.key.get_pressed(), start_game=just_started)
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
                        bg_scaled = pygame.transform.scale(bg_orig, (800, 600))
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
                time_rect = time_text.get_rect(midtop=(800 // 2, 10))
                game_surface.blit(time_text, time_rect)
            else:
                # no game state yet — clear to default
                game_surface.fill(background_color)

            game_state = socket.recv_pyobj() # receive game_state
            #print("game_state:",game_state)        

        # Scale the fixed 800x600 game surface to the window size with aspect ratio preserved.
        win_w, win_h = display.get_size()
        scale = min(win_w / 800, win_h / 600)
        scaled_w = int(800 * scale)
        scaled_h = int(600 * scale)
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
    if len(sys.argv) > 3:
        host = sys.argv[3]
    main(name, port, host)
