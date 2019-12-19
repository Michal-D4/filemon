import pytest
from pathlib import Path
import sqlite3
from loguru import logger
# import sys

from src.core import create_db as db
import src.core.load_db_data as ld

DETECT_TYPES = sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
PATH_TO_DATA = Path('data')
FILE_NAME_LIST = PATH_TO_DATA / 'file_list.txt'
TEST_ROOT_DIR = Path.cwd().parent.parent / 'test_data'
logger.remove()
fmt = '<green>{time:HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | ' \
      '<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> ' \
      '- <level>{message}</level>'
# logger.add(sys.stderr, format=fmt, level='INFO')


@pytest.fixture(params=[
    ('',),
    ('pdf', 'ui'),
    '*'
])
def expected_files(request):
    """
    List of files to be loaded/found with 'yield_files' function
    @param request: list of file extensions
    @return: expected_list_of_files, extensions_parameter_for_yield_files
    """
    def check_ext(ext_, file_parts: tuple) -> bool:
        """
        @param ext_: list of extensions
        @param file_parts: as return with Path.parts, to be used both in Windows & Linux
        return True if file extension is in the list
                       or the list contains symbol '*' - any extension
        """
        if '*' in ext_:
            return True
        last_part = file_parts[-1]
        name, ext_file = last_part.rpartition('.')[0::2]
        file_ext = ext_file if name else ''
        return file_ext in ext_

    ext = request.param
    files = []
    with open(FILE_NAME_LIST) as fl:
        for line in fl:
            row = tuple(line.strip().split('/'))
            if check_ext(ext, row):
                files.append(row)
    return files, ext


@pytest.fixture()
def init_load_obj() -> (ld.LoadDBData, sqlite3.Connection):
    conn = sqlite3.connect(":memory:", check_same_thread=False,
                           detect_types=DETECT_TYPES)
    conn.cursor().execute('PRAGMA foreign_keys = ON;')
    db.create_all_objects(conn)
    loads = ld.LoadDBData(conn)
    return loads, conn


root_paths = [
    ('.dir3', '',   # TEST_ROOT_DIR, '' - empty extension
     ('dir1', None),
     ('.dir3/.dir.1.1', TEST_ROOT_DIR / '.dir3'),
     ('.dir3', TEST_ROOT_DIR / '.dir3'),
     ),
    ('', ('pd', 'png'),
     ('', None),
     )
]


@pytest.fixture(params=root_paths)
def db_with_loaded_data(request):
    conn = sqlite3.connect(":memory:", check_same_thread=False,
                           detect_types=DETECT_TYPES)
    conn.cursor().execute('PRAGMA foreign_keys = ON;')
    db.create_all_objects(conn)
    loads = ld.LoadDBData(conn)
    rt = TEST_ROOT_DIR / request.param[0]
    loads.load_data(rt, request.param[1])
    return loads, conn, request.param[2:]


@pytest.mark.parametrize('root, ext, expect',
                         [(TEST_ROOT_DIR / '.dir3', ('txt', 'py'), 2),
                          (TEST_ROOT_DIR, '*', 14),
                          (TEST_ROOT_DIR, '', 3),
                          ])
def test_load_data_file_count(init_load_obj, root, ext, expect):
    """
    test count of loaded files
    """
    load_d, conn_d = init_load_obj
    load_d.load_data(root, ext)
    file_count = conn_d.execute('select count(*) from files;').fetchone()
    assert file_count[0] == expect


def test_yield_files(expected_files):
    ll = len(TEST_ROOT_DIR.parts) - 1
    ext = expected_files[1]     # list of extensions
    files = ld.yield_files(TEST_ROOT_DIR, ext)
    exp = expected_files[0]     # list of expected files (file parts)
    for file in files:
        ff = Path(file).parts[ll:]
        assert ff in exp


def test_insert_dir(init_load_obj, expected_files):
    """
    test that "insert_dir" method always return correct dir_id
    """
    def construct_dir(root_: Path, file_parts: tuple) -> Path:
        rr = root_
        for fp in file_parts:
            rr = rr / fp
        return rr.parent    # remove file name, left only path

    load_d, conn_d = init_load_obj    # LoadDBData object, sqlite Connection
    root = TEST_ROOT_DIR.parent
    for file in expected_files[0]:
        dir_ = construct_dir(root,  file)
        dir_id, inserted = load_d.insert_dir(dir_)
        cur_path = conn_d.execute('select path from dirs where dirid = ?;', str(dir_id)).fetchone()
        cur_path = Path(cur_path[0])
        assert cur_path == dir_


def test_search_closest_parent(db_with_loaded_data):
    load_d, conn_d, *dirs = db_with_loaded_data  # LoadDBData object, sqlite Connection
    for dd in dirs[0]:
        logger.debug(dd)
        dd_path = TEST_ROOT_DIR / dd[0]
        _, parent = load_d.search_closest_parent(dd_path)
        assert parent == dd[1]


def test_change_parent():
    pass


def test_parent_id_for_child():
    pass


def test_insert_file():
    pass


def test_insert_extension():
    pass