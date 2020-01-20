# src/inter/method_link.py

from PyQt5.QtCore import (QSortFilterProxyModel, Qt, QModelIndex)
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import (QApplication, QComboBox, QGridLayout, QGroupBox, QMenu, QTextEdit,
                             QLabel, QTreeView, QVBoxLayout, QWidget, QAbstractItemView)
import sqlite3
from pathlib import Path
from loguru import logger
from datetime import datetime
from collections.abc import Iterable

# ---------------------------------------------------------
# doesn't catch exception without this code in Windows ! ! !
import sys
_excepthook = sys.excepthook


def my_exception_hook(exc_, value, traceback):
    # Print the error and traceback
    # logger.debug(f'{exc_}, {value}, {traceback}')
    print(traceback)
    # Call the normal Exception hook after
    _excepthook(exc_, value, traceback)
    sys.exit(1)


sys.excepthook = my_exception_hook
# ---------------------------------------------------------


class MySortFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super(MySortFilterProxyModel, self).__init__(parent)

        self.module_filter = ''
        self.module_all = True
        self.class_filter = ''
        self.class_all = True
        self.note_filter = True

    def filterAcceptsRow(self, sourceRow, sourceParent: QModelIndex):
        index0 = self.sourceModel().index(sourceRow, 1, sourceParent)
        index1 = self.sourceModel().index(sourceRow, 2, sourceParent)
        index3 = self.sourceModel().index(sourceRow, 4, sourceParent)

        return (
            (self.module_all or self.sourceModel().data(index0) == self.module_filter) and
            (self.class_all or self.sourceModel().data(index1) == self.class_filter) and
            (self.note_filter or self.sourceModel().data(index3) != '')
        )

    def lessThan(self, left, right):
        left_data = self.sourceModel().data(left)
        right_data = self.sourceModel().data(right)

        return (left_data is not None) and (right_data is not None) and left_data < right_data

    def filter_changed(self, item1, item2, item3):
        self.module_all = item1 == 'All'
        self.module_filter = item1
        self.class_all = item2  == 'All'
        self.class_filter = item2
        self.note_filter = item3 == 'All'
        self.invalidateFilter()

    def get_data(self, index, role=Qt.DisplayRole):
        """
        Get module, class, method from current row
        @param index: index of current row
        @return: module, class, method from current row
        """
        if index.isValid():
            parent = self.parent(index)
            row = index.row()
            res = []
            if role == Qt.DisplayRole:
                for i in range(5):
                    idx = self.mapToSource(self.index(row, i, parent))
                    res.append(self.sourceModel().data(idx))
                return res
            elif role == Qt.UserRole:
                idx = self.mapToSource(self.index(row, 0, parent))
                return self.sourceModel().data(idx, Qt.UserRole)
        return None

    def setData(self, index, data, role=Qt.DisplayRole):
        ok = super(MySortFilterProxyModel, self).setData(index, data, role)
        if ok:
            if role == Qt.EditRole:
                idn0 = self.mapToSource(self.index(index.row(), 0, 
                                        self.parent(index)))
                idx = self.sourceModel().data(idn0, Qt.UserRole) 
                logger.debug((data, idx))
                logger.debug(upd0.format(headers[index.column()]))
                conn.execute(upd0.format(headers[index.column()]), (data, idx))
                conn.commit()
        return ok


