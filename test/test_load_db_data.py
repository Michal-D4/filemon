import pytest
from pathlib import Path
import sqlite3
from loguru import logger

from conftest import DETECT_TYPES

import sys
from os import path
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from src.core import create_db as db
import src.core.load_db_data as ld

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

    ext = request.param
    files = []
    for line in FILE_LIST:
        row = Path(line)
        if check_ext(ext, row):
            files.append(row.parts)
    return files, ext


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


def test_yield_files(expected_files):
    ll = len(TEST_ROOT_DIR.parts) - 1
    ext = expected_files[1]     # list of extensions
    files = ld.yield_files(TEST_ROOT_DIR, ext)
    exp = expected_files[0]     # list of expected files (file parts)
    for file in files:
        ff = Path(file).parts[ll:]
        assert ff in exp


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


dir_list = [ # (dir_to_be_inserted, to_be_inserted, parent)
    (('dir1', True, ''), ('dir1', False, ''), ('dir1/dir2', True, 'dir1'),),
    (('dir1', True, ''), ('dir1/dir2', True, 'dir1'), ('dir1/dir3', True, 'dir1'), ('dir1/dir2/dir3', True, 'dir1/dir2'),),
]


@pytest.mark.parametrize('dirs', dir_list)
def test_insert_dir(init_load_obj, dirs):
    """
    test that "insert_dir" method always return correct dir_id
    """
    parent_dir = {'': 0}
    load_d, conn_d = init_load_obj  # LoadDBData object, sqlite Connection
    for dir_ in dirs:
        dd = dir_[0]
        dir_id, inserted = load_d.insert_dir(Path(dd))
        assert inserted is dir_[1]
        parent_dir[dd] = dir_id
        cur_path = conn_d.execute('select path, parentid from dirs where dirid = ?;', str(dir_id)).fetchone()
        assert Path(cur_path[0]) == Path(dd)
        assert cur_path[1] == parent_dir[dir_[2]]


root_paths = [ # 'insert_to_db, search_for_parent, expected'
    (('.dir3/dir.1.1/',), 'dir1', None),
    (('.dir3/dir.1.1',), '.dir3/.dir.1.2/dir.1.2.3', None),
    (('.dir3',), '.dir3/.dir.1.2/dir.1.2.3', '.dir3'),
    (('dir1',), 'dir1', 'dir1'),   # search_closest_parent returns the dir itself if already in DB
    (('',), '', None),   # but '' - is a root, but its name in DB is None
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
    to_insert = [(x, ) for x in request.param[0]]
    conn.executemany('insert into Dirs (Path, ParentID, FolderType) values (?, 0, 0);',
                     to_insert)
    conn.commit()
    return loads


def test_search_closest_parent(db_with_loaded_data):
    load_d, dirs = db_with_loaded_data  # LoadDBData object, sqlite Connection
    i, parent = load_d.search_closest_parent(Path(dirs[0]))
    print('|---> 1', i, parent, dirs)
    if i > 0:
        assert parent == Path(dirs[1]), f"parent is {parent}, expected {dirs[1]}"
    else:
        assert parent is None, f"parent {parent} with ID=0 is found for {dirs[0]}"


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
        assert cnt[0] == 1, f"file {file[0]} must be inserted only once in one directory"
        res = curs.execute('select dirid from files where filename = ?;',
                           file[:1]).fetchall()
        assert (dir_ids[file[1]][0],) in res, f"file {file[0]} must be inserted, but not"


def insert_dirs(curs, dirs):
    dir_ids = {'': (0, 0),     # root
               None: (0, -1),  # not found
               }               # others will construct from data
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
        assert id > 0, "method must return extension ID > 0  either inserted now or before now"
        ext = conn_d.execute('select Extension from Extensions where ExtID = ?;',
                             (str(id),)).fetchall()
        assert len(ext) == 1, 'extension must be saved only once'
        assert ext[0][0] == p_file.suffix.strip('.'), f"extension of file {p_file} is not {ext[0][0]}"


child_parent = [ # 'insert_to_db, search_for_parent'
    (
        (   # 1) dirs to be inserted to db: dir, parent
            ('.dir3/dir.1.1/', ''),               # dir, parent; '' - root
            ('dir2/dir21', ''),
            ('dir2/dir22', ''),
            ('dir2/dir21/dir212', 'dir2/dir21'),
        ),
        (   # 2) (parameter of find_old_parent_id method, expected found child, if assertion should fail)
            ('dir1', None, False),             # search for 'dir1', expected parent '' - root
            ('dir2/dir21/dir211', None, False),
            ('dir2', 'dir2/dir21', False),
            ('dir2', 'dir2/dir21/dir212', True)
        ),
    ),
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


def test_find_old_parent_id(child_parent_fixture):
    o_load, conn, dir_ids, dir_parent = child_parent_fixture
    for dir_ in dir_parent:
        res = o_load.find_old_parent_id(Path(dir_[0]))
        if dir_[2]:
            assert not res == dir_ids[dir_[1]][1], f"{dir_[0]} must not be parent for {res}"
        else:
            assert res == dir_ids[dir_[1]][1],  f"{dir_[0]} must be parent for {res}"


def insert_dir_in_test(o_load: ld.LoadDBData, conn: sqlite3.Connection, path: Path):
    idx, parent_path = o_load.search_closest_parent(path)
    if parent_path == path:
        return idx, False

    curs = conn.cursor()
    curs.execute(ld.INSERT_DIR, {'path': str(path), 'id': idx})
    idx = curs.lastrowid
    return idx, True


def test_change_parent(child_parent_fixture):
    """
    Test that parent of children changed if new dir inserted according the pattern:
    paretn -> [new_dir] -> child/children
    @param child_parent_fixture:
    @return:
    """
    o_load, conn, dir_ids, dir_parent = child_parent_fixture
    for dir_ in dir_parent:
        new_id, inserted = insert_dir_in_test(o_load, conn, Path(dir_[0]))
        if inserted:
            o_load.change_parent(new_id, Path(dir_[0]))
            curs = conn.execute('select * from dirs where parentId = ?', str(new_id))
            for cc in curs:
                assert str(cc[1]).startswith(dir_[0]), f'child path must start with {dir_[0]}'
                assert cc[0] != cc[3], "child can't be parent to itself"
