import websockets
import asyncio

ADDR = "ws://104.197.184.61:1080"

async def main():
    async with websockets.connect(ADDR) as socket:
        print("Connected to", ADDR)
        print(await socket.recv())

asyncio.run(main())
