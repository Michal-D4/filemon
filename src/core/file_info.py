# file_info.py

from collections import namedtuple
import datetime
from loguru import logger
from pathlib import Path
import re
import sqlite3

import PyPDF2
from PyQt5.QtCore import pyqtSignal, QObject, pyqtSlot, QRunnable

from src.core.load_db_data import LoadDBData

DETECT_TYPES = sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES

AUTHOR_ID = 'select AuthorID from Authors where Author = ?;'

INSERT_AUTHOR = 'insert into Authors (Author) values (?);'

FILE_AUTHOR_LINKED = 'select * from FileAuthor where FileID=? and AuthorID=?'

CREATE_FILE_AUTHOR_LINK = 'insert into FileAuthor (FileID, AuthorID) values (?, ?);'

SELECT_COMMENT = 'select BookTitle from Comments where CommentID=?;'

INSERT_COMMENT = 'insert into Comments (BookTitle, Comment) values (?, ?);'

FILES_TO_UPDATE = ('select f.FileID, f.FileName, d.Path, f.CommentID, '
                   'f.IssueDate, f.Pages from Files f, Dirs d '
                   'where f.DirID = d.DirID and d.DirID in ({});')

UPDATE_FILE = ('update Files set '
               'CommentID = :comm_id ,'
               'FileDate = :date ,'
               'Pages = :page, '
               'Size = :size, '
               'IssueDate = :issue_date '
               'where FileID = :file_id;')


def pdf_creation_date(ww):
    if ww:
        tt = '-'.join((ww[2:6], ww[6:8], ww[8:10]))
        try:
            datetime.datetime.strptime(tt, '%Y-%m-%d')
        except ValueError:
            tt = '0001-01-01'
        return tt
    return '0001-01-01'


def ext_translate(ext: str):
    """
    String of file extensions separated by comma
    converted into tuple of extensions without dot
    @param ext: string of file extensions
    @return: tuple of extensions
    """
    ext_ = tuple(x.strip('. ') for x in ext.split(','))
    return '*' if '*' in ext_ else ext_


class LFSignal(QObject):
    # LF - LoadFiles
    finished = pyqtSignal(object)


class FISignal(QObject):
    # FI - FileInfo
    finished = pyqtSignal()


class LoadFiles(QRunnable):
    """
    Load files with of extensions from list 'ext_' located under Path 'path_'
    Run in thread
    :param path_: dir location of collected files (and all subdirs)
    :param ext_: list of extensions
    :param db_name: full name of DB file where to save
    """

    def __init__(self, path_: str, ext_: str, conn: sqlite3.Connection):
        super(LoadFiles, self).__init__()
        logger.debug(' '.join((path_, '|', ext_, '|')))
        self.conn = conn
        self.path_ = path_
        self.ext_ = ext_translate(ext_)
        self.signal = LFSignal()   # send set of str(ID) of updated dirs

    @pyqtSlot()
    def run(self):
        """
        Load files using LoadDBData class
        """
        files = LoadDBData(self.conn)
        logger.debug(f' {self.path_} | {self.ext_}')
        files.load_data(self.path_, self.ext_)
        self.signal.finished.emit(files.get_updated_dirs())


