FROM python:slim

RUN pip install -U pip setuptools wheel

COPY botbattle botbattle
COPY common common
COPY requirements.txt .

RUN pip install -r requirements.txt -r common/requirements.txt

COPY __init__.py .

COPY scheduler scheduler

CMD ["uvicorn", "scheduler.scheduler:app", "--host", "0.0.0.0", "--port", "8202"]

EXPOSE 8202
