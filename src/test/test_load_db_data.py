import pytest
from pathlib import Path
import sqlite3
from loguru import logger
# import sys

from src.core import create_db as db
import src.core.load_db_data as ld

DETECT_TYPES = sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
PATH_TO_DATA = Path('data')
TEST_ROOT_DIR = Path.cwd().parent.parent / 'test_data'
logger.remove()
fmt = '<green>{time:HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | ' \
      '<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> ' \
      '- <level>{message}</level>'
# logger.add(sys.stderr, format=fmt, level='INFO')
FILE_LIST = [
    'test_data/.gitignore',
    'test_data/.dir3/.dir.1.2/dir.1.2.3/file2.py',
    'test_data/.dir3/dir.1.1/.file2.pd',
    'test_data/.dir3/dir.1.1/file1.sql',
    'test_data/.dir3/dir.1.1/PyCharm_ReferenceCard.pdf',
    'test_data/.dir3/.file1',
    'test_data/.dir3/.file2.txt',
    'test_data/.dir3/file2',
    'test_data/dir1/file1.py',
    'test_data/dir1/Structuring_and_automating_a_Python_project.pdf',
    'test_data/dir2/fixtures2.txt',
    'test_data/dir2/sel_opt.png',
    'test_data/dir2/sel_opt.ui',
    'test_data/file1.py',
]


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
    def check_ext(ext_, file_: Path) -> bool:
        """
        @param ext_: list of extensions
        @param file_: as return with Path.parts, to be used both in Windows & Linux
        return True if file extension is in the list
                       or the list contains symbol '*' - any extension
        """
        if '*' in ext_:
            return True
        file_ext = file_.suffix.strip('.')
        return file_ext in ext_

    ext = request.param
    files = []
    for line in FILE_LIST:
        row = Path(line)
        if check_ext(ext, row):
            files.append(row.parts)
    return files, ext


def test_yield_files(expected_files):
    ll = len(TEST_ROOT_DIR.parts) - 1
    ext = expected_files[1]     # list of extensions
    files = ld.yield_files(TEST_ROOT_DIR, ext)
    exp = expected_files[0]     # list of expected files (file parts)
    for file in files:
        ff = Path(file).parts[ll:]
        assert ff in exp


@pytest.fixture()
def init_load_obj() -> (ld.LoadDBData, sqlite3.Connection):
    conn = sqlite3.connect(":memory:", check_same_thread=False,
                           detect_types=DETECT_TYPES)
    conn.cursor().execute('PRAGMA foreign_keys = ON;')
    db.create_all_objects(conn)
    loads = ld.LoadDBData(conn)
    return loads, conn


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


def test_insert_dir(init_load_obj, expected_files):
    """
    test that "insert_dir" method always return correct dir_id
    """

    load_d, conn_d = init_load_obj    # LoadDBData object, sqlite Connection
    root = TEST_ROOT_DIR.parent
    for file in expected_files[0]:
        dir_ = construct_dir(root,  file)
        dir_id, inserted = load_d.insert_dir(dir_)
        cur_path = conn_d.execute('select path from dirs where dirid = ?;', str(dir_id)).fetchone()
        cur_path = Path(cur_path[0])
        assert cur_path == dir_


def construct_dir(root_: Path, file_parts: tuple) -> Path:
    rr = root_
    for fp in file_parts:
        rr = rr / fp
    return rr.parent    # remove file name, left only path


root_paths = [ # 'insert_to_db, search_for_parent, expected'
    (('.dir3/dir.1.1/',), 'dir1', None),
    (('.dir3/dir.1.1',), '.dir3/.dir.1.2/dir.1.2.3', None),
    (('.dir3',), '.dir3/.dir.1.2/dir.1.2.3', '.dir3'),
    (('dir1',), 'dir1', 'dir1'),
    (('',), '', ''),
]


@pytest.fixture(params=root_paths)
def db_with_loaded_data(request):
    conn = sqlite3.connect(":memory:", check_same_thread=False,
                           detect_types=DETECT_TYPES)
    loads = load_dirs(conn, request)

    return loads, request.param[1:]


def load_dirs(conn, request):
    conn.cursor().execute('PRAGMA foreign_keys = ON;')
    db.create_all_objects(conn)
    loads = ld.LoadDBData(conn)
    to_insert = [(str(TEST_ROOT_DIR / x), '0', '0') for x in request.param[0]]
    conn.executemany('insert into Dirs (Path, ParentID, FolderType) values (?, ?, ?);',
                     to_insert)
    conn.commit()
    return loads