class Window(QWidget):
    def __init__(self, connection):
        super(Window, self).__init__()

        self.conn = connection

        self.proxyModel = MySortFilterProxyModel(self)
        self.proxyModel.setDynamicSortFilter(True)

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

        self.infLabel = QLabel()
        self.set_filters()

        proxyLayout = QGridLayout()
        proxyLayout.addWidget(self.proxyView, 0, 0, 1, 4)
        proxyLayout.addWidget(self.filterModuleLabel, 1, 0)
        proxyLayout.addWidget(self.filterClassLabel, 1, 1)
        proxyLayout.addWidget(self.filterNoteLabel, 1, 2)
        proxyLayout.addWidget(self.infLabel, 1, 3)
        proxyLayout.addWidget(self.filterModule, 2, 0)
        proxyLayout.addWidget(self.filterClass, 2, 1)
        proxyLayout.addWidget(self.filterNote, 2, 2)
        proxyLayout.addWidget(self.resView, 3, 0, 1, 4)
        proxyGroupBox = QGroupBox("Module/Class/Method list")
        proxyGroupBox.setLayout(proxyLayout)

        mainLayout = QVBoxLayout()
        mainLayout.addWidget(proxyGroupBox)
        self.setLayout(mainLayout)

        self.rep_append = None
        self.query_time = None

        self.setWindowTitle("Custom Sort/Filter Model")
        self.resize(900, 750)

    def set_filters(self):
        self.filterModule = QComboBox()
        self.filterModule.addItem("All")
        self.filterModuleLabel = QLabel("&Module Filter")
        self.filterModuleLabel.setBuddy(self.filterModule)

        self.filterClass = QComboBox()
        self.filterClass.addItem("All")
        self.filterClassLabel = QLabel("&Class Filter")
        self.filterClassLabel.setBuddy(self.filterClass)

        self.filterNote = QComboBox()
        self.filterNote.addItem("All")
        self.filterNote.addItem("Not blank")
        self.filterNoteLabel = QLabel("&Note Filter")
        self.filterNoteLabel.setBuddy(self.filterNote)

        self.filterModule.currentIndexChanged.connect(self.textFilterModuleChanged)
        self.filterClass.currentIndexChanged.connect(self.textFilterChanged)
        self.filterNote.currentIndexChanged.connect(self.textFilterChanged)

        self.textFilterChanged()
        self.set_filters_combo()

    def set_filters_combo(self):
        curs = self.conn.cursor()
        curs.execute('select distinct module from methods2;')
        for cc in curs:
            self.filterModule.addItem(cc[0])

        curs.execute('select distinct class from methods2;')
        for cc in curs:
            self.filterClass.addItem(cc[0])

    def textFilterModuleChanged(self):
        curs = self.conn.cursor()
        self.filterClass.clear()
        self.filterClass.addItem('All')
        if self.filterModule.currentText() == 'All':
            curs.execute('select distinct class from methods2;')
            for cc in curs:
                self.filterClass.addItem(cc[0])
        else:
            curs.execute(('select distinct class from methods2 '
                          'where module = ?;'),
                         (self.filterModule.currentText(),))
            for cc in curs:
                self.filterClass.addItem(cc[0])

    def pop_menu(self, pos):
        idx = self.proxyView.indexAt(pos)
        if idx.isValid():
            menu = QMenu(self)
            menu.addAction(menu_items[0])
            menu.addSeparator()
            menu.addAction(menu_items[1])
            menu.addAction(menu_items[2])
            menu.addSeparator()
            menu.addAction(menu_items[3])
            menu.addAction(menu_items[4])
            menu.addAction(menu_items[5])
            menu.addSeparator()
            menu.addAction(menu_items[-1])
            action = menu.exec_(self.proxyView.mapToGlobal(pos))
            if action:
                self.menu_action(action.text())

    def setSourceModel(self, model: QStandardItemModel):
        self.proxyModel.setSourceModel(model)
        self.set_columns_width()

    def set_columns_width(self):
        prop = (3, 6, 8, 9, 5)
        ss = sum(prop)
        model = self.proxyView.model()
        n = model.columnCount()
        w = self.proxyView.width()
        for k in range(n):
            self.proxyView.setColumnWidth(k, w / ss * prop[k])

    def textFilterChanged(self):
        self.proxyModel.filter_changed(self.filterModule.currentText(),
                                       self.filterClass.currentText(),
                                       self.filterNote.currentText())

    def menu_action(self, act: str):
        if act == 'Cancel':
            return

        self.resView.clear()
        if act in menu_items[:3]:
            self.time_run()
            method_ids, method_names = self.get_selected_methods()

            {menu_items[0]: self.first_level_only,
             menu_items[1]: self.sort_by_level,
             menu_items[2]: self.sort_by_module,
             }[act](method_ids, method_names)
        else:
            curr_idx = self.proxyView.currentIndex()

            {menu_items[3]: self.append_row,
             menu_items[4]: self.delete_current,
             menu_items[5]: self.edit_links,
             }[act](curr_idx)

    def append_row(self, index: QModelIndex):
        crs = conn.cursor()
        crs.execute(ins0, (('', 'b', 'c', 'd', 'e')))
        idn = crs.lastrowid
        logger.debug(idn)
        conn.commit()
        model = self.proxyModel.sourceModel()
        self.proxyModel.beginInsertRows()
        idx = addItem(model, idn, '', 'b-', 'c-', 'd-', 'e-')
        self.proxyModel.endInsertRows()
        self.proxyView.setCurrentIndex(self.proxyModel.mapFromSource(idx))

    def delete_current(self, index: QModelIndex):
        logger.debug(self.proxyModel.get_data(index, Qt.UserRole))
        pass

    def edit_links(self, index: QModelIndex):
        logger.debug(self.proxyModel.get_data(index, Qt.UserRole))
        pass

    def time_run(self):
        tt = datetime.now()
        self.query_time = (tt.strftime("%b %d"), tt.strftime("%H:%M:%S"))
        self.resView.append(rep_head.format(self.query_time[0]))

    def get_selected_methods(self):
        """
        Returns two lists for rows selected in the proxyView:
        1) ids - id-s of selected methods
        2) methods - full names of selected methods, ie. (module, class, method)
        @return: ids, methods
        """
        indexes = self.proxyView.selectionModel().selectedRows()
        methods = []
        ids = []
        for idx in indexes:
            ids.append(self.proxyModel.get_data(idx, Qt.UserRole))
            methods.append(self.proxyModel.get_data(idx))

        return ids, methods

    def first_level_only(self, ids, names):
        """
        Show lists of methods that is immediate child / parent
        ie. only from first level
        @param ids: indexes of selected methods
        @return:
        """
        self.rep_append = concrete_report(lambda row: ''.join(row[1:4]))
        opt = len(ids) if len(ids) < 3 else 'more than 2'
        {1: self.first_1,
         2: self.first_2,
         'more than 2': self.first_more_than_2,
         }[opt](ids, names)

    def first_1(self, ids, names):
        """
        Only one method selected
        @param ids: - index of method - tuple of length 1
        @param names: - list of (module, class, method)
        @return: None
        """
        self.selected_only_one(ids, names, 1)

    def selected_only_one(self, ids, names, lvl):
        pre = (self.query_time[1], 'Sel', '')
        self.rep_append(self.resView, names, pre=pre)
        what_sql = prep_sql(what_call_1,
                            self.filterModule.currentText(),
                            self.filterClass.currentText(), lvl)
        lst = self.first_1_part(ids, what_sql)
        pre = (self.query_time[1], 'What', '')
        self.rep_append(self.resView, lst, pre=pre)
        from_sql = prep_sql(called_from_1,
                            self.filterModule.currentText(),
                            self.filterClass.currentText(), lvl)
        lst = self.first_1_part(ids, from_sql)
        pre = (self.query_time[1], 'From', '')
        self.rep_append(self.resView, lst, pre=pre)

    def first_1_part(self, ids, sql):
        lst = self.exec_sql_b(sql, ids)
        return [(*map(str, x),) for x in lst]

    def first_2(self, ids, names):
        """
        Two methods selected.
        Show 8 lists -
        1) called from any of both methods
        2) called from first method but not from second
        3) called from second method but not from first
        4) called from first and from second methods
        5) call any of first and second method
        6) call only first method but not second
        7) call only second method but not first
        8) call both first and second methods
        (time, {what|from}, {A | B, A - B, B - A, A & B}, module, class, method
        @param ids: indexes of two methods
        @return: None
        """
        self.selected_exactly_two(ids, names, 1)

    def selected_exactly_two(self, ids, names, lvl):
        pre = (self.query_time[1], 'Sel')
        n_names = [('A', *names[0]), ('B', *names[1])]
        self.rep_append(self.resView, n_names, pre=pre)
        what_sql = prep_sql(what_call_1,
                            self.filterModule.currentText(),
                            self.filterClass.currentText(), lvl)
        lst_a = self.first_1_part((ids[0],), what_sql)
        lst_b = self.first_1_part((ids[1],), what_sql)
        self.report_four(lst_a, lst_b, "What")
        from_sql = prep_sql(called_from_1,
                            self.filterModule.currentText(),
                            self.filterClass.currentText(), lvl)
        lst_a = self.first_1_part((ids[0],), from_sql)
        lst_b = self.first_1_part((ids[1],), from_sql)
        self.report_four(lst_a, lst_b, "From")

    def report_four(self, lst_a, lst_b, what):
        logger.debug('A | B')
        self.rep_append(self.resView, list(set(lst_a) | set(lst_b)),
                        pre=(self.query_time[1], what, 'A | B'))
        logger.debug('A - B')
        self.rep_append(self.resView, list(set(lst_a) - set(lst_b)),
                        pre=(self.query_time[1], what, 'A - B'))
        logger.debug('B - A')
        self.rep_append(self.resView, list(set(lst_b) - set(lst_a)),
                        pre=(self.query_time[1], what, 'B - A'))
        logger.debug('A & B')
        self.rep_append(self.resView, list(set(lst_a) & set(lst_b)),
                        pre=(self.query_time[1], what, 'A & B'))

    def first_more_than_2(self, ids, names):
        self.selected_more_than_two(ids, names, 1)

    def selected_more_than_two(self, ids, names, lvl):
        pre = (self.query_time[1], 'Sel', '')
        self.rep_append(self.resView, names, pre=pre)
        what_sql = prep_sql(what_call_3,
                            self.filterModule.currentText(),
                            self.filterClass.currentText(), lvl)
        param = (what_id, what_sql, 'What', 'ALL', 'ANY')
        self.report_23(ids, param)
        from_sql = prep_sql(called_from_3,
                            self.filterModule.currentText(),
                            self.filterClass.currentText(), lvl)
        param = (from_id, from_sql, 'From', 'ALL', 'ANY')
        self.report_23(ids, param)

    def report_23(self, ids, param):
        links = self.exec_sql_2(ids, param[0])
        rep_prep = pre_report(links)

        if rep_prep[0]:
            logger.debug(len(rep_prep[0]))
            cc = self.exec_sql_f(param[1], (','.join((rep_prep[0])),))
            logger.debug(cc)
            pre = (self.query_time[1], param[2], param[3])
            self.rep_append(self.resView, cc, pre=pre)

        if rep_prep[1]:
            cc = self.exec_sql_f(param[1], (','.join((rep_prep[1])),))
            pre = (self.query_time[1], param[2], param[4])
            self.rep_append(self.resView, cc, pre=pre)

    def exec_sql_2(self, ids, sql):
        res = []
        curs = self.conn.cursor()
        for id_ in ids:
            w_id = curs.execute(sql, (id_,))
            res.append([str(x[0]) for x in w_id])
        return res

    def sort_by_level(self, ids, names):
        """
        Show lists of methods sorted by level
        @param ids: indexes of selected methods
        @param names: selected methods as (module, class, method) list
        @return: None
        """
        self.rep_append = concrete_report(lambda row: ''.join((row[4].rjust(2), *row[1:4])))
        self.sel_count_handle(ids, names)

    def sort_by_module(self, ids, names):
        """
        Show lists of methods sorted by module name
        @param ids: indexes of selected methods
        @param names: selected methods as (module, class, method) list
        @return: None
        """
        self.rep_append = concrete_report(lambda row: ''.join(row[1:4]))
        self.sel_count_handle(ids, names)

    def sel_count_handle(self, ids, names):
        """
        This method does the same as the "first_only" method
        @param ids: db id-s of selected methods
        @param names: selected methods as (module, class, method) list
        @return:
        """
        logger.debug(ids)
        opt = len(ids) if len(ids) < 3 else 'more than 2'
        {1: self.do_1,
         2: self.do_2,
         'more than 2': self.do_more_than_2,
         }[opt](ids, names)

    def do_1(self, ids, names):
        """
        Only one method selected
        @param ids: - index of method - tuple of length 1
        @param names: - list of (module, class, method)
        @return: None
        """
        self.selected_only_one(ids, names, 0)

    def do_2(self, ids, names):
        self.selected_exactly_two(ids, names, 0)

    def do_more_than_2(self, ids, names):
        self.selected_more_than_two(ids, names, 0)

    def exec_sql_b(self, sql: str, sql_par: tuple):
        """
        exesute SQL - bind parameters with '?'
        @param sql:
        @param sql_par:
        @return: cursor
        """
        curs = self.conn.cursor()
        logger.debug(sql)
        logger.debug(sql_par)
        cc = curs.execute(sql, sql_par)
        return [(*map(str, x),) for x in cc]

    def exec_sql_f(self, sql: str, sql_par: tuple):
        """
        exesute SQL - insert parameters into SQL with str.format method
        @param sql:
        @param sql_par:
        @return: cursor
        """
        curs = self.conn.cursor()
        cc = curs.execute(sql.format(*sql_par))
        return [(*map(str, x),) for x in cc]


