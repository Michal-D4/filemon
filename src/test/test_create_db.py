from typing import Iterable
import pytest
import sqlite3
from src.core import create_db as db
from src.test.conftest import FILES, PATH_TO_DATA


@pytest.fixture()
def start_db():
    return sqlite3.connect(":memory:")


@pytest.fixture()
def schema_db():
    lines = []
    with open('data/file.sql') as fl:
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


def test_load_data(init_db, expected):
    conn: sqlite3.Connection = init_db
    exp: dict = expected

    for key, it in exp.items():
        if it:
            print(key)
            sql = f'select * from {key};'
            curs = conn.execute(sql)
            i = 0
            for row in curs:
                print(row)
                if None not in row:
                    assert tuple(map(str,row)) == it[i]
                    i += 1


@pytest.fixture()
def expected() -> dict():
    res = dict()
    for fl in FILES:
        fll = PATH_TO_DATA / fl[0]
        values = []
        with open(fll) as fi:
            skip_line = True
            for line in fi:
                if skip_line:
                    skip_line = False
                else:
                    values.append(tuple(line.strip('\n').split('|')))

        res[fl[0].split('.')[0]] = values
    return res


@pytest.fixture()
def init_db() -> sqlite3.Connection:
    def create_sql(table: str, header: Iterable):
        placeholders = ','.join(['?'] * len(header))
        return f'INSERT INTO {table} ({",".join(header)}) VALUES ({placeholders});'

    conn = sqlite3.connect(":memory:")
    db.create_all_objects(conn)
    for fl in FILES:
        fll = PATH_TO_DATA / fl[0]
        # if fl[0].startswith('inDirs'):
        #     tbl = 'Dirs'
        # else:
        tbl = fl[0].split('.')[0]
        vals = []
        sql = ''
        with open(fll) as fi:
            is_header = True
            for line in fi:
                fields = line.strip('\n').split('|')[fl[1]:]
                if is_header:
                    sql = create_sql(tbl, fields)
                    is_header = False
                else:
                    vals.append(tuple(fields))
        if vals:
            conn.executemany(sql, vals)

    conn.execute('PRAGMA foreign_keys = ON;')
    return conn