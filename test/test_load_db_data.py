import pytest
from pathlib import Path
import sqlite3

import core
from core import create_db as db
import core.load_db_data as ld


FILE_LIST = [
    ".gitignore",
    ".dir3/.dir.1.2/dir.1.2.3/file2.py",
    ".dir3/dir.1.1/.file2.pd",
    ".dir3/dir.1.1/file1.sql",
    ".dir3/dir.1.1/PyCharm_ReferenceCard.pdf",
    ".dir3/.file1",
    ".dir3/.file2.txt",
    ".dir3/file2",
    "dir1/file1.py",
    "dir1/Structuring_and_automating_a_Python_project.pdf",
    "dir2/fixtures2.txt",
    "dir2/sel_opt.png",
    "dir2/sel_opt.ui",
    "file1.py",
]

@pytest.fixture(scope='module')
def root_data_path(tmp_path_factory):
    root_path = tmp_path_factory.getbasetemp() / "tst_data"
    root_path.mkdir()
    for line in FILE_LIST:
        row = Path(line).parts
        if row[:-1]:
            cur_dir: Path = root_path / '/'.join(row[:-1])
            cur_dir.mkdir(parents=True, exist_ok=True)
        else:
            cur_dir: Path = root_path
        file: Path = cur_dir / row[-1]
        file.touch(exist_ok=True)
    return root_path


@pytest.fixture(params=[("",), ("pdf", "ui"), "*"])
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
            files.append(row.parts[-1])
    return files, ext


def check_ext(ext_, file_: Path) -> bool:
    """
    @param ext_: list of extensions
    @param file_: as return with Path.parts, to be used both in Windows & Linux
    return True if file extension is in the list
                   or the list contains symbol '*' - any extension
    """
    if "*" in ext_:
        return True
    file_ext = file_.suffix.strip(".")
    return file_ext in ext_


def test_yield_files(expected_files, root_data_path):
    ext = expected_files[1]  # list of extensions
    files = ld.yield_files(root_data_path, ext)
    exp = expected_files[0]  # list of expected files (file parts)
    count = 0
    for file in files:
        ff = Path(file).parts[-1]
        count =+ 1
        assert ff in exp
    assert count > 0


# @pytest.mark.skip(reason="the test directory doesn't exist")
@pytest.mark.parametrize("child, ext, expect",
    [
        (".dir3", ("txt", "py"), 2),
        ('', "*", 14),
        ('', "", 3),
    ],
)
def test_load_data_file_count(init_load_obj, root_data_path, child, ext, expect):
    """
    test count of loaded files
    """
    load_d, conn_d = init_load_obj
    load_d.load_data(root_data_path / child, ext)
    file_count = conn_d.execute("select count(*) from files;").fetchone()
    assert file_count[0] == expect


dir_list = [  # (dir_to_be_inserted, to_be_inserted, parent)
    (
        ("dir1", True, ""), 
        ("dir1", False, ""), 
        ("dir1/dir2", True, "dir1")
    ),
    (
        ("dir1", True, ""),
        ("dir1/dir2", True, "dir1"),
        ("dir1/dir3", True, "dir1"),
        ("dir1/dir2/dir3", True, "dir1/dir2"),
    ),
]


@pytest.mark.parametrize("dirs", dir_list)
def test_insert_dir_is_inserted(init_load_obj, dirs):
    """
    test that "insert_dir" method always return correct dir_id
    """
    parent_dir = {"": 0}
    load_d, conn_d = init_load_obj  # LoadDBData object, sqlite Connection
    for dir_ in dirs:
        dd = dir_[0]
        dir_id, inserted = load_d.insert_dir(Path(dd))
        assert inserted is dir_[1]


@pytest.mark.parametrize("dirs", dir_list)
def test_insert_dir_check_dir(init_load_obj, dirs):
    """
    test that "insert_dir" method always return correct dir_id
    """
    parent_dir = {"": 0}
    load_d, conn_d = init_load_obj  # LoadDBData object, sqlite Connection
    for dir_ in dirs:
        dd = dir_[0]
        dir_id, inserted = load_d.insert_dir(Path(dd))
        parent_dir[dd] = dir_id
        cur_path = conn_d.execute(
            "select path, parentid from dirs where dirid = ?;", str(dir_id)
        ).fetchone()
        assert Path(cur_path[0]) == Path(dd)


