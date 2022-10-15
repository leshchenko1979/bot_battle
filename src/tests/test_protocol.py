from bot_battle_sdk.protocol import NewGameResponseWait, NewGameResponse

def test_new_game_creation():
    resp = NewGameResponse(response={"response_type": "wait", "wait_for": 10})
    print(resp)

    json = resp.json()
    print(json)

    assert resp == NewGameResponse.parse_raw(json)
    assert type(resp.response) == NewGameResponseWait
