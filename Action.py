class Action:

    def __init__(self, name, left, right, jump):
        self.name = name
        self.left = left
        self.right = right
        self.jump = jump

    def __repr__(self):
        return f"name: {self.name} left:{self.left} right:{self.right} jump:{self.jump}"

    def get_name(self):
        return self.name

    def is_left(self):
        return self.left
        
    def is_right(self):
        return self.right
        
    def is_jump(self):
        return self.jump
