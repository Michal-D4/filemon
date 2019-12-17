import sqlite3
import pytest
from pathlib import Path
from typing import Iterable

import src.core.create_db as db


PATH_TO_DATA = Path('data')

# Files with input data for DB (name, autoincrement)
#  if "autoincrement" then the ID (first field) should be skipped: [1:]
FILES = [('Dirs.txt', 1),
         ('VirtDirs.txt', 0),
         ('Files.txt', 1),
         ('VirtFiles.txt', 0),
         ('Comments.txt', 1),
         ('Extensions.txt', 1),
         ('ExtGroups.txt', 1),
         ('FileAuthor.txt', 0),
         ('Tags.txt', 1),
         ('FileTag.txt', 0),
         ]


def create_sql(table: str, header: Iterable):
    placeholders = ','.join(['?'] * len(header))
    sql = f'INSERT INTO {table} ({",".join(header)}) VALUES ({placeholders});'
    return sql


@pytest.fixture()
def init_db() -> sqlite3.Connection:
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


@pytest.fixture()
def expected() -> dict():
    res = dict()
    for fl in FILES:
        fll = PATH_TO_DATA / fl[0]
        vals = []
        with open(fll) as fi:
            skip_line = True
            for line in fi:
                if skip_line:
                    skip_line = False
                else:
                    vals.append(tuple(line.strip('\n').split('|')))

        res[fl[0].split('.')[0]] = vals
    return res
