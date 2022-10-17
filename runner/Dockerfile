FROM python:slim

RUN pip install -U pip setuptools wheel

COPY botbattle .
COPY project.toml .
COPY requirements.txt .

RUN pip install -e .

COPY common/requirements.txt ./runner

RUN pip install -r runner/requirements.txt

COPY runner .

# WORKDIR /src

CMD ["uvicorn", "runner.runner:app", "--host", "0.0.0.0", "--port", "8200"]

EXPOSE 8200
