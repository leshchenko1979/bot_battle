import os

import pytest
from fastapi.testclient import TestClient

from ..dispatcher.webserver import app
from ..dispatcher.database import db

@pytest.fixture
def client():
    yield TestClient(app)

@pytest.fixture
def clean_up():
    db().execute("TRUNCATE games CASCADE")

"""
@pytest.fixture
def test_db():
    # db().execute("CREATE DATABASE public;")
    statements = get_creation_statements(
        Path("src/tests/supabase_dump.sql").read_text()
    )

    # db().execute("CREATE TABLE bots (id bigint NOT NULL,    created_at timestamp with time zone DEFAULT now() NOT NULL)")
    for statement in statements:
        db().execute(statement)


def get_creation_statements(text: str) -> list[str]:
    splitted = text.split("\n\n")

    needed_starts = ["CREATE TABLE public", "ALTER TABLE public"]

    domains = ["public"]

    s = "\n".join(
        stmt
        for stmt in splitted
        if any(stmt.startswith(start) for start in needed_starts)
    )

    s = s.replace("public.", "")

    s = s.replace("uuid ", "text ")

    s = s.replace("DEFAULT extensions.uuid_generate_v4()", "")

    s = s.replace("now()", "CURRENT_TIMESTAMP")

    return s.split(";")
"""
