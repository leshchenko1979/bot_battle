FROM python:slim

RUN pip install -U pip setuptools wheel

COPY botbattle botbattle
COPY common common
COPY requirements.txt .

RUN pip install -r requirements.txt -r common/requirements.txt

COPY runner runner
COPY __init__.py .

CMD ["uvicorn", "runner.runner:app", "--host", "0.0.0.0", "--port", "8201"]