def pre_report(list_of_tuples):
    if not list_of_tuples:
        return (), ()
    all_ = any_ = set(list_of_tuples[0])
    for tpl in list_of_tuples:
        tt = set(tpl)
        all_ = all_ & tt
        any_ = any_ | tt

    return all_, any_


def concrete_report(sort_key):
    """
    sort report list
    @param sort_key: BY_MODULE = 0 or BY_LEVEL = 1
    @return: function that appends report lines in the order of sort_key
    """
    def sorted_report(report: list, lst: list, pre: Iterable = '', post: Iterable = ''):
        lst.sort(key=sort_key)
        for ll in lst:
            report.append('\t'.join((*pre, *ll, *post)))
    return sorted_report



menu_items = (
    'First level only',
    'sort by level',
    'sort by module',
    'append row',
    'delete',
    'edit links',
    'Cancel',    
)
upd0 = "update methods2 set {}=? where id=?;"
ins0 = (
    'insert into methods2 ('
    'type, module, class, method, remark) '
    'values (?, ?, ?, ?, ?);'
)
rep_head = '<============== {} ==============>'
memb_type = {
    'm': 'method',
    'sql': 'sql',
    's': 'signal',
    'c': 'constant',
    'f': 'field',
    'i': 'instance',
    'w': 'widget',
    '': '',
}
# method id-s from methods2 by their names
meth = "select id from methods2 where module || class || method in ('{}');"
# id-s of methods called from given method id
what_id = 'select id from simple_link where call_id = ?;'
# id-s of methods that call given method id
from_id = 'select call_id from simple_link where id = ?;'

