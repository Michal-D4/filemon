import sqlite3

import pytest

import sys
from os import path
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from src.core import load_db_data as ld, create_db as db


DETECT_TYPES = sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES


@pytest.fixture()
def init_load_obj() -> (ld.LoadDBData, sqlite3.Connection):
    conn = sqlite3.connect(":memory:", check_same_thread=False,
                           detect_types=DETECT_TYPES)
    conn.cursor().execute('PRAGMA foreign_keys = ON;')
    db.create_all_objects(conn)
    loads = ld.LoadDBData(conn)
    return loads, conn
