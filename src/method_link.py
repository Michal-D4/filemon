from PyQt5.QtCore import (QSortFilterProxyModel, Qt, QModelIndex)
from PyQt5.QtGui import QStandardItemModel
from PyQt5.QtWidgets import (QApplication, QComboBox, QGridLayout, QGroupBox, QMenu,
                             QLabel, QTreeView, QVBoxLayout, QWidget)
import sqlite3
from pathlib import Path


class MySortFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super(MySortFilterProxyModel, self).__init__(parent)

        self.module_filter = ''
        self.module_all = True
        self.class_filter = ''
        self.class_all = True
        self.note_filter = True

    def filterAcceptsRow(self, sourceRow, sourceParent: QModelIndex):
        index0 = self.sourceModel().index(sourceRow, 0, sourceParent)
        index1 = self.sourceModel().index(sourceRow, 1, sourceParent)
        index3 = self.sourceModel().index(sourceRow, 3, sourceParent)

        return (
            (self.module_all or self.sourceModel().data(index0) == self.module_filter) and
            (self.class_all or self.sourceModel().data(index1) == self.class_filter) and
            (self.note_filter or self.sourceModel().data(index3) != '')
        )

    def lessThan(self, left, right):
        left_data = self.sourceModel().data(left)
        right_data = self.sourceModel().data(right)

        return left_data < right_data

    def filter_changed(self, item1, item2, item3):
        self.module_all = item1 == 'All'
        self.module_filter = item1
        self.class_all = item2  == 'All'
        self.class_filter = item2
        self.note_filter = item3 == 'All'
        self.invalidateFilter()

    def get_data(self, index):
        """
        Get data from three first columns of current row
        @param index: index of current row
        @return: module, class, method from current row
        Is it possible to get the same result with the following code: ???
        parent = self.parent(index)
        row = index.row()
        idx_n = self.mapToSource(self.index(row, n, parent)
        """
        if index.isValid():
            parent = self.sourceModel().parent(index)
            row = self.mapToSource(index).row()

            idx0 = self.sourceModel().index(row, 0, parent)
            idx1 = self.sourceModel().index(row, 1, parent)
            idx2 = self.sourceModel().index(row, 2, parent)

            return (self.sourceModel().data(idx0),
                    self.sourceModel().data(idx1),
                    self.sourceModel().data(idx2))
        return None


