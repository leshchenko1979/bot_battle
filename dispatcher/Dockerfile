FROM python:slim

RUN pip install -U pip setuptools wheel

COPY botbattle .
COPY project.toml .
COPY requirements.txt .

RUN pip install -e .

COPY dispatcher/requirements.txt ./dispatcher

RUN pip install -r dispatcher/requirements.txt

COPY dispatcher .

# WORKDIR /src

CMD ["uvicorn", "dispatcher.dispatcher:app", "--host", "0.0.0.0", "--port", "8200"]

EXPOSE 8200
