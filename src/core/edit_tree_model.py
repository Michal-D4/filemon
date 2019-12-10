# edit_tree_model.py

from loguru import logger
import copy
from collections import namedtuple, defaultdict

from PyQt5.QtCore import (QAbstractItemModel, QModelIndex, Qt, QMimeData, QByteArray,
                          QDataStream, QIODevice, QPersistentModelIndex)
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont

from src.core.helper import (REAL_FOLDER, VIRTUAL_FOLDER,
                             MimeTypes, DROP_COPY_FOLDER, DROP_MOVE_FOLDER,
                             DROP_COPY_FILE, DROP_MOVE_FILE, Shared)
import src.core.utilities as ut

DirData = namedtuple('DirData', 'dir_id parent_id is_virtual path')
# dir_id: int, parent_id: int, is_virtual: int, path: str

ALL_ITEMS = defaultdict(list)


class EditTreeItem(object):

    def __init__(self, data_, user_data=None, parent=None):
        self.parent_ = parent
        if user_data:
            self.userData = DirData(*user_data)
        else:
            self.userData = None
        self.itemData = data_
        self.children = []

    def childNumber(self):
        if self.parent_ is not None:
            return self.parent_.children.index(self)
        return 0

    def removeChildren(self, position, count):
        logger.debug(f'children count: {len(self.children)}, userData: {self.userData}')
        if position < 0 or position + count > len(self.children):
            return False

        for _ in range(count):
            logger.debug(f'userData: {self.children[position].userData}')
            self.children.pop(position)
        logger.debug(f'childCount: {self.childCount()}, {len(self.children)}')

        return True

    def is_virtual(self):
        return self.userData.is_virtual > 0

    def is_favorites(self):
        return (self.userData.is_virtual == 1)

    def child(self, row):
        return self.children[row]

    def childCount(self):
        return len(self.children)

    def columnCount(self):
        return len(self.itemData)

    def data(self, column, role):
        if role == Qt.DisplayRole:
            return self.itemData[column]

        if role == Qt.UserRole:
            return self.userData

        if role == Qt.BackgroundRole:
            if self.is_virtual():
                return QApplication.palette().alternateBase()
            return QApplication.palette().base()

        if role == Qt.FontRole:
            if self.is_virtual():
                return EditTreeModel.alt_font
        return None

    def appendChild(self, item):
        item.parent_ = self
        logger.debug(f'to: {self.userData}')
        item.userData = item.userData._replace(parent_id=self.userData.dir_id)
        logger.debug('Child: {item.userData}')
        ALL_ITEMS[item.userData.dir_id].append(item)
        self.children.append(item)

    def parent(self):
        return self.parent_

    def row(self):
        if self.parent_:
            return self.parent_.children.index(self)

        return 0

    def set_data(self, data_):
        self.itemData = data_


