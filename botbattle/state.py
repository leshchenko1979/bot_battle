import itertools

from pydantic import BaseModel

from .side import Side


class ColumnFullException(Exception):
    pass


class State(BaseModel):
    """State of the game."""

    board: list[list[Side | None]] = [[None] * 7 for _ in range(7)]
    next_side: Side

    def winners(self) -> list[Side]:
        if self.all_cells_filled():
            return [Side.RED, Side.BLUE]

        winner = self.find_a_line(4)

        return [winner] if winner else []

    def all_cells_filled(self) -> bool:
        return all(all(line) for line in self.board)

    def find_a_line(self, length: int) -> Side | None:
        return (
            self.find_horizontal(length)
            or self.find_vertical(length)
            or self.find_diagonal(length)
        )

    def find_horizontal(self, length: int) -> Side | None:
        for line in self.board:
            for i in range(len(line) - length + 1):
                population = set(line[i : i + length])
                if len(population) == 1 and population != {None}:
                    return list(population)[0]

    def find_vertical(self, length: int) -> Side | None:
        for col, row in itertools.product(
            range(len(self.board[0])), range(len(self.board) - length + 1)
        ):
            population = {self.board[row + i][col] for i in range(length)}
            if len(population) == 1 and population != {None}:
                return list(population)[0]

    def find_diagonal(self, length: int) -> Side | None:
        for col, row in itertools.product(
            range(len(self.board[0]) - length + 1), range(len(self.board) - length + 1)
        ):
            population = {self.board[row + i][col + i] for i in range(length)}
            if len(population) == 1 and population != {None}:
                return list(population)[0]

            population = {
                self.board[row + i][col + length - 1 - i] for i in range(length)
            }
            if len(population) == 1 and population != {None}:
                return list(population)[0]

    def drop_token(self, col: int, side: Side = None) -> None:
        if self.column_full(col):
            raise ColumnFullException

        i = 0
        while i < len(self.board) and not self.board[i][col]:
            i += 1
        self.board[i - 1][col] = side or self.next_side
        self.next_side = self.next_side.next_side()

    def column_full(self, col: int) -> bool:
        return self.board[0][col]
