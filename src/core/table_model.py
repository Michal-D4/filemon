# table_model.py

from collections.abc import Iterable

# from PyQt5.QtCore import QModelIndex, Qt, QAbstractTableModel, QSortFilterProxyModel
from PyQt5.QtCore import (QAbstractTableModel, QModelIndex, Qt, QMimeData, QByteArray,
                          QDataStream, QIODevice, QSortFilterProxyModel)

from src.core.helper import MimeTypes, VIRTUAL_FILE, REAL_FILE


class ProxyModel(QSortFilterProxyModel):

    def __init__(self, parent=None):
        super().__init__(parent)

    def append_row(self, row, user_data=None):
        self.sourceModel().append_row(row, user_data)

    def update(self, index, data, role=Qt.DisplayRole):
        self.sourceModel().update(self.mapToSource(index), data, role)

    def delete_row(self, index):
        self.sourceModel().delete_row(self.mapToSource(index))

    def setHeaderData(self, value):
        self.sourceModel().setHeaderData(0, Qt.Horizontal, value)

    def get_headers(self):
        return self.sourceModel().header

    def rowCount(self, parent=QModelIndex()):
        return self.sourceModel().rowCount(parent)


class ProxyModel2(ProxyModel):
    """
    Specific model for file list
    """

    def __init__(self, parent=None):
        super().__init__(parent)

    def in_real_folder(self, index):
        return self.sourceModel().data(self.mapToSource(index), role=Qt.UserRole)[-1] == 0

    def lessThan(self, left, right):
        s_model = self.sourceModel()
        left_data = s_model.data(left)
        right_data = s_model.data(right)

        if s_model.headerData(left.column(), Qt.Horizontal) in ('Pages', 'Size'):
            left_data = int(left_data) or 0
            right_data = int(right_data) or 0

        return left_data < right_data

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags

        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled

    def supportedDropActions(self):
        return Qt.IgnoreAction

    def mimeTypes(self):
        return [MimeTypes[REAL_FILE], MimeTypes[VIRTUAL_FILE]]

    def mimeData(self, indexes):
        item_data = QByteArray()
        data_stream = QDataStream(item_data, QIODevice.WriteOnly)

        data_stream.writeInt(len(indexes))
        tmp = None
        for idx in indexes:
            s_idx = self.mapToSource(idx)
            tmp = self.sourceModel().data(s_idx, role=Qt.UserRole)
            data_stream.writeInt(tmp.file_id)    # file ID
            # may need, in case of copy/move for real folder using mimeData
            data_stream.writeInt(tmp.dir_id)
            # > 0 - virtual folder, 0 - real, -1 - adv.
            data_stream.writeInt(tmp.source)

        mime_data = QMimeData()
        if tmp.source > 0:         # files are from virtual folder
            mime_data.setData(MimeTypes[VIRTUAL_FILE], item_data)
        else:
            mime_data.setData(MimeTypes[REAL_FILE], item_data)
        return mime_data


class TableModel(QAbstractTableModel):
    def __init__(self, parent=None, *args):
        super(TableModel, self).__init__(parent)
        self.header = ()
        self.__data = []
        self.__user_data = []
        self.column_count = 0

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(self.__data)

    def setColumnCount(self, count):
        self.column_count = count

    def columnCount(self, parent=None):
        return self.column_count

    def data(self, index, role=Qt.DisplayRole):
        if index.isValid():
            if role == Qt.DisplayRole:
                # row length > current column
                if len(self.__data[index.row()]) > index.column():
                    return self.__data[index.row()][index.column()]
                return None
            elif role == Qt.UserRole:
                return self.__user_data[index.row()]
            elif role == Qt.TextAlignmentRole:
                if index.column() == 0:
                    return Qt.AlignLeft
                return Qt.AlignRight

    def update(self, index, data, role=Qt.DisplayRole):
        if index.isValid():
            if role == Qt.DisplayRole:
                i = index.column()
                if i + 1 < len(self.__data[index.row()]):
                    self.__data[index.row()] = self.__data[index.row()][:i] + \
                        (data,) + self.__data[index.row()][(i+1):]
                else:
                    self.__data[index.row()] = self.__data[index.row()
                                                           ][:-1] + (data,)
            elif role == Qt.UserRole:
                self.__user_data[index.row()] = data

    def delete_row(self, index):
        if index.isValid():
            self.beginRemoveRows(QModelIndex(), index.row(), index.row())
            row = index.row()
            self.__data.remove(self.__data[row])
            self.__user_data.remove(self.__user_data[row])
            self.endRemoveRows()

    def append_row(self, row, user_data=None):
        self.beginInsertRows(QModelIndex(), self.rowCount(), self.rowCount())
        if isinstance(row, str) or not isinstance(row, Iterable):
            row = (str(row),)
        else:
            rr = []
            for r in row:
                rr.append(str(r))
            row = tuple(rr)

        self.__data.append(row)
        self.__user_data.append(user_data)
        self.endInsertRows()

    def insert_row(self, index, row_data, user_data=None):
        if index.isValid():
            row = index.row()
            self.beginInsertRows(QModelIndex(), row, row)
            self.__data.insert(row, row_data)
            self.__user_data.insert(row, user_data)
        else:
            self.beginInsertRows(
                QModelIndex(), self.rowCount(), self.rowCount())
            self.__data.append(row_data)
            self.__user_data.append(user_data)
        self.endInsertRows()

    def appendData(self, value, role=Qt.EditRole):
        in_row = self.rowCount(QModelIndex())
        self.__data.append(value)
        index = self.createIndex(in_row, 0, 0)
        self.dataChanged.emit(index, index)
        return True

    def removeRows(self, row, count=1, parent=QModelIndex()):
        self.beginRemoveRows(QModelIndex(), row, row + count - 1)
        del self.__data[row:row + count]
        del self.__user_data[row:row + count]
        self.endRemoveRows()
        return True

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if not self.header:
            return None
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.header[section]

    def setHeaderData(self, p_int, orientation, value, role=None):
        if isinstance(value, str):
            value = value.split(' ')
        self.header = value
        self.column_count = len(value)

    def setData(self, index, value, role):
        if index.isValid():
            if role == Qt.DisplayRole:
                self.__data[index.row()][index.column()] = value
                return
            if role == Qt.UserRole:
                self.__user_data[index.row()][index.column()] = value

    def get_row(self, row):
        if row >= 0 & row < self.rowCount():
            return self.__data[row], self.__user_data[row]
        return ()


class TableModel2(TableModel):
    """
    for edit tags / authors assigned to file
    Show data with custom alignment
    """

    def __init__(self, parent=None, *args):
        super().__init__(parent, *args)

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.TextAlignmentRole:
            return Qt.AlignRight
        return super().data(index, role)
