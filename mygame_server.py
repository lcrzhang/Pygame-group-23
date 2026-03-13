import sys
import zmq
import time
import pygame

from Action import Action
from Game_State import Game_State

def main(port, host):
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind(f"tcp://{host}:{port}")
    print(f"Waiting for clients on port '{port}' on host '{host}'.")

    poller = zmq.Poller()
    poller.register(socket, zmq.POLLIN)

    game_fps = 60
    frame_duration_ms = 1000 // game_fps
    prev_time = time.time()
    actions = {}
    game_state = Game_State(pygame.Vector2(800, 600))

    while True:
        # Calculate timeout until next frame update
        elapsed_ms = (time.time() - prev_time) * 1000
        timeout_ms = max(0, frame_duration_ms - elapsed_ms)

        # Wait efficiently for incoming messages or timeout
        events = poller.poll(timeout=timeout_ms)

        for sock, _ in events:
            action = sock.recv_pyobj()
            actions[action.get_name()] = action
            sock.send_pyobj(game_state)

        # Update game state when frame time has elapsed
        if time.time() - prev_time >= 1 / game_fps:
            delta_time = time.time() - prev_time
            game_state.tick_timer(delta_time)
            prev_time = time.time()
            
            update_game_state(game_state, actions)

def update_game_state(game_state, actions):
    for name, action in actions.items():
        if name != '_': # ignore user '_'
            game_state.update(action)
    game_state.spawn_units()
            
if __name__ == "__main__":
    port = 2345
    host = "127.0.0.1"
    if len(sys.argv)>1:
        port = int(sys.argv[1])
    if len(sys.argv)>2:
        host = sys.argv[2]
    main(port, host)
