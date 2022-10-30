import pytest
from botbattle import Side, State, Vector


def test_lines():
    state = State(board=[[None]], next_side=Side.RED)
    assert state.line(Vector(0, 0, 1, 0, 1)) == (None,)

    state = State(
        board=[
            [None, None, None],
            [None, Side.BLUE, None],
            [None, None, Side.BLUE],
        ],
        next_side=Side.RED,
    )
    assert state.line(Vector(0, 0, 1, 0, 1)) == (None,)
    assert state.line(Vector(0, 0, 1, 1, 3)) == (None, Side.BLUE, Side.BLUE)
    assert state.line(Vector(2, 2, -1, -1, 3)) == (Side.BLUE, Side.BLUE, None)

    assert state.line_side(state.line(Vector(1, 1, 1, 1, 2))) == Side.BLUE
    assert state.line_side(state.line(Vector(0, 0, 1, 1, 3))) is None


@pytest.mark.parametrize(
    "x, y, dx, dy, length, by_start, by_end, new_x, new_y, new_length",
    [
        [0, 0, 1, 0, 1, 0, 0, 0, 0, 1],
        [0, 0, 1, 0, 1, 1, 0, -1, 0, 2],
        [0, 0, 1, 1, 1, 1, 1, -1, -1, 3],
        [0, 0, -1, 0, 1, 1, 1, 1, 0, 3],
        [0, 0, -1, 0, 1, 1, None, 1, 0, 3],
        [0, 0, 1, 0, 3, -1, None, 1, 0, 1],
    ],
)
def test_vector_extend(
    x, y, dx, dy, length, by_start, by_end, new_x, new_y, new_length
):
    assert Vector(x, y, dx, dy, length).extend(by_start, by_end) == Vector(
        new_x, new_y, dx, dy, new_length
    )


@pytest.mark.parametrize(
    "x, y, dx, dy, length, len_x, len_y, new_x, new_y, new_length",
    [
        [0, 0, 1, 0, 2, 1, 1, 0, 0, 1],
        [0, 0, 1, 0, 3, 1, 1, 0, 0, 1],
        [1, 1, 0, 1, 3, 3, 3, 1, 1, 2],
        [0, 0, 1, 0, 3, 2, 1, 0, 0, 2],
        [1, 1, 1, 0, 3, 3, 3, 1, 1, 2],
        [0, 0, 1, 1, 3, 2, 1, 0, 0, 1],
        [0, 1, 1, 1, 4, 3, 3, 0, 1, 2],
        [1, 1, -1, 1, 4, 3, 3, 1, 1, 2],
        [0, 0, -1, 0, 2, 1, 1, 0, 0, 1],
        [-1, -1, 1, 1, 3, 3, 3, 0, 0, 2],
    ],
)
def test_vector_crop(x, y, dx, dy, length, len_x, len_y, new_x, new_y, new_length):
    new_vec = Vector(new_x, new_y, dx, dy, new_length)
    assert Vector(x, y, dx, dy, length).crop(0, 0, len_x, len_y) == new_vec


@pytest.mark.parametrize(
    "x, y, dx, dy, length, in_bounds",
    [
        [0, 0, 1, 1, 3, True],
        [1, 1, 1, 1, 2, True],
        [1, 1, 1, 1, 3, False],
        [3, 3, 1, 1, 2, False],
        [3, 3, -1, -1, 2, False],
    ],
)
def test_vector_in_bounds(x, y, dx, dy, length, in_bounds):
    state = State(
        board=[[None, None, None]] * 3,
        next_side=Side.RED,
    )
    assert state.vector_in_bounds(Vector(x, y, dx, dy, length)) == in_bounds


