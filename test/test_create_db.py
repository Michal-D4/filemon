from pathlib import Path
from typing import Iterable
import pytest
import sqlite3

from src.core import create_db as db


PATH_TO_DATA = Path("test/data")

# Files with input data for DB (table name, autoincrement)
#  if "autoincrement" then the ID (first field) should be skipped: [1:]
FILES = [
    ("Dirs.txt", 1),
    ("VirtDirs.txt", 0),
    ("Files.txt", 1),
    ("VirtFiles.txt", 0),
    ("Comments.txt", 1),
    ("Extensions.txt", 1),
    ("ExtGroups.txt", 1),
    ("Authors.txt", 1),
    ("FileAuthor.txt", 0),
    ("Tags.txt", 1),
    ("FileTag.txt", 0),
]


@pytest.fixture()
def start_db():
    return sqlite3.connect(":memory:")


@pytest.fixture()
def schema_db():
    """
    file 'data/file.sql' contains current schema of DB.
    The 'CREATE clause can span multiple lines.
    @return:
    """
    lines = []
    with open(PATH_TO_DATA / "file.sql") as fl:
        curr = next(fl)
        for line in fl:
            if line.startswith("CREATE"):
                lines.append(curr.strip("\n"))
                curr = line
            else:
                curr += line
        lines.append(curr.strip())
    return lines


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
                    values.append(tuple(line.strip("\n").split("|")))

        res[
            fl[0].split(".")[0]
        ] = values  # fl[0].split('.')[0] a dict key = "table name"
    return res


@pytest.fixture()
def init_db() -> sqlite3.Connection:
    """
    Establish connection with DB
    Create all DB objects
    Load data from saved working database tables (full select)
    @return: None
    """

    def create_sql(table: str, header: Iterable):
        placeholders = ",".join(["?"] * len(header))
        return f'INSERT INTO {table} ({",".join(header)}) VALUES ({placeholders});'

    conn = sqlite3.connect(":memory:")
    db.create_all_objects(conn)
    for fl in FILES:
        fll = PATH_TO_DATA / fl[0]
        tbl = fl[0].split(".")[0]
        vals = []
        sql = ""
        with open(fll) as fi:
            is_header = True
            for line in fi:
                fields = line.strip("\n").split("|")[fl[1] :]
                if is_header:
                    sql = create_sql(tbl, fields)
                    is_header = False
                else:
                    vals.append(tuple(fields))
        if vals:
            conn.executemany(sql, vals)

    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def test_create_connection(start_db):
    con = start_db
    assert isinstance(con, sqlite3.Connection)


def test_create_all_objects(start_db, schema_db):
    """
    test number of created db objects and
    'CREATE' clauses for its creation
    @param start_db: db connection
    @param schema_db: expected 'CREATE' clauses
    @return: None
    """
    con = start_db
    db.create_all_objects(con)

    schema_ = schema_db
    # sql == ''  for auto created primary keys
    lines = con.execute(
        "select count(*)  from sqlite_master where sql != '';"
    ).fetchone()
    assert lines[0] == len(schema_)

    schema = con.execute("select sql from sqlite_master where sql != '';")
    i = 0
    for row in schema:
        assert row[0] == schema_[i]
        i += 1


def test_load_data(init_db, expected):
    """
    Test whether unloaded data loaded correctly
    @param init_db: fixture - creates DB and load data into it
    @param expected: expected data in each DB table
    @return:
    """
    conn: sqlite3.Connection = init_db
    exp: dict = expected

    for key, it in exp.items():
        if it:
            sql = f"select * from {key};"
            curs = conn.execute(sql)
            i = 0
            for row in curs:
                if None not in row:  # skip common root record in Dirs table
                    assert tuple(map(str, row)) == it[i]
                    i += 1
