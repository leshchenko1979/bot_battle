from bot_battle_sdk.protocol import ClientData
from fastapi import BackgroundTasks, FastAPI, Request

from .database import db
from .models import BotModel
from .runner import Runner

app = FastAPI()

from logging import basicConfig, info

basicConfig(level="DEBUG")


async def register_in_db(bot: BotModel, client_data: ClientData, request: Request):
    # set status to alive
    bot.alive = True

    # set ports
    bot.starting_port = client_data.starting_port
    bot.max_sockets = client_data.max_sockets

    # set host
    bot.host = request.client.host

    info(f"Bot requesting games: {bot}")

    db().commit()


runner_running = False


async def start_runner():
    global runner_running
    if not runner_running:
        runner_running = True
        await Runner().run()
        runner_running = False


@app.post("/")
async def client_alive(
    client_data: ClientData, request: Request, backgound_tasks: BackgroundTasks
):
    # check if token exists
    bot: BotModel = (
        db().query(BotModel).filter(BotModel.token == client_data.token).one()
    )

    backgound_tasks.add_task(register_in_db, bot, client_data, request)
    backgound_tasks.add_task(start_runner)

    return {"bot_id": bot.id}
