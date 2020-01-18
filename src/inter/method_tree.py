# src/method_tree.py

import sqlite3
from pathlib import Path

in_file = Path.cwd() / 'tmp/xls/prj.txt'
DB = Path.cwd() / "prj.db"


methods = ('create table IF NOT EXISTS methods ('
           'ID INTEGER NOT NULL PRIMARY KEY, '
           'type text, '      # type - {m – method/function; sql; c – const; f – field; …}
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
            'type text, '      # type - {m – method/function; sql; c – const; f – field; …}
            'module text, '
            'class text, '
            'method text, '
            'start text);'
            )

ins1 = ('insert into methods ('
        "'type', 'module', 'class', 'method', "
        "'c_method', 'c_module', 'c_class', 'Start') "
        'values (?, ?, ?, ?, ?, ?, ?, ?);'
        )

others = (
    (
        'insert into methods2 (type, module, class, method) '
        'select distinct type, module, class, method '
        'from methods;'
     ),
    (
        'with c_meth (type, module, class, method) as ('
        "select distinct 'm', c_module, c_class, c_method "
        'from methods a where not exists (select * from methods2 b '
        'where a.c_module = b.module  and a.c_class = b.class '
        'and a.c_method = b.method)) '
        'insert into methods2 (type, module, class, method) '
        'select * from c_meth;'
     ),
    (
        'update methods2 set start = ('
        "select start from methods where methods.start != '' "
        'and methods.module = methods2.module '
        'and methods.class = methods2.class '
        'and methods.method = methods2.method);'
     ),
    (
        'insert into link_path (ID, call_ID, level, path) '
        "select a.ID, b.ID, 1, b.id || '/' from methods c "
        'left join methods2 a on a.module = c.module '
        'and a.class = c.class and a.method = c.method '
        'left join methods2 b on b.module = c.c_module '
        'and b.class = c.c_class and b.method = c.c_method;'
     ),
    (
        'with recc (ID, call_ID, level, path) as ('
        "select ID, call_ID, level, path || ID || '/' from link_path "
        # 'where call_ID is not null '
        'union all select b.ID, a.call_ID, a.level+1, a.path || b.id || '
        "'/' from recc a join link_path b on b.call_ID = a.ID) "
        'insert into link_path (ID, call_ID, level, path) '
        'select * from recc where level > 1;'
     ),
    "update link_path set path = path || id || '/' where level = 1;",
    (
        'insert into simple_link (id, call_ID, level) '
        'select id, call_ID, min(level) from link_path '
        'group by id, call_ID;'
     ),
)


def drop_tables(con_):
    con_.execute('drop table simple_link;')
    con_.execute('drop table link_path;')
    con_.execute('drop table methods2;')
    con_.execute('drop table methods;')


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
                curs.execute(ins1, ll[:8])                   # into methods

        con_.commit()


if __name__ == "__main__":
    print('|--> input:', in_file)
    print('|-->    db:', DB)

    conn = sqlite3.connect(DB)
    # either
    conn.execute('delete from methods2;')
    conn.execute('delete from link_path;')
    conn.execute('delete from simple_link;')
    # or
    # drop_tables(conn)
    # create_tables(conn)

    fill_methods(conn, in_file)

    for sql in others:
        conn.execute(sql)
        conn.commit()
