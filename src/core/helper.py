# helper.py

from collections import namedtuple

from PyQt5.QtCore import Qt, QPersistentModelIndex, QModelIndex, QSettings, QVariant
from PyQt5.QtGui import QFontDatabase

# Shared things
# immutable
from PyQt5.QtWidgets import QAbstractItemView

EXT_ID_INCREMENT = 100000
Fields = namedtuple('Fields', 'fields headers indexes')
# fields: str  - tuple of fields (in table Files) to be displayed in the view filesList
# headers: str - tuple of headers in the view filesList
# indexes: int - order of fields

REAL_FOLDER, VIRTUAL_FOLDER, REAL_FILE, VIRTUAL_FILE = range(4)
MimeTypes = ["application/x-folder-list",
             "application/x-folder-list/virtual",
             "application/x-file-list",
             "application/x-file-list/virtual"]

DROP_NO_ACTION, DROP_COPY_FOLDER, DROP_MOVE_FOLDER, DROP_COPY_FILE, DROP_MOVE_FILE = (0, 1, 2, 4, 8)


# mutable
Shared = {'AppFont': QFontDatabase.systemFont(QFontDatabase.GeneralFont),
          'AppWindow': None,
          'Controller': None,
          'DB choice dialog': None,
          'DB connection': None,
          'DB utility': None}


def get_file_extension(file_name):
    if file_name.rfind('.') > 0:
        return str.lower(file_name.rpartition('.')[2])
    return ''

def show_message(message, time=3000):
    Shared['AppWindow'].ui.statusbar.showMessage(message, time)


def selected_db_indexes(view: QAbstractItemView) -> list:
    """
    The DB indexes are stored in the model_ data under Qt.UserRole
    Method retrives these indexes for selected items
    :param view: QAbstractItemView, Qt.UserRole should be implemented as need
    :return: list of indexes. Type - int
    """
    sel_model_idx = view.selectedIndexes()
    model = view.model()
    ids = []
    for idx in sel_model_idx:
        ids.append(model.data(idx, Qt.UserRole)[0])
    return ids


def finish_thread() -> None:
    show_message('Updating of files is finished', 5000)


def persistent_row_indexes(view_: QAbstractItemView) -> list:
    """

    :param view_:
    :return:
    """
    indexes = view_.selectionModel().selectedRows()
    model_ = view_.model()
    list_rows = []
    for idx_ in indexes:
        list_rows.append(QPersistentModelIndex(model_.mapToSource(idx_)))
    return list_rows


def del_add_items(new_list: list, old_list: list) -> (list, list):
    """
    Creates two list
    1) items from old_list but not in new_list
    2) items from new_list but not in old_list
    :param new_list: type of items?
    :param old_list: type of items?
    :return: to_del_ids: list, to_add: set
    """
    old_words_set = set([item[0] for item in old_list])
    new_words_set = set(new_list)

    to_del = old_words_set.difference(new_words_set)
    to_del_ids = [item[1] for item in old_list if item[0] in to_del]

    old_words_set.add('')
    to_add = new_words_set.difference(old_words_set)

    return to_del_ids, list(to_add)


def save_path(index: QModelIndex) -> None:
    path = full_tree_path(index)

    settings = QSettings()
    settings.setValue('TREE_SEL_IDX', QVariant(path))


def full_tree_path(index: QModelIndex) -> list:
    idx = index
    path = []
    while idx.isValid():
        path.append(idx.row())
        idx = idx.parent()
    path.reverse()
    return path


def get_selected_items(view: QAbstractItemView) -> str:
    idxs = view.selectedIndexes()
    if idxs:
        model = view.model()
        items_str = ', '.join(model.data(i, Qt.DisplayRole) for i in idxs)
    else:
        items_str = ''
    return items_str