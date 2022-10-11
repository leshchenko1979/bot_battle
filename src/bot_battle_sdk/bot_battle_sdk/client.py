import asyncio
from pathlib import Path

import httpx

from .protocol import (
    NewGameResponse, NewGameResponseType, GameStateResponse
)

from logging import info, debug

MAX_SOCKETS = 10
STARTING_PORT = 8100


class BotClient:
    def __init__(
        self,
        token: str,
        cls: type,
        dispatcher_url,
        max_games: int = 10
    ):
        self.bot_id = None
        self.bot_token = token
        self.bot_cls = cls

        self.dispatcher_url = Path(dispatcher_url)
        self.players = {}  # game_id: player

        self.semaphore = asyncio.Semaphore(max_games)
        self.runners = set()  # set of tasks running games

        self.set_up_http_client()

    def __repr__(self):
        return f"<BotClient(id={self.bot_id})>"

    def set_up_http_client(self):
        headers = {"Authorization": f"Bearer {self.token}"}
        self.http_client = httpx.AsyncClient(
            base_url=self.dispatcher_url, header=headers
        )

    async def get(self, path, **kwargs):
        return await self.http_client.get(path, **kwargs)

    async def post(self, path, **kwargs):
        return await self.http_client.post(path, **kwargs)

    async def run(self):
        await asyncio.gather(self.request_games(), self.run_games())

    async def request_games(self):
        info("Requesting new games")
        while True:
            response = NewGameResponse(await self.get("/new_game").json())

            if response.response_type == NewGameResponseType.WAIT:
                info(f"Asked to wait for {response.wait_for} seconds")
                await asyncio.sleep(response.wait_for)
                continue

            await self.semaphore.acquire()
            info(f"Starting new game {response.game_id}")
            self.runners.add(asyncio.create_task(self.game_runner(response.game_id)))

    async def run_games(self):
        info("Running games")
        while True:
            if not(self.runners):
                asyncio.sleep(1)
                continue

            done, self.runners = asyncio.wait(self.runners, return_when=asyncio.FIRST_COMPLETED)

            for _ in range(len(done)):
                self.semaphore.release()

    async def game_runner(self, game_id):
        player = self.bot_cls()

        # request initial state
        response = GameStateResponse(await self.get("/games/{game_id}/latest").json())

        while not response.result:
            # make a move
            move = player.make_move(response.state)
            response = GameStateResponse(await self.post(f"/games/{game_id}/move?move={move}").json())

        # show results
        info(f"Game {game_id} finished")
        info(f"{response.result}")
