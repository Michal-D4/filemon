import pytest
import sqlite3
import src.core.create_db as db


@pytest.fixture()
def start_db():
    return sqlite3.connect(":memory:")


@pytest.fixture()
def schema_db():
    lines = []
    with open('file.sql') as fl:
        curr = next(fl)
        for line in fl:
            if line.startswith('CREATE'):
                lines.append(curr.strip('\n'))
                curr = line
            else:
                curr += line
        lines.append(curr.strip('\n'))
    return lines


def test_create_connection(start_db):
    con = start_db
    assert isinstance(con, sqlite3.Connection)


def test_create_all_objects(start_db, schema_db):
    con = start_db
    db.create_all_objects(con)

    expected = schema_db
    lines = con.execute('select count(*)  from sqlite_master;').fetchone()
    assert lines[0] == len(expected)

    schema = con.execute('select sql from sqlite_master;')
    i = 0
    for row in schema:
        assert row[0] == expected[i]
        i += 1

