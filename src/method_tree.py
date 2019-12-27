# src/method_tree.py

import sqlite3
from pathlib import Path

in_file = Path.cwd().parent / 'tmp/xls/prj.txt'
DB = Path.cwd() / "prj.db"


methods = ('create table IF NOT EXISTS methods ('
           'ID INTEGER NOT NULL PRIMARY KEY, '
           'module text, '
           'class text, '
           'method text, '
           'c_module text, '
           'c_class text, '
           'c_method text, '
           'start text);'
           )
call_link = ('create table IF NOT EXISTS call_link ('
             'ID integer, '
             'call_ID integer, '
             'level integer, '
             'primary key(ID, call_ID), '
             'foreign key (ID) references methods2(ID), '
             'foreign key (call_ID) references methods2(ID));'
             )
methods2 = ('create table IF NOT EXISTS methods2 ('
            'ID INTEGER NOT NULL PRIMARY KEY, '
            'module text, '
            'class text, '
            'method text, '
            'start text);'
            )
sel2 = 'select * from call_link where call_id = ?;'


def drop_tables(con_):
    con_.execute('drop table methods;')
    con_.execute('drop table call_link;')
    con_.execute('drop table methods2;')


def create_tables(con_):
    con_.execute(methods)
    con_.execute(methods2)
    con_.execute(call_link)


ins1 = ('insert into methods ('
        "'module', 'class', 'method', 'c_method', 'c_module', 'c_class', 'Start') "
        'values (?, ?, ?, ?, ?, ?, ?);'
        )
ins2 = ('insert into call_link ('
        "'ID', 'call_ID', 'level') values(?, ?, ?);"
        )
ins3 = ('insert into methods2 ('
        "'module', 'class', 'method', 'Start') "
        'values (?, ?, ?, ?);'
        )
sel1 = ('select id from methods2 '
        'where module = ? '
        'and class = ? '
        'and method = ?;'
        )


def fill_methods(con_, file_):
    curs = con_.cursor()
    curs2 = con_.cursor()
    curs2.execute('delete from methods;')
    with open(file_) as fl:
        heads = fl.__next__()
        i = 0
        for line in fl:
            ll = line.strip().split(',')
            curs.execute(ins1, ll[1:])                             # into methods

        con_.commit()


def init_methods2(con_):
    """
    Unique ID for 'module', 'class', 'method'
    """
    curs = con_.cursor()
    curs2 = con_.cursor()
    c_meth = curs.execute('select * from methods;')
    curs2.execute('delete from methods2;')

    rr = []
    meth = {}
    for row in c_meth:
        if row[1:4] == rr:
            continue
        rr = row[1:4]
        cc = curs2.execute(ins3, (*rr, row[7]))                    # into methods2
        meth[(*rr,)] = cc.lastrowid

    con_.commit()
    return meth


def set_calling_id(row: list, meth: dict, curs2: sqlite3.Connection.cursor):
    cing = (*row[4:7],)  # calling
    cal_id = 0
    try:
        cal_id = meth[cing]
    except KeyError:
        if row[5]:
            id = curs2.execute(sel1, (*row[4:7],)).fetchone()  # from methods2
            if id:
                cal_id = id[0]
            else:
                ci = curs2.execute(ins3, (*row[4:8],))         # into methods2
                cal_id = ci.lastrowid
    return cal_id


def init_link(con_, meth: dict):
    curs = con_.cursor()
    curs2 = con_.cursor()
    curs2.execute('delete from call_link;')
    _meth = curs.execute('select * from methods;')
    for row in _meth:
        call_id = set_calling_id(row, meth, con_.cursor())
        if call_id:
            ced = (*row[1:4],)    # called
            cc = curs2.execute(ins2, (meth[ced], call_id, 1))     # into call_link

    con_.commit()


def deep_link(con_, id: int, cal_id: int):
    cur = con_.cursor().execute(sel2, (id,))           # from call_link
    for cc in cur:
        id1 = cc[0]
        lvl = cc[2] + 1
        try:
            cur2 = con_.cursor().execute(ins2, (id1, cal_id, lvl))
        except sqlite3.IntegrityError:
            pass
        deep_link(con_, id1, cal_id)


if __name__ == "__main__":
    conn = sqlite3.connect(DB)

    drop_tables(conn)
    create_tables(conn)

    fill_methods(conn, in_file)
    meth = init_methods2(conn)

    init_link(conn, meth)

    curs = conn.cursor()
    c_meth = curs.execute('select * from call_link;')
    for cc in c_meth:
        deep_link(conn, cc[0], cc[1])

