import websockets
import asyncio

async def handler(websocket):
    print(await websocket.recv())

PORT = 80

async def main():
    async with websockets.serve(handler, "localhost", PORT):
        print("Server listening on port", PORT)
        await asyncio.Future()

asyncio.run(main())
