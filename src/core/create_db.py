# create_db.py

import sqlite3
from loguru import logger

OBJ_DEFS = (
    '''
CREATE TABLE IF NOT EXISTS Files (
FileID INTEGER NOT NULL PRIMARY KEY,
DirID INTEGER NOT NULL,
ExtID INTEGER,
FileName TEXT,
CommentID INTEGER,
FileDate DATE not null default '0001-01-01',
Pages INTEGER not null default 0,
Size INTEGER not null default 0,
IssueDate DATE not null default '0001-01-01',
Opened TEXT not null default '0001-01-01',
Commented DATE not null default '0001-01-01',
FOREIGN KEY(DirID) REFERENCES Dirs(DirID),
FOREIGN KEY(CommentID) REFERENCES Comments(CommentID),
FOREIGN KEY(ExtID) REFERENCES Extensions(ExtID)
);''',

    '''
CREATE TABLE IF NOT EXISTS Authors (
AuthorID INTEGER NOT NULL PRIMARY KEY,
Author TEXT
);''',

    '''
CREATE TABLE IF NOT EXISTS FileAuthor (
FileID INTEGER NOT NULL,
AuthorID INTEGER NOT NULL,
primary key(FileID, AuthorID) 
);''',

    '''
CREATE TABLE IF NOT EXISTS Tags (
TagID INTEGER NOT NULL PRIMARY KEY,
Tag TEXT
);''',

    '''
CREATE TABLE IF NOT EXISTS FileTag (
FileID INTEGER NOT NULL,
TagID INTEGER NOT NULL
primary key(FileID, TagID) 
);''',

    '''
CREATE TABLE IF NOT EXISTS Dirs (
DirID INTEGER NOT NULL PRIMARY KEY,
Path TEXT,
ParentID INTEGER,
FolderType INTEGER,
FOREIGN KEY(ParentID) REFERENCES Dirs(DirID) ON DELETE CASCADE
);''',

    '''
CREATE TABLE IF NOT EXISTS Extensions (
ExtID INTEGER NOT NULL PRIMARY KEY,
Extension TEXT,
GroupID INTEGER
);''',

    '''
CREATE TABLE IF NOT EXISTS ExtGroups (
GroupID INTEGER NOT NULL PRIMARY KEY,
GroupName TEXT
);''',

    '''
CREATE TABLE IF NOT EXISTS Comments (
CommentID INTEGER NOT NULL PRIMARY KEY,
Comment TEXT,
BookTitle TEXT
);''',

    '''
CREATE TABLE IF NOT EXISTS VirtDirs (
ParentID INTEGER not null,
DirID INTEGER not null,
FOREIGN KEY(ParentID) REFERENCES Dirs(DirID) ON DELETE CASCADE
);''',

    '''
CREATE TABLE IF NOT EXISTS VirtFiles (
DirID INTEGER not null,
FileID INTEGER not null,
FOREIGN KEY(DirID) REFERENCES Dirs(DirID) ON DELETE CASCADE
);''',

    'CREATE INDEX IF NOT EXISTS Dirs_ParentID ON Dirs(ParentID);',
)


def create_all_objects(connection):
    cursor = connection.cursor()
    for obj in OBJ_DEFS:
        try:
            cursor.execute(obj)
        except sqlite3.Error as err:
            logger.error(' | '.join(("An error occurred:", err.args[0])))

    initiate_db(connection)


def initiate_db(connection):
    cursor = connection.cursor()
    try:
        cursor.execute('insert into Dirs (DirID) values (0);')  # common root - without parent
    except sqlite3.Error as err:
        print("An error occurred:", err.args[0])

    connection.commit()

