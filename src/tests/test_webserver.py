from ..dispatcher.models import BotModel, StateModel, ParticipantModel
from ..dispatcher.database import db

def get(client, bot, url, **params):
    headers = {"Authorization": f"Bearer {bot.token}"}
    return client.get(url, headers=headers, **params)

def test_game_creation(client, clean_up):
    bot_1 = db().query(BotModel).filter(BotModel.id == 1).one()
    bot_2 = db().query(BotModel).filter(BotModel.id == 2).one()

    get(client, bot_1, "/games/new_game")
    get(client, bot_2, "/games/new_game")


    game_id_1 = get(client, bot_1, "/games/new_game").json()["response"]["game_id"]
    game_id_2 = get(client, bot_2, "/games/new_game").json()["response"]["game_id"]

    assert game_id_1 == game_id_2
