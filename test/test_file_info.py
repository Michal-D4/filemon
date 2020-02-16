import pytest
from pathlib import Path
import sqlite3

import sys
from os import path
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

import src.core.file_info as lf   # lf ~ fiLe_inFo


def test_ext_translate():
    """
    test whether extensions list in string format
    correctly converted into tuple / string '*'
    @return: None
    """
    ex1 = ', b'
    tx1 = lf.ext_translate(ex1)
    assert tx1 == ('', 'b')
    ex2 = 'a, .b,c,.d'
    tx2 = lf.ext_translate(ex2)
    assert tx2 == ('a', 'b', 'c', 'd')
    ex3 = 'a, .b,*,.d'
    tx3 = lf.ext_translate(ex3)
    assert tx3 == '*'
    ex4 = '., a'
    tx4 = lf.ext_translate(ex4)
    assert tx4 == ('', 'a')


files_authors = [
    (
     ('dir1/file1.txt', 'dir1/file2.pdf',
      'dir2/file3.py', 'dir1/dir12/file4.doc',
      ),
     {'file1': ('author1', 'author2'),
      'file2': ('author1', 'author 2'),
      'file3': ('author3',),
      'file4': ('author4', 'author 2'),
      },
    )
]


def insert_dir(curs, dir_, dir_id: dict):
    if dir_ in dir_id.keys():
        return dir_id[dir_]

    for ss in dir_id.keys():
        if ss.startswith(dir_):
            parent_id = dir_id[ss]
            break
    else:
        parent_id = 0

    curs.execute('insert into Dirs (Path, ParentID, FolderType) values (?, ?, 0);',
                 (dir_, str(parent_id)))
    id = curs.lastrowid
    dir_id[dir_] = id
    return id


def load_files(conn: sqlite3.Connection, files):
    file_id = {}
    dir_id = {}
    curs = conn.cursor()
    for file in files:
        ff = Path(file)
        f_name = ff.name
        f_dir = ff.parent
        d_id = insert_dir(curs, str(f_dir), dir_id)
        curs.execute("insert into Files (DirID, FileName) values (?, ?);",
                     (str(d_id), f_name))
        file_id[ff.stem] = curs.lastrowid

    return file_id


@pytest.mark.parametrize('files, authors_dict', files_authors)
def test_insert_author(init_load_obj, files, authors_dict):
    ld, conn = init_load_obj
    fi = lf.FileInfo(set(), conn)
    curs = conn.cursor()
    curs.execute("insert into Extensions (Extension, GroupID) values ('a', '0')")
    f_ids = load_files(conn, files)
    for key, authors in authors_dict.items():
        f_id = f_ids[key]
        for author in authors:
            a_id = fi.insert_author(f_id, author)
            aa = curs.execute('select Author from Authors where AuthorID = ?',
                              (str(a_id),)).fetchone()
            assert aa[0] == author
            fi.link_file_author(f_id, a_id)
            fa = curs.execute(lf.FILE_AUTHOR_LINKED, (str(f_id), str(a_id))).fetchone()
            assert fa == (f_id, a_id)


def test_get_file_info():
    pass
