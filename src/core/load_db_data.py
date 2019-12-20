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


def yield_files(root: str, ext: str):
    """
    generator of file list
    :param root: root directory
    :param ext: list of extensions as comma separated string
    :return: generator
    """
    r_path = pathlib.Path(root)
    for filename in r_path.rglob('*'):
        if not filename.is_file():
            continue
        elif '*' in ext:
            yield filename
        elif filename.suffix.strip('.') in ext:
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
        logger.debug(f'{path_} | {ext_}')
        files = yield_files(path_, ext_)
        for line in files:
            logger.debug(line)
            file = pathlib.Path(line)
            path = file.parent
            idx, _ = self.insert_dir(path)
            if idx > 0:
                self.updated_dirs.add(str(idx))
                self.insert_file(idx, file)
        self.conn.commit()
        logger.debug(f'end | {len(self.updated_dirs)}')

    def insert_file(self, dir_id: int, full_file_name: pathlib.Path):
        """
        Insert file into Files table
        :param dir_id: int > 0
        :param full_file_name:
        :return: None
        """
        logger.debug(f'{dir_id} | {full_file_name}')
        file_ = full_file_name.name

        logger.debug(file_)

        item = self.cursor.execute(FIND_FILE, {'dir_id': dir_id, 'file': file_}).fetchone()
        if not item:
            ext_id = self.insert_extension(full_file_name)
            self.cursor.execute(INSERT_FILE, {'dir_id': dir_id,
                                              'file': file_,
                                              'ext_id': ext_id})

    def insert_extension(self, file: pathlib.Path) -> int:
        '''
        insert or find extension in DB
        :param file - file name
        returns (ext_id, extension_of_file)
        '''
        ext = file.suffix.strip('.')
        item = self.cursor.execute(FIND_EXT, (ext,)).fetchone()
        if item:
            return item[0]

        self.cursor.execute(INSERT_EXT, {'ext': ext})
        idx = self.cursor.lastrowid
        self.conn.commit()
        return idx

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
        to the new file can be a parent for existing folders,
        and if so, apply it as the parent for these folders.
        :param new_parent_id: id of new dir
        :param path: path of new dir
        """
        old_parent_id = self.parent_id_for_child(path)
        if old_parent_id != -1:
            self.cursor.execute(CHANGE_PARENT_ID, {'currId': old_parent_id,
                                                   'newId': new_parent_id,
                                                   'newPath': str(path) + '%'})

    def parent_id_for_child(self, path: pathlib.PurePath) -> int:
        """
        Check whether the new dir can be parent for other directories
        ie. the new path (not inserted yet) is shorten the some existing path
        parents for such paths will be replaced by this new path later
        :param path:
        :return: parent Id of first found child, -1 if no children
        """
        item = self.cursor.execute(FIND_PART_PATH, {'newPath': str(path) + '%'}).fetchone()
        if item:
            return item[0]

        return -1

    def search_closest_parent(self, path: pathlib.PurePath) -> (int, pathlib.PurePath):
        """
        Search parent directory in DB
        :param path:  file path
        :return: parent_id: int, parent_path: pathlib.PurePath;  or   0, None
        """
        # WORKAROUND: the dummy path "path / '@'", that is path is a parent for it.
        # So parents includes the path itself
        for path_ in (path / '@').parents:
            parent_id = self.cursor.execute(FIND_EXACT_PATH, (str(path_),)).fetchone()
            if parent_id:
                return parent_id[0], path_

        return 0, None


if __name__ == "__main__":
    pass
