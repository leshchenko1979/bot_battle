from enum import Enum

class Side(Enum):
    RED = 0
    BLUE = 1

    def next_side(self):
        return Side.BLUE if self == Side.RED else Side.RED
