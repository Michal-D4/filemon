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
        print(tt, cc[0])
        assert cc[0] == di_met[tt]


def test_set_calling_id():
    pass


@pytest.mark.parametrize('ids',
                         [((4, 1),
                           (4, 2),
                           (1, 3),
                           ),
                          ])
def test_init_link(db_init, ids):
    conn, in_ = db_init
    mt.fill_methods(conn, in_)
    di_met = mt.init_methods2(conn)
    mt.init_link(conn, di_met)
    cur = conn.cursor()
    cu_ = cur.execute('select * from call_link;')
    for cc in cu_:
        print('|--->', cc)
        tt = cc[0:1]
        assert tt == ids[0] or tt == ids[1] or tt == ids[2]



def test_deep_link():
    pass
