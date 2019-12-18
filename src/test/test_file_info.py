import pytest
import src.core.file_info as lf   # lf ~ fiLe_inFo


def test_ext_translate():
    ex1 = ''
    tx1 = lf.ext_translate(ex1)
    assert tx1 == ('',)
    ex2 = 'a, .b,c,.d'
    tx2 = lf.ext_translate(ex2)
    assert tx2 == ('a', 'b', 'c', 'd')
    ex3 = 'a, .b,*,.d'
    tx3 = lf.ext_translate(ex3)
    assert tx3 == '*'
    ex4 = '., a'
    tx4 = lf.ext_translate(ex4)
    assert tx4 == ('', 'a')
