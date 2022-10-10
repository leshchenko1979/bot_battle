import asyncio

from concurrent.futures import ThreadPoolExecutor
import time

import bot_battle_sdk.client
import uvicorn
from src.dispatcher import runner, webserver

import random_player

from src.dispatcher.database import db


def main():
    db().execute("UPDATE bots SET alive=false")

    with ThreadPoolExecutor() as executor:
        for func in [start_webserver, start_clients, start_runner]:
            executor.submit(func)


def start_webserver():
    uvicorn.run(webserver.app, port=8200)


def start_clients(no_bots = 1):
    tokens = [
        "d2b16e4a-c547-4076-be18-5f3699de3dbf",
        "4aa1e9e5-1979-4a89-94fe-776483cc8a4a",
        "f99e3af5-fdc7-4abd-b32e-a21cd4c5b851",
    ]
    ports = [8100, 8120, 8140]

    bot_clients = [
        bot_battle_sdk.client.Client(
            token, random_player.RandomPlayer, starting_port=port
        )
        for token, port in list(zip(tokens, ports))[:no_bots]
    ]

    async def run_bots(bot_clients):
        tasks = [asyncio.create_task(client.run()) for client in bot_clients]
        await asyncio.wait(tasks)
        print("All bots shutting down")

    asyncio.run(run_bots(bot_clients))


def start_runner():
    time.sleep(2)
    asyncio.run(runner.Runner().run())


if __name__ == "__main__":
    main()
