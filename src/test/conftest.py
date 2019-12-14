import sqlite3
import pytest
import src.core.create_db as db


PATH_TO_DATA = '../tmp/CSV'

# Files with input data for DB
FILES = ['dirs.csv',
         'VirtDirs.csv',
         'Files.csv',
         'VirtFiles.csv',
         'Comments.csv',
         'extensions.csv',
         'ExtGroups.csv',
         'FileAuthor.csv',
         'Tags.csv',
         'FileTag.csv',
         ]


@pytest.fixture()
def init_db():
    conn = sqlite3.connect(":memory:")
    db.create_all_objects(conn)
