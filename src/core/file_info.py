# file_info.py

from collections import namedtuple
import datetime
from loguru import logger
import os
import re
import sqlite3

from PyPDF2 import PdfFileReader, utils
from PyQt5.QtCore import pyqtSignal, QObject, pyqtSlot, QRunnable

from src.core.helper import get_file_extension
from src.core.load_db_data import LoadDBData

DETECT_TYPES = sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES

AUTHOR_ID = 'select AuthorID from Authors where Author = ?;'

INSERT_AUTHOR = 'insert into Authors (Author) values (?);'

FILE_AUTHOR = 'select * from FileAuthor where FileID=? and AuthorID=?'

INSERT_FILEAUTHOR = 'insert into FileAuthor (FileID, AuthorID) values (?, ?);'

SELECT_COMMENT = 'select BookTitle from Comments where CommentID=?;'

INSERT_COMMENT = 'insert into Comments (BookTitle, Comment) values (?, ?);'

FILES_IN_LOAD = ' '.join(('select f.FileID, f.FileName, d.Path, f.CommentID,',
                          'f.IssueDate, f.Pages from Files f, Dirs d',
                          'where f.DirID = d.DirID and d.DirID in ({});'))

UPDATE_FILE = ' '.join(('update Files set',
                        'CommentID = :comm_id,',
                        'FileDate = :date,',
                        'Pages = :page,',
                        'Size = :size,',
                        'IssueDate = :issue_date',
                        'where FileID = :file_id;'))


class LoadFiles(QRunnable):
    """
    Load files with of extensions from list 'ext_' located under Path 'path_'

    :param path_: location of collected files (and all subdirs)
    :param ext_: list of extensions
    :param db_name: full name of DB file
    :param updated_dirs: list to return the dirID created/updated in the DB
    """

    def __init__(self, path_, ext_, db_name, updated_dirs: list):
        """
        Load files with list of extensions 'ext_' from Path 'path_'
        """
        super(LoadFiles, self).__init__()
        logger.debug(' '.join((path_, '|', ext_, '|')))
        self.conn = sqlite3.connect(db_name, check_same_thread=False,
                                    detect_types=DETECT_TYPES)
        self.conn.cursor().execute('PRAGMA foreign_keys = ON;')
        self.path_ = path_
        self.ext_ = ext_
        self.updated_dirs = updated_dirs
        self.finished = pyqtSignal()

    @pyqtSlot()
    def run(self):
        files = LoadDBData()
        logger.debug(' | '.join((self.path_, self.ext_)))
        files.load_data(self.path_, self.ext_)
        self.updated_dirs.append(files.get_updated_dirs())


