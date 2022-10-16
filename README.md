# The client

Sample code:

```python
from bot_battle_sdk import Client, PlayerAbstract, State

TOKEN = "XXX"

class MyPlayer(PlayerAbstract):
    def make_move(self, state: State) -> int:
        """Your code here"""
        ...

asyncio.run(Client(TOKEN, MyPlayer).run())
```

Sample output:
```
Bot name: devil_bot_2331
Connected to server: http://111.111.111.111: 1111
Your rating: 2450
42 other bots online
Game 1: 30 moves played. You won!
Game 2: 26 moves played. You won!
Game 3: 35 moves played. You won!
Game 4: 41 moves played. You lose!
Game 5: 28 moves played. You won!
Game 6: 29 moves played. You won!
Game 7: 49 moves played. Tie!
Game 8: 15 moves played. You won!
Waiting for games (press Ctrl-C to interrupt)...interrupted
Your rating: 2560 (+110)
Check your rating at https://botbattle.dev/bot/devil_bot_2331
```
