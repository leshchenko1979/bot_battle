from ..dispatcher.models import JSONState
from bot_battle_sdk.state import State
from bot_battle_sdk.sides import Side

def test_state_conversion():
    state = State(board=[[Side.RED]], next_side=Side.BLUE)

    json = JSONState.process_bind_param(state, None)
    print(json)

    assert state == JSONState.process_result_value(json, None)
