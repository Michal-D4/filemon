import src.method_tree as mt
import sqlite3
import pytest

lines = (
    ',m1,c1,me2,me1,m1,c1,start',
    ',m1,c1,me3,me1,m1,c1,',
    ',m1,c1,me3,me2,m1,c1,',
    ',m1,c1,me1,,m1,c1,',
)


@pytest.fixture(scope='module')
def db_init(tmpdir_factory):
    conn = sqlite3.connect(':memory:')
    mt.create_tables(conn)
    in_ = tmpdir_factory.mktemp("data").join('met.txt')
    in_.write('\n'.join(('heads', *lines)))
    return conn, in_


def test_fill_methods(db_init, tmp_path):
    conn, in_ = db_init
    mt.fill_methods(conn, in_)
    curs = conn.cursor()
    sel = curs.execute('select module, class, method, c_method, c_module, c_class, start '
                       'from methods;')

    i = 0
    for row in sel:
        assert row == (*lines[i].split(','),)[1:]
        i += 1


def test_init_methods2_1(db_init):
    conn, in_ = db_init
    mt.fill_methods(conn, in_)
    di_met = mt.init_methods2(conn)
    already_in = []
    curs = conn.cursor()
    cur = curs.execute('select module, class, method from methods;')
    for cc in cur:
        tt = (*cc,)
        if tt in already_in:
            id = di_met[tt]
        else:
            already_in.append(tt)
            id = len(already_in)
        assert id == di_met[tt]


def test_init_methods2_2(db_init):
    conn, in_ = db_init
    mt.fill_methods(conn, in_)
    di_met = mt.init_methods2(conn)
    curs = conn.cursor()
    cur = curs.execute('select * from methods2;')
    for cc in cur:
        tt = (*cc[1:4],)
        assert cc[0] == di_met[tt]


def test_set_calling_id():
    pass


call_link = [(
    (1, 3),
    (2, 3),
    (2, 1),
    (3, 4),
),
]


@pytest.mark.parametrize('ids', call_link)
def test_init_link(db_init, ids):
    conn, in_ = db_init
    mt.fill_methods(conn, in_)
    di_met = mt.init_methods2(conn)
    mt.init_link(conn, di_met)
    cur = conn.cursor()
    cu_ = cur.execute('select * from call_link;')
    for cc in cu_:
        assert cc[0:2] in ids


deep = [
    (
        (1, 3,),
        (1, 4,),
        (2, 1,),
        (2, 3,),
        (2, 4,),
        (3, 4,),
    )
]


@pytest.mark.parametrize('ids', deep)
def test_deep_link(db_init, ids):
    conn, in_ = db_init
    mt.fill_methods(conn, in_)
    di_met = mt.init_methods2(conn)
    mt.init_link(conn, di_met)
    mt.deep_link(conn, 3, 4)
    cur = conn.cursor()
    cu_ = cur.execute('select * from call_link;')
    for cc in cu_:
        assert cc[0:2] in ids
        # assert cc[0:2] not in [(1, 4,), (2, 4,),]