def test_search_closest_parent(db_with_loaded_data):
    load_d, dirs = db_with_loaded_data  # LoadDBData object, sqlite Connection
    i, parent = load_d.search_closest_parent(TEST_ROOT_DIR / dirs[0])
    if i > 0:
        assert TEST_ROOT_DIR / parent == TEST_ROOT_DIR / dirs[1]
    else:
        assert parent is dirs[1]


insert_file_data = [(
    (       # dirs
        ('dir1', ''),         # dir_name, '' - parent is root
        ('dir2', 'dir1'),     # parent is dir1
    ),  (   # files
        ('file1.ext1', 'dir1'),   # file name, dir - where file located
        ('file2.ext2', 'dir2'),
        ('file2.ext2', 'dir2'),   # the same file_name and dir
        ('file1.ext1', 'dir2'),   # the same file_name but another dir
    )
),
]


@pytest.mark.parametrize('dirs, files', insert_file_data)
def test_insert_file(init_load_obj, dirs, files):
    load_d, conn_d = init_load_obj
    curs = conn_d.cursor()
    dir_ids = insert_dirs(curs, dirs)

    for file in files:
        load_d.insert_file(dir_ids[file[1]][0], Path(file[0]))
        cnt = curs.execute('select count(*) from files where DirID = ? and filename = ?;',
                           (str(dir_ids[file[1]][0]), file[0])).fetchone()
        assert cnt[0] == 1
        res = curs.execute('select dirid from files where filename = ?;',
                           file[:1]).fetchall()
        assert (dir_ids[file[1]][0],) in res


def insert_dirs(curs, dirs):
    dir_ids = {'': (0, 0), None: (0, -1)}
    for dd in dirs:
        curs.execute('insert into dirs (Path, ParentID, FolderType) values (?, ?, 0);',
                     (dd[0], str(dir_ids[dd[1]][0])))
        dir_ids[dd[0]] = (curs.lastrowid, dir_ids[dd[1]][0])
    return dir_ids


@pytest.mark.parametrize('files', [('x.a', 'x.b', 'y.a', 'z')])
def test_insert_extension(init_load_obj, files):
    load_d, conn_d = init_load_obj
    for file in files:
        p_file = Path(file)
        id = load_d.insert_extension(p_file)
        assert id > 0
        ext = conn_d.execute('select Extension from Extensions where ExtID = ?;',
                             (str(id),)).fetchall()
        assert len(ext) == 1
        assert ext[0][0] == p_file.suffix.strip('.')


child_parent = [ # 'insert_to_db, search_for_parent'
    (
        (   # 'insert_to_db
            ('.dir3/dir.1.1/', ''),         # dir, parent; '' - root
            # ('dir2', ''),
            ('dir2/dir21', '')
        ),
        (   # search_for_parent
            ('dir1', None),             # search for 'dir1', expected parent '' - root
            ('dir2/dir21/dir211', 'dir2/dir21'),
            ('dir2', 'dir2/dir21'),
        ),
    ),
    # (('.dir3/dir.1.1',), ('.dir3',)),
    # (('.dir3',), ('.dir3/.dir.1.2/dir.1.2.3',), -1),
    # (('dir1',), ('dir1',), -1),
    # (('',), ('',), -1),
]


@pytest.fixture(params=child_parent)
def child_parent_fixture(request):
    conn = sqlite3.connect(":memory:", check_same_thread=False,
                           detect_types=DETECT_TYPES)
    conn.cursor().execute('PRAGMA foreign_keys = ON;')
    db.create_all_objects(conn)
    loads = ld.LoadDBData(conn)
    curs = conn.cursor()
    dir_ids = insert_dirs(curs, request.param[0])

    return loads, conn, dir_ids, request.param[1]


def test_parent_id_for_child(child_parent_fixture):
    o_load, conn, dir_ids, dir_parent = child_parent_fixture
    for dir in dir_parent:
        res = o_load.parent_id_for_child(Path(dir[0]))
        assert res == dir_ids[dir[1]][1]


def test_change_parent(child_parent_fixture):
    o_load, conn, dir_ids, dir_parent = child_parent_fixture
    crr = conn.execute('select * from dirs')
    for cc in crr:
        print('|A===>', cc)
    for dir_ in dir_parent:
        print('|0===>', dir_)
        par_id, par_name = o_load.search_closest_parent(Path(dir_[0]))
        print('|1===>', par_id, par_name)
        o_load.change_parent(par_id, Path(dir_[0]))
        curs = conn.execute('select path from dirs where parentId = ?', str(par_id))
        for cc in curs:
            print('|2===>', cc, dir_)
            assert str(cc[0]).startswith(dir_[0]) or par_name is None

