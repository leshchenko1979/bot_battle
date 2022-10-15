from fastapi import BackgroundTasks, FastAPI, Request

from .database import db
from .models import BotModel
from .runner import Runner

app = FastAPI()

from logging import basicConfig, info

basicConfig(level="DEBUG")

@app.post("/update_code")
async def update_code(code: str):
    ...
