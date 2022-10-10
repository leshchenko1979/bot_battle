import asyncio
import random
from logging import info
from uuid import uuid4

import sqlalchemy
import websockets
from bot_battle_sdk.protocol import (
    MoveMessage,
    ResultMessage,
    StartingMessage,
    StateMessage,
)
from bot_battle_sdk.sides import Side
from bot_battle_sdk.state import State

from .database import db
from .models import BotModel, GameModel

COMMUNICATION_ERRORS = (
    ConnectionRefusedError,
    asyncio.exceptions.IncompleteReadError,
    websockets.WebSocketException,
)


class Bot:
    busy_ports: set()
    model: BotModel

    def __init__(self, model: BotModel):
        self.busy_ports = set()
        self.model = model

    def __repr__(self):
        return f"<Bot({self.model.id}, alive={self.model.alive})>"

    def yield_free_port(self) -> int:
        all_ports = set(
            range(
                self.model.starting_port,
                self.model.starting_port + self.model.max_sockets,
            )
        )
        free_ports = all_ports - self.busy_ports
        chosen = next(iter(free_ports))
        self.busy_ports.add(chosen)
        return chosen


class Game:
    bots: list[Bot]

    def __repr__(self):
        return f"<Game(bots={self.bots})>"


class Runner:
    def __init__(self, max_games=10, cycle_time=5, games_to_play: int = None):
        self.max_games = max_games
        self.cycle_time = cycle_time

        self.games_to_play = games_to_play

        self.games = asyncio.Queue(max_games)
        self.alive_bots: dict[int, Bot] = {}
        self.health_check_queue = asyncio.Queue()

    async def run(self):
        info("Runner started")

        try:
            await asyncio.wait(
                [
                    self.schedule_games(),
                    self.run_scheduled_games(),
                    self.process_health_check_queue(),
                ]
            )
        finally:
            db().close()

        info("Runner finished")

    async def schedule_games(self) -> None:
        while self.games_to_play or self.games_to_play is None:
            bots_from_db = db().query(BotModel).filter(BotModel.alive).all()
            info(f"Alive bots: {self.alive_bots}")

            self.update_bots(bots_from_db)
            self.check_alive(self.alive_bots.values())

            if len(self.alive_bots) < 2:
                info("No bots to match, sleeping")
                await asyncio.sleep(self.cycle_time)
                continue

            await asyncio.wait(
                [
                    asyncio.wait([self.schedule_cycle()], timeout=self.cycle_time),
                    asyncio.sleep(self.cycle_time),
                ]
            )

    def update_bots(self, bots_from_db: list[BotModel]):
        db_dict = dict(zip([bot.id for bot in bots_from_db], bots_from_db))

        db_alive_ids = set(db_dict.keys())
        memory_alive_ids = set(self.alive_bots.keys())

        new = db_alive_ids - memory_alive_ids
        missing = memory_alive_ids - db_alive_ids

        # add new
        for bot_id in new:
            info(f"Adding bot {bot_id}")
            self.alive_bots[bot_id] = Bot(db_dict[bot_id])

        # remove missing
        for bot_id in missing:
            info(f"Removing bot {bot_id}")
            del self.alive_bots[bot_id]

    async def schedule_cycle(self):
        for bots in self.match_bots():
            game = Game()
            game.bots = bots
            info(f"Adding game {game}")
            await self.games.put(game)
            info(f"Game {game} added")

    def match_bots(self):
        while True:
            # get bots with free ports
            candidates = [
                bot
                for bot in self.alive_bots.values()
                if len(bot.busy_ports) < bot.model.max_sockets
            ]

            # yield two random bots
            if len(candidates) < 2:
                break

            yield random.sample(candidates, 2)

    async def run_scheduled_games(self):
        info("Running scheduled games")

        running = set()

        while True:  # run this cycle once per game completion
            # fill up the games pool
            if not running and self.games.empty():
                info("Waiting for scheduled games")
                await asyncio.sleep(self.cycle_time)
                continue
            else:
                info("Skip waiting")

            while (
                (not self.games.empty())
                and (len(running) < self.max_games)
                and (self.games_to_play or self.games_to_play is None)
            ):
                info(
                    f"Filling up games pool. {self.games.qsize()} games scheduled, {len(running)} running"
                )
                game = await self.games.get()
                info(f"Game received: {game}")
                running.add(asyncio.create_task(self.run_game(game)))

                if self.games_to_play is not None:
                    self.games_to_play -= 1

            info(f"Running {len(running)} scheduled games")
            done, running = await asyncio.wait(
                running, return_when=asyncio.FIRST_COMPLETED
            )

            if not (running or self.games_to_play or self.games_to_play is None):
                break

    async def run_game(self, game: Game):
        info(f"Starting game {game}")

        if any(not bot.model.alive for bot in game.bots):
            info(f"Game {game} aborted, as not all bots are alive")
            return

        # find free ports
        ports = [bot.yield_free_port() for bot in game.bots]

        blue_socket, red_socket = None, None

        try:
            # establish connections
            blue_socket, red_socket = await asyncio.gather(
                *[
                    websockets.connect(f"ws://{bot.model.host}:{port}")
                    for bot, port in zip(game.bots, ports)
                ]
            )

            # send starting messages
            game_id = uuid4()
            tasks = [
                socket.send(StartingMessage(game_id=game_id, side=side).json())
                for socket, side in ((blue_socket, Side.BLUE), (red_socket, Side.RED))
            ]
            await asyncio.wait(tasks)

            # send states and get moves
            state = State(next_side=Side.BLUE)
            cur_bot_socket = blue_socket

            while not (winners := state.winners()):
                await cur_bot_socket.send(StateMessage(state=state).json())
                move = MoveMessage.parse_raw(await cur_bot_socket.recv()).move
                state.drop_token(move)
                cur_bot_socket = (
                    blue_socket if cur_bot_socket == red_socket else red_socket
                )

            # send results and assign game winner
            result_msg = ResultMessage(
                winner=(None if len(winners) == 2 else winners[0])
            )
            await asyncio.wait(
                [socket.send(result_msg.json()) for socket in [blue_socket, red_socket]]
            )

            # save results in database
            game_model = GameModel()
            game_model.participants = [bot.model.id for bot in game.bots]
            game_model.winner = (
                game.bots[0].model.id
                if result_msg.winner == Side.BLUE
                else game.bots[1].model.id
            )

            db().add(game_model)
            try:
                db().commit()
                info(f"Game {game} saved in database")
            except sqlalchemy.exc.PendingRollbackError:
                db().rollback()
                db().add(game_model)
                db().commit()
                info(f"Game {game} saved in database")

        except COMMUNICATION_ERRORS:
            info("WebSocketException, checking bots")
            self.check_alive(game.bots)

        finally:
            # close connections
            tasks = [
                socket.close()
                for socket in [blue_socket, red_socket]
                if socket and not socket.closed
            ]

            if tasks:
                await asyncio.wait(tasks)

            # make ports available
            for bot, port in zip(game.bots, ports):
                bot.busy_ports -= {port}

    def check_alive(self, bots: list[Bot]) -> bool:
        for bot in bots:
            self.health_check_queue.put_nowait(bot)

    async def process_health_check_queue(self):
        while True:
            bot = await self.health_check_queue.get()
            if bot.model.alive:
                health_port = bot.model.starting_port + bot.model.max_sockets

                try:
                    async with websockets.connect(
                        f"ws://{bot.model.host}:{health_port}"
                    ):
                        info(f"Bot {bot} is alive")

                except COMMUNICATION_ERRORS:
                    info(f"Bot {bot} is dead")

                    bot.model.alive = False
                    db().commit()

                    if bot.model.id in self.alive_bots:
                        del self.alive_bots[bot.model.id]


if __name__ == "__main__":
    asyncio.run(Runner().run())
