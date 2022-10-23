FROM python:slim

RUN pip install -U pip setuptools wheel

COPY requirements.txt .
COPY common/requirements.txt common/

RUN pip install -r requirements.txt -r common/requirements.txt

COPY __init__.py .
COPY botbattle botbattle
COPY common common
COPY dispatcher dispatcher

CMD ["uvicorn", "dispatcher.dispatcher:app", "--host", "0.0.0.0", "--port", "8200"]

EXPOSE 8200
