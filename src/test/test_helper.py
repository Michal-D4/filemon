import pytest
import src.core.helper as hp


@pytest.mark.parametrize("path,expected", [
('/home/michal/file1.pdf', 'pdf'),
('/home/michal/.file.pdf', 'pdf'),
('/home/michal/.gitignore', ''),
('/home/michal/file0', ''),
('/home/michal/', ''),
])
def test_get_file_extension(path, expected):
    ext = hp.get_file_extension(path)
    assert ext == expected
