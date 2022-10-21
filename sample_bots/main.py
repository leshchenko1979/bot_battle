from dotenv import load_dotenv

load_dotenv()


import asyncio
from concurrent.futures import ThreadPoolExecutor
from logging import basicConfig

import uvicorn
from botbattle import BotClient
from dispatcher import dispatcher
from runner import runner
from scheduler import scheduler

import random_player

basicConfig(level="DEBUG")


def main():
    with ThreadPoolExecutor() as executor:
        for func in [
            # start_dispatcher,
            # start_runner,
            # start_scheduler,
            start_clients,
        ]:
            executor.submit(func)


def start_dispatcher():
    uvicorn.run(dispatcher.app, port=8200)


def start_runner():
    uvicorn.run(runner.app, port=8201)


def start_scheduler():
    uvicorn.run(scheduler.app, port=8202)


class CustomRandomPlayer(random_player.RandomPlayer):
    ...

def start_clients(no_bots=1):
    tokens = [
        "d2b16e4a-c547-4076-be18-5f3699de3dbf",
        "4aa1e9e5-1979-4a89-94fe-776483cc8a4a",
        "f99e3af5-fdc7-4abd-b32e-a21cd4c5b851",
    ]
    bot_clients = [
        BotClient(token, CustomRandomPlayer, "http://localhost:8200")
        for token in tokens[:no_bots]
    ]

    async def run_bots(bot_clients):
        tasks = [asyncio.create_task(run_bot(client)) for client in bot_clients]
        await asyncio.wait(tasks)
        print("All bots shutting down")

    async def run_bot(bot_client: BotClient):
        bot_client.run()

    asyncio.run(run_bots(bot_clients))


if __name__ == "__main__":
    main()
