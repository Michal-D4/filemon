# model/utilities.py

import sqlite3
import datetime

EXT_ID_INCREMENT = 100000
DETECT_TYPES = sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES

Selects = {'TREE':  # (Dir name, DirID, ParentID, Full path of dir)
               (('WITH x(Path, DirID, ParentID, FolderType, level) AS '
                 '(SELECT Path, DirID, ParentID, FolderType, 0 as level'),
                'FROM Dirs WHERE DirID = {}',
                'FROM Dirs WHERE ParentID = {}',
                ('UNION ALL SELECT t.Path, t.DirID, t.ParentID, t.FolderType, '
                 'x.level + 1 as lvl FROM x INNER JOIN Dirs AS t '
                 'ON t.ParentID = x.DirID'),
                'and lvl <= {}) SELECT * FROM x order by level desc, Path;',
                ') SELECT * FROM x order by level desc, Path;',
                ),

           'VIRT_DIRS': ('select d.Path, d.DirID, v.ParentID, d.FolderType from Dirs d ' 
                                  'inner join VirtDirs v on d.DirID = v.DirID;'),
           'DIR_IDS':
               ('WITH x(DirID, ParentID, FolderType, level) AS '
                '(SELECT DirID, ParentID, FolderType, 0 as level',
                'FROM Dirs WHERE DirID = {}',
                'FROM Dirs WHERE ParentID = {}',
                ('UNION ALL SELECT t.DirID, t.ParentID, t.FolderType, '
                 'x.level + 1 as lvl FROM x INNER JOIN Dirs AS t '
                 'ON t.ParentID = x.DirID'),
                'and lvl <= {}) SELECT DirID FROM x order by DirID;',
                ') SELECT DirID FROM x order by DirID;'),

           'PRAGMA': 'PRAGMA foreign_keys = ON;',

           'FILE_IDS_ALL_TAG': ('select FileID from FileTag where TagID in ({}) '
                                'group by FileID having count(*) = {};'),
           'PATH': 'select Path from Dirs where DirID = ?;',
           'EXT': ('select Extension as title, ExtID+{}, GroupID '
                   'as ID from Extensions UNION select GroupName as title, '
                    'GroupID, 0 as ID from ExtGroups '
                    'order by ID desc, title;').format(EXT_ID_INCREMENT),
           'HAS_EXT': 'select count(*) from Extensions where Extension = ?;',
           'EXT_ID_IN_GROUP': 'select ExtID from Extensions where GroupID = ?;',
           'EXT_IN_GROUP': 'select Extension, ExtID from Extensions where GroupID = ?;',
           'EXT_IN_FILES': 'select FileID from Files where ExtID = ?;',
           'FILE_INFO': ('select A.FileName || " " || COALESCE(B.BookTitle, "") '
                         '|| " " || COALESCE(B.Comment, ""), A.FileID from '
                         'Files A left join Comments B on B.CommentID = A.CommentID '
                         'where A.ExtID in ({}) and NOT EXISTS (select * from FileTag '
                         'where FileID = A.FileID and TagID = {});'),
           'FILE_IN_DIR': 'select FileID from Files where DirID={} and FileName="{}";',
           'TAGS': 'select Tag, TagID from Tags order by Tag COLLATE NOCASE;',
           'FILE_TAGS': ('select Tag, TagID from Tags where TagID in '
                         '(select TagID from FileTag where FileID = ?);'),
           'TAG_FILES': 'select * from FileTag where TagID=:tag_id;',
           'TAGS_BY_NAME': 'select Tag, TagID from Tags where Tag in ("{}");',
           'TAG_FILE': 'select * from FileTag where FileID = ? and TagID =?;',
           'FILE_IDS_ANY_TAG': 'select FileID from FileTag where TagID in ({}) order by FileID;',
           'AUTHORS': 'select Author, AuthorID from Authors order by Author COLLATE NOCASE;',
           'FILE_AUTHORS': ('select Author, AuthorID from Authors where AuthorID in '
                            '(select AuthorID from FileAuthor where FileID = ?);'),
           'AUTHOR_FILES': 'select * from FileAuthor where AuthorID=:author_id;',
           'AUTHORS_BY_NAME': 'select Author, AuthorID from Authors where Author in ("{}");',
           'AUTHOR_FILE': 'select * from FileAuthor where FileID = ? and AuthorID =?;',
           'FILE_IDS_AUTHORS': 'select FileID from FileAuthor where AuthorID in ({});',
           'FILE_COMMENT': 'select Comment, BookTitle from Comments where CommentID = ?;',
           'ADV_SELECT':
               (
                   'DirID in ({})',
                   'ExtID in ({})',
                   'FileID in ({})',
                   'FileDate > {}',
                   'IssueDate > {}',
                   ('select FileName, FileDate, Pages, Size, IssueDate, '
                    'Opened, Commented, FileID, DirID, coalesce(CommentID, 0), '
                    'ExtID from Files')
               ),
           'FILES_CURR_DIR': ('select FileName, FileDate, Pages, Size, IssueDate, '
                              'Opened, Commented, FileID, DirID, coalesce(CommentID, 0), '
                              'ExtID from Files where DirId = ?;'),
           'FILES_VIRT': ('select FileName, FileDate, Pages, Size, IssueDate, Opened, '
                          'Commented, FileID, DirID, coalesce(CommentID, 0), ExtID '
                          'from Files where FileID in (select FileID from VirtFiles where '
                          'DirID = ?);'),
           'FAV_ID': 'select DirID from Dirs where FolderType = 1',
           'ISSUE_DATE': 'select IssueDate from Files where FileID = ?;',
           'EXIST_IN_VIRT_DIRS': 'select * from VirtDirs where DirID = ? and ParentID = ?;'
           }