what_call_1 = ('select a.type, a.module, a.class, a.method, min(b.level) '
               'from simple_link b join methods2 a on a.id = b.id '
               'where b.call_id = ? '
               )
called_from_1 = ('select a.type, a.module, a.class, a.method, min(b.level) '
                 'from simple_link b join methods2 a on a.id = b.call_id '
                 'where b.id = ? '
                 )
what_call_3 = ('select a.type, a.module, a.class, a.method, min(b.level) '
               'from simple_link b join methods2 a on a.id = b.id '
               'where b.call_id in ({}) '
               )
called_from_3 = ('select a.type, a.module, a.class, a.method, min(b.level) '
                 'from simple_link b join methods2 a on a.id = b.call_id '
                 'where b.id in ({}) '
                 )
where_mod = "and a.module = '{}' "
where_cls = "and a.class = '{}' "
and_level = 'and b.level = 1 '
group_by = 'group by a.type, a.module, a.class, a.method;'
headers = (
    "type",
    "module",
    "Class",
    "method",
    "Note",
)


def prep_sql(sql: str, mod: str, cls:str, lvl: int = 0) -> str:
    logger.debug(mod + '|' + cls)
    return (sql +
            ('' if mod == 'All' else where_mod.format(mod)) +
            ('' if cls == 'All' else where_cls.format(cls)) +
            (and_level if lvl else '') +
            group_by
            )


def addItem(model, id, type, module, class_, method, note):
    model.insertRow(0)
    idx0 = model.index(0, 0)
    model.setData(idx0, memb_type[type.lower()])
    model.setData(model.index(0, 1), module)
    model.setData(model.index(0, 2), class_)
    model.setData(model.index(0, 3), method)
    model.setData(model.index(0, 4), note if note else '')
    model.setData(idx0, id, Qt.UserRole)
    return idx0


def createModel(parent):
    model = QStandardItemModel(0, 5, parent)

    model.setHeaderData(0, Qt.Horizontal, headers[0])
    model.setHeaderData(1, Qt.Horizontal, headers[1])
    model.setHeaderData(2, Qt.Horizontal, headers[2])
    model.setHeaderData(3, Qt.Horizontal, headers[3])
    model.setHeaderData(4, Qt.Horizontal, headers[4])

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
    logger.debug(DB)
    conn = sqlite3.connect(DB)

    window = Window(conn)
    window.setSourceModel(createModel(window))
    window.show()

    sys.exit(app.exec_())