@pytest.mark.parametrize("dirs", dir_list)
def test_insert_dir_check_parent(init_load_obj, dirs):
    """
    test that "insert_dir" method always return correct dir_id
    """
    parent_dir = {"": 0}
    load_d, conn_d = init_load_obj  # LoadDBData object, sqlite Connection
    for dir_ in dirs:
        dd = dir_[0]
        dir_id, inserted = load_d.insert_dir(Path(dd))
        parent_dir[dd] = dir_id
        cur_path = conn_d.execute(
            "select path, parentid from dirs where dirid = ?;", str(dir_id)
        ).fetchone()
        assert cur_path[1] == parent_dir[dir_[2]]


root_paths = [  # 'insert_to_db, search_for_parent, expected'
    ( #0
        (".dir3/dir.1.1/", "dir1"), "dir1", "dir1"
    ),
    ( #1
        (".dir3/dir.1.1",), ".dir3/.dir.1.2/dir.1.2.3", None
    ),
    ( #2
        (".dir3",), ".dir3/.dir.1.2/dir.1.2.3", ".dir3"
    ),
    ( #3
        (".dir3/.dir.1.2/dir1",), ".dir3/.dir.1.2/dir2", None
    ),
    ( #4
        ("dir1",), "dir1", "dir1",
    ),  # search_closest_parent returns the dir itself if already in DB
    ( #5
        ("",), "", None
    ),  # but '' - is a root, but its name in DB is None
]


@pytest.fixture(params=root_paths)
def db_with_loaded_data(init_load_obj, request):
    loads, conn = init_load_obj
    load_dirs(loads, conn, request)

    return loads, request.param[1:]


def load_dirs(loads, conn, request):
    to_insert = [(x,) for x in request.param[0]]
    conn.executemany(
        "insert into Dirs (Path, ParentID, FolderType) values (?, 0, 0);", to_insert
    )
    conn.commit()


def insert_dirs(curs, dirs):
    dir_ids = {
        "": (0, 0),     # root
        None: (0, -1),  # not found
    }                   # others will construct from data
    for dd in dirs:
        curs.execute(
            "insert into dirs (Path, ParentID, FolderType) values (?, ?, 0);",
            (dd[0], str(dir_ids[dd[1]][0])),
        )
        dir_ids[dd[0]] = (curs.lastrowid, dir_ids[dd[1]][0])
    return dir_ids


def test_search_closest_parent(db_with_loaded_data):
    load_d, dirs = db_with_loaded_data  # LoadDBData object, sqlite Connection
    i, parent = load_d.search_closest_parent(Path(dirs[0]))

    if dirs[1] is None:
        assert parent is None, f"parent {parent} with ID={i} is found; expected None"
    else:
        assert parent == Path(dirs[1]), f"parent {parent} is found; expected {dirs[1]}"


insert_file_data = [
    (
        (  # dirs
            ("dir1", ""),  # dir_name, '' - parent is root
            ("dir2", "dir1"),  # parent is dir1
        ),
        (  # files
            ("file1.ext1", "dir1"),  # file name, dir - where file located
            ("file2.ext2", "dir2"),
            ("file2.ext2", "dir2"),  # the same file_name and dir
            ("file1.ext1", "dir2"),  # the same file_name but another dir
        ),
    )
]


@pytest.mark.parametrize("dirs, files", insert_file_data)
def test_insert_file_only_once(init_load_obj, dirs, files):
    load_d, conn_d = init_load_obj
    curs = conn_d.cursor()
    dir_ids = insert_dirs(curs, dirs)

    for file in files:
        load_d.insert_file(dir_ids[file[1]][0], Path(file[0]))
        cnt = curs.execute(
            "select count(*) from files where DirID = ? and filename = ?;",
            (str(dir_ids[file[1]][0]), file[0]),
        ).fetchone()
        assert cnt[0] == 1, f"file {file[0]} must be inserted only once in one directory"