Insert = {'VIRTUAL_FILE': 'insert into VirtFiles (DirID, FileID) values (?, ?);',
          'COMMENT': 'insert into Comments (Comment, BookTitle) values (?, ?);',
          'EXT': 'insert into Extensions (Extension, GroupID) values (:ext, 0);',
          'EXT_GROUP': 'insert into ExtGroups (GroupName) values (?);',
          'AUTHORS': 'insert into Authors (Author) values (:author);',
          'AUTHOR_FILE': 'insert into FileAuthor (AuthorID, FileID) values (:author_id, :file_id);',
          'TAGS': 'insert into Tags (Tag) values (:tag);',
          'TAG_FILE': 'insert into FileTag (TagID, FileID) values (:tag_id, :file_id);',
          'COPY_TAGS': ('insert into FileTag (TagID, FileID) select TagID, '
                        '{} from FileTag where FileID = {};'),
          'COPY_AUTHORS': ('insert into FileAuthor (AuthorID, FileID) select AuthorID, '
                           '{} from FileAuthor where FileID = {};'),
          'COPY_FILE': ('insert into Files (DirID, ExtID, '
                        'FileName, CommentID, FileDate, Pages, Size, '
                        'IssueDate, Opened, Commented) SELECT {}, {}, '
                        'ExtID, FileName, CommentID, FileDate, Pages, '
                        'Size, IssueDate, Opened, Commented FROM Files '
                        'where FileID = {};'),
          'DIR': 'insert into Dirs (Path, ParentID, FolderType) values (?, ?, ?);',
          'VIRTUAL_DIR': 'insert into VirtDirs (ParentID, DirID) values (?, ?);',
          }

Update = {'EXT_GROUP': 'update Extensions set GroupID = ? where ExtID = ?;',
          'ISSUE_DATE': 'update Files set IssueDate = ? where FileID = ?;',
          'BOOK_TITLE': 'update Comments set BookTitle = ? where CommentID = ?;',
          'COMMENT': 'update Comments set Comment = ? where CommentID = ?;',
          'FILE_COMMENT': 'update Files set CommentID = ? where FileID = ?;',
          'FILE_NAME': 'update Files set FileName = ? where FileID = ?;',
          'FILE_DIR_ID': 'update Files set DirID = ? where FileID = ?;',
          'PAGES': 'update Files set Pages = ? where FileID = ?;',
          'OPEN_DATE': "update Files set Opened = ? where FileID = ?;",
          'COMMENT_DATE': "update Files set Commented = date('now') where FileID = ?;",
          'UPDATE_TAG': 'update Tags set Tag = ? where TagID = ?;',
          'DIR_NAME': 'update Dirs set Path = ? where DirID = ?;',
          'DIR_PARENT': 'update Dirs set ParentId = ? where DirID = ?;',
          'VIRTUAL_FILE_MOVE': 'update VirtFiles set DirID = ? where DirID = ? and FileID = ?;'
          }

Delete = {'EXT': 'delete from Extensions where ExtID = ?;',
          'FILE_BY_EXT': 'delete from Files where ExtID = ?;',
          'UNUSED_EXT_GROUP': ('delete from ExtGroups where NOT EXISTS ('
                               'select * from Extensions where GroupID = '
                               'ExtGroups.GroupID);'),
          'UNUSED_AUTHORS': ('delete from Authors where NOT EXISTS (select * '
                             'from FileAuthor where AuthorID = Authors.AuthorID);'),
          'UNUSED_TAGS': ('delete from Tags where NOT EXISTS (select * '
                          'from FileTag where TagID = Tags.TagID);'),
          'UNUSED_EXT': ('delete from Extensions where NOT EXISTS (select * '
                         'from Files where ExtID = Extensions.ExtID);'),
          'FILE_VIRT': 'delete from VirtFiles where DirID = ? and FileID = ?;',
          'FAVOR_ALL': 'delete from VirtFiles where FileID = ?;',
          'COMMENT': ('delete from Comments where CommentID = {} and '
                      'not exists (select * from Files where CommentID = {});'),
          'FILE': 'delete from Files where FileID = ?;',
          'AUTHOR_FILE': 'delete from FileAuthor where AuthorID=:author_id and FileID=:file_id;',
          'AUTHOR': 'delete from Authors where AuthorID=:author_id;',
          'AUTHOR_FILE_BY_FILE': 'delete from FileAuthor where FileID=?;',
          'TAG_FILE': 'delete from FileTag where TagID=:tag_id and FileID=:file_id;',
          'TAG_FILE_BY_FILE': 'delete from FileTag where FileID = ?;',
          'TAG': 'delete from Tags where TagID=:tag_id;',
          'EMPTY_DIRS': ('delete from Dirs where FolderType = 0 and NOT EXISTS ',
                         '(select * from Files where DirID = Dirs.DirID);'),
          'VIRT_FROM_DIRS': 'delete from Dirs where DirID = ? and FolderType > 0;',
          'FROM_VIRT_DIRS': 'delete from VirtDirs where ParentID = ? and DirID = ?;',
          'VIRT_DIR_ID': 'delete from VirtDirs where DirID = ?;'
          }


