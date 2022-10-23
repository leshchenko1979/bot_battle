FROM python:slim

RUN pip install -U pip setuptools wheel

COPY __init__.py .
COPY requirements.txt .
COPY common/requirements.txt common/

RUN pip install -r requirements.txt -r common/requirements.txt

COPY botbattle botbattle
COPY common common
COPY runner runner

CMD ["uvicorn", "runner.runner:app", "--host", "0.0.0.0", "--port", "8201"]
