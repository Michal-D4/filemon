# load_db_data.py

from loguru import logger
import os
import pathlib
from typing import Optional

from .helper import get_file_extension
from .utilities import DB_Connection

FIND_PART_PATH = 'select ParentID from Dirs where Path like :newPath;'

FIND_EXACT_PATH = 'select DirID from Dirs where Path = :newPath;'

CHANGE_PARENT_ID = '''update Dirs set ParentID = :newId
 where ParentID = :currId and Path like :newPath and DirID != :newId;'''

FIND_FILE = 'select * from Files where DirID = :dir_id and FileName = :file;'

INSERT_DIR = 'insert into Dirs (Path, ParentID, FolderType) values (:path, :id, 0);'

INSERT_FILE = 'insert into Files (DirID, FileName, ExtID) values (:dir_id, :file, :ext_id);'

FIND_EXT = 'select ExtID from Extensions where Extension = ?;'

INSERT_EXT = 'insert into Extensions (Extension, GroupID) values (:ext, 0);'


def yield_files(root: str, extensions: str):
    """
    generator of file list
    :param root: root directory
    :param extensions: list of extensions as comma separated string
    :return: generator
    """
    r_path = pathlib.Path(root)
    ext_ = tuple(x.strip('. ') for x in extensions.split(','))
    for filename in r_path.rglob('*'):
        logger.debug(f'{extensions}, type {type(extensions)}')
        logger.debug(f'filename type {type(filename)}')
        if not filename.is_file():
            continue
        elif (not extensions) and filename.suffix == '':
            yield filename
        elif '*' in ext_:
            yield filename
        elif filename.suffix in ext_:
            yield filename
        else:
            continue


class LoadDBData:
    """
    class LoadDBData
    """
    def __init__(self, conn):
        """
        class LoadDBData
        :param connection: - connection to database
        """
        self.conn = conn
        self.cursor = self.conn.cursor()
        self.updated_dirs = set()

    def get_updated_dirs(self):
        return self.updated_dirs

    def load_data(self, path_, ext_):
        """
        Load data in data base
        :param data: - iterable lines of file names with full path
        :return: None
        """
        logger.debug(' | '.join((path_, ext_)))
        # breakpoint()
        files = yield_files(path_, ext_)
        for line in files:
            logger.debug(' : '.join(('line', line)))
            path = pathlib.Path(line).parent
            idx, _ = self.insert_dir(path)
            self.updated_dirs.add(str(idx))
            self.insert_file(idx, line)
        self.conn.commit()

    def insert_file(self, dir_id: int, full_file_name: str):
        """
        Insert file into Files table
        :param dir_id:
        :param full_file_name:
        :return: None
        """
        logger.debug(' | '.join((str(dir_id), full_file_name)))
        file_ = os.path.basename(full_file_name)

        logger.debug(file_)

        item = self.cursor.execute(FIND_FILE, {'dir_id': dir_id, 'file': file_}).fetchone()
        if not item:
            ext_id, _ = self.insert_extension(file_)
            if ext_id:      # files with an empty extension are not handled
                self.cursor.execute(INSERT_FILE, {'dir_id': dir_id,
                                                  'file': file_,
                                                  'ext_id': ext_id})

    def insert_extension(self, file: str) -> (int, str):
        '''
        insert or find extension in DB
        :param file - file name
        returns (ext_id, extension_of_file)
        '''
        ext = get_file_extension(file)
        if ext:
            item = self.cursor.execute(FIND_EXT, (ext,)).fetchone()
            if item:
                idx = item[0]
            else:
                self.cursor.execute(INSERT_EXT, {'ext': ext})
                idx = self.cursor.lastrowid
                self.conn.commit()
        else:
            idx = 0
        return idx, ext

    def insert_dir(self, path: pathlib.PurePath) -> (int, bool):
        '''
        Insert directory into Dirs table
        :param path:
        :return: (dirID, is_created)
        "is_created = false" means that dirID already exists; doesn't mean error
        '''
        idx, parent_path = self.search_closest_parent(path)
        if parent_path == path:
            return idx, False

        self.cursor.execute(INSERT_DIR, {'path': str(path), 'id': idx})
        idx = self.cursor.lastrowid

        self.change_parent(idx, path)
        self.conn.commit()
        return idx, True

    def change_parent(self, new_parent_id: int, path: pathlib.PurePath):
        """
        The purpose of this method is to check whether the path
        to the new file can be parent for existing folders,
        and if so, apply it as the parent for them.
        :param new_parent_id: id of new dir
        :param path: path of new dir
        """
        old_parent_id = self.parent_id_for_child(path)
        if old_parent_id != -1:
            self.cursor.execute(CHANGE_PARENT_ID, {'currId': old_parent_id,
                                                       'newId': new_parent_id,
                                                       'newPath': str(path) + '%'})

    def parent_id_for_child(self, path: pathlib.PurePath) -> int:
        '''
        Check the new file path:
          if it can be parent for other directories
        :param path:
        :return: parent Id of first found child, -1 if not children
        '''
        item = self.cursor.execute(FIND_PART_PATH, {'newPath': str(path) + '%'}).fetchone()
        if item:
            return item[0]

        return -1

    def search_closest_parent(self, path: pathlib.PurePath) -> (int, pathlib.PurePath):
        '''
        Search parent directory in DB
        :param path:  file path
        :rtype: tuple(parent_id: int, parent_path: str) or (0, None)
        '''
        # 'path / 'a' is workaround. Need check the path itself
        # and all its parents, not only parents
        for path_ in (path / 'a').parents:
            logger.debug(path_)   # the issue that there is a different separator than stored in DB
            parent_id = self.cursor.execute(FIND_EXACT_PATH, (str(path_),)).fetchone()
            if parent_id:
                return (parent_id[0], path_)

        return (0, None)


if __name__ == "__main__":
    pass