@pytest.mark.parametrize("dirs, files", insert_file_data)
def test_insert_file_is_inserted(init_load_obj, dirs, files):
    load_d, conn_d = init_load_obj
    curs = conn_d.cursor()
    dir_ids = insert_dirs(curs, dirs)

    for file in files:
        load_d.insert_file(dir_ids[file[1]][0], Path(file[0]))
        res = curs.execute(
            "select dirid from files where filename = ?;", file[:1]
        ).fetchall()
        assert (dir_ids[file[1]][0],) in res, f"file {file[0]} must be inserted, but not"


@pytest.mark.parametrize("files", [("x.a", "x.b", "y.a", "z")])
def test_insert_extension_0_id(init_load_obj, files):
    print()
    load_d, conn_d = init_load_obj
    for file in files:
        print(file)
        p_file = Path(file)
        id = load_d.insert_extension(p_file)
        print(id)
        assert id > 0, f"method must return extension ID > 0; {id} is returned"


@pytest.mark.parametrize("files", [("x.a", "x.b", "y.a", "z")])
def test_insert_extension_count(init_load_obj, files):
    print()
    load_d, conn_d = init_load_obj
    for file in files:
        print(file)
        p_file = Path(file)
        id = load_d.insert_extension(p_file)
        cnt = conn_d.execute(
            "select count(*) from Extensions where ExtID = ?;", (str(id),)
        ).fetchone()
        assert cnt[0] == 1, "extension must be saved only once"


@pytest.mark.parametrize("files", [("x.a", "x.b", "y.a", "z")])
def test_insert_extension_check(init_load_obj, files):
    print()
    load_d, conn_d = init_load_obj
    for file in files:
        print(file)
        p_file = Path(file)
        id = load_d.insert_extension(p_file)
        ext = conn_d.execute(
            "select Extension from Extensions where ExtID = ?;", (str(id),)
        ).fetchone()
        print(ext)
        assert ext[0] == p_file.suffix.strip("."), f"extension of file {p_file} is not {ext[0][0]}"


child_parent = [  # 'insert_to_db, search_for_parent'
    (
        (  # 1) dirs to be inserted to db: dir, parent
            (".dir3/dir.1.1/", ""),  # dir, parent; '' - root
            ("dir2/dir21", ""),
            ("dir2/dir22", ""),
            ("dir2/dir21/dir212", "dir2/dir21"),
        ),
        (  # 2) (parameter of find_old_parent_id method, expected found child, if assertion should fail)
            ("dir1", None, False),  # search for 'dir1', expected parent '' - root
            ("dir2/dir21/dir211", None, False),
            ("dir2", "dir2/dir21", False),
            ("dir2", "dir2/dir21/dir212", True),
        ),
    )
]


@pytest.fixture(params=child_parent)
def child_parent_fixture(init_load_obj, request):
    loads, conn = init_load_obj
    dir_ids = insert_dirs(conn.cursor(), request.param[0])

    return loads, conn, dir_ids, request.param[1]


def test_find_old_parent_id(child_parent_fixture):
    o_load, conn, dir_ids, dir_parent = child_parent_fixture
    for dir_ in dir_parent:
        res = o_load.find_old_parent_id(Path(dir_[0]))
        if dir_[2]:
            assert not res == dir_ids[dir_[1]][1], f"{dir_[0]} must not be parent for {res}"
        else:
            assert res == dir_ids[dir_[1]][1], f"{dir_[0]} must be parent for {res}"


def insert_dir_in_test(o_load: ld.LoadDBData, conn: sqlite3.Connection, path: Path):
    idx, parent_path = o_load.search_closest_parent(path)
    if parent_path == path:
        return idx, False

    curs = conn.cursor()
    curs.execute(ld.INSERT_DIR, {"path": str(path), "id": idx})
    idx = curs.lastrowid
    return idx, True


def test_change_parent(child_parent_fixture):
    """
    Test that parent of children changed if new dir inserted according the pattern:
    paretn -> [new_dir] -> child/children
    """
    o_load, conn, dir_ids, dir_parent = child_parent_fixture
    for dir_ in dir_parent:
        new_id, inserted = insert_dir_in_test(o_load, conn, Path(dir_[0]))
        if inserted:
            o_load.change_parent(new_id, Path(dir_[0]))
            curs = conn.execute("select * from dirs where parentId = ?", str(new_id))
            for cc in curs:
                assert str(cc[1]).startswith(dir_[0]), f"child path must start with {dir_[0]}"
                assert cc[0] != cc[3], "child can't be parent to itself"