class FileInfo(QRunnable):

    @pyqtSlot()
    def run(self):
        logger.debug('--> FileInfo.run')
        self._update_files()
        self.finished.emit()           # 'Updating of files is finished'

    def __init__(self, updated_dirs, db_path):
        super(FileInfo, self).__init__()
        logger.debug('--> FileInfo.__init__')
        self.upd_dirs = updated_dirs
        self.conn = sqlite3.connect(db_path, check_same_thread=False,
                                    detect_types=DETECT_TYPES)
        self.conn.cursor().execute('PRAGMA foreign_keys = ON;')
        self.cursor = self.conn.cursor()
        self.file_info = []
        self.finished = pyqtSignal()

    def _insert_author(self, file_id):
        authors = re.split(r',|;|&|\band\b', self.file_info[3])
        for author in authors:
            aut = author.strip()
            auth_idl = self.cursor.execute(AUTHOR_ID, (aut,)).fetchone()
            if not auth_idl:
                self.cursor.execute(INSERT_AUTHOR, (aut,))
                self.conn.commit()
                auth_id = self.cursor.lastrowid
            else:
                auth_id = auth_idl[0]
                check = self.cursor.execute(FILE_AUTHOR, (file_id, auth_id))
                if check:
                    return
            self.cursor.execute(INSERT_FILEAUTHOR, (file_id, auth_id))
            self.conn.commit()

    def _insert_comment(self, _file):
        if len(self.file_info) > 2:
            try:
                pages = self.file_info[2]
                issue_date = self.file_info[4]
                book_title = self.file_info[5]
            except IndexError:
                logger.exception(' | '.join(('IndexError ', len(self.file_info))))
            else:
                self.cursor.execute(INSERT_COMMENT, (book_title, ''))
                self.conn.commit()
                comm_id = self.cursor.lastrowid
        else:
            comm_id = _file.comment_id
            pages = _file.pages
            issue_date = _file.issue_date
        return comm_id, pages, issue_date

    def _get_file_info(self, full_file_name):
        """
        Store info in self.file_info
        :param full_file_name:
        :return: None
        """
        self.file_info.clear()
        if os.path.isfile(full_file_name):
            st = os.stat(full_file_name)
            self.file_info.append(st.st_size)
            self.file_info.append(datetime.datetime.fromtimestamp(st.st_mtime).date().isoformat())
            if get_file_extension(full_file_name) == 'pdf':
                self._get_pdf_info(full_file_name)
        else:
            self.file_info.append('')
            self.file_info.append('')

    def _get_pdf_info(self, file_):
        with (open(file_, "rb")) as pdf_file:
            try:            # with + try -- it's overkill !!!  TODO
                fr = PdfFileReader(pdf_file, strict=False)
                fi = fr.documentInfo
                self.file_info.append(fr.getNumPages())
            except (ValueError, utils.PdfReadError, utils.PdfStreamError) as e:
                logger.exception(' | '.join(('--> _get_pdf_info, EXCEPTION', e)))
                self.file_info += [0, '', '', '']
            else:
                if fi is not None:
                    self.file_info.append(fi.getText('/Author'))
                    self.file_info.append(FileInfo._pdf_creation_date(fi))
                    self.file_info.append(fi.getText('/Title'))
                else:
                    self.file_info += ['', '', '']

    @staticmethod
    def _pdf_creation_date(fi):
        ww = fi.getText('/CreationDate')
        if ww:
            tt = '-'.join((ww[2:6], ww[6:8], ww[8:10]))
            try:
                datetime.datetime.strptime(tt, '%Y-%m-%d')
            except ValueError:
                tt = '0001-01-01'
            return tt
        return '0001-01-01'

    def _update_file(self, file_):
        """
        Update file info in tables Files, Authors and Comments
        :param file_: file_id, full_name, comment_id, issue_date, pages
        :return: None
        """
        self._get_file_info(file_.full_name)
        if file_.comment_id is None:
            comm_id, pages, issue_date = self._insert_comment(file_)
        else:
            comm_id = file_.comment_id
            pages = file_.pages
            issue_date = file_.issue_date if file_.issue_date else '0001-01-01'

        self.cursor.execute(UPDATE_FILE, {'comm_id': comm_id,
                                          'date': self.file_info[1],
                                          'page': pages,
                                          'size': self.file_info[0],
                                          'issue_date': issue_date,
                                          'file_id': file_.file_id})
        self.conn.commit()
        if len(self.file_info) > 3 and self.file_info[3]:
            self._insert_author(file_.file_id)

    def _update_files(self):
        logger.debug("_update_files <- start")
        db_file_info = namedtuple('db_file_info',
                                  'file_id full_name comment_id issue_date pages')
        # file_id: int, full_name: str, comment_id: int issue_date: date, pages: int

        # list of dir_id
        dir_ids = ','.join(self.upd_dirs)
        file_list = self.cursor.execute(FILES_IN_LOAD.format(dir_ids)).fetchall()
        # not iterate all rows in cursor - so used fetchall(), why ???
        for file_descr in file_list:
            file_name = os.path.join(file_descr[2], file_descr[1])
            file_ = db_file_info._make((file_descr[0], file_name) + file_descr[-3:])
            self._update_file(file_)

        logger.debug("_update_files <- finish")