class Window(QWidget):
    def __init__(self, connection):
        super(Window, self).__init__()

        self.conn = connection

        self.proxyModel = MySortFilterProxyModel(self)
        self.proxyModel.setDynamicSortFilter(True)

        self.filterModule = QComboBox()
        self.filterModule.addItem("All", '*')
        filterModuleLabel = QLabel("&Module Filter")
        filterModuleLabel.setBuddy(self.filterModule)
        self.filterClass = QComboBox()
        self.filterClass.addItem("All", '*')
        filterClassLabel = QLabel("&Class Filter")
        filterClassLabel.setBuddy(self.filterClass)
        self.filterNote = QComboBox()
        self.filterNote.addItem("All", '*')
        self.filterNote.addItem("Not blank", '+')
        filterNoteLabel = QLabel("&Note Filter")
        filterNoteLabel.setBuddy(self.filterNote)

        self.filterModule.currentIndexChanged.connect(self.textFilterChanged)
        self.filterClass.currentIndexChanged.connect(self.textFilterChanged)
        self.filterNote.currentIndexChanged.connect(self.textFilterChanged)

        self.proxyView = QTreeView()
        self.proxyView.setRootIsDecorated(False)
        self.proxyView.setAlternatingRowColors(True)
        self.proxyView.setModel(self.proxyModel)
        self.proxyView.setSortingEnabled(True)
        self.proxyView.sortByColumn(1, Qt.AscendingOrder)
        self.proxyView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.proxyView.customContextMenuRequested.connect(self.pop_menu)

        self.textFilterChanged()
        self.set_filters_combo()

        proxyLayout = QGridLayout()
        proxyLayout.addWidget(self.proxyView, 0, 0, 1, 3)
        proxyLayout.addWidget(filterModuleLabel, 1, 0)
        proxyLayout.addWidget(filterClassLabel, 1, 1)
        proxyLayout.addWidget(filterNoteLabel, 1, 2)
        proxyLayout.addWidget(self.filterModule, 2, 0)
        proxyLayout.addWidget(self.filterClass, 2, 1)
        proxyLayout.addWidget(self.filterNote, 2, 2)
        proxyGroupBox = QGroupBox("Sorted/Filtered Model")
        proxyGroupBox.setLayout(proxyLayout)

        mainLayout = QVBoxLayout()
        mainLayout.addWidget(proxyGroupBox)
        self.setLayout(mainLayout)

        self.setWindowTitle("Custom Sort/Filter Model")
        self.resize(800, 450)

    def set_filters_combo(self):
        curs = self.conn.cursor()
        curs.execute('select distinct module from methods2;')
        for cc in curs:
            self.filterModule.addItem(cc[0])

        curs.execute('select distinct class from methods2;')
        for cc in curs:
            self.filterClass.addItem(cc[0])

    def pop_menu(self, pos):
        idx = self.proxyView.indexAt(pos)
        if idx.isValid():
            menu = QMenu(self)
            menu.addAction('order by level')
            menu.addAction('order by module')
            menu.addSeparator()
            menu.addAction('Cancel')
            action = menu.exec_(self.proxyView.mapToGlobal(pos))
            if action:
                self.execute_sql(action.text(), idx)

    def setSourceModel(self, model):
        self.proxyModel.setSourceModel(model)

    def textFilterChanged(self):
        self.proxyModel.filter_changed(self.filterModule.currentText(),
                                       self.filterClass.currentText(),
                                       self.filterNote.currentText())

    def execute_sql(self, act: str, idx):
        if act == 'Cancel':
            return

        sqls = {'order by level': (what_call_lvl_ord, called_from_lvl_ord),
                'order by module': (what_call_mod_ord, called_from_mod_ord),
                }
        sql_par = self.proxyModel.get_data(idx)
        curs = self.conn.cursor()
        meth_id = curs.execute(curr_id, sql_par).fetchone()
        print(meth_id + sql_par)
        print('<---------------- what call ------------------------->')
        curs.execute(sqls[act][0], meth_id)
        for cc in curs:
            print(cc)
        print('<---------------- called from ------------------------->')
        curs.execute(sqls[act][1], meth_id)
        for cc in curs:
            print(cc)


curr_id = 'select id from methods2 where module = ? and class = ? and method = ?;'

what_call_lvl_ord = ('select a.module, a.class, a.method, b.level '
                     'from simple_link b join methods2 a on a.id = b.id '
                     'where b.call_id = ? order by b.level, a.module, a.class, a.method;')
called_from_lvl_ord = ('select a.module, a.class, a.method, b.level '
                       'from simple_link b join methods2 a on a.id = b.call_id '
                       'where b.id = ? order by b.level, a.module, a.class, a.method;')
what_call_mod_ord = ('select a.module, a.class, a.method, b.level '
                     'from simple_link b join methods2 a on a.id = b.id '
                     'where b.call_id = ? order by a.module, b.level, a.method;')
called_from_mod_ord = ('select a.module, a.class, a.method, b.level '
                       'from simple_link b join methods2 a on a.id = b.call_id '
                       'where b.id = ? order by a.module, b.level, a.method;')


def addItem(model, id, module, class_, method, note):
    model.insertRow(0)
    model.setData(model.index(0, 0), module)
    model.setData(model.index(0, 1), class_)
    model.setData(model.index(0, 2), method)
    model.setData(model.index(0, 3), note if note else '')
    for i in range(4):
        model.setData(model.index(0, i), id, Qt.UserRole)


def createModel(parent):
    model = QStandardItemModel(0, 4, parent)

    model.setHeaderData(0, Qt.Horizontal, "module")
    model.setHeaderData(1, Qt.Horizontal, "Class")
    model.setHeaderData(2, Qt.Horizontal, "method")
    model.setHeaderData(3, Qt.Horizontal, "Note")

    curs = parent.conn.cursor()
    curs.execute('select * from methods2;')

    for cc in curs:
        addItem(model, *cc)

    return model


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    DB = Path.cwd() / "prj.db"
    conn = sqlite3.connect(DB)

    window = Window(conn)
    window.setSourceModel(createModel(window))
    window.show()

    sys.exit(app.exec_())
