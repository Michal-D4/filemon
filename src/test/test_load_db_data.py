import pytest
from pathlib import Path
import src.core.load_db_data as ld

PATH_TO_DATA = Path('data')
ROOT = Path.cwd().parent.parent / 'test_data'


@pytest.fixture(params=[
    ('',),
    ('pdf', 'ui'),
    '*'
])
def expected_files(request):
    def check_ext(ext, file_parts: tuple) -> bool:
        if '*' in ext:
            return True
        last_part = file_parts[-1]
        name, ext_ = last_part.rpartition('.')[0::2]
        file_ext = ext_ if name else ''
        return file_ext in ext

    ext = request.param
    files = []
    with open(PATH_TO_DATA / 'file_list.txt') as fl:
        for line in fl:
            row = tuple(line.strip().split('/'))
            if check_ext(ext, row):
                files.append(row)
    return files, ext


def test_yield_files(expected_files):
    ll = len(ROOT.parts) - 1
    ext = expected_files[1]
    files = ld.yield_files(ROOT,'*')
    exp = expected_files[0]
    for file in files:
        ff = Path(file).parts[ll:]
        assert ff in exp