DB_Connection = {'Path': '',
                 'Conn': None,
                }


def generate_adv_sql(param: dict) -> str:
    """
    Generate SQL from tuple "Selects['ADV_SELECT']" of length 6
    according to choices made on "SelOpt" dialog
    @param param: dictionary with keys:
    'dir', 'ext', 'file' and 'date'
    The first three contain lists of IDs for Dirs, Extensions, Files tables
    as comma separated string
    The last is tuple of 3 items:
    @return:
    """

    tmp = []

    keys_ = {'dir': 0, 'ext': 1, 'file': 2}
    for kk in keys_:
        if param[kk]:
            tmp.append(Selects['ADV_SELECT'][keys_[kk]].format(param[kk]))

    if param['date'][0]:
        tt = datetime.date.today()
        tt = tt.replace(year=tt.year - int(param['date'][1]))
        if param['date'][2]:
            tmp.append(Selects['ADV_SELECT'][3].format(tt))
        else:
            tmp.append(Selects['ADV_SELECT'][4].format(tt))

    tt = ' and '.join(tmp)
    sql = ' where '.join((Selects['ADV_SELECT'][5], tt))

    return sql


def advanced_selection(param):
    if not DB_Connection['Conn']:
        return ()

    sql = generate_adv_sql(param)
    # print(sql)

    if sql:
        return DB_Connection['Conn'].execute(sql)
    return ()


def generate_sql(dir_id, level, sql='TREE'):
    tree_sql = Selects[sql]
    tmp = (tree_sql[0], tree_sql[1].format(dir_id),
           tree_sql[2].format(dir_id), tree_sql[3],
           tree_sql[4].format(level), tree_sql[5])
    cc = [(0, 2, 3, 5),
          (0, 1, 3, 5),
          (0, 2, 3, 4),
          (0, 1, 3, 4)]
    i = (level > 0) * 2 + (dir_id > 0)  # 00 = 0, 01 = 1, 10 = 2, 11 = 3
    sql = ' '.join([tmp[j] for j in cc[i]])
    return sql


def dir_tree_select(dir_id, level):
    """
    Select tree of directories starting from dir_id up to level
    :param dir_id: - starting directory, 0 - from root
    :param level: - max level of tree, 0 - all levels
    :return: cursor of directories
    """
    sql = generate_sql(dir_id, level)

    return DB_Connection['Conn'].cursor().execute(sql)


def dir_ids_select(dir_id, level):
    """
    Select tree of directories starting from dir_id up to level
    :param dir_id: - starting directory, 0 - from root
    :param level: - max level of tree, 0 - all levels
    :return: list of directories ids
    """
    sql = generate_sql(dir_id, level, sql='DIR_IDS')

    return DB_Connection['Conn'].cursor().execute(sql)


def select_other(sql, params=()):
    return DB_Connection['Conn'].cursor().execute(Selects[sql], params)


def select_other2(sql, params=()):
    return DB_Connection['Conn'].cursor().execute(Selects[sql].format(*params))


def insert_other(sql, data):
    ss = DB_Connection['Conn'].cursor().execute(Insert[sql], data)
    DB_Connection['Conn'].commit()
    return ss.lastrowid


def insert_other2(sql, data):
    ss = DB_Connection['Conn'].cursor().execute(Insert[sql].format(*data))
    DB_Connection['Conn'].commit()
    return ss.lastrowid


def update_other(sql, data):
    DB_Connection['Conn'].cursor().execute(Update[sql], data)
    DB_Connection['Conn'].commit()


def delete_other(sql, data):
    try:
        DB_Connection['Conn'].cursor().execute(Delete[sql], data)
    except sqlite3.IntegrityError:
        pass
    else:
        DB_Connection['Conn'].commit()


def delete_other2(sql, data):
    DB_Connection['Conn'].cursor().execute(Delete[sql].format(*data))
    DB_Connection['Conn'].commit()
