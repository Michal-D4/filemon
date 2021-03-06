# src/inter/method_tree.py

import sqlite3
from pathlib import Path

in_file = Path.cwd() / "tmp/xls/prj.txt"
DB = Path.cwd() / "prj.db"


methods = (
    "create table IF NOT EXISTS methods ("
    "ID INTEGER NOT NULL PRIMARY KEY, "
    "type text, "
    "module text, "
    "class text, "
    "method text, "
    "c_module text, "
    "c_class text, "
    "c_method text, "
    "remark text);"
)
links = (
    "create table IF NOT EXISTS links ("
    "ID integer references methods2(ID) ON DELETE CASCADE, "
    "call_ID integer references methods2(ID) ON DELETE CASCADE, "
    "level integer, "
    "primary key(ID, call_ID));"
)
one_link = (
    "create table IF NOT EXISTS one_link ("
    "ID integer references methods2(ID) ON DELETE CASCADE, "
    "call_ID integer references methods2(ID) ON DELETE CASCADE, "
    "primary key(ID, call_ID));"
)

methods2 = (
    "create table IF NOT EXISTS methods2 ("
    "ID INTEGER NOT NULL PRIMARY KEY, "
    "type text, "
    "module text, "
    "class text, "
    "method text, "
    "CC text, "
    "length text, "
    "remark text);"
)

ins1 = (
    "insert into methods ("
    "'type', 'module', 'class', 'method', "
    "'c_method', 'c_module', 'c_class', 'remark') "
    "values (?, ?, ?, ?, ?, ?, ?, ?);"
)

others = (
    (  # insert type, module, class, method from methods to methods2
        "insert into methods2 (type, module, class, method) "
        "select distinct type, module, class, method "
        "from methods;"
    ),
    (  # append methods, that is in calling but not in called, into methods2
        "with c_meth (module, class, method) as ("
        "select c_module, c_class, c_method from methods "
        "where c_method != '' except "
        "select module, class, method from methods) "
        "insert into methods2 (type, module, class, method) "
        "select 'm', module, class, method from c_meth;"
    ),
    (  # simple insert into field "remark" data from methods.remark
        "update methods2 set remark = ("
        "select remark from methods where methods.remark != '' "
        "and methods.module = methods2.module "
        "and methods.class = methods2.class "
        "and methods.method = methods2.method);"
    ),
    (  # only first level links
        "insert into one_link (ID, call_ID) "
        "select a.ID, b.ID from methods c "
        "left join methods2 a on a.module = c.module "
        "and a.class = c.class and a.method = c.method "
        "left join methods2 b on b.module = c.c_module "
        "and b.class = c.c_class and b.method = c.c_method "
        "where b.ID is not null;"
    ),
)

all_levels_link =(  
    "with recc (ID, call_ID, level) as ("
    "select ID, call_ID, 1 from one_link "
    "union select b.ID, a.call_ID, a.level+1 "
    "from recc a join one_link b on b.call_ID = a.ID) "
    "insert into links (ID, call_ID, level) "
    "select ID, call_ID, min(level) from recc group by ID, call_ID;"
)


def drop_tables(con_):
    con_.execute("drop table IF EXISTS links;")
    con_.execute("drop table IF EXISTS one_link;")
    con_.execute("drop table IF EXISTS methods2;")
    con_.execute("drop table IF EXISTS methods;")


def create_tables(con_):
    con_.execute(methods)
    con_.execute(methods2)
    con_.execute(one_link)
    con_.execute(links)


def recreate_tables(con_):
    drop_tables(con_)
    create_tables(con_)


def clear_tables(con_):
    con_.execute("delete from methods2;")
    con_.execute("delete from one_link;")
    con_.execute("delete from links;")


def fill_methods(con_, file_):
    curs = con_.cursor()
    curs2 = con_.cursor()
    curs2.execute("delete from methods;")
    with open(file_) as fl:
        fl.__next__()
        for line in fl:
            if line.strip():
                ll = line.strip().split(",")
                curs.execute(ins1, ll[:8])  # into methods

        con_.commit()


if __name__ == "__main__":
    print("|--> input:", in_file)
    print("|-->    db:", DB)

    con_ = sqlite3.connect(DB)

    # either
    clear_tables(con_)
    # or; use only when change schema
    # recreate_tables(con_)

    fill_methods(con_, in_file)

    for sql in others:
        con_.execute(sql)
        con_.commit()

    con_.execute(all_levels_link)
    con_.commit()
