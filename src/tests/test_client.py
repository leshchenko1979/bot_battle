from bot_battle_sdk.client import BotClient
from ..sample_bots.random_player import RandomPlayer

def test_client():
    BotClient("123123", RandomPlayer, "123123123")
