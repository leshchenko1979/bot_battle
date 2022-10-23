from botbattle import PlayerAbstract, BotClient

TOKEN = "d2b16e4a-c547-4076-be18-5f3699de3dbf"

class Player(PlayerAbstract):
    ...

BotClient(TOKEN, Player, "http://localhost:8200").run()
