from dataclasses import dataclass
import itertools

import icontract
from pydantic import BaseModel

from .side import Side


class StateException(Exception):
    pass


class ColumnFullException(StateException):
    pass


@dataclass
class Vector:
    x: int
    y: int
    dx: int
    dy: int
    length: int

    @staticmethod
    def from_coords(x1: int, y1: int, x2: int, y2: int):
        get_d = lambda c1, c2: 0 if c1 == c2 else c2 - c1 / abs(c2 - c1)
        dx, dy = get_d(x1, x2), get_d(y1, y2)
        length = max(dx * abs(x2 - x1), dy * abs(y2 - y1))
        return Vector(x1, y1, dx, dy, length)

    def extend(self, by_start: int, by_end: int = None):
        by_end = by_start if by_end is None else by_end
        return Vector(
            self.x - by_start * self.dx,
            self.y - by_start * self.dy,
            self.dx,
            self.dy,
            self.length + by_start + by_end,
        )

    def crop(self, x1, y1, x2, y2):
        cropped = lambda coord, min_, max_: coord - min(max(coord, min_), max_ - 1)

        left = cropped(self.x, x1, x2)
        top = cropped(self.y, y1, y2)

        right = cropped(self.x_end(), x1, x2)
        bottom = cropped(self.y_end(), y1, y2)

        # print(left, top, right, bottom)

        cropped_start = max(abs(left), abs(top))
        cropped_end = max(abs(right), abs(bottom))

        # assert cropped_start >= 0
        # assert cropped_end >= 0

        # print(cropped_start, cropped_end)

        return self.extend(-cropped_start, -cropped_end)

    def x_end(self):
        return self.x + self.dx * (self.length - 1)

    def y_end(self):
        return self.y + self.dy * (self.length - 1)

    def in_bounds(self, x1, y1, x2, y2) -> bool:
        return all(
            [
                x1 <= self.x < x2,
                y1 <= self.y < y2,
                x1 <= self.x_end() < x2,
                y1 <= self.y_end() < y2,
            ]
        )


class State(BaseModel):
    """State of the game."""

    board: list[list[Side | None]] = [[None] * 7 for _ in range(7)]
    next_side: Side

    @icontract.require(lambda self, vec: self.vector_in_bounds(vec))
    def line(self, vec: Vector) -> tuple[Side | None]:
        return tuple(
            self.board[vec.y + i * vec.dy][vec.x + i * vec.dx]
            for i in range(vec.length)
        )

    def vector_in_bounds(self, vec: Vector) -> bool:
        return vec.in_bounds(0, 0, self.len_x(), self.len_y())

    def line_side(self, line: tuple[Side]) -> Side | None:
        return next((side for side in Side if set(line) == {side}), None)

    @icontract.require(lambda self, vec: self.vector_in_bounds(vec))
    @icontract.ensure(lambda self, result: self.vector_in_bounds(result))
    def extend_vector(self, vec: Vector, by: int) -> Vector:
        return vec.extend(by).crop(0, 0, self.len_x(), self.len_y())

    def winners(self) -> list[Side]:
        if self.all_cells_filled():
            return [Side.RED, Side.BLUE]

        return [side for side in Side if self.find_all_lines(4, side)]

    def all_cells_filled(self) -> bool:
        return all(all(line) for line in self.board)

    @icontract.require(lambda length: length > 1)
    def find_all_lines(self, length: int, side: Side) -> tuple[Vector]:
        return tuple(
            itertools.chain.from_iterable(
                self.find_all_generic(dx, dy, length, side)
                for dx, dy in [[1, 0], [0, 1], [1, 1], [1, -1]]
            )
        )

    def len_x(self) -> int:
        return len(self.board[0])

    def len_y(self) -> int:
        return len(self.board)

    @icontract.require(lambda dx, dy: -1 <= dx <= 1 and -1 <= dy <= 1)
    def find_all_generic(
        self, dx: int, dy: int, length: int, side: Side
    ) -> tuple[Vector]:
        def make_range(board_len: int, line_len: int, d: int):
            if d == 1:
                return range(0, board_len - line_len + 1, d)
            elif d == -1:
                return range(board_len - 1, line_len - 1, d)
            else:
                return range(board_len)

        range_x = make_range(self.len_x(), length, dx)
        range_y = make_range(self.len_y(), length, dy)

        # print(range_x, range_y)

        def vec_side(x, y, dx, dy, length):
            vec = Vector(x, y, dx, dy, length)
            side = self.line_side(self.line(vec))
            return vec, side

        return tuple(
            found_vec_side[0]
            for x, y in itertools.product(range_x, range_y)
            if (found_vec_side := vec_side(x, y, dx, dy, length))[1] == side
        )

    @icontract.require(lambda self, col: 0 <= col < self.len_x(), "col out of bounds")
    @icontract.require(lambda col: isinstance(col, int), "col should be an integer")
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
