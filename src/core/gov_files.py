# gov_files.py

import os
import re
import sqlite3
import webbrowser
from collections import namedtuple

from PyQt5.QtCore import (Qt, QModelIndex, QItemSelectionModel,
                          QSettings, QDate, QDateTime, QItemSelection, QVariant,
                          QThreadPool, QPersistentModelIndex,
                          )
from PyQt5.QtWidgets import (QInputDialog, QLineEdit, QFileDialog,
                             QLabel, QFontDialog, QApplication, QAbstractItemView,
                             )
from PyQt5.QtGui import QFontDatabase

from .main_window import AppWindow
from .table_model import TableModel, ProxyModel2
from .tree_model import TreeModel
from .edit_tree_model import EditTreeModel, EditTreeItem
from .file_info import FileInfo, LoadFiles
from .helper import Fields, open_file_or_folder
from .load_db_data import LoadDBData
from .input_date import DateInputDialog
from .item_edit import ItemEdit
from .sel_opt import SelOpt
from .set_fields import SetFields
import src.core.utilities as ut

DefFont = QFontDatabase.systemFont(QFontDatabase.GeneralFont)
FileData = namedtuple("FileData", "file_id dir_id comment_id ext_id source")
# file_id: int, dir_id: int, comment_id: int, ext_id: int,
# source: int - one of the FOLDER, VIRTUAL, ADVANCE constants
FOLDER, VIRTUAL, ADVANCE = (1, 2, 4)


def insert_virt_dirs(dir_tree: list):
    virt_dirs = ut.select_other("VIRT_DIRS", ())
    id_list = [x[1] for x in dir_tree]

    for vd in virt_dirs:
        if vd[-1] == 1:
            vd = (*vd[:-1], 2)
        try:
            idx = id_list.index(vd[2])
            dir_tree.insert(idx, (os.path.split(vd[0])[1], *vd[1:], vd[0]))
            id_list.insert(idx, vd[1])
        except ValueError:
            print('gov_files.insert_virt_dirs: ValueError')


def persistent_row_indexes(view_: QAbstractItemView) -> list:
    """
    :@param view_:
    :@return: list of row indexes (selected)
    """
    indexes = view_.selectionModel().selectedRows()
    model_ = view_.model()
    list_rows = []
    for idx_ in indexes:
        list_rows.append(QPersistentModelIndex(model_.mapToSource(idx_)))
    return list_rows


def selected_db_indexes(view: QAbstractItemView) -> list:
    """
    The DB indexes are stored in the model_ data under Qt.UserRole
    Method retrives these indexes for selected items
    :@param view: QAbstractItemView, Qt.UserRole should be implemented as need
    :@return: list of indexes. Type - int
    """
    sel_model_idx = view.selectedIndexes()
    model = view.model()
    ids = []
    for idx in sel_model_idx:
        ids.append(model.data(idx, Qt.UserRole)[0])
    return ids


def del_add_items(new_list: list, old_list: list) -> (list, list):
    """
    Creates two list
    1) items from old_list but not in new_list
    2) items from new_list but not in old_list
    :@param new_list: type of items?
    :@param old_list: type of items?
    :@return: to_del_ids: list, to_add: list
    """
    old_words_set = set([item[0] for item in old_list])
    new_words_set = set(new_list)

    to_del = old_words_set.difference(new_words_set)
    to_del_ids = [item[1] for item in old_list if item[0] in to_del]

    old_words_set.add("")
    to_add = new_words_set.difference(old_words_set)

    return to_del_ids, list(to_add)


def save_path(index: QModelIndex) -> None:
    path = full_tree_path(index)

    settings = QSettings()
    settings.setValue("TREE_SEL_IDX", QVariant(path))


def full_tree_path(index: QModelIndex) -> list:
    idx = index
    path = []
    while idx.isValid():
        path.append(idx.row())
        idx = idx.parent()
    path.reverse()
    return path


def get_dirs():
    """
    Returns directory tree
    :return: list of tuples (Dir name, DirID, ParentID, FolderType, Full path of dir)
    """
    dirs = []
    dir_tree = ut.dir_tree_select(dir_id=0, level=0)

    for rr in dir_tree:
        dirs.append((os.path.split(rr[0])[1], *rr[1: len(rr) - 1], rr[0]))
    return dirs


def _exist_in_virt_dirs(dir_id: int, parent_id: int):
    return ut.select_other("EXIST_IN_VIRT_DIRS", (dir_id, parent_id)).fetchone()


def collect_all_ext(ids):
    all_id = set()
    for id_ in ids:
        if id_ < ut.EXT_ID_INCREMENT:
            curr = ut.select_other("EXT_ID_IN_GROUP", (id_,))
            for idd in curr:
                all_id.add(idd[0])
        else:
            all_id.add(id_ - ut.EXT_ID_INCREMENT)
    return all_id


def _delete_from_db(file_ids):
    ut.delete_other("VIRT_ALL", (file_ids[0],))
    ut.delete_other("AUTHOR_FILE_BY_FILE", (file_ids[0],))
    ut.delete_other("TAG_FILE_BY_FILE", (file_ids[0],))
    ut.delete_other("FILE", (file_ids[0],))
    # when file for this comment not exist in DB
    ut.delete_other2("COMMENT", (file_ids[2], file_ids[2]))


