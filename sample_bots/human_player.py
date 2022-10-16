from players import PlayerAbstract
from beartype import beartype
from state import State
from icontract import ensure

class HumanPlayer(PlayerAbstract):
    @beartype
    @ensure(lambda state, result: 0 <= result < len(state.board[0]))
    def make_move(self, state: State) -> int:
        return int(input("Your move: ")) - 1
