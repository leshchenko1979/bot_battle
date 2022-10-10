FROM python:slim

RUN pip install -U pip setuptools wheel

COPY src/bot_battle_sdk src/bot_battle_sdk

RUN pip install -e src/bot_battle_sdk

COPY src/dispatcher/requirements.txt src/dispatcher/

RUN pip install -r src/dispatcher/requirements.txt

COPY src/dispatcher src/dispatcher/

COPY src/*.py src/

# WORKDIR /src

CMD ["uvicorn", "src.dispatcher.webserver:app", "--host", "0.0.0.0", "--port", "8200"]

EXPOSE 8200
