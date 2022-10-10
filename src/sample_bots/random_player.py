from random import randint

from beartype import beartype

from bot_battle_sdk.players import PlayerAbstract
from bot_battle_sdk.state import State


class RandomPlayer(PlayerAbstract):
    @beartype
    def make_move(self, state: State) -> int:
        available = {i for i in range(len(state.board[0])) if not state.column_full(i)}
        while available:
            col = randint(0, len(available) - 1)
            return list(available)[col]
