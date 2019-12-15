# create_db.py

import sqlite3
from loguru import logger

OBJ_DEFS = (
    '''CREATE TABLE IF NOT EXISTS Files (
FileID INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
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

    '''CREATE TABLE IF NOT EXISTS Authors (
AuthorID INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
Author TEXT
);''',

    '''
CREATE TABLE IF NOT EXISTS FileAuthor (
FileID INTEGER NOT NULL,
AuthorID INTEGER NOT NULL
);''',
    'CREATE UNIQUE INDEX IF NOT EXISTS FileAuthorIdx1 ON FileAuthor(FileID, AuthorID);',
    'CREATE INDEX IF NOT EXISTS FileAuthorIdx2 ON FileAuthor(AuthorID);',

    '''CREATE TABLE IF NOT EXISTS Tags (
TagID INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
Tag TEXT
);''',

    '''CREATE TABLE IF NOT EXISTS FileTag (
FileID INTEGER NOT NULL,
TagID INTEGER NOT NULL
);''',
    'CREATE UNIQUE INDEX IF NOT EXISTS FileTagIdx1 ON FileTag(FileID, TagID);',
    'CREATE INDEX IF NOT EXISTS FileTagIdx2 ON FileTag(TagID);',

    '''CREATE TABLE IF NOT EXISTS Dirs (
DirID INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
Path TEXT,
ParentID INTEGER,
FolderType INTEGER,
FOREIGN KEY(ParentID) REFERENCES Dirs(DirID) ON DELETE CASCADE
);''',

    '''CREATE TABLE IF NOT EXISTS Extensions (
ExtID INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
Extension TEXT,
GroupID INTEGER
);''',
    'CREATE INDEX IF NOT EXISTS ExtIdx ON Extensions(GroupID);',

    '''CREATE TABLE IF NOT EXISTS ExtGroups (
GroupID INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
GroupName TEXT
);''',

    '''CREATE TABLE IF NOT EXISTS Comments (
CommentID INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
Comment TEXT,
BookTitle TEXT
);''',

    '''CREATE TABLE IF NOT EXISTS Log (
ActTime DATETIME,
ObjID INTEGER,
ActCode INTEGER
);''',

    '''CREATE TABLE IF NOT EXISTS VirtDirs (
ParentID INTEGER not null,
DirID INTEGER not null,
FOREIGN KEY(ParentID) REFERENCES Dirs(DirID) ON DELETE CASCADE
);''',
    '''CREATE TABLE IF NOT EXISTS VirtFiles (
DirID INTEGER not null,
FileID INTEGER not null,
FOREIGN KEY(DirID) REFERENCES Dirs(DirID) ON DELETE CASCADE
);''',

    'CREATE INDEX IF NOT EXISTS Dirs_ParentID ON Dirs(ParentID);',
    'CREATE INDEX IF NOT EXISTS LogIdx ON Log(ActTime desc);',
    'CREATE INDEX IF NOT EXISTS LogIdx ON Log(ObjID, ActTime desc);',
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
        cursor.execute('insert into Dirs (DirID) values (0);')
        cursor.execute('insert into Dirs (Path, ParentID, FolderType)'
                       ' values ("Favorites", 0, 1);')
    except sqlite3.Error as err:
        print("An error occurred:", err.args[0])

    connection.commit()


if __name__ == "__main__":
    BASE_FILE = ":memory:"
    IT_IS = sqlite3.connect(BASE_FILE)
    create_all_objects(IT_IS)
