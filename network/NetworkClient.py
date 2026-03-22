import zmq

class NetworkClient:
    """Manages the network connection to the game server using ZeroMQ."""
    
    def __init__(self, host: str, port: str):
        """Initializes the ZeroMQ context and connects to the server."""
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(f"tcp://{host}:{port}")
        print(f"Connected to Game Server at 'tcp://{host}:{port}'.")

    def send_action(self, action):
        """Sends an Action object to the server."""
        self.socket.send_pyobj(action)

    def receive_game_state(self):
        """Receives the latest Game_State from the server. Blocking call."""
        return self.socket.recv_pyobj()
        
    def send_disconnect_action(self, action):
        """Sends a disconnect action and clears the immediate server response."""
        try:
            self.socket.send_pyobj(action)
            self.socket.recv_pyobj() # clear response
        except Exception:
            pass