class EditTreeModel(QAbstractItemModel):

    alt_font = QFont("Times", 10)

    @staticmethod
    def set_alt_font(font: QFont):
        EditTreeModel.alt_font = QFont(font)
        EditTreeModel.alt_font.setItalic(True)

    def __init__(self, parent=None):
        super(EditTreeModel, self).__init__(parent)

        self.rootItem = EditTreeItem(data_=('',), user_data=(0, 0, 0, "Root"))
        ALL_ITEMS.clear()

    @staticmethod
    def is_virtual(index):
        if index.isValid():
            return index.internalPointer().is_virtual()
        return False

    @staticmethod
    def is_favorites(index):
        if index.isValid():
            return index.internalPointer().is_favorites()
        return False

    def columnCount(self, parent):
        return self.rootItem.columnCount()

    def data(self, index, role):
        if index.isValid():
            item = index.internalPointer()
            if item:
                return item.data(index.column(), role)
        return None

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags

        # return Qt.ItemIsEnabled | Qt.ItemIsSelectable
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | \
               Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled

    def getItem(self, index):
        if index.isValid():
            item = index.internalPointer()
            if item:
                return item

        return self.rootItem

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.rootItem.data(section, role)
        return None

    def index(self, row, column, parent=QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()

        childItem = parentItem.child(row)
        if childItem:
            return self.createIndex(row, column, childItem)

        return QModelIndex()

    def parent(self, index):
        """
        return parent index for index
        """
        if not index.isValid():
            return QModelIndex()

        child_item: EditTreeItem = index.internalPointer()
        parent_item = child_item.parent()

        if parent_item == self.rootItem:
            return QModelIndex()

        return self.createIndex(parent_item.childNumber(), 0, parent_item)

    def create_new_parent(self, curr_idx, new_parent_data, idx_list):
        """
        update parent for selected items
        :param curr_idx  - to find parent for new_parent_item,
        :param new_parent_data  - data to create new_parent_item:
           0 - dir_id of new_parent_item,
           1 - path,
           2 - parent_id for new_parent,
           3 - is_virtual = 3
        :param: idx_list - indexes of items to change parent = new_parent
        """
        new_parent_item = EditTreeItem((new_parent_data[1],),
                                       (new_parent_data[0],
                                        *new_parent_data[2:4],
                                        new_parent_data[1]))
        for idx in idx_list:
            item = copy.deepcopy(QModelIndex(idx).internalPointer())
            item.userData = item.userData._replace(parent_id=new_parent_data[2])
            ut.update_other('DIR_PARENT', (new_parent_data[0], item.userData.dir_id))
            new_parent_item.appendChild(item)
        
        curr_idx.internalPointer().parent().appendChild(new_parent_item)

        for idx in idx_list:
            self.remove_row(QModelIndex(idx))

    def removeRows(self, row, count, parent=QModelIndex()):
        """
        removes count of rows starting with the given row in parent item
        :param row:
        :param count:
        :param parent:
        :return: bool
        """
        parentItem = self.getItem(parent)

        self.beginRemoveRows(parent, row, row + count - 1)
        success = parentItem.removeChildren(row, count)
        self.endRemoveRows()

        return success

    def remove_row(self, index):
        logger.debug(f'row: {self.data(index, Qt.UserRole)}')
        logger.debug(f'parent: {self.getItem(index).parent().itemData}')
        return self.removeRows(index.row(), 1, self.parent(index))

    def remove_all_copies(self, index):
        """
        removes all copy of virtual folder when initial folder deleted
        :param  index
        :return None 
        """
        dir_id = index.internalPointer().userData.dir_id
        items = ALL_ITEMS[dir_id]
        logger.debug(f'dir_id: {dir_id}, len: {len(items)}')
        idx_list = []
        for item in items:
            logger.debug(f'userData: {item.userData}, item_row: {item.row()}')
            idx = self.createIndex(item.row(), 0, item)
            idx_list.append(QPersistentModelIndex(idx))

        for idx in idx_list:
            logger.debug(f'data: self.data(QModelIndex(idx), Qt.UserRole), '
                         f'row: {QModelIndex(idx).row()}')
            res = self.remove_row(QModelIndex(idx))
            logger.debug(f'res= {res}')
            
        ALL_ITEMS.pop(dir_id)

    def rowCount(self, parent=QModelIndex()):
        parentItem = self.getItem(parent)

        return parentItem.childCount()

    def setHeaderData(self, p_int, orientation, value, role=None):
        if isinstance(value, str):
            value = value.split(';')
        self.rootItem.set_data(value)

    def append_child(self, item: EditTreeItem, parent):
        parentItem: EditTreeItem = self.getItem(parent)
        item.userData = item.userData._replace(parent_id=parentItem.userData.dir_id)
        position = parentItem.childCount()

        self.beginInsertRows(parent, position, position)
        parentItem.appendChild(item)
        self.endInsertRows()
        return True

    def update_folder_name(self, index, name):
        item = self.getItem(index)
        name = name.strip()
        item.itemData = (name,)
        item.userData = item.userData._replace(path=name)

    def set_model_data(self, rows):
        """
        Fill tree structure
        :param rows: iterable, each item contains at least 3 elements
             item[0]  - string/"tuple of strings" to be shown == Qt.DisplayRole,
             item[1:] - user_data:
                  item[1]  - Id of item, unique,
                  item[2]  - Id of parent item, 0 for root,
                        ...
             and sorted by item(2) - parent ID - in descendant order
        :return: None
        """
        id_list = []
        items_dict = {0: self.rootItem}
        for row in rows:
            if not isinstance(row[0], tuple):
                row = ((row[0],),) + tuple(row[1:])
            items_dict[row[1]] = EditTreeItem(data_=row[0], user_data=(row[1:]))
            id_list.append((row[1:]))

        for id_ in id_list:
            if id_[1] in items_dict:
                items_dict[id_[1]].appendChild(copy.deepcopy(items_dict[id_[0]]))

    def supportedDropActions(self):
        return Qt.CopyAction | Qt.MoveAction

    def mimeTypes(self):
        return MimeTypes

    @classmethod
    def mimeData(cls, indexes):
        item_data = QByteArray()
        data_stream = QDataStream(item_data, QIODevice.WriteOnly)
        data_stream.writeInt(len(indexes))
        all_virtual = True

        for idx in indexes:
            it: EditTreeItem = idx.internalPointer()
            all_virtual &= (it.is_virtual() & (not it.is_favorites()))
            pack = cls._save_index(idx)
            data_stream.writeQString(','.join((str(x) for x in pack)))

        mime_data = QMimeData()
        if all_virtual:
            mime_data.setData(MimeTypes[VIRTUAL_FOLDER], item_data)
        else:
            mime_data.setData(MimeTypes[REAL_FOLDER], item_data)

        return mime_data

    def dropMimeData(self, mime_data: QMimeData, action, parent):
        """
        Intensionally list of parameters differs from standard:
          row, column - parameters are not used.
        :param mime_data:
        :param action:  not Qt defined actions, instead Drop* from helper.py
        :param parent: where mime_data is dragged
        :return: True if dropped
        """
        if action & (DROP_MOVE_FOLDER | DROP_COPY_FOLDER):
            return self._drop_folders(action, mime_data, parent)

        if action & (DROP_MOVE_FILE | DROP_COPY_FILE):
            return self._drop_files(action, mime_data, parent)

        return False

    def _drop_files(self, action, mime_data, parent):
        if self.is_virtual(parent):
            return self._drop_files_to_virtual(action, mime_data, parent)
        else:
            path = self.data(parent, role=Qt.UserRole).path
            if action == DROP_COPY_FILE:
                Shared['Controller'].copy_files_to(path)
            else:
                Shared['Controller'].move_files_to(path)

            return True

    def _drop_files_to_virtual(self, action, mime_data, parent):
        parent_dir_id = self.data(parent, role=Qt.UserRole).dir_id

        mime_format = mime_data.formats()
        drop_data = mime_data.data(mime_format[0])
        stream = QDataStream(drop_data, QIODevice.ReadOnly)

        count = stream.readInt()
        fav_id = 0
        for _ in range(count):
            file_id = stream.readInt()
            # dir_id = stream.readInt() # may be restored, if copy/move from real folder
            fav_id = stream.readInt()
            if action == DROP_COPY_FILE:
                ut.insert_other('VIRTUAL_FILE', (parent_dir_id, file_id))
            else:
                if fav_id > 0:
                    ut.update_other('VIRTUAL_FILE_MOVE', (parent_dir_id, fav_id, file_id))

        if action == DROP_MOVE_FILE:          # update file list after moving files
            Shared['Controller'].files_virtual_folder(fav_id)

        return (fav_id != -1)

    def _drop_folders(self, action, mime_data, parent):
        mime_format = mime_data.formats()[0]
        drop_data = mime_data.data(mime_format)
        stream = QDataStream(drop_data, QIODevice.ReadOnly)
        idx_count = stream.readInt()
        for _ in range(idx_count):
            tmp_str = stream.readQString()
            id_list = (int(i) for i in tmp_str.split(','))
            index = self._restore_index(id_list)
            if action == DROP_MOVE_FOLDER:
                self._move_folder(index, parent)
            else:
                self._copy_folder(index, parent)
        return True

    def _move_folder(self, index, parent):
        item = index.internalPointer()
        self.append_child(copy.deepcopy(item), parent)

        parent_id = self.data(parent, role=Qt.UserRole).dir_id
        item_id = self.data(index, role=Qt.UserRole).dir_id
        ut.update_other('DIR_PARENT', (parent_id, item_id))

        self.remove_row(index)

    def _copy_folder(self, index, parent):
        item: EditTreeItem = index.internalPointer()
        new_item: EditTreeItem = copy.deepcopy(item)
        if item.is_favorites():
            new_item.userData = item.userData._replace(is_virtual=2)
        self.append_child(new_item, parent)

        parent_id = self.data(parent, role=Qt.UserRole).dir_id
        item_id = self.data(index, role=Qt.UserRole).dir_id
        ut.insert_other('VIRTUAL_DIR', (parent_id, item_id))

    def _restore_index(self, path):
        parent = QModelIndex()
        for id_ in path:
            idx = self.index(int(id_), 0, parent)
            parent = idx
        return parent

    @staticmethod
    def _save_index(index):
        idx = index
        path = []
        while idx.isValid():
            path.append(idx.row())
            idx = idx.parent()
        path.reverse()
        return path