class FilesCrt:
    def __init__(self, app_window: AppWindow):
        self.app_window = app_window
        self.ui = self.app_window.ui
        self.app_font = None

        self.status_label = QLabel(app_window)
        self.ui.statusbar.addPermanentWidget(self.status_label)

        self.fields: Fields = Fields._make(((), (), ()))
        self.thread_pool = QThreadPool()
        self.file_list_source = FOLDER
        self._opt = SelOpt(self)
        self._restore_font()
        self._restore_fields()

    def _add_group_folder(self):
        """
        group of real folders - organise for better vision
        """
        folder_name = "<Group name>"
        new_name, ok_ = QInputDialog.getText(
            self.ui.dirTree, "Input folder name", "", QLineEdit.Normal, folder_name
        )
        if ok_:
            curr_idx = self.ui.dirTree.currentIndex()
            idx_list = self._selected_dirs(curr_idx)

            d_dat = self.ui.dirTree.model().data(curr_idx, Qt.UserRole)
            new_parent = (new_name, d_dat.parent_id, 3)
            new_parent_id = ut.insert_other("DIR", new_parent)
            self.ui.dirTree.model().create_new_parent(
                curr_idx, (new_parent_id, *new_parent), idx_list
            )

    def _selected_dirs(self, curr_idx):
        if not self.ui.dirTree.selectionModel().isSelected(curr_idx):
            self.ui.dirTree.selectionModel().select(
                curr_idx, QItemSelectionModel.SelectCurrent
            )
        selected_indexes = self.ui.dirTree.selectionModel().selectedRows()

        idx_list = []
        for idx in selected_indexes:
            idx_list.append(QPersistentModelIndex(idx))

        return idx_list

    def _create_virtual_child(self):
        folder_name = "New folder"
        new_name, ok_ = QInputDialog.getText(
            self.ui.dirTree, "Input folder name", "", QLineEdit.Normal, folder_name
        )
        if ok_:
            cur_idx = self.ui.dirTree.currentIndex()
            self._create_virtual_folder(new_name, cur_idx)

    def _create_virtual(self):
        folder_name = "New folder"
        new_name, ok_ = QInputDialog.getText(
            self.ui.dirTree, "Input folder name", "", QLineEdit.Normal, folder_name
        )
        if ok_:
            cur_idx = self.ui.dirTree.currentIndex()
            parent = self.ui.dirTree.model().parent(cur_idx)
            self._create_virtual_folder(new_name, parent)

    def _create_virtual_folder(self, folder_name, parent):
        if parent.isValid():
            parent_id = self.ui.dirTree.model().data(parent, role=Qt.UserRole).dir_id
        else:
            parent_id = 0
        dir_id = ut.insert_other("DIR", (folder_name, parent_id, 2))

        item = EditTreeItem(
            (folder_name,), (dir_id, parent_id, 2, folder_name))

        self.ui.dirTree.model().append_child(item, parent)

    def _delete_virtual(self):
        cur_idx = self.ui.dirTree.currentIndex()
        parent = self.ui.dirTree.model().parent(cur_idx)
        parent_id = (
            0
            if not parent.isValid()
            else self.ui.dirTree.model().data(parent, role=Qt.UserRole).dir_id
        )
        dir_id = self.ui.dirTree.model().data(cur_idx, role=Qt.UserRole).dir_id

        if _exist_in_virt_dirs(dir_id, parent_id):
            ut.delete_other("FROM_VIRT_DIRS", (parent_id, dir_id))
            self.ui.dirTree.model().remove_row(cur_idx)
        else:
            ut.delete_other("VIRT_FROM_DIRS", (dir_id,))
            ut.delete_other("VIRT_DIR_ID", (dir_id,))
            self.ui.dirTree.model().remove_all_copies(cur_idx)

    def _rename_folder(self):
        cur_idx = self.ui.dirTree.currentIndex()
        u_data = self.ui.dirTree.model().data(cur_idx, role=Qt.UserRole)
        folder_name = u_data.path
        new_name, ok_ = QInputDialog.getText(
            self.ui.dirTree, "Input new folder name", "", QLineEdit.Normal, folder_name
        )
        if ok_:
            ut.update_other("DIR_NAME", (new_name, u_data.dir_id))
            self.ui.dirTree.model().update_folder_name(cur_idx, new_name)

    def _selected_files(self):
        """
        used while copying, moving, deleting files
        :return:  tuple of (model index, full path, user data, file name)
                  where user data = (FileID, DirID, CommentID, ExtID, Source)
                  if Source > 0 then it is dir_id of virtual folder,
                  if Source ==0 then it is real folder,
                  if Source == -1 then it is advanced selection
        """
        file_ = namedtuple("file_", "index name_with_path user_data name")
        # index: int, name_with_path: str, user_data: tuple, name: str
        files = []
        indexes = persistent_row_indexes(self.ui.filesList)
        model = self.ui.filesList.model().sourceModel()
        for idx in indexes:
            if idx.column() == 0:
                file_name = model.data(idx)
                u_dat = model.data(idx, Qt.UserRole)
                file_path = ut.select_other("PATH", (u_dat.dir_id,)).fetchone()
                file_data = file_._make(
                    (idx, os.path.join(file_path[0], file_name), 
                     u_dat, file_name)
                )
                files.append(file_data)
        return files

    def _move_file_to(self, dir_id, to_path, file):
        import shutil

        try:
            shutil.move(file[1], to_path)
            ut.update_other("FILE_DIR_ID", (dir_id, file[2][0]))
            self.ui.filesList.model().sourceModel().delete_row(file[0])
        except IOError:
            self.app_window.show_message(
                'Can\'t move file "{}" into folder "{}"'.format(
                    file[3], to_path), 5000
            )

    def _copy_file_to(self, dir_id, to_path, file_):
        # file_ = namedtuple('file_', 'index name_with_path user_data name')
        import shutil

        try:
            shutil.copy2(file_.name_with_path, to_path)
            file_id = ut.select_other2(
                "FILE_IN_DIR", (dir_id, file_.name)).fetchone()
            if file_id:
                new_file_id = file_id[0]
            else:
                new_file_id = ut.insert_other2(
                    "COPY_FILE", (dir_id, file_.user_data[0])
                )

            ut.insert_other2("COPY_TAGS", (new_file_id, file_.user_data[0]))
            ut.insert_other2("COPY_AUTHORS", (new_file_id, file_.user_data[0]))
        except IOError:
            self.app_window.show_message(
                'Can\'t copy file "{}" into folder "{}"'.format(
                    file_[3], to_path), 5000
            )

    def _get_dir_id(self, to_path: str) -> (int, bool):
        """
        copy files to to_path directory
        :@param to_path:  target directory
        :@return: (DirId: int, isNewDirID: bool) ID of target directory
        """
        ld = LoadDBData(ut.DB_setting["Conn"])
        return ld.insert_dir(to_path)

    def _copy_files(self):
        """
        _copy_files - select directory to copy selected files
        and copy them to this directory
        """
        to_path = QFileDialog().getExistingDirectory(
            self.ui.filesList, "Select the folder to copy"
        )
        if to_path:
            if self.copy_files_to(to_path):
                self._populate_directory_tree()

    def copy_files_to(self, to_path: str) -> bool:
        dir_id, is_new_dir_id = self._get_dir_id(to_path)
        if dir_id > 0:
            selected_files = self._selected_files()
            for file in selected_files:
                self._copy_file_to(dir_id, to_path, file)
        return is_new_dir_id

    def _remove_file(self, file_):
        try:
            os.remove(file_[1])
            _delete_from_db(file_[2])
            self.ui.filesList.model().sourceModel().delete_row(file_[0])
        except FileNotFoundError:
            self.app_window.show_message(
                'File "{}" not found'.format(file_[1]))

    def _remove_files(self):
        selected_files = self._selected_files()
        for file in selected_files:
            self._remove_file(file)

    def _move_files(self):
        to_path = QFileDialog().getExistingDirectory(
            self.ui.filesList, "Select the folder to move"
        )
        if to_path:
            if self.move_files_to(to_path):
                self._populate_directory_tree()

    def move_files_to(self, to_path):
        dir_id, is_new_id = self._get_dir_id(to_path)
        if dir_id > 0:
            selected_files = self._selected_files()
            for file in selected_files:
                self._move_file_to(dir_id, to_path, file)
        return is_new_id

    def _rename_file(self):
        path, file_name, file_id, idx = self._file_path()
        new_name, ok_ = QInputDialog.getText(
            self.ui.filesList, "Input new name", "", QLineEdit.Normal, file_name
        )
        if ok_:
            self.ui.filesList.model().sourceModel().update(idx, new_name)
            os.rename(os.path.join(path, file_name),
                      os.path.join(path, new_name))
            ut.update_other("FILE_NAME", (new_name, file_id))

    def _restore_fields(self):
        settings = QSettings()
        self.fields = Fields._make(
            settings.value(
                "FIELDS",
                (
                    ["FileName", "FileDate", "Pages", "Size"],
                    ["File", "Date", "Pages", "Size"],
                    [0, 1, 2, 3],
                ),
            )
        )
        self._set_file_model()
        self._resize_columns()

    def _set_fields(self):
        curr_dir_idx = self.ui.dirTree.currentIndex()
        set_fields_dialog = SetFields(self.fields)
        if set_fields_dialog.exec_():
            self.fields = set_fields_dialog.get_result()
            settings = QSettings()
            settings.setValue("FIELDS", self.fields)
            # TODO move to another method to not use dirTree here
            self._restore_file_list(curr_dir_idx)
            self._resize_columns()

    def _tag_rename(self):
        idx = self.ui.tagsList.currentIndex()
        if idx.isValid():
            tag = self.ui.tagsList.model().data(idx, role=Qt.DisplayRole)
            id_ = self.ui.tagsList.model().data(idx, role=Qt.UserRole)
            tag, ok = QInputDialog.getText(
                self.ui.extList, "Input new name", "", QLineEdit.Normal, tag
            )
            if ok:
                ut.update_other("UPDATE_TAG", (tag, id_))
                self.ui.tagsList.model().update(idx, tag, Qt.DisplayRole)

    def _copy_file_name(self):
        idx = self.ui.filesList.currentIndex()
        if idx.column() == 0:
            txt = self.ui.filesList.model().data(idx, role=Qt.DisplayRole)
            QApplication.clipboard().setText(txt)

    def _copy_path(self):
        path, *_ = self._file_path()
        QApplication.clipboard().setText(path)

    def on_change_data(self, action: str) -> None:
        """
        run methods for change_data_signal
        :@param action: string to select handle method
        :@return: None
        """
        data_methods = {
            "Author Remove unused": self._author_remove_unused,
            "change_font": self._ask_for_change_font,
            "Dirs Create virtual folder as child": self._create_virtual_child,
            "Dirs Create virtual folder": self._create_virtual,
            "Dirs Delete folder": self._delete_virtual,
            "Dirs Remove empty folders": self._del_empty_dirs,
            "Dirs Group": self._add_group_folder,
            "Dirs Rename folder": self._rename_folder,
            "Dirs Rescan dir": self._rescan_dir,
            "Edit authors": self._edit_authors,
            "Edit comment": self._edit_comment,
            "Edit key words": self._edit_key_words,
            "Edit title": self._edit_title,
            "Ext Create group": self._ext_create_group,
            "Ext Delete all files with current extension": self._ext_delete_current,
            "Ext Remove unused": self._ext_remove_unused,
            "File Copy file name": self._copy_file_name,
            "File Copy file(s)": self._copy_files,
            "File Copy path": self._copy_path,
            "File Delete row": self._delete_files,
            "File Delete file(s)": self._remove_files,
            "File Move file(s)": self._move_files,
            "File Open folder": self._open_folder,
            "File Open": self._open_file,
            "File Rename file": self._rename_file,
            "File_doubleClicked": self._double_click_file,
            "Resize columns": self._resize_columns,
            "Select files": self._list_selected_files,
            "Selection options": self._selection_options,
            "Set fields": self._set_fields,
            "Tag Remove unused": self._tag_remove_unused,
            "Tag Rename": self._tag_rename,
            "Tag Scan in names": self._scan_for_tags,
            "start app": self._populate_all_widgets,
        }

        try:
            act = action.split("/")
            if len(act) == 1:
                data_methods[action]()
            else:
                data_methods[act[0]](act[1:])
        except KeyError:
            self.app_window.show_message(
                f'Action "{action}" not implemented', 5000
            )

    def _scan_for_tags(self):
        """
        Tags are searched if files with selected EXTENSIONS
        :return:
        """
        self.app_window.show_message("Scan in files with selected extensions")
        ext_idx = selected_db_indexes(self.ui.extList)
        all_id = collect_all_ext(ext_idx)

        sel_tag = self.get_selected_tags()
        for tag in sel_tag:
            files = ut.select_other2(
                "FILE_INFO", (",".join([str(i) for i in all_id]), tag[1])
            ).fetchall()
            for file in files:
                if re.search(tag[0], file[0], re.IGNORECASE):
                    try:
                        ut.insert_other("TAG_FILE", (tag[1], file[1]))
                    except sqlite3.IntegrityError:
                        print('FilesCtr._scan_for_tags: sqlite3.IntegrityError')

    def get_selected_tags(self):
        idxs = self.ui.tagsList.selectedIndexes()
        t_ids = []
        tag_s = []
        rb = r"\b"
        if idxs:
            model = self.ui.tagsList.model()
            for i in idxs:
                t_ids.append(model.data(i, Qt.UserRole))
                tag_s.append(rb + model.data(i, Qt.DisplayRole) + rb)
            return list(zip(tag_s, t_ids))
        return []

    def _ask_for_change_font(self):
        self.app_font, ok_ = QFontDialog.getFont(
            self.ui.dirTree.font(), self.ui.dirTree
        )
        if ok_:
            self._change_font()
            settings = QSettings()
            settings.setValue("FONT", self.app_font)

    def _restore_font(self):
        settings = QSettings()
        self.app_font = settings.value("FONT", DefFont)
        if self.app_font:
            self._change_font()

    def _change_font(self):
        self.ui.dirTree.setFont(self.app_font)
        self.ui.extList.setFont(self.app_font)
        self.ui.filesList.setFont(self.app_font)
        self.ui.tagsList.setFont(self.app_font)
        self.ui.authorsList.setFont(self.app_font)
        self.ui.commentField.setFont(self.app_font)

    def _author_remove_unused(self):
        ut.delete_other("UNUSED_AUTHORS", ())
        self._populate_author_list()

    def _tag_remove_unused(self):
        ut.delete_other("UNUSED_TAGS", ())
        self._populate_tag_list()

    def _ext_remove_unused(self):
        ut.delete_other("UNUSED_EXT", ())
        ut.delete_other("UNUSED_EXT_GROUP", ())
        self._populate_ext_list()

    def _ext_delete_current(self):
        cur_idx = self.ui.extList.currentIndex()
        ext_id = self.ui.extList.model().data(cur_idx, role=Qt.UserRole)[0]
        if ext_id > ut.EXT_ID_INCREMENT:
            ut.delete_other("FILE_BY_EXT", (ext_id - ut.EXT_ID_INCREMENT,))
            ut.delete_other("EXT", (ext_id - ut.EXT_ID_INCREMENT,))
            self._populate_ext_list()

    def _ext_create_group(self) -> None:
        ids = selected_db_indexes(self.ui.extList)
        if ids:
            group_name, ok_pressed = QInputDialog.getText(
                self.ui.extList, "Input group name", "", QLineEdit.Normal, ""
            )
            if ok_pressed:
                gr_id = ut.insert_other("EXT_GROUP", (group_name,))
                all_id = collect_all_ext(ids)

                for id_ in all_id:
                    ut.update_other("EXT_GROUP", (gr_id, id_))

                ut.delete_other("UNUSED_EXT_GROUP", ())

                self._populate_ext_list()

    def _dir_update(self, updated_dirs) -> None:
        self._populate_directory_tree()
        self._populate_ext_list()

        files_ = FileInfo(
            updated_dirs, ut.create_connection(ut.DB_setting["Path"]))
        files_.signal.finished.connect(self._dir_update_finish)
        self.thread_pool.start(files_)

    def _dir_update_finish(self):
        self.app_window.show_message("Updating of files is finished.", 5000)

    def _populate_virtual(self, dir_id) -> None:
        """
        List of files from virtual folder
        :@param dir_id:
        :@return: None
        """
        self.file_list_source = VIRTUAL
        settings = QSettings()
        settings.setValue("FILE_LIST_SOURCE", self.file_list_source)
        res = self.files_virtual_folder(dir_id)

        if not res:
            self.status_label.setText("No files in folder")

    def files_virtual_folder(self, dir_id):
        files = ut.select_other("FILES_VIRT", (dir_id,)).fetchall()

        if files:
            self.show_files(files, dir_id)
            return True
        return False

    def _selection_options(self) -> None:
        """
        Show files according optional conditions
        1) folder and nested sub-folders
        2) list of extensions
        3) list of tags (match all/mutch any)
        4) list of authors - match any
        5) date of "file modification" / "book issue" - after/before/between
        :return:
        """
        if self._opt.exec_():
            self._list_selected_files()

    def _list_selected_files(self) -> None:
        res = self._opt.get_result()
        curs = ut.advanced_selection(res)
        if curs:
            self.show_files(curs, -1)
            self.file_list_source = ADVANCE
            settings = QSettings()
            settings.setValue("FILE_LIST_SOURCE", self.file_list_source)
        else:
            self.app_window.show_message(
                "Nothing found. Change your choice.", 5000)

    def _delete_files(self) -> None:
        indexes = persistent_row_indexes(self.ui.filesList)
        model = self.ui.filesList.model().sourceModel()
        for f_idx in indexes:
            if f_idx.isValid():
                u_data = model.data(f_idx, Qt.UserRole)
                if u_data.source > 0:  # file is from virtual folder
                    ut.delete_other(
                        "FILE_VIRT", (u_data.source, u_data.file_id))
                elif u_data.source == 0:  # file is from real folder
                    _delete_from_db(u_data)
                else:  # -1   - advanced file list = do nothing
                    pass

                model.delete_row(f_idx)

    def _open_folder(self):
        path, *_ = self._file_path()
        open_file_or_folder("".join(("file://", path)))

    def _double_click_file(self):
        f_idx = self.ui.filesList.currentIndex()
        column_head = self.ui.filesList.model().headerData(
            f_idx.column(), Qt.Horizontal
        )
        if column_head == "File":
            self._open_file()
        elif column_head == "Pages":
            pages = self.ui.filesList.model().data(f_idx)
            file_id = self.ui.filesList.model().data(f_idx, role=Qt.UserRole).file_id
            self._update_pages(f_idx, file_id, pages)
        elif column_head == "Issued":
            issue_date = self.ui.filesList.model().data(f_idx)
            file_id = self.ui.filesList.model().data(f_idx, role=Qt.UserRole).file_id
            self._update_issue_date(f_idx, file_id, issue_date)

    def _update_issue_date(self, f_idx, file_id, issue_date):
        try:
            zz = [int(t) for t in issue_date.split("-")]
            issue_date = QDate(*zz)
        except (TypeError, ValueError):
            issue_date = QDate.currentDate()

        _date, ok_ = DateInputDialog.getDate(issue_date)
        if ok_:
            ut.update_other("ISSUE_DATE", (_date, file_id))
            self.ui.filesList.model().update(f_idx, _date)

    def _update_pages(self, f_idx, file_id, page_number):
        if not page_number:
            page_number = 0
        pages, ok_pressed = QInputDialog.getInt(
            self.ui.extList, "Input page number", "", int(page_number)
        )
        if ok_pressed:
            ut.update_other("PAGES", (pages, file_id))
            self.ui.filesList.model().update(f_idx, pages)

    def _open_file(self):
        path, file_name, file_id, idx = self._file_path()
        full_file_name = os.path.join(path, file_name)
        if os.path.isfile(full_file_name):
            try:
                if open_file_or_folder(full_file_name):
                    self.update_opened(idx, file_id)
            except OSError:
                self.app_window.show_message(
                    f'Can\'t open file "{full_file_name}"')
        else:
            self.app_window.show_message(
                f'Can\'t find file "{full_file_name}"')

    def update_opened(self, idx, file_id):
        cur_date = QDateTime.currentDateTime().toString(Qt.ISODate)[:16]
        cur_date = cur_date.replace("T", " ")
        ut.update_other("OPEN_DATE", (cur_date, file_id))
        model = self.ui.filesList.model()
        heads = model.get_headers()
        if "Opened" in heads:
            idx_s = model.sourceModel().createIndex(idx.row(), heads.index("Opened"))
            model.sourceModel().update(idx_s, cur_date)

    def _file_path(self) -> (str, str, int, int):
        """
        Extract current file's path saved in model's User data
        :return:  path, file_name, file_id - DB id, file_idx - model index
        """
        f_idx = self.ui.filesList.currentIndex()
        if f_idx.isValid():
            model = self.ui.filesList.model()
            f_idx = model.mapToSource(f_idx)
            if not f_idx.column() == 0:
                f_idx = model.sourceModel().createIndex(f_idx.row(), 0)
            file_name = model.sourceModel().data(f_idx)
            file_id, dir_id, *_ = model.sourceModel().data(f_idx, role=Qt.UserRole)
            path = ut.select_other("PATH", (dir_id,)).fetchone()
            return path[0], file_name, file_id, f_idx
        return "", "", 0, f_idx

    def _edit_key_words(self):
        curr_idx = self.ui.filesList.currentIndex()
        u_data = self.ui.filesList.model().data(curr_idx, Qt.UserRole)

        titles = ("Enter new tags", "Select tags from list",
                  "Apply key words / tags")
        tag_list = ut.select_other("TAGS").fetchall()
        sel_tags = ut.select_other("FILE_TAGS", (u_data.file_id,)).fetchall()

        edit_tags = ItemEdit(
            titles, [tag[0] for tag in tag_list], [tag[0] for tag in sel_tags], re_=True
        )

        if edit_tags.exec_():
            res = edit_tags.get_result()

            to_del, to_add = del_add_items(res, sel_tags)

            self._del_item_links(
                to_del, file_id=u_data.file_id, sqls=(
                    "TAG_FILE", "TAG_FILES", "TAG")
            )
            self._add_item_links(
                to_add,
                file_id=u_data.file_id,
                sqls=("TAGS_BY_NAME", "TAGS", "TAG_FILE"),
            )

            self._populate_tag_list()
            self._populate_comment_field(u_data, edit=True)

    def _del_item_links(self, items2del, file_id, sqls):
        for item in items2del:
            ut.delete_other(sqls[0], (item, file_id))
            res = ut.select_other(sqls[1], (item,)).fetchone()
            if not res:
                ut.delete_other(sqls[2], (item,))

    def _add_item_links(self, items2add, file_id, sqls):
        add_ids = ut.select_other2(
            sqls[0], ('","'.join(items2add),)).fetchall()
        sel_items = [item[0] for item in add_ids]
        not_in_ids = [item for item in items2add if not item in sel_items]

        for item in not_in_ids:
            item_id = ut.insert_other(sqls[1], (item,))
            ut.insert_other(sqls[2], (item_id, file_id))

        for item in add_ids:
            ut.insert_other(sqls[2], (item[1], file_id))

    def _edit_authors(self):
        """
        model().data(curr_idx, Qt.UserRole) = (FileID, DirID, CommentID, ExtID)
        """
        curr_idx = self.ui.filesList.currentIndex()
        u_data = self.ui.filesList.model().data(curr_idx, Qt.UserRole)

        titles = (
            "Enter authors separated by commas",
            "Select authors from list",
            "Apply authors",
        )
        authors = ut.select_other("AUTHORS").fetchall()
        sel_authors = ut.select_other(
            "FILE_AUTHORS", (u_data.file_id,)).fetchall()

        edit_authors = ItemEdit(
            titles,
            [tag[0] for tag in authors],
            [tag[0] for tag in sel_authors]
        )

        if edit_authors.exec_():
            res = edit_authors.get_result()

            to_del, to_add = del_add_items(res, sel_authors)

            self._del_item_links(
                to_del,
                file_id=u_data.file_id,
                sqls=("AUTHOR_FILE", "AUTHOR_FILES", "AUTHOR"),
            )
            self._add_item_links(
                to_add,
                file_id=u_data.file_id,
                sqls=("AUTHORS_BY_NAME", "AUTHORS", "AUTHOR_FILE"),
            )

            self._populate_author_list()
            self._populate_comment_field(u_data, edit=True)

    def _check_existence(self):
        """
        Check if comment record already created for file
        Note: user_data = (FileID, DirID, CommentID, ExtID, Source)
        :return: (file_id, dir_id, comment_id, comment, book_title)
        """
        file_comment = namedtuple(
            "file_comment", "file_id dir_id comment_id comment book_title"
        )
        curr_idx = self.ui.filesList.currentIndex()
        user_data = self.ui.filesList.model().data(curr_idx, Qt.UserRole)
        comment = ut.select_other(
            "FILE_COMMENT", (user_data.comment_id,)).fetchone()
        res = file_comment._make(
            user_data[:3] + (comment if comment else ("", "")))
        if not comment:
            comment = ("", "")
            comment_id = ut.insert_other("COMMENT", comment)
            ut.update_other("FILE_COMMENT", (comment_id, res.file_id))
            user_data = user_data._replace(comment_id=comment_id)
            self.ui.filesList.model().update(curr_idx, user_data, Qt.UserRole)
            res = res._replace(
                comment_id=comment_id, comment=comment[0], book_title=comment[1]
            )
        return res

    def get_list_source(self, curr_dir_idx):
        if not curr_dir_idx.isValid():
            curr_dir_idx = self.ui.dirTree.model().index(0, 0)
        if ut.DB_setting["SameDB"]:  
            # TODO save/restore setting within DB, then if won't need
            settings = QSettings()
            self.file_list_source = settings.value("FILE_LIST_SOURCE", FOLDER)
            row = settings.value("FILE_IDX", 0)
        else:
            if self.ui.dirTree.model().is_virtual(curr_dir_idx):
                self.file_list_source = VIRTUAL
            else:
                self.file_list_source = FOLDER
            row = 0
        return curr_dir_idx, row

    def _restore_file_list(self, curr_dir_idx):
        curr_dir_idx, row = self.get_list_source(curr_dir_idx)
        dir_idx = self.ui.dirTree.model().data(curr_dir_idx, Qt.UserRole)

        if dir_idx is None:  # clear file list when creating new DB
            self._set_file_model()
            return
        if self.file_list_source == VIRTUAL:
            self._populate_virtual(dir_idx.dir_id)
        elif self.file_list_source == FOLDER:
            self._populate_file_list(dir_idx)
        else:  # ADVANCE
            self._list_selected_files()

        if self.ui.filesList.model().rowCount() == 0:
            idx = QModelIndex()
        else:
            idx = self.ui.filesList.model().index(row, 0)

        if idx.isValid():
            self.ui.filesList.setCurrentIndex(idx)
            self.ui.filesList.selectionModel().select(idx, QItemSelectionModel.Select)

    def _edit_title(self):
        checked = self._check_existence()
        data_, ok_pressed = QInputDialog.getText(
            self.ui.extList,
            "Input book title",
            "",
            QLineEdit.Normal,
            getattr(checked, "book_title"),
        )
        if ok_pressed:
            ut.update_other("BOOK_TITLE", (data_, checked.comment_id))
            self._populate_comment_field(checked, edit=True)

    def _edit_comment(self):
        # self._edit_comment_item(('COMMENT', 'Input comment'), 'comment')
        #    _edit_comment_item(self, to_update, item_no):
        checked = self._check_existence()
        data_, ok_pressed = QInputDialog.getMultiLineText(
            self.ui.extList, "Input comment", "", getattr(checked, "comment")
        )
        if ok_pressed:
            ut.update_other("COMMENT", (data_, checked.comment_id))
            self._populate_comment_field(checked, edit=True)

    def _populate_ext_list(self):
        ext_list = ut.select_other("EXT")
        model = TreeModel()
        model.set_model_data(ext_list)
        model.setHeaderData(0, Qt.Horizontal, "Extensions")
        self.ui.extList.setModel(model)
        self.ui.extList.selectionModel().selectionChanged.connect(self._ext_sel_changed)

    def _ext_sel_changed(self, selected: QItemSelection, deselected: QItemSelection):
        """
        Selection changed for view.extList, save new selection
        :@param selected: QItemSelection
        :@param deselected: QItemSelection
        :@return: None
        """
        model = self.ui.extList.model()
        for id_ in selected.indexes():
            if model.rowCount(id_) > 0:
                self.ui.extList.setExpanded(id_, True)
                sel = QItemSelection(
                    model.index(0, 0, id_),
                    model.index(
                        model.rowCount(id_) -
                        1, model.columnCount(id_) - 1, id_
                    ),
                )
                self.ui.extList.selectionModel().select(sel, QItemSelectionModel.Select)

        for id_ in deselected.indexes():
            if id_.parent().isValid():
                self.ui.extList.selectionModel().select(
                    id_.parent(), QItemSelectionModel.Deselect
                )

        self._save_ext_selection()

    def _save_ext_selection(self):
        idxs = self.ui.extList.selectedIndexes()
        sel = []
        for ss in idxs:
            sel.append((ss.row(), ss.parent().row()))

        settings = QSettings()
        settings.setValue("EXT_SEL_LIST", sel)

    def _populate_tag_list(self):
        tag_list = ut.select_other("TAGS")
        model = TableModel()
        model.setHeaderData(0, Qt.Horizontal, ("Tags",))
        for tag, id_ in tag_list:
            model.append_row(tag, id_)
        self.ui.tagsList.setModel(model)
        self.ui.tagsList.selectionModel().selectionChanged.connect(
            self._tag_sel_changed
        )

    def _tag_sel_changed(self):
        idxs = self.ui.tagsList.selectedIndexes()
        sel = []
        for ss in idxs:
            sel.append((ss.row(), ss.parent().row()))

        settings = QSettings()
        settings.setValue("TAG_SEL_LIST", sel)

    def _restore_tag_selection(self):
        if ut.DB_setting["SameDB"]:  
            # TODO save/restore setting within DB, then if won't need
            settings = QSettings()
            sel = settings.value("TAG_SEL_LIST", [])
            model = self.ui.tagsList.model()
            for ss in sel:
                idx = model.index(ss[0], 0, QModelIndex())
                self.ui.tagsList.selectionModel().select(
                    idx, QItemSelectionModel.Select
                )

    def _populate_author_list(self):
        author_list = ut.select_other("AUTHORS")
        model = TableModel()
        model.setHeaderData(0, Qt.Horizontal, "Authors")
        for author, id_ in author_list:
            model.append_row(author, id_)
        self.ui.authorsList.setModel(model)
        self.ui.authorsList.selectionModel().selectionChanged.connect(
            self._author_sel_changed
        )

    def _author_sel_changed(self):
        idxs = self.ui.authorsList.selectedIndexes()
        sel = []
        for ss in idxs:
            sel.append((ss.row(), ss.parent().row()))

        settings = QSettings()
        settings.setValue("AUTHOR_SEL_LIST", sel)

    def _restore_author_selection(self):
        if ut.DB_setting["SameDB"]:  
            # TODO save/restore setting within DB, then if won't need
            settings = QSettings()
            sel = settings.value("AUTHOR_SEL_LIST", [])
            model = self.ui.authorsList.model()
            for ss in sel:
                idx = model.index(ss[0], 0, QModelIndex())
                self.ui.authorsList.selectionModel().select(
                    idx, QItemSelectionModel.Select
                )

    def _populate_file_list(self, dir_idx):
        """
        :@param dir_idx:
        :@return:
        """
        if dir_idx is None:  # no any dir in Dirs table
            return
        if dir_idx[-2] > 0:
            self._form_virtual_folder(dir_idx)
        else:
            self._from_real_folder(dir_idx)

    def _form_virtual_folder(self, dir_idx):
        self._populate_virtual(dir_idx[0])

    def _from_real_folder(self, dir_idx):
        self.file_list_source = FOLDER
        settings = QSettings()
        settings.setValue("FILE_LIST_SOURCE", self.file_list_source)
        if dir_idx:
            files = ut.select_other("FILES_CURR_DIR", (dir_idx[0],))
            self.show_files(files, 0)

            self.status_label.setText(
                "{} ({})".format(
                    dir_idx[-1], self.ui.filesList.model().rowCount(QModelIndex())
                )
            )
        else:
            self.status_label.setText("No data")

    def _set_file_model(self):
        model = TableModel()
        proxy_model = ProxyModel2()
        proxy_model.setSourceModel(model)
        model.setHeaderData(0, Qt.Horizontal, getattr(self.fields, "headers"))
        self.ui.filesList.setModel(proxy_model)
        return proxy_model

    def show_files(self, files, source):
        """
        populate file's model
        :@param files
        :@param source -  0 - if file from real folder,
                         -1 - if custom list of files
                         >0 - it is dir_id of virtual folder
        """
        idx = getattr(self.fields, "indexes")
        model = self._set_file_model()
        s_model = model.sourceModel()
        for ff in files:
            ff1 = [ff[i] for i in idx]
            s_model.append_row(tuple(ff1), FileData(*ff[-4:], source))

        self.ui.filesList.selectionModel().currentRowChanged.connect(
            self._cur_file_changed
        )
        index_ = model.index(0, 0)
        self.ui.filesList.setCurrentIndex(index_)
        self.ui.filesList.setFocus()

    def _cur_file_changed(self, curr_idx):
        """
        currentRowChanged in filesList
        :@param curr_idx:
        :@return:
        """
        settings = QSettings()
        settings.setValue("FILE_IDX", curr_idx.row())
        if curr_idx.isValid():
            data = self.ui.filesList.model().data(curr_idx, role=Qt.UserRole)
            self._populate_comment_field(data)

    def _populate_comment_field(self, user_data, edit=False):
        file_id = user_data.file_id
        comment_id = user_data.comment_id
        if file_id:
            tags = ut.select_other("FILE_TAGS", (file_id,)).fetchall()
            authors = ut.select_other("FILE_AUTHORS", (file_id,)).fetchall()

            if comment_id:
                comment = ut.select_other(
                    "FILE_COMMENT", (comment_id,)).fetchone()
            else:
                comment = ("", "")

            self.ui.commentField.setText(
                "".join(
                    (
                        '<html><body><p><a href="Edit key words">Key words</a>: {}</p>'.format(
                            ", ".join([tag[0] for tag in tags])
                        ),
                        '<p><a href="Edit authors">Authors</a>: {}</p>'.format(
                            ", ".join([author[0] for author in authors])
                        ),
                        '<p><a href="Edit title"4>Title</a>: {}</p>'.format(
                            comment[1]),
                        '<p><a href="Edit comment">Comment:</a> {}</p></body></html>'.format(
                            comment[0]
                        ),
                    )
                )
            )

            path = ut.select_other("PATH", (user_data.dir_id,)).fetchone()
            self.status_label.setText(path[0])

            if edit:
                self._update_comment_date(file_id)

    def _update_comment_date(self, file_id):
        ut.update_other("COMMENT_DATE", (file_id,))
        model = self.ui.filesList.model()
        heads = model.get_headers()
        if "Commented" in heads:
            idx = model.sourceModel().createIndex(
                self.ui.filesList.currentIndex().row(), heads.index("Commented")
            )
            cur_date = QDate.currentDate().toString(Qt.ISODate)
            model.update(idx, cur_date)

    def _populate_all_widgets(self):
        self.app_window.setWindowTitle(f"Current DB:{ut.DB_setting['Path']}")
        self._populate_ext_list()
        self._restore_ext_selection()
        self._populate_tag_list()
        self._restore_tag_selection()
        self._populate_author_list()
        self._restore_author_selection()
        self._populate_directory_tree()

    def _restore_ext_selection(self):
        if ut.DB_setting["SameDB"]:  
            # TODO save/restore setting within DB, then if won't need
            settings = QSettings()
            sel = settings.value("EXT_SEL_LIST", [])
            model = self.ui.extList.model()
            for ss in sel:
                if ss[1] == -1:
                    parent = QModelIndex()
                else:
                    parent = model.index(ss[1], 0)
                    self.ui.extList.setExpanded(parent, True)

                idx = model.index(ss[0], 0, parent)

                self.ui.extList.selectionModel().select(idx, QItemSelectionModel.Select)

    def _populate_directory_tree(self):
        """
        restore the state of dirs and file as were on close.
        When open another DB the current dir is the first dir
        and current file is first file in this dir.
        """
        dirs = get_dirs()
        insert_virt_dirs(dirs)

        model = EditTreeModel(parent=self)
        model.set_alt_font(self.app_font)

        model.set_model_data(dirs)

        model.setHeaderData(0, Qt.Horizontal, ("Directories",))
        self.ui.dirTree.setModel(model)

        self.ui.dirTree.selectionModel().currentRowChanged.connect(
            self._cur_dir_changed
        )
        cur_dir_idx = self._restore_path()

        self._restore_file_list(cur_dir_idx)

        self._resize_columns()

    def _cur_dir_changed(self, curr_idx):
        """
        currentRowChanged in dirTree
        :@param curr_idx:
        :@return: None
        """
        if curr_idx.isValid():
            save_path(curr_idx)
            dir_idx = self.ui.dirTree.model().data(curr_idx, Qt.UserRole)
            if self.ui.dirTree.model().is_virtual(curr_idx):
                self._populate_virtual(dir_idx.dir_id)
            else:
                self._populate_file_list(dir_idx)

    def _restore_path(self):
        """
        restore expand state and current index of dirTree
        :return: current index
        """
        model = self.ui.dirTree.model()
        parent = QModelIndex()
        if ut.DB_setting["SameDB"]:  
            # TODO save/restore setting within DB, then if won't need
            settings = QSettings()
            aux = settings.value("TREE_SEL_IDX", [0])
            for id_ in aux:
                if parent.isValid():
                    if not self.ui.dirTree.isExpanded(parent):
                        self.ui.dirTree.setExpanded(parent, True)
                idx = model.index(int(id_), 0, parent)
                self.ui.dirTree.setCurrentIndex(idx)
                parent = idx

        if parent.isValid():
            return parent

        idx = model.index(0, 0, QModelIndex())
        self.ui.dirTree.setCurrentIndex(idx)
        return idx

    def _del_empty_dirs(self):
        ut.delete_other("EMPTY_DIRS", ())
        self._populate_directory_tree()

    def _rescan_dir(self) -> None:
        """
        Rescan the selected dirs for files with given extensions
        Invoke dialog to input extensions
        if list of extensions empty it searches files without extension
        '*' means any extension
        @return: None
        """
        idx = self.ui.dirTree.currentIndex()
        dir_ = self.ui.dirTree.model().data(idx, Qt.UserRole)
        ext_: str = self._get_selected_ext()
        ext_item, ok_pressed = QInputDialog.getText(
            self.ui.extList,
            "Input extensions",
            "Input extensions (* - any)",
            QLineEdit.Normal,
            ext_,
        )
        if ok_pressed:
            self._load_files(dir_.path, ext_item.strip())

    def on_scan_files(self) -> None:
        """
        The purpose is to fill the data base with files by means of
        scanning the file system
        :return: None
        """
        path_, ext_ = self._scan_file_system()
        self._load_files(path_, ext_)

    def _load_files(self, path_: str, ext_):
        load_ = LoadFiles(
            path_, ext_, ut.create_connection(ut.DB_setting["Path"]))
        load_.signal.finished.connect(self._dir_update)
        self.thread_pool.start(load_)

    def _scan_file_system(self) -> (str, str):
        """
        Invoke dialog to enter extensions of searching files
        and root directory
        @return: root, ext;  ext is the list of extensions as comma separated string
                 if ext is empty it searches files without extension
                    ext contains '*' selects files with any extension
        """
        ext_: str = self._get_selected_ext()
        ext_, ok_pressed = QInputDialog.getText(
            self.ui.extList, "Input extensions", "", QLineEdit.Normal, ext_
        )
        if ok_pressed:
            root: str = QFileDialog().getExistingDirectory(
                self.ui.extList, "Select root folder"
            )
            if root:
                return root, ext_
        return "", ""  # not ok_pressed or root is empty

    def _get_selected_ext(self) -> str:
        idxs = self.ui.extList.selectedIndexes()
        res = set()
        if idxs:
            model = self.ui.extList.model()
            for i in idxs:
                tt = model.data(i, Qt.UserRole)
                if tt[0] > ut.EXT_ID_INCREMENT:
                    res.add(model.data(i, Qt.DisplayRole))
                else:              # group of extentions
                    ext_ = ut.select_other("EXT_IN_GROUP", (tt[0],)).fetchall()
                    res.update([ee[0] for ee in ext_])
            res = list(res)
            res.sort()
            return ", ".join(res)
        return ""

    def _resize_columns(self):
        w = self.ui.filesList.width() - 2
        widths = self._calc_columns_width()
        if len(widths) > 1:
            ww = w * 0.75
            sum_w = sum(widths)
            if ww > sum_w:
                widths[0] = w - sum_w
            else:
                widths[0] = w * 0.25
                for i in range(1, len(widths)):
                    widths[i] = ww / sum_w * widths[i]
            for k, width in enumerate(widths):
                self.ui.filesList.setColumnWidth(k, width)
        else:
            self.ui.filesList.setColumnWidth(0, w)

    def _calc_columns_width(self):
        width = [0]
        font_metrics = self.ui.filesList.fontMetrics()
        heads = self.ui.filesList.model().get_headers()
        if len(heads) > 1:
            for head in heads[1:]:
                ind = SetFields.Heads.index(head)
                width.append(font_metrics.boundingRect(
                    SetFields.Masks[ind]).width())
        return width
