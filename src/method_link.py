from PyQt5.QtCore import (QSortFilterProxyModel, Qt, QModelIndex)
from PyQt5.QtGui import QStandardItemModel
from PyQt5.QtWidgets import (QApplication, QComboBox, QGridLayout, QGroupBox, QMenu, QTextEdit,
                             QLabel, QTreeView, QVBoxLayout, QWidget, QAbstractItemView)
import sqlite3
from pathlib import Path
from loguru import logger


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
        self.filterNote.addItem("All")
        self.filterNote.addItem("Not blank")
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
        self.proxyView.setSelectionMode(QAbstractItemView.ExtendedSelection)

        self.resView = QTextEdit()
        self.resView.setReadOnly(True)

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
        proxyLayout.addWidget(self.resView, 3, 0, 1, 3)
        proxyGroupBox = QGroupBox("Module/Class/Method list")
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
            menu.addAction('First level only')
            menu.addSeparator()
            menu.addAction('sort by level')
            menu.addAction('sort by module')
            menu.addSeparator()
            menu.addAction('Cancel')
            action = menu.exec_(self.proxyView.mapToGlobal(pos))
            if action:
                self.menu_action(action.text())

    def setSourceModel(self, model):
        self.proxyModel.setSourceModel(model)

    def textFilterChanged(self):
        self.proxyModel.filter_changed(self.filterModule.currentText(),
                                       self.filterClass.currentText(),
                                       self.filterNote.currentText())

    def menu_action(self, act: str):
        logger.debug(act)
        if act == 'Cancel':
            return

        method_ids, method_names = self.get_selected_methods()

        {'First level only': self.first_only,
         'sort by level': self.sort_by_level,
         'sort by module': self.sort_by_module,
         }[act](method_ids)

    def get_selected_methods(self):
        """
        Returns two lists:
        1) ids of selected methods
        2) full names of selected methods
        @return: ids, methods
        """
        self.resView.clear()
        self.resView.append(ttl_sel)
        indexes = self.proxyView.selectionModel().selectedRows()
        methods = []
        for idx in indexes:
            sql_par = self.proxyModel.get_data(idx)
            methods.append(sql_par)
        ids = exec_sql0(self.conn, meth.format(
            "','".join(tab_list(methods, ''))
        ))
        report_append(self.resView, tab_list(methods))
        return [x[0] for x in ids], methods

    def first_only(self, ids):
        """
        Show lists of methods that is immediate child / parent
        ie. only from first level
        @param ids: indexes of selected methods
        @return:
        """
        opt = len(ids) if len(ids) < 3 else 'more than 2'
        logger.debug(opt)
        {1: self.first_1,
         2: self.first_2,
         'more than 2': self.first_more_than_2,
         }[opt](ids)

    def first_1(self, ids):
        """
        Only one method selected
        @param ids: - index of method
        @return: None
        """
        self.resView.append(ttl_what)
        lst = self.first_1_part(ids, what_call_1st_lvl)
        report_append(self.resView, lst)

        self.resView.append(ttl_from)
        lst = self.first_1_part(ids, called_from_1st_lvl)
        report_append(self.resView, lst)

    def first_1_part(self, ids, sql):
        lst = exec_sql(self.conn, ids, sql)
        return tab_str_list(lst)

    def first_2(self, ids):
        """
        Two methods selected.
        Show 8 lists - see eight_lists variable
        @param ids: indexes of two methods
        @return: None
        """
        eight_lists = ('1) called from any of both methods',
                       '2) called from first method but not from second',
                       '3) called from second method but not from first',
                       '4) called from first and from second methods',
                       '5) call any of first and second method',
                       '6) call only first method but not second',
                       '7) call only second method but not first',
                       '8) call both first and second methods',
                       )

        self.resView.append(ttl_what)
        lst_a = self.first_1_part((ids[0],), what_call_1st_lvl)
        lst_b = self.first_1_part((ids[1],), what_call_1st_lvl)

        self.report_four(lst_a, lst_b, eight_lists)

        self.resView.append(ttl_from)
        lst_a = self.first_1_part((ids[0],), called_from_1st_lvl)
        lst_b = self.first_1_part((ids[1],), called_from_1st_lvl)

        self.report_four(lst_a, lst_b, eight_lists[4:])

    def report_four(self, lst_a, lst_b, ttls):
        self.resView.append(ttls[0])
        report_append(self.resView, list(set(lst_a) | set(lst_b)))
        self.resView.append(ttls[1])
        report_append(self.resView, list(set(lst_a) - set(lst_b)))
        self.resView.append(ttls[2])
        report_append(self.resView, list(set(lst_b) - set(lst_a)))
        self.resView.append(ttls[3])
        report_append(self.resView, list(set(lst_a) & set(lst_b)))

    def first_more_than_2(self, ids):
        pass

    def sort_by_level(self, ids):
        """
        Show lists of methods sorted by level
        @param ids: indexes of selected methods
        @return: None
        """
        pass

    def sort_by_module(self, idx):
        """
        Show lists of methods sorted by module name
        @param ids: indexes of selected methods
        @return: None
        """
        pass


def exec_sql(conn, sql_par: tuple, sql: str):
    curs = conn.cursor()
    logger.debug(sql)
    logger.debug(sql_par)
    cc = curs.execute(sql, sql_par).fetchall()
    return cc


def exec_sql0(conn, sql: str):
    curs = conn.cursor()
    logger.debug(sql)
    cc = curs.execute(sql).fetchall()
    return cc


def tab_list(lst: list, delim: str = '\t') -> list:
    res = []
    for ll in lst:
        res.append(delim.join(ll))
    return res


def tab_str_list(lst: list, delim: str = '\t') -> list:
    res = []
    for ll in lst:
        res.append(delim.join([x for x in map(str, ll)]))
    return res


def report_append(report: list, lst: list):
    for ll in lst:
        report.append(ll)


ttl_sel = '<============== Selected Methods ======================>'
ttl_what = '<---------------- what   call ------------------------->'
ttl_from = '<---------------- called from ------------------------->'
curr_id = 'select id from methods2 where module = ? and class = ? and method = ?;'
meth = "select id from methods2 where module || class || method in ('{}');"

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
what_call_1st_lvl = ('select a.module, a.class, a.method, b.level '
                     'from simple_link b join methods2 a on a.id = b.id '
                     'where b.call_id = ? and b.level = 1 '
                     'order by a.module, a.class, a.method;')
called_from_1st_lvl = ('select a.module, a.class, a.method, b.level '
                       'from simple_link b join methods2 a on a.id = b.call_id '
                       'where b.id = ? and b.level = 1 '
                       'order by a.module, a.class, a.method;')
sqls = {
    'First level only': (what_call_1st_lvl, called_from_1st_lvl),
    'order by level': (what_call_lvl_ord, called_from_lvl_ord),
    'order by module': (what_call_mod_ord, called_from_mod_ord),
}


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

    logger.remove()
    fmt = '<green>{time:HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | ' \
          '<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> '   \
          '- <level>{message}</level>'
    logger.add(sys.stderr, level="DEBUG", format=fmt, enqueue = True)
    logger.debug("logger DEBUG add")

    app = QApplication(sys.argv)
    DB = Path.cwd() / "prj.db"
    conn = sqlite3.connect(DB)

    window = Window(conn)
    window.setSourceModel(createModel(window))
    window.show()

    sys.exit(app.exec_())
