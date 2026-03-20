class Action:

    def __init__(self, name, left, right, jump, down=False, start_game=False, set_pause=None, color=(255, 255, 255)):
        self.name = name
        self.left = left
        self.right = right
        self.jump = jump
        self.down = down
        self.start_game = start_game
        self.set_pause = set_pause
        self.color = color

    def __repr__(self):
        return f"name: {self.name} left:{self.left} right:{self.right} jump:{self.jump} down:{self.down} start:{self.start_game} pause:{self.set_pause} color:{self.color}"

    def get_name(self):
        return self.name

    def is_left(self):
        return self.left
        
    def is_right(self):
        return self.right
        
    def is_jump(self):
        return self.jump

    def is_down(self):
        return self.down

    def is_start_game(self):
        return self.start_game

    def get_set_pause(self):
        return self.set_pause

    def get_color(self):
        return self.color
