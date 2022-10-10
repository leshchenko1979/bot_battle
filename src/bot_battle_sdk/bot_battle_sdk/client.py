import asyncio

import httpx
import websockets

from .protocol import (
    MoveMessage,
    ResultMessage,
    StartingMessage,
    StateMessage,
    ClientData,
)

MAX_SOCKETS = 10
STARTING_PORT = 8100


class Client:
    def __init__(
        self,
        token: str,
        cls: type,
        dispatcher_url="http://localhost:8200",
        starting_port=STARTING_PORT,
        max_sockets=MAX_SOCKETS,
    ):
        self.bot_id = None
        self.bot_token = token
        self.bot_cls = cls

        self.dispatcher_url = dispatcher_url
        self.starting_port = starting_port
        self.max_sockets = max_sockets
        self.players = {}  # game_id: player

        self.sockets = [None] * (max_sockets + 1)

    def __repr__(self):
        return f"<Client(id={self.bot_id})>"

    async def run(self):
        try:
            tasks = [
                self.set_up_socket(i, self.game_runner) for i in range(self.max_sockets)
            ]
            tasks += [self.set_up_socket(self.max_sockets, self.health_checker)]
            await asyncio.wait(tasks)
            print(f"{self.max_sockets + 1} sockets set up")

            await self.keep_connection()

        except KeyboardInterrupt:
            print("Interrupted by user")

        for socket in self.sockets:
            socket.close()

    async def keep_connection(self):
        while True:
            print(f"Connecting to {self.dispatcher_url}")

            # register self with the dispatcher
            async with httpx.AsyncClient() as client:
                result = await client.post(
                    self.dispatcher_url,
                    data=ClientData(
                        token=self.bot_token,
                        starting_port=self.starting_port,
                        max_sockets=self.max_sockets,
                    ).json(),
                )

            print("Connection result:", result)

            if result.status_code == 200:
                json = result.json()
                self.bot_id = json["bot_id"]

            await asyncio.sleep(10)

    async def set_up_socket(self, i: int, handler):
        port = self.starting_port + i
        self.sockets[i] = await websockets.serve(handler, "localhost", port)

    async def game_runner(self, websocket):
        game_id = None
        try:
            # start
            starting_msg = StartingMessage.parse_raw(await websocket.recv())
            game_id, side = starting_msg.game_id, starting_msg.side

            self.players[game_id] = self.bot_cls(side)
            print(f"Started a game {game_id}, {side}")

            # make moves
            while True:
                msg = await websocket.recv()
                try:
                    state_msg = StateMessage.parse_raw(msg)
                except Exception:
                    break

                # print(f"Received state {state_msg}")

                move = self.players[game_id].make_move(state_msg.state)
                move_msg = MoveMessage(move=move).json()

                # print(f"Sending move: {move}")
                await websocket.send(move_msg)

            # print results
            result = ResultMessage.parse_raw(msg)
            print(f"{game_id}: {result}")

        except (
            websockets.exceptions.WebSocketException,
            asyncio.exceptions.IncompleteReadError,
        ) as e:
            print(f"Websocket error: {e}")

        finally:
            if game_id and game_id in self.players:
                del self.players[game_id]

    @staticmethod
    async def health_checker(websocket):
        pass
