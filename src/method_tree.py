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
link_path = ('create table IF NOT EXISTS link_path ('
             'ID integer, '
             'call_ID integer, '
             'level integer, '
             'path text, '
             'primary key(ID, call_ID, path), '
             'foreign key (ID) references methods2(ID), '
             'foreign key (call_ID) references methods2(ID));'
             )
simple_link = ('create table IF NOT EXISTS simple_link ('
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
sel2 = 'select * from link_path where call_id = ?;'


ins1 = ('insert into methods ('
        "'module', 'class', 'method', 'c_method', 'c_module', 'c_class', 'Start') "
        'values (?, ?, ?, ?, ?, ?, ?);'
        )
ins2 = ('insert into link_path ('
        "'ID', 'call_ID', 'level') values(?, ?, ?);"
        )
ins3 = ('insert into methods2 ('
        "'module', 'class', 'method', 'Start') "
        'values (?, ?, ?, ?);'
        )

others = (
    ('insert into methods2 (module, class, method) '
     'select distinct module, class, method '
     'from methods;'
     ),
    ('with c_meth (module, class, method) as ('
     'select distinct c_module, c_class, c_method '
     'from methods a where not exists (select * from methods2 b '
     'where a.c_module = b.module  and a.c_class = b.class '
     'and a.c_method = b.method)) '
     'insert into methods2 (module, class, method) '
     'select * from c_meth;'
     ),
    ('update methods2 set start = ('
     "select start from methods where methods.start != '' "
     'and methods.module = methods2.module '
     'and methods.class = methods2.class '
     'and methods.method = methods2.method);'
     ),
    ('insert into link_path (ID, call_ID, level, path) '
     "select a.ID, b.ID, 1, b.id || '/' from methods c "
     'left join methods2 a on a.module = c.module '
     'and a.class = c.class and a.method = c.method '
     'left join methods2 b on b.module = c.c_module '
     'and b.class = c.c_class and b.method = c.c_method;'
     ),
    ('with recc (ID, call_ID, level, path) as ('
     "select ID, call_ID, level, path || ID || '/' from link_path "
     # 'where call_ID is not null '
     'union all select b.ID, a.call_ID, a.level+1, a.path || b.id || '
     "'/' from recc a join link_path b on b.call_ID = a.ID) "
     'insert into link_path (ID, call_ID, level, path) '
     'select * from recc where level > 1;'
     ),
    "update link_path set path = path || id || '/' where level = 1;",
    ('insert into simple_link (id, call_ID, level) '
     'select id, call_ID, min(level) from link_path '
     'group by id, call_ID;'
     ),
)
sel1 = ('select id from methods2 '
        'where module = ? '
        'and class = ? '
        'and method = ?;'
        )


def drop_tables(con_):
    con_.execute('drop table call_link;')
    con_.execute('drop table methods;')
    con_.execute('drop table link_path;')
    con_.execute('drop table methods2;')


def create_tables(con_):
    con_.execute(methods)
    con_.execute(methods2)
    con_.execute(link_path)
    con_.execute(simple_link)


def fill_methods(con_, file_):
    curs = con_.cursor()
    curs2 = con_.cursor()
    curs2.execute('delete from methods;')
    with open(file_) as fl:
        heads = fl.__next__()
        i = 0
        for line in fl:
            if line.strip():
                ll = line.strip().split(',')
                curs.execute(ins1, ll[1:])                   # into methods

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
    curs2.execute('delete from link_path;')
    _meth = curs.execute('select * from methods;')
    for row in _meth:
        call_id = set_calling_id(row, meth, con_.cursor())
        if call_id:
            ced = (*row[1:4],)    # called
            cc = curs2.execute(ins2, (meth[ced], call_id, 1))     # into link_path

    con_.commit()


def deep_link(con_, id: int, cal_id: int, lvl: int):
    """
    Establish the called-caller links between methods
    @param con_:  DB connection
    @param id:  method id called by method with id = cal_id
    @param cal_id: method that call
    @param lvl:  1 if cal_id immediate call of id
    @return: None
    """
    lvl += 1
    id1 = con_.cursor().execute(sel2, (id,)).fetchone()           # from link_path
    if id1:
        id1 = id1[0]
        try:
            con_.cursor().execute(ins2, (id1, cal_id, lvl))
            con_.commit()
        except sqlite3.IntegrityError:
            pass
        else:
            deep_link(con_, id1, cal_id, lvl)


if __name__ == "__main__":
    conn = sqlite3.connect(DB)
    conn.execute('delete from methods2;')
    conn.execute('delete from link_path;')
    conn.execute('delete from simple_link;')

    # drop_tables(conn)
    # create_tables(conn)
    print('|--> input:', in_file)
    print('|-->    db:', DB)

    fill_methods(conn, in_file)

    for sql in others:
        conn.execute(sql)
        conn.commit()

    # meth = init_methods2(conn)

    # init_link(conn, meth)

    # curs = conn.cursor()
    # curs.execute('delete from link_path where level > 1;')
    # c_meth = curs.execute('select * from link_path;')
    # for cc in c_meth:
    #     deep_link(conn, cc[0], cc[1], 1)

