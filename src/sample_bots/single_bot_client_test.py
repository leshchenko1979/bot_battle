import asyncio

import bot_battle_sdk.client

import random_player

from logging import basicConfig

basicConfig(level="INFO")

DISPATCHER_URI = "https://dispatcher-q22dvnigiq-uc.a.run.app"

def start_clients(no_bots=1):
    tokens = [
        "d2b16e4a-c547-4076-be18-5f3699de3dbf",
        "4aa1e9e5-1979-4a89-94fe-776483cc8a4a",
        "f99e3af5-fdc7-4abd-b32e-a21cd4c5b851",
    ]
    ports = [
        8100,
        8120,
        8140,
    ]

    bot_clients = [
        bot_battle_sdk.client.Client(
            token, random_player.RandomPlayer, starting_port=port, dispatcher_url=DISPATCHER_URI
        )
        for token, port in list(zip(tokens, ports))[:no_bots]
    ]

    async def run_bots(bot_clients):
        tasks = [asyncio.create_task(client.run()) for client in bot_clients]
        await asyncio.wait(tasks)
        print("All bots shutting down")

    asyncio.run(run_bots(bot_clients))

start_clients(2)
