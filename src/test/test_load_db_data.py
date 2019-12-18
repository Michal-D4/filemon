import pytest
from pathlib import Path
import sqlite3
from loguru import logger

from src.core import create_db as db
import src.core.load_db_data as ld

DETECT_TYPES = sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
PATH_TO_DATA = Path('data')
ROOT = Path.cwd().parent.parent / 'test_data'
logger.remove()


@pytest.fixture(params=[
    ('',),
    ('pdf', 'ui'),
    '*'
])
def expected_files(request):
    def check_ext(ext_, file_parts: tuple) -> bool:
        if '*' in ext_:
            return True
        last_part = file_parts[-1]
        name, ext_file = last_part.rpartition('.')[0::2]
        file_ext = ext_file if name else ''
        return file_ext in ext_

    ext = request.param
    files = []
    # 'file_list.txt' - file with expected results
    with open(PATH_TO_DATA / 'file_list.txt') as fl:
        for line in fl:
            row = tuple(line.strip().split('/'))
            if check_ext(ext, row):
                files.append(row)
    return files, ext


@pytest.fixture()
def init_load() -> (ld.LoadDBData, sqlite3.Connection):
    conn = sqlite3.connect(":memory:", check_same_thread=False,
                           detect_types=DETECT_TYPES)
    conn.cursor().execute('PRAGMA foreign_keys = ON;')
    db.create_all_objects(conn)
    loads = ld.LoadDBData(conn)
    return loads, conn


@pytest.mark.parametrize('root, ext, expect',
                         [(ROOT / '.dir3', ('txt', 'py'), 2),
                          (ROOT, '*', 11),
                          (ROOT, '', 0),     # because files without extension are not loaded
                          ])
def test_load_data_file_count(init_load, root, ext, expect):
    """
    test count of loaded files
    """
    load_d, conn_d = init_load
    load_d.load_data(root, ext)
    file_count = conn_d.execute('select count(*) from files;').fetchone()
    assert file_count[0] == expect


def test_yield_files(expected_files):
    ll = len(ROOT.parts) - 1
    ext = expected_files[1]
    files = ld.yield_files(ROOT, ext)
    exp = expected_files[0]
    for file in files:
        ff = Path(file).parts[ll:]
        assert ff in exp


def test_insert_dir():
    pass


def test_search_closest_parent():
    pass


def test_change_parent():
    pass


def test_parent_id_for_child():
    pass


def test_insert_file():
    pass


def test_insert_extension():
    pass