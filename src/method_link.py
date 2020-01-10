from PyQt5.QtCore import (QSortFilterProxyModel, Qt, QModelIndex)
from PyQt5.QtGui import QStandardItemModel
from PyQt5.QtWidgets import (QApplication, QComboBox, QGridLayout, QGroupBox, QMenu, QTextEdit,
                             QLabel, QTreeView, QVBoxLayout, QWidget, QAbstractItemView)
import sqlite3
from pathlib import Path
from loguru import logger
from datetime import datetime
from collections.abc import Iterable
import operator as op

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


BY_MODULE, BY_LEVEL = range(2)

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
        Get module, class, method from current row
        @param index: index of current row
        @return: module, class, method from current row
        """
        if index.isValid():
            parent = self.parent(index)
            row = index.row()

            idx0 = self.mapToSource(self.index(row, 1, parent))
            idx1 = self.mapToSource(self.index(row, 2, parent))
            idx2 = self.mapToSource(self.index(row, 3, parent))

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

        self.set_filters()

        proxyLayout = QGridLayout()
        proxyLayout.addWidget(self.proxyView, 0, 0, 1, 3)
        proxyLayout.addWidget(self.filterModuleLabel, 1, 0)
        proxyLayout.addWidget(self.filterClassLabel, 1, 1)
        proxyLayout.addWidget(self.filterNoteLabel, 1, 2)
        proxyLayout.addWidget(self.filterModule, 2, 0)
        proxyLayout.addWidget(self.filterClass, 2, 1)
        proxyLayout.addWidget(self.filterNote, 2, 2)
        proxyLayout.addWidget(self.resView, 3, 0, 1, 3)
        proxyGroupBox = QGroupBox("Module/Class/Method list")
        proxyGroupBox.setLayout(proxyLayout)

        mainLayout = QVBoxLayout()
        mainLayout.addWidget(proxyGroupBox)
        self.setLayout(mainLayout)

        self.rep_append = None
        self.query_time = None

        self.setWindowTitle("Custom Sort/Filter Model")
        self.resize(800, 450)

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

        self.filterModule.currentIndexChanged.connect(self.textFilterChanged)
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
        if act == 'Cancel':
            return

        method_ids, method_names = self.get_selected_methods()

        {'First level only': self.first_level_only,
         'sort by level': self.sort_by_level,
         'sort by module': self.sort_by_module,
         }[act](method_ids, method_names)

    def get_selected_methods(self):
        """
        Returns two lists for rows selected in the proxyView:
        1) ids - id-s of selected methods
        2) methods - full names of selected methods, ie. (module, class, method)
        @return: ids, methods
        """
        self.resView.clear()
        indexes = self.proxyView.selectionModel().selectedRows()
        methods = []
        for idx in indexes:
            sql_par = self.proxyModel.get_data(idx)
            methods.append(sql_par)

        ids = self.exec_sql_f(meth,
                              ("','".join(tab_list(methods, delim='')),)
                              )

        tt = datetime.now()
        self.query_time = (tt.strftime("%b %d"), tt.strftime("%H:%M:%S"))
        self.resView.append(rep_head.format(self.query_time[0]))

        return [x[0] for x in ids], methods

    def first_level_only(self, ids, names):
        """
        Show lists of methods that is immediate child / parent
        ie. only from first level
        @param ids: indexes of selected methods
        @return:
        """
        self.rep_append = concrete_report(lambda row: ''.join(row[:3]))
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
            logger.debug(cc)
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
        self.rep_append = concrete_report(lambda row: ''.join((row[3].rjust(2), *row[:3])))
        self.sel_count_handle(ids, names)

    def sort_by_module(self, ids, names):
        """
        Show lists of methods sorted by module name
        @param ids: indexes of selected methods
        @param names: selected methods as (module, class, method) list
        @return: None
        """
        self.rep_append = concrete_report(lambda row: ''.join(row[:3]))
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
        logger.debug(sql_par)
        logger.debug(sql.format(*sql_par))
        cc = curs.execute(sql.format(*sql_par))
        return [(*map(str, x),) for x in cc]


def pre_report(list_of_tuples):
    logger.debug(list_of_tuples)
    if not list_of_tuples:
        return (), ()
    all_ = any_ = set(list_of_tuples[0])
    for tpl in list_of_tuples:
        tt = set(tpl)
        all_ = all_ & tt
        any_ = any_ | tt

    return all_, any_


def prep_sql(sql: str, mod: str, cls:str, lvl: int = 0) -> str:
    logger.debug(mod + '|' + cls)
    rr = '' if mod == 'All' else where_mod.format(mod)
    return (sql +
            ('' if mod == 'All' else where_mod.format(mod)) +
            ('' if cls == 'All' else where_cls.format(cls)) +
            (and_level if lvl else '')
            )


def tab_list(lst: list, delim: str = '\t') -> list:
    res = []
    logger.debug(delim)
    for ll in lst:
        logger.debug(ll)
        res.append(delim.join(ll))
    return res


def concrete_report(sort_key):
    """
    sort report list
    @param sort_key: BY_MODULE = 0 or BY_LEVEL = 1
    @return: function that appends report lines in the order of sort_key
    """
    def sorted_report(report: list, lst: list, pre: Iterable = '', post: Iterable = ''):
        logger.debug(lst[-1])
        if sort_key:
            lst.sort(key=sort_key)
        for ll in lst:
            report.append('\t'.join((*pre, *ll, *post)))
    return sorted_report


rep_head = '<============== {} ==============>'
memb_type = {
    'm': 'method',
    'sql': 'sql',
    's': 'signal',
    'c': 'constant',
    'f': 'field',
}
# method id-s from methods2 by their names
meth = "select id from methods2 where module || class || method in ('{}');"
# id-s of methods called from given method id
what_id = 'select id from simple_link where call_id = ?;'
# id-s of methods that call given method id
from_id = 'select call_id from simple_link where id = ?;'

what_call_1 = ('select a.type, a.module, a.class, a.method, b.level '
               'from simple_link b join methods2 a on a.id = b.id '
               'where b.call_id = ? ')
called_from_1 = ('select a.type, a.module, a.class, a.method, b.level '
                 'from simple_link b join methods2 a on a.id = b.call_id '
                 'where b.id = ? ')
what_call_3 = ('select a.type, a.module, a.class, a.method, b.level '
               'from simple_link b join methods2 a on a.id = b.id '
               'where b.call_id in ({}) ')
called_from_3 = ('select a.type, a.module, a.class, a.method, b.level '
                 'from simple_link b join methods2 a on a.id = b.call_id '
                 'where b.id in ({}) ')
where_mod = "and a.module = '{}' "
where_cls = "and a.class = '{}' "
and_level = 'and b.level = 1 '


def addItem(model, id, type, module, class_, method, note):
    model.insertRow(0)
    model.setData(model.index(0, 0), type)
    model.setData(model.index(0, 1), module)
    model.setData(model.index(0, 2), class_)
    model.setData(model.index(0, 3), method)
    model.setData(model.index(0, 4), note if note else '')


def createModel(parent):
    model = QStandardItemModel(0, 5, parent)

    model.setHeaderData(0, Qt.Horizontal, "type")
    model.setHeaderData(1, Qt.Horizontal, "module")
    model.setHeaderData(2, Qt.Horizontal, "Class")
    model.setHeaderData(3, Qt.Horizontal, "method")
    model.setHeaderData(4, Qt.Horizontal, "Note")

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
