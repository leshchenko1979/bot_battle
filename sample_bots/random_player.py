from botbattle import PlayerAbstract, State
import random


class RandomPlayer(PlayerAbstract):
    def make_move(self, state: State) -> int:
        available = {i for i in range(len(state.board[0])) if not state.column_full(i)}
        while available:
            col = random.randint(0, len(available) - 1)
            return list(available)[col]