@pytest.mark.parametrize(
    "old_x, old_y, dx, dy, old_length, extension_length, new_x, new_y, new_length",
    [
        [0, 0, 1, 1, 1, 1, 0, 0, 2],
        [0, 2, 1, -1, 1, 1, 0, 2, 2],
        [1, 1, 1, 1, 1, 1, 0, 0, 3],
        [1, 1, 1, 1, 1, 2, 0, 0, 3],
        # [1, 1, 1, 0, 3, 2, 0, 1, 3],
        # [1, 1, 1, 0, 3, 2, 0, 1, 3],
        # [1, 1, 1, 0, 3, 5, 0, 1, 3],
        # [1, 2, 1, -1, 5, 5, 1, 2, 2],
    ],
)
def test_vector_extension(
    old_x, old_y, dx, dy, old_length, extension_length, new_x, new_y, new_length
):
    state = State(
        board=[[None, None, None]] * 3,
        next_side=Side.RED,
    )

    old_vec = Vector(old_x, old_y, dx, dy, old_length)
    new_vec = Vector(new_x, new_y, dx, dy, new_length)
    assert state.extend_vector(old_vec, extension_length) == new_vec
    assert state.vector_in_bounds(new_vec)


def test_find_all_generic():
    state = State(
        board=[
            [None, None, None],
            [None, Side.BLUE, None],
            [None, None, Side.BLUE],
        ],
        next_side=Side.RED,
    )
    assert state.find_all_generic(1, 1, 2, Side.BLUE) == (Vector(1, 1, 1, 1, 2),)


def test_find_all_lines():
    state = State(
        board=[
            [None, Side.RED, None],
            [None, Side.RED, Side.BLUE],
            [None, Side.BLUE, None],
        ],
        next_side=Side.RED,
    )
    assert state.find_all_generic(1, -1, 2, Side.BLUE) == (Vector(1, 2, 1, -1, 2),)
    assert state.find_all_lines(2, Side.BLUE) == (Vector(1, 2, 1, -1, 2),)
    assert state.find_all_lines(2, Side.RED) == (Vector(1, 0, 0, 1, 2),)


def test_winners():
    state = State(
        board=[
            [None, Side.RED, None, None, None, None, None],
            [None, Side.RED, None, None, None, None, None],
            [None, Side.RED, None, None, None, None, None],
            [None, Side.RED, None, None, None, None, None],
            [None, Side.RED, None, None, None, None, None],
            [None, Side.RED, Side.BLUE, None, None, None, None],
            [None, Side.BLUE, None, None, None, None, None],
        ],
        next_side=Side.RED,
    )
    assert state.winners() == [Side.RED]

    state = State(
        board=[
            [None, None, None, None, None, None, None],
            [None, Side.RED, None, None, None, None, None],
            [None, Side.RED, None, None, None, None, None],
            [None, Side.RED, None, None, None, None, None],
            [None, None, None, None, None, None, None],
            [None, Side.RED, Side.BLUE, None, None, None, None],
            [None, Side.BLUE, None, None, None, None, None],
        ],
        next_side=Side.RED,
    )
    assert state.winners() == []

    state = State(
        board=[
            [None, Side.RED, None, None, None, None, None],
            [None, Side.RED, None, None, None, None, None],
            [None, Side.RED, None, None, None, None, None],
            [None, Side.RED, None, None, Side.BLUE, None, None],
            [None, None, None, Side.BLUE, None, None, None],
            [None, Side.RED, Side.BLUE, None, None, None, None],
            [None, Side.BLUE, None, None, None, None, None],
        ],
        next_side=Side.RED,
    )
    assert state.winners() == [Side.RED, Side.BLUE]
    assert state.line(state.extend_vector(state.find_all_lines(4, Side.BLUE)[0], 3))


def test_drop_token():
    state = State(board=[[None]], next_side=Side.RED)
    state.drop_token(0, Side.RED)

    assert state.board == [[Side.RED]]

    state = State(board=[[None], [Side.RED]], next_side=Side.RED)
    state.drop_token(0, Side.RED)

    assert state.board == [[Side.RED], [Side.RED]]

    assert state.all_cells_filled()

    with pytest.raises(Exception):
        state.drop_token(0, Side.RED)
