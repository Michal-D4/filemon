import sqlite3
import pytest

import prj_info
import prj_info.method_tree as mt

lines = (
    ",m1,c1,me2,me1,m1,c1,start",
    ",m1,c1,me3,me1,m1,c1,",
    ",m1,c1,me3,me2,m1,c1,",
    ",m1,c1,me1,,m1,c1,",
)


@pytest.fixture(scope="module")
def db_init(tmpdir_factory):
    conn = sqlite3.connect(":memory:")
    mt.create_tables(conn)
    in_ = tmpdir_factory.mktemp("data").join("met.txt")
    in_.write("\n".join(("heads", *lines)))
    return conn, in_


def test_fill_methods(db_init, tmp_path):
    conn, in_ = db_init
    mt.fill_methods(conn, in_)
    curs = conn.cursor()
    sel = curs.execute(
        "select module, class, method, c_method, c_module, "
        "c_class, remark from methods;"
    )

    i = 0
    for row in sel:
        assert row == (*lines[i].split(","),)[1:]
        i += 1

