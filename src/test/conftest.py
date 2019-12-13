import _sqlite3
import pytest


@pytest.fixture()
def start_db():
    return _sqlite3.connect(":memory:")


@pytest.fixture()
def schema_db():
    lines = []
    with open('./src/test/file.sql') as fl:
        for line in fl:
            lines.append((line.strip(),))
    return lines