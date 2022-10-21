from logging import basicConfig, getLogger

from botbattle import Code, GameLog, Side
from common.database import db
from common.models import Bot, CodeVersion, Game, Participant, StateModel
from fastapi import BackgroundTasks, FastAPI, Request

app = FastAPI()

basicConfig(level="DEBUG")

logger = getLogger(__name__)
info = logger.info
debug = logger.debug
warning = logger.warning


@app.post("/update_code")
async def update_code(code: Code, request: Request):
    # find the bot
    bot = extract_bot(request)

    # load last code version
    last_version = bot.load_latest_code()

    # if nothing changed then quit
    if last_version and last_version == code:
        return

    # else save new code version
    new_version = CodeVersion(bot.id, code.source, code.cls_name)
    bot.suspended = False

    db().add(new_version)
    db().commit()


@app.post("/game_result")
async def game_result(result: GameLog, background: BackgroundTasks):
    background.add_task(save_game_result, result)


async def save_game_result(result: GameLog):
    info(f"Saving game {result.game_id} result")

    participants: list[Participant] = (
        db().query(Participant).filter(Participant.game_id == result.game_id).all()
    )

    assert len(participants) == 2

    if result.exception:
        game: Game = db().query(Game).filter(Game.id == result.game_id).one()
        game.exception = result.exception.msg

        if result.exception.caused_by_side == Side(participants[0].side):
            part_results = ("crashed", "opponent_crashed")
            perpetrator_idx = 0
        else:
            part_results = ("opponent_crashed", "crashed")
            perpetrator_idx = 1

        # mark the bot that caused the crash as suspended
        bot: Bot = (
            db().query(Bot).filter(Bot.id == participants[perpetrator_idx].bot_id).one()
        )
        bot.suspended = True

    elif result.winner:
        game: Game = db().query(Game).filter(Game.id == result.game_id).one()

        if Side(participants[0].side) == result.winner:
            part_results = ("victory", "loss")
            game.winner_id = participants[0].bot_id
        else:
            part_results = ("loss", "victory")
            game.winner_id = participants[1].bot_id

    else:
        part_results = ("tie", "tie")

    # save results for participants
    for participant, part_result in zip(participants, part_results):
        participant.result = part_result

    # save states
    for i, state in enumerate(result.states):
        state_model = StateModel(result.game_id, i, state.board, state.next_side.value)
        db().add(state_model)

    db().commit()


def extract_bot(request: Request) -> Bot:
    token = request.headers["Authorization"].split()[-1]
    bot: Bot = db().query(Bot).filter_by(token=token).one()
    debug(f"Processing request from bot {bot.id}")
    return bot
