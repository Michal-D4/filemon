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
def db_init():
    conn = sqlite3.connect(':memory:')
    mt.create_tables(conn)
    return conn


def test_fill_methods(db_init, tmp_path):
    conn = db_init
    in_ = tmp_path / 'met.txt'
    in_.write_text('\n'.join(('heads', *lines)))
    mt.fill_methods(conn, in_)
    curs = conn.cursor()
    sel = curs.execute('select module, class, method, c_method, c_module, c_class, start '
                       'from methods;')

    i = 0
    for row in sel:
        assert row == (*lines[i].split(','),)[1:]
        i += 1


def test_init_methods2(db_init, tmp_path):
    pass


def test_set_calling_id():
    pass


def test_init_link():
    pass


def test_deep_link():
    pass