class FileInfo(QRunnable):
    """
    Collect data about all files in the updated by LoadFiles dirs
    Run in thread
    :param updated_dirs: IDs of updated dirs
    :param db_name: full name of DB file
    """

    @pyqtSlot()
    def run(self):
        logger.debug('--> FileInfo.run')
        self.update_files()
        self.signal.finished.emit()

    def __init__(self, updated_dirs: set, conn: sqlite3.Connection):
        super(FileInfo, self).__init__()
        logger.debug('--> FileInfo.__init__')
        self.upd_dirs = updated_dirs
        self.conn = conn
        self.cursor = self.conn.cursor()
        self.file_info = []
        self.signal = FISignal()

    def insert_authors(self, file_id: int, authors):
        """
        Save authors name of pdf file
        """
        for author in authors:
            author = author.strip()
            author_id = self.insert_author(file_id, author)
            self.link_file_author(file_id, author_id)

    def insert_author(self, file_id: int, author: str):
        """
        Save author name of pdf file
        """
        auth_id = self.cursor.execute(AUTHOR_ID, (author,)).fetchone()
        if auth_id:
            return auth_id[0]
        self.cursor.execute(INSERT_AUTHOR, (author,))
        self.conn.commit()
        return self.cursor.lastrowid

    def link_file_author(self, file_id, author_id):
        if self.cursor.execute(FILE_AUTHOR_LINKED, (file_id, author_id)).fetchone():
            return
        self.cursor.execute(CREATE_FILE_AUTHOR_LINK, (file_id, author_id))
        self.conn.commit()

    def insert_comment(self, _file):
        if len(self.file_info) > 2:
            try:
                pages = self.file_info[2]
                issue_date = self.file_info[4]
                book_title = self.file_info[5]
            except IndexError:
                logger.exception(' IndexError: {len(self.file_info)}, must be >= 6')
            else:
                self.cursor.execute(INSERT_COMMENT, (book_title, ''))
                self.conn.commit()
                comm_id = self.cursor.lastrowid
        else:
            comm_id = _file.comment_id
            pages = _file.pages
            issue_date = _file.issue_date
        return comm_id, pages, issue_date

    def get_file_info(self, full_file_name):
        """
        Store info in self.file_info
        :param full_file_name:
        :return: None
        """
        self.file_info.clear()
        path_file = Path(full_file_name)
        if path_file.is_file():
            st = path_file.stat()
            self.file_info += [st.st_size,
                               datetime.datetime.fromtimestamp(st.st_mtime).date().isoformat()]
            if path_file.suffix == '.pdf':
                self.get_pdf_info(full_file_name)
        else:
            self.file_info += ['', '']

    def get_pdf_info(self, file_):
        with (open(file_, "rb")) as pdf_file:
            try:
                fr = PyPDF2.PdfFileReader(pdf_file, strict=False)
                fi = fr.documentInfo
                self.file_info.append(fr.getNumPages())
            except (ValueError, PyPDF2.utils.PdfReadError,
                    PyPDF2.utils.PdfStreamError) as e:
                logger.exception(e)
                self.file_info += [0, '', '', '']
            else:
                if fi is not None:
                    cr_date = pdf_creation_date(fi.getText('/CreationDate'))
                    self.file_info += [fi.getText('/Author'),
                                       cr_date,
                                       fi.getText('/Title')]
                else:
                    self.file_info += ['', '', '']

    def update_file(self, file_):
        """
        Update file info in tables Files, Authors and Comments
        :param file_: namedtuple: file_id, full_name, comment_id, issue_date, pages
        :return: None
        """
        self.get_file_info(file_.full_name)
        if file_.comment_id is None:
            comm_id, pages, issue_date = self.insert_comment(file_)
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
            authors = re.split(r',|;|&|\band\b', self.file_info[3])
            self.insert_authors(file_.file_id)

    def update_files(self):
        logger.debug("<- start")
        db_file_info = namedtuple('db_file_info',
                                  'file_id full_name comment_id issue_date pages')
        # file_id: int, full_name: str, comment_id: int issue_date: date, pages: int

        # list of dir_id
        dir_ids = ','.join(self.upd_dirs)
        file_list = self.cursor.execute(FILES_TO_UPDATE.format(dir_ids)).fetchall()
        # not iterate all rows in cursor - so used fetchall(), why ???
        for file_descr in file_list:
            file_name = Path(file_descr[2]).joinpath(file_descr[1])
            file_ = db_file_info._make((file_descr[0], file_name) + file_descr[-3:])
            self.update_file(file_)

        logger.debug("<- finish")
