import asyncio
from concurrent.futures import ThreadPoolExecutor
from logging import basicConfig

import uvicorn
from botbattle import BotClient
from dispatcher import runner, webserver
from dispatcher.database import db

import random_player

basicConfig(level="DEBUG")


def main():
    # db().execute("")

    with ThreadPoolExecutor() as executor:
        for func in [start_webserver, start_clients, start_runner]:
            executor.submit(func)


def start_webserver():
    uvicorn.run(webserver.app, port=8200)


def start_clients(no_bots=3):
    tokens = [
        "d2b16e4a-c547-4076-be18-5f3699de3dbf",
        "4aa1e9e5-1979-4a89-94fe-776483cc8a4a",
        "f99e3af5-fdc7-4abd-b32e-a21cd4c5b851",
    ]
    bot_clients = [
        BotClient(token, random_player.RandomPlayer, "http://localhost:8200")
        for token in tokens[:no_bots]
    ]

    async def run_bots(bot_clients):
        tasks = [asyncio.create_task(run_bot(client)) for client in bot_clients]
        await asyncio.wait(tasks)
        print("All bots shutting down")

    async def run_bot(bot_client: BotClient):
        bot_client.run()

    asyncio.run(run_bots(bot_clients))


def start_runner():
    uvicorn.run(runner.app, port=8201)


if __name__ == "__main__":
    main()
