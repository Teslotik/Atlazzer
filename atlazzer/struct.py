class UVRect:
    def __init__(self, data, x:float, y:float, w:float, h:float, margin = 0.0):
        self.data = data
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.margin = margin