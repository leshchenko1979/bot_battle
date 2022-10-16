import pytest
from botbattle import Side, State


def test_drop_token():
    state = State(board = [[None]], next_side = Side.RED)
    state.drop_token(0, Side.RED)

    assert state.board == [[Side.RED]]

    state = State(board = [[None], [Side.RED]], next_side = Side.RED)
    state.drop_token(0, Side.RED)

    assert state.board == [[Side.RED], [Side.RED]]

    assert state.all_cells_filled()

    with pytest.raises(Exception):
        state.drop_token(0, Side.RED)


def test_find_horizontal():
    state = State(board=[[Side.RED]], next_side=Side.RED)
    assert state.find_horizontal(1) == Side.RED

    state = State(board=[[Side.RED, Side.BLUE]], next_side=Side.RED)
    assert state.find_horizontal(1) == Side.RED
    assert state.find_horizontal(2) is None

    state = State(board=[[Side.RED, Side.BLUE, Side.RED]], next_side=Side.RED)
    assert state.find_horizontal(2) is None

    state = State(board=[[Side.RED, Side.BLUE, Side.BLUE]], next_side=Side.RED)
    assert state.find_horizontal(2) is Side.BLUE


def test_find_vertical():
    state = State(board=[[Side.RED]], next_side=Side.RED)
    assert state.find_vertical(1) == Side.RED

    state = State(board=[[Side.RED], [Side.BLUE]], next_side=Side.RED)
    assert state.find_vertical(1) == Side.RED
    assert state.find_vertical(2) is None

    state = State(board=[[Side.RED], [Side.BLUE], [Side.RED]], next_side=Side.RED)
    assert state.find_vertical(2) is None

    state = State(board=[[Side.RED], [Side.BLUE], [Side.BLUE]], next_side=Side.RED)
    assert state.find_vertical(2) is Side.BLUE


def test_find_diagonal():
    state = State(board=[[Side.RED]], next_side=Side.RED)
    assert state.find_diagonal(1) == Side.RED

    state = State(board=[[Side.RED], [Side.BLUE]], next_side=Side.RED)
    assert state.find_diagonal(1) == Side.RED
    assert state.find_diagonal(2) is None

    state = State(
        board=[
            [None, None, None],
            [None, Side.BLUE, None],
            [None, None, Side.BLUE],
        ],
        next_side=Side.RED,
    )
    assert state.find_diagonal(2) is Side.BLUE

    state = State(
        board=[
            [None, None, None],
            [None, None, Side.BLUE],
            [None, Side.BLUE, None],
        ],
        next_side=Side.RED,
    )
    assert state.find_diagonal(2) is Side.BLUE
