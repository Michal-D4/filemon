import sqlite3
import pytest
from pathlib import Path
from typing import Iterable

import src.core.create_db as db


PATH_TO_DATA = Path.cwd().parent.parent / 'tmp/CSV'

# Files with input data for DB (name, autoincrement)
FILES = [('inDirs.csv', 1),
         ('VirtDirs.csv', 0),
         ('Files.csv', 1),
         ('VirtFiles.csv', 0),
         ('Comments.csv', 1),
         ('Extensions.csv', 1),
         ('ExtGroups.csv', 1),
         ('FileAuthor.csv', 0),
         ('Tags.csv', 1),
         ('FileTag.csv', 0),
         ]

FILEI = ['Dirs.csv',   # because of "Favorites"
         'VirtDirs.csv',
         'Files.csv',
         'VirtFiles.csv',
         'Comments.csv',
         'Extensions.csv',
         'ExtGroups.csv',
         'FileAuthor.csv',
         'Tags.csv',
         'FileTag.csv',
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
        if fl[0].startswith('inDirs'):
            tbl = 'Dirs'
        else:
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
    for fl in FILEI:
        fll = PATH_TO_DATA / fl
        vals = []
        with open(fll) as fi:
            skip_line = True
            for line in fi:
                if skip_line:
                    skip_line = False
                else:
                    vals.append(tuple(line.strip('\n').split('|')))

        res[fl.split('.')[0]] = vals
    return res
