import pytest
from pathlib import Path
import src.core.load_db_data as ld

PATH_TO_DATA = Path('data')
ROOT = Path.cwd().parent.parent / 'test_data'


@pytest.fixture()
def expected_files():
    files = []
    with open(PATH_TO_DATA / 'file_list.txt') as fl:
        for line in fl:
            files.append(tuple(line.strip().split('/')))
    return files


def test_yield_files(expected_files):
    ll = len(ROOT.parts) - 1
    files = ld.yield_files(ROOT,'*')
    exp = expected_files
    for file in files:
        ff = Path(file).parts[ll:]
        assert ff in exp
