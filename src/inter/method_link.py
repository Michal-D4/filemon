# src/inter/method_link.py

import sqlite3

from PyQt5.QtCore import QSortFilterProxyModel, Qt, QModelIndex, QPersistentModelIndex
from PyQt5.QtGui import QStandardItemModel
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QMenu,
    QTextEdit,
    QLabel,
    QTreeView,
    QVBoxLayout,
    QWidget,
    QAbstractItemView,
    QDialogButtonBox,
)
from pathlib import Path
from loguru import logger
from datetime import datetime
from collections import defaultdict
from collections.abc import Iterable, Callable

from complexity import cc_report
from method_tree import all_levels_link

# ---------------------------------------------------------
# doesn't catch exception without this code in Windows ! ! !
import sys

_excepthook = sys.excepthook


def my_exception_hook(exc_, value, traceback):
    print(traceback)
    _excepthook(exc_, value, traceback)
    sys.exit(1)


sys.excepthook = my_exception_hook
# ---------------------------------------------------------


class MySortFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super(MySortFilterProxyModel, self).__init__(parent)

        self.type_filter = ""
        self.type_all = True
        self.module_filter = ""
        self.module_all = True
        self.class_filter = ""
        self.class_all = True
        self.note_filter = True

    def filterAcceptsRow(self, sourceRow, sourceParent: QModelIndex):
        index0 = self.sourceModel().index(sourceRow, 0, sourceParent)
        index1 = self.sourceModel().index(sourceRow, 1, sourceParent)
        index2 = self.sourceModel().index(sourceRow, 2, sourceParent)
        index3 = self.sourceModel().index(sourceRow, 4, sourceParent)

        return (
            (self.type_all or self.sourceModel().data(index0) == self.type_filter)
            and (
                self.module_all or self.sourceModel().data(index1) == self.module_filter
            )
            and (self.class_all or self.sourceModel().data(index2) == self.class_filter)
            and (self.note_filter or self.sourceModel().data(index3) != "")
        )

    def lessThan(self, left, right):
        left_data = self.sourceModel().data(left)
        right_data = self.sourceModel().data(right)

        return (
            (left_data is not None)
            and (right_data is not None)
            and left_data < right_data
        )
        # return False

    def filter_changed(self, typ, mod_, cls, note):
        self.type_all = typ == "All"
        self.type_filter = typ
        self.module_all = mod_ == "All"
        self.module_filter = mod_
        self.class_all = cls == "All"
        self.class_filter = cls
        self.note_filter = note == "All"
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
                for i in range(self.columnCount()):
                    idx = self.mapToSource(self.index(row, i, parent))
                    res.append(self.sourceModel().data(idx))
                return res
            elif role == Qt.UserRole:
                idx = self.mapToSource(self.index(row, 0, parent))
                return self.sourceModel().data(idx, Qt.UserRole)
        return None

    def setData(self, index, data, role=Qt.DisplayRole):
        if role == Qt.EditRole:
            col = index.column()
            idn0 = self.mapToSource(self.index(index.row(), 0, self.parent(index)))
            if col == 0:
                data_0 = memb_type[data]
                if data_0:
                    data_ins = data
                    data = data_0
                else:
                    data_ins = memb_type[data]
                    data = data if data_ins else data_ins
            else:
                data_ins = data

            idx = self.sourceModel().data(idn0, Qt.UserRole)
            field = main_headers.split(",")[col]
            conn.execute(upd0.format(field), (data_ins, idx))
            conn.commit()
        ok = super(MySortFilterProxyModel, self).setData(index, data, role)
        return ok


class Window(QWidget):
    def __init__(self, connection):
        super(Window, self).__init__()

        self.conn = connection

        self.proxyModel = MySortFilterProxyModel(self)
        self.proxyModel.setDynamicSortFilter(True)

        self.proxyView = QTreeView()
        set_tree_view(self.proxyView)
        self.proxyView.setModel(self.proxyModel)
        self.proxyView.customContextMenuRequested.connect(self.pop_menu)

        self.filterType = QComboBox()
        self.filterModule = QComboBox()
        self.filterClass = QComboBox()
        self.filterNote = QComboBox()

        self.infLabel = QLabel()
        self.link_type = QComboBox()

        self.resView = QTreeView()
        set_tree_view(self.resView)
        self.resModel = QSortFilterProxyModel(self.resView)
        self.resView.setModel(self.resModel)
        self.resView.customContextMenuRequested.connect(self.menu_res_view)

        self.link_box = self.set_layout()

        self.sort_key = None
        self.repo = []
        self.old_links = []
        self.new_links = []
        self.query_time = time_run()
        self.curr_id_db = 0

        self.setWindowTitle("Custom Sort/Filter Model")
        self.resize(900, 750)

    def set_layout(self):
        filter_box: QGroupBox = self.set_filter_box()
        height = 92
        filter_box.setMaximumHeight(height)
        link_box = self.set_link_box()
        link_box.setMaximumHeight(height)
        link_box.hide()
        stack_layout = QVBoxLayout()
        stack_layout.addWidget(filter_box)
        stack_layout.addWidget(link_box)

        proxyLayout = QGridLayout()
        proxyLayout.addWidget(self.proxyView, 0, 0)
        proxyLayout.addLayout(stack_layout, 1, 0)
        proxyLayout.addWidget(self.resView, 2, 0)
        proxyLayout.setRowStretch(0, 5)
        proxyLayout.setRowStretch(1, 0)
        proxyLayout.setRowStretch(2, 3)

        proxyGroupBox = QGroupBox("Module/Class/Method list")
        proxyGroupBox.setLayout(proxyLayout)

        mainLayout = QVBoxLayout()
        mainLayout.addWidget(proxyGroupBox)
        self.setLayout(mainLayout)

        return link_box

    def save_clicked(self, btn):
        {"Save": save_init, "Copy to clipboard": copy_to_clipboard}[btn.text()]()

    def set_filter_box(self):
        save_btn = QDialogButtonBox(Qt.Vertical)
        save_btn.addButton("Save", QDialogButtonBox.ActionRole)
        save_btn.addButton("Copy to clipboard", QDialogButtonBox.ActionRole)
        save_btn.clicked.connect(self.save_clicked)
        self.filterNote.addItem("All")
        self.filterNote.addItem("Not blank")

        filterTypeLabel = QLabel("&Type Filter")
        filterTypeLabel.setBuddy(self.filterType)
        filterModuleLabel = QLabel("&Module Filter")
        filterModuleLabel.setBuddy(self.filterModule)
        filterClassLabel = QLabel("&Class Filter")
        filterClassLabel.setBuddy(self.filterClass)
        filterNoteLabel = QLabel("&Remark Filter")
        filterNoteLabel.setBuddy(self.filterNote)

        filter_box = QGridLayout()
        filter_box.addWidget(filterTypeLabel, 0, 0)
        filter_box.addWidget(filterModuleLabel, 0, 1)
        filter_box.addWidget(filterClassLabel, 0, 2)
        filter_box.addWidget(filterNoteLabel, 0, 3)
        filter_box.addWidget(save_btn, 0, 4, 2, 1)
        filter_box.addWidget(self.filterType, 1, 0)
        filter_box.addWidget(self.filterModule, 1, 1)
        filter_box.addWidget(self.filterClass, 1, 2)
        filter_box.addWidget(self.filterNote, 1, 3)

        self.set_filters_combo()
        self.textFilterChanged()

        self.filterType.currentIndexChanged.connect(self.textFilterChanged)
        self.filterModule.currentIndexChanged.connect(self.textFilterModuleChanged)
        self.filterClass.currentIndexChanged.connect(self.textFilterChanged)
        self.filterNote.currentIndexChanged.connect(self.textFilterChanged)

        grp_box = QGroupBox()
        grp_box.setFlat(True)
        grp_box.setLayout(filter_box)
        return grp_box

    def set_filters_combo(self):
        curs = self.conn.cursor()

        self.filterType.clear()
        self.filterType.addItem("All")
        curs.execute(qsel3)
        for cc in curs:
            logger.debug(f"{cc[0]},  {memb_type[cc[0]]}")
            self.filterType.addItem(memb_type[cc[0]])

        self.filterModule.clear()
        self.filterModule.addItem("All")
        self.filterModule.addItem("")
        curs.execute(qsel0)
        for cc in curs:
            self.filterModule.addItem(cc[0])

        self.filterClass.clear()
        self.filterClass.addItem("All")
        curs.execute(qsel1)
        for cc in curs:
            self.filterClass.addItem(cc[0])

    def textFilterModuleChanged(self):
        curs = self.conn.cursor()
        self.filterClass.clear()
        self.filterClass.addItem("All")
        if self.filterModule.currentText() == "All":
            curs.execute(qsel1)
        else:
            curs.execute(
                (
                    "select distinct class from methods2 "
                    "where module = ? order by class;"
                ),
                (self.filterModule.currentText(),),
            )

        for cc in curs:
            self.filterClass.addItem(cc[0])

    def menu_res_view(self, pos):
        """
        only copy to clipboard
        """
        menu = QMenu(self)
        menu.addAction("clipboard")
        action = menu.exec_(self.resView.mapToGlobal(pos))
        if action:
            self._to_clipboard()

    def _to_clipboard(self):
        rr = []
        for rep in self.repo:
            pp = [str(x) for x in rep]
            rr.append("\t".join(pp))

        QApplication.clipboard().setText("\n".join(rr))

    def pop_menu(self, pos):
        idx = self.proxyView.indexAt(pos)
        if idx.isValid():
            menu = QMenu(self)
            menu.addAction("First level only")
            menu.addSeparator()
            menu.addAction("sort by level")
            menu.addAction("sort by module")
            menu.addSeparator()
            menu.addAction("append row")
            menu.addAction("delete rows")
            menu.addAction("edit links")
            menu.addSeparator()
            menu.addAction("not called")
            menu.addSeparator()
            menu.addAction("refresh")
            menu.addSeparator()
            menu.addAction("reload")
            menu.addSeparator()
            menu.addAction("complexity")
            action = menu.exec_(self.proxyView.mapToGlobal(pos))
            if action:
                self.menu_action(action.text())

    def setSourceModel(self, model: QStandardItemModel):
        self.proxyModel.setSourceModel(model)
        set_columns_width(self.proxyView)
        set_headers(self.proxyModel, main_headers)

    def textFilterChanged(self):
        self.proxyModel.filter_changed(
            self.filterType.currentText(),
            self.filterModule.currentText(),
            self.filterClass.currentText(),
            self.filterNote.currentText(),
        )

    def menu_action(self, act: str):
        menu_items = (
            "First level only",
            "sort by level",
            "sort by module",
            "append row",
            "edit links",
            "delete rows",
            "refresh",
            "not called",
            "complexity",
            "reload",
        )

        if act in menu_items[:3]:
            self.prepare_report_view()
            method_ids, method_names = self.get_selected_methods()
            {
                menu_items[0]: self.first_level_only,
                menu_items[1]: self.sort_by_level,
                menu_items[2]: self.sort_by_module,
            }[act](method_ids, method_names)
        elif act in menu_items[5:]:
            {
                menu_items[5]: self.delete_selected_rows,
                menu_items[6]: self.refresh,
                menu_items[7]: self.is_not_called,
                menu_items[8]: self.recalc_complexity,
                menu_items[9]: reload_data,
            }[act]()
        else:
            curr_idx = self.proxyView.currentIndex()
            {menu_items[3]: self.append_row, menu_items[4]: self.edit_links}[act](
                curr_idx
            )

    def recalc_complexity(self):
        mm = self.filterModule.currentText()
        module = "" if mm == "All" else mm
        cc_list = cc_report(module)
        for row in cc_list:
            self.update_cc(row)

    def update_cc(self, row: Iterable):
        """
        @param row: type(C/F/M), module, class, method, CC, length
        """
        sql_sel = (
            "select id from methods2 where "
            "type = ? and module = ? and class = ? and method = ?"
        )
        sql_upd = "update methods2 set cc_old = cc, cc = ?, length = ? " "where id = ?"
        sql_ins = (
            "insert into methods2 (CC, length, type, module, "
            "Class, method, remark) values(?,?,?,?,?,?,?);"
        )
        rr = (*row,)
        qq = self.conn.cursor()
        id = qq.execute(sql_sel, rr[2:]).fetchone()
        if id:
            qq.execute(sql_upd, (*rr[:2], id[0]))
        else:
            tt = datetime.now().strftime("%Y-%m-%d %H:%M")
            qq.execute(sql_ins, (*rr, tt))
        self.conn.commit()

    def is_not_called(self):
        qq = self.conn.cursor()
        qq.execute(not_called)
        self.repo.clear()
        for row in qq:
            self.repo.append(row)
        model = QStandardItemModel(0, len(call_headers.split(",")), self.resView)
        fill_in_model(model, self.repo, user_data=False)
        self.resModel.setSourceModel(model)
        set_columns_width(self.resView, proportion=(2, 2, 5, 7, 7, 2, 3, 5))
        set_headers(self.resModel, call_headers)

    def refresh(self):
        model = QStandardItemModel(0, len(main_headers.split(",")), self.proxyView)
        qq = conn.cursor()
        qq.execute(qsel2)
        vv = ((x[0], memb_type[x[1]], *x[2:-2], x[-2].rjust(4), x[-1]) for x in qq)
        fill_in_model(model, vv)
        self.setSourceModel(model)

    def prepare_report_view(self):
        self.repo.clear()
        model = QStandardItemModel(0, len(rep_headers.split(",")), self.resView)
        self.resModel.setSourceModel(model)
        set_columns_width(self.resView, proportion=(3, 2, 2, 2, 7, 7, 7, 1))
        set_headers(self.resModel, rep_headers)
        self.query_time = time_run()

    def append_row(self, index: QModelIndex):
        crs = conn.cursor()
        items = (
            "",
            self.proxyModel.module_filter,
            self.proxyModel.class_filter,
            "",
            self.query_time[0],
        )
        crs.execute(ins0, items)
        idn = crs.lastrowid
        conn.commit()

        model = self.proxyModel.sourceModel()
        parent = self.proxyModel.mapToSource(index.parent())

        model.beginInsertRows(parent, 0, 0)
        add_row(model, (idn, *items), True)
        model.endInsertRows()

    def delete_selected_rows(self):
        idx_list = self.proxyView.selectionModel().selectedRows()
        idx_list.reverse()
        parent = QModelIndex()
        for p_idx in idx_list:
            if p_idx.isValid():
                row = p_idx.row()
                self.delete_from_db(p_idx)
                self.proxyModel.beginRemoveRows(parent, row, row)
                self.proxyModel.removeRows(row, 1)
                self.proxyModel.endRemoveRows()

    def delete_from_db(self, index: QModelIndex):
        id_db = self.proxyModel.get_data(index, Qt.UserRole)
        conn.execute("delete from methods2 where id=?;", (id_db,))
        conn.commit()

    def edit_links(self, index: QModelIndex):
        ss = self.proxyModel.get_data(index)
        id_db = self.proxyModel.get_data(index, Qt.UserRole)
        self.infLabel.setText("{:04d}: {}".format(id_db, ".".join(ss[1:4])))
        self.link_box.show()

        model = QStandardItemModel(0, len(link_headers.split(",")), self.resView)
        qq = conn.cursor()
        qq.execute(sql_links.format(id_db, id_db))
        fill_in_model(model, qq)
        self.old_links = qq.execute(sql_id2.format(id_db, id_db)).fetchall()
        self.new_links = self.old_links[:]
        self.curr_id_db = id_db

        self.resModel.setSourceModel(model)
        set_columns_width(self.resView, proportion=(3, 2, 8, 8, 8))
        set_headers(self.resModel, link_headers)

    def set_link_box(self):
        self.link_type.addItem("What")
        self.link_type.addItem("From")
        f_type = QLabel("Link &type:")
        f_type.setBuddy(self.link_type)

        ok_btn = QDialogButtonBox()
        ok_btn.setStandardButtons(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok_btn.addButton("+", QDialogButtonBox.ActionRole)
        ok_btn.addButton("-", QDialogButtonBox.ActionRole)
        ok_btn.clicked.connect(self.btn_clicked)

        l_box = QGridLayout()
        l_box.addWidget(self.infLabel, 0, 0)
        l_box.addWidget(f_type, 1, 0)
        l_box.addWidget(self.link_type, 1, 1)
        l_box.addWidget(ok_btn, 1, 2)
        l_box.setRowStretch(0, 1)
        l_box.setRowStretch(1, 0)
        l_box.setRowStretch(2, 1)

        grp = QGroupBox()
        grp.setFlat(True)
        grp.setLayout(l_box)
        return grp

    def btn_clicked(self, btn):
        {
            "OK": self.ok_clicked,
            "Cancel": self.cancel_cliked,
            "+": self.plus_clicked,
            "-": self.minus_clicked,
        }[btn.text()]()

    def ok_clicked(self):
        s_new = set(self.new_links)
        s_old = set(self.old_links)
        added = s_new - s_old
        removed = s_old - s_new
        if removed:
            for link in removed:
                conn.execute("delete from one_link where id=? and call_id=?;", link)
        if added:
            for link in added:
                conn.execute("insert into one_link (id, call_id) values (?, ?);", link)
        conn.commit()
        self.resModel.sourceModel().clear()
        self.link_box.hide()
        if removed or added:
            recreate_links()

    def cancel_cliked(self):
        self.resModel.sourceModel().clear()
        self.link_box.hide()

    def plus_clicked(self):
        # 1. add to resModel
        stat = self.link_type.currentText()
        idx_sel = self.proxyView.selectedIndexes()
        idx_col0 = [ix for ix in idx_sel if ix.column() == 0]
        to_insert = []
        for idx in idx_col0:
            id = self.proxyModel.get_data(idx, Qt.UserRole)
            link = (id, self.curr_id_db) if stat == "What" else (self.curr_id_db, id)
            if link in self.new_links or link[::-1] in self.new_links:
                continue
            self.new_links.append(link)
            row = self.proxyModel.get_data(idx)[:-1]
            to_insert.append([id, stat] + row)

        if to_insert:
            self.resModel.beginInsertRows(QModelIndex(), 0, 0)
            model = self.resModel.sourceModel()
            for row in to_insert:
                add_row(model, row, True)
            self.resModel.endInsertRows()

    def minus_clicked(self):
        idx_sel = self.resView.selectionModel().selectedRows()
        idx_sel.reverse()
        for idx in idx_sel:
            self.remove_in_new_links(idx)
            self.remove_row(idx)

    def remove_in_new_links(self, index: QModelIndex):
        link_type = self.resModel.data(index)
        id_db = self.resModel.data(index, Qt.UserRole)
        link = (
            (id_db, self.curr_id_db)
            if link_type == "What"
            else (self.curr_id_db, id_db)
        )
        self.new_links.remove(link)

    def remove_row(self, index):
        row = index.row()
        self.resModel.beginRemoveRows(QModelIndex(), row, row)
        self.resModel.removeRows(row, 1)
        self.resModel.endRemoveRows()

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
        self.sort_key = sort_keys["by module"]
        opt = len(ids) if len(ids) < 3 else "more than 2"
        {1: self.first_1, 2: self.first_2, "more than 2": self.first_more_than_2}[opt](
            ids, names
        )

    def first_1(self, ids, names):
        """
        Only one method selected
        @param ids: - index of method - tuple of length 1
        @param names: - list of (module, class, method)
        @return: None
        """
        self.selected_only_one(ids, names, 1)

    def selected_only_one(self, ids, names, lvl):
        pre = (self.query_time[1], "Sel", "")
        self.sorted_report(self.repo, (pre, names, ""))
        what_sql = prep_sql(
            what_call_1,
            self.filterModule.currentText(),
            self.filterClass.currentText(),
            lvl,
        )
        lst = self.first_1_part(ids, what_sql)
        pre = (self.query_time[1], "What", "")
        self.sorted_report(self.repo, (pre, lst, ""))
        from_sql = prep_sql(
            called_from_1,
            self.filterModule.currentText(),
            self.filterClass.currentText(),
            lvl,
        )
        lst = self.first_1_part(ids, from_sql)
        pre = (self.query_time[1], "From", "")
        self.sorted_report(self.repo, (pre, lst, ""))
        fill_in_model(self.resModel.sourceModel(), self.repo, user_data=False)

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
        pre = (self.query_time[1], "Sel")
        n_names = [("A", *names[0]), ("B", *names[1])]
        self.sorted_report(self.repo, (pre, n_names, ""))
        what_sql = prep_sql(
            what_call_1,
            self.filterModule.currentText(),
            self.filterClass.currentText(),
            lvl,
        )
        lst_a = self.first_1_part((ids[0],), what_sql)
        lst_b = self.first_1_part((ids[1],), what_sql)
        self.report_four(lst_a, lst_b, "What")
        from_sql = prep_sql(
            called_from_1,
            self.filterModule.currentText(),
            self.filterClass.currentText(),
            lvl,
        )
        lst_a = self.first_1_part((ids[0],), from_sql)
        lst_b = self.first_1_part((ids[1],), from_sql)
        self.report_four(lst_a, lst_b, "From")

    def report_four(self, lst_a, lst_b, what):
        self.sorted_report(
            self.repo,
            ((self.query_time[1], what, "A | B"), list(set(lst_a) | set(lst_b)), ""),
        )
        self.sorted_report(
            self.repo,
            ((self.query_time[1], what, "A - B"), list(set(lst_a) - set(lst_b)), ""),
        )
        self.sorted_report(
            self.repo,
            ((self.query_time[1], what, "B - A"), list(set(lst_b) - set(lst_a)), ""),
        )
        self.sorted_report(
            self.repo,
            ((self.query_time[1], what, "A & B"), list(set(lst_a) & set(lst_b)), ""),
        )
        fill_in_model(self.resModel.sourceModel(), self.repo, user_data=False)

    def first_more_than_2(self, ids, names):
        self.selected_more_than_two(ids, names, 1)

    def selected_more_than_two(self, ids, names, lvl):
        pre = (self.query_time[1], "Sel", "")
        self.sorted_report(self.repo, (pre, names, ""))

        self.report_23(ids, "What", lvl)

        self.report_23(ids, "From", lvl)

    def report_23(self, ids, param, lvl):
        opt = {"What": (what_id, what_call_3), "From": (from_id, called_from_3)}[param]
        links = self.exec_sql_2(ids, lvl, opt[0])
        rep_prep = pre_report(links)

        self.methods_by_id_list(opt[1], rep_prep[0:3:2], param, "ALL")

        self.methods_by_id_list(opt[1], rep_prep[1:], param, "ANY")

        fill_in_model(self.resModel.sourceModel(), self.repo, user_data=False)

    def exec_sql_2(self, ids, lvl, sql):
        res = []
        curs = self.conn.cursor()
        loc_sql = sql.format("and level=1" if lvl else "")
        for id_ in ids:
            w_id = curs.execute(loc_sql, (id_,))
            res.append(dict(w_id))
        return res

    def methods_by_id_list(self, sql: str, ids: list, what: str, all_any: str):
        if ids:
            cc = self.exec_sql_f(sql, (",".join((map(str, ids[0]))),))
            pre = (self.query_time[1], what, all_any)
            vv = insert_levels(cc, ids[1])
            self.sorted_report(self.repo, (pre, vv, ""))

    def sort_by_level(self, ids, names):
        """
        Show lists of methods sorted by level
        @param ids: indexes of selected methods
        @param names: selected methods as (module, class, method) list
        @return: None
        """
        self.sort_key = sort_keys["by level"]
        self.sel_count_handle(ids, names)

    def sort_by_module(self, ids, names):
        """
        Show lists of methods sorted by module name
        @param ids: indexes of selected methods
        @param names: selected methods as (module, class, method) list
        @return: None
        """
        self.sort_key = sort_keys["by module"]
        self.sel_count_handle(ids, names)

    def sel_count_handle(self, ids, names):
        """
        This method does the same as the "first_only" method
        @param ids: db id-s of selected methods
        @param names: selected methods as (module, class, method) list
        @return:
        """
        opt = len(ids) if len(ids) < 3 else "more than 2"
        {1: self.do_1, 2: self.do_2, "more than 2": self.do_more_than_2}[opt](
            ids, names
        )

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
        @return: list of lists of strings
        """
        curs = self.conn.cursor()
        cc = curs.execute(sql, sql_par)
        return [(*map(str, x),) for x in cc]

    def exec_sql_f(self, sql: str, sql_par: tuple):
        """
        exesute SQL - insert parameters into SQL with str.format method
        @param sql:
        @param sql_par:
        @return: list of lists of strings
        """
        curs = self.conn.cursor()
        cc = curs.execute(sql.format(*sql_par))
        return [(*map(str, x),) for x in cc]

    def sorted_report(self, report: list, rep_data: tuple):
        pre, lst, post = rep_data
        lst.sort(key=self.sort_key)
        for ll in lst:
            report.append((*pre, *ll, *post))


def save_init():
    """
    save content of methods2 & one_link tables in file
    """
    ts = datetime.now().strftime("_%d-%m-%Y_%H%M%S")
    save_method_list(ts)
    save_links_table(ts)


def save_method_list(ts: str):
    out_file = Path.cwd() / "".join(("tmp/xls/meth", ts, ".txt"))
    outfile = open(out_file, "w", encoding="utf­8")
    csr = conn.cursor()
    sql = (
        "select ID,type,module,class,method,COALESCE(CC,''),"
        "COALESCE(CC_old,''),COALESCE(length,0),"
        "COALESCE(remark,'') from methods2;"
    )
    csr.execute(sql)
    for row in csr:
        rr = (row[0], memb_key[memb_type[row[1]]], *row[2:])
        outfile.write(",".join((*map(str, rr), "\n")))


def save_links_table(ts: str):
    out_file = Path.cwd() / "".join(("tmp/xls/link", ts, ".txt"))
    outfile = open(out_file, "w", encoding="utf­8")
    csr = conn.cursor()
    csr.execute("select * from one_link;")
    for row in csr:
        outfile.write(",".join((*map(str, row), "\n")))


def copy_to_clipboard():
    """
    copy current content of methods2 & one_link tables in clipboard
    """
    csr = conn.cursor()
    csr.execute(save_links)
    to_save = []
    for row in csr:
        to_save.append("\t".join(row))

    QApplication.clipboard().setText("\n".join(to_save))


def reload_data():
    in_path = Path.cwd() / "tmp/xls"
    sql1 = (
        "delete from methods2;",
        "insert into methods2  ("
        "ID, type, module, class, method, CC, CC_old, length, remark) "
        "values (?, ?, ?, ?, ?, ?, ?, ?, ?);",
    )
    input_file = in_path / "methods.txt"
    load_table(input_file, sql1)

    sql2 = (
        "delete from one_link;",
        "insert into one_link (id, call_id) values (?, ?);",
    )
    input_file = in_path / "links.txt"
    load_table(input_file, sql2)

    curs = conn.cursor()
    curs.execute("delete from links;")
    conn.commit()
    curs.execute(all_levels_link)
    conn.commit()


def load_table(input_file: str, sql: str):
    curs = conn.cursor()
    curs.execute(sql[0])
    conn.commit()
    with open(input_file) as fl:
        for line in fl:
            curs.execute(sql[1], line.split(",")[:-1])
        conn.commit()


def pre_report(list_of_dicts):
    if not list_of_dicts:
        return (), (), {}
    rd = list_of_dicts[0]
    all_ = set(rd.keys())
    any_ = set(rd.keys())
    for tpl in list_of_dicts[1:]:
        rd.update(tpl)
        tt = set(tpl.keys())
        all_ = all_ & tt
        any_ = any_ | tt

    return all_, any_, rd


def set_tree_view(view: QTreeView):
    view.setRootIsDecorated(False)
    view.setAlternatingRowColors(True)
    view.setSortingEnabled(True)
    view.sortByColumn(1, Qt.AscendingOrder)
    view.setContextMenuPolicy(Qt.CustomContextMenu)
    view.setSelectionMode(QAbstractItemView.ExtendedSelection)


memb_type = defaultdict(str)
memb_type.update(
    {
        "M": "method",
        "sql": "sql",
        "S": "signal",
        "cc": "constant",
        "C": "Class",
        "F": "function",
        "G": "global",
        "i": "instance",
        "W": "widget",
        "P": "package",
    }
)
memb_key = defaultdict(str)
memb_key.update(
    {
        "method": "M",
        "sql": "sql",
        "signal": "S",
        "constant": "cc",
        "Class": "C",
        "function": "F",
        "global": "G",
        "instance": "i",
        "widget": "W",
        "package": "P",
    }
)
upd0 = "update methods2 set {}=? where id=?;"
ins0 = (
    "insert into methods2 ("
    "type, module, class, method, remark) "
    "values (?, ?, ?, ?, ?);"
)
sql_links = (
    "select a.id, 'From', a.type, a.module, a.class, a.method "
    "from methods2 a join one_link b on b.call_id = a.id "
    "where b.id = {} "
    "union select a.id, 'What', a.type, a.module, a.class, a.method "
    "from methods2 a join one_link b on b.id = a.id "
    "where b.call_id = {};"
)
sql_id2 = (
    "select * from one_link where id={} "
    "union select * from one_link where call_id={}"
)
qsel0 = "select distinct module from methods2 where module != '' order by module;"
qsel1 = "select distinct class from methods2 order by upper(class);"
qsel3 = "select distinct type from methods2 order by upper(type);"
qsel2 = (
    "select ID, type, module, class, method, CC, CC_old, "
    "COALESCE(length, ''), remark from methods2;"
)
not_called = (
    "with not_called (id) as (select id from methods2 "
    "except select id from one_link) "
    "select a.Id,a.type,a.module,a.class,a.method,a.cc,a.length,a.remark "
    "from methods2 a join not_called b on a.id = b.id;"
)
# id-s of methods called from given method id
what_id = "select id idn, min(level) from links " "where call_id = ? {} group by idn;"
# id-s of methods that call given method id
from_id = "select call_id idn, min(level) from links " "where id = ? {} group by idn;"

what_call_1 = (
    "select a.type, a.module, a.class, a.method, min(b.level) "
    "from links b join methods2 a on a.id = b.id "
    "where b.call_id = ? "
)
called_from_1 = (
    "select a.type, a.module, a.class, a.method, min(b.level) "
    "from links b join methods2 a on a.id = b.call_id "
    "where b.id = ? "
)
what_call_3 = (
    "select type, module, class, method, id " "from methods2 where id in ({}) "
)
called_from_3 = (
    "select type, module, class, method, id " "from methods2 where id in ({}) "
)
where_mod = "and a.module = '{}' "
where_cls = "and a.class = '{}' "
and_level = "and b.level = 1 "
group_by = "group by a.type, a.module, a.class, a.method;"
main_headers = "type,module,Class,method,cc,occ,length,remark"
rep_headers = "time,What/From,All/Any,Type,module,Class,method,level"
link_headers = "What/From,Type,module,Class,method"
call_headers = "id,type,module,class,method,cc,length,comment"
save_links = (
    "select a.type type, a.module module, a.class class, a.method method, "
    "COALESCE(b.method,'') c_method, COALESCE(b.module,'') c_module, "
    "COALESCE(b.class,'') c_class, COALESCE(a.remark,'') remark "
    "from methods2 a left join one_link c on c.id = a.id "
    "left join methods2 b on b.id = c.call_ID "
    "order by module, type, class, method, c_module, c_class, c_method;"
)
sort_keys = {
    "by module": lambda row: "".join(row[1:4]),
    "by level": lambda row: "".join((row[4].rjust(2), *row[1:4])),
}


def insert_levels(cc: sqlite3.Cursor, dd: dict):
    rr = []
    for row in cc:
        rr.append((*row[:-1], str(dd[int(row[-1])])))
    return rr


def recreate_links():
    re_sql = (  # all levels link
        "with recc (ID, call_ID, level) as ("
        "select ID, call_ID, 1 from one_link "
        "union select b.ID, a.call_ID, a.level+1 "
        "from recc a join one_link b on b.call_ID = a.ID) "
        "insert into links (ID, call_ID, level) "
        "select ID, call_ID, min(level) from recc group by ID, call_ID;"
    )
    conn.execute("delete from links;")
    conn.execute(re_sql)
    conn.commit()


def time_run():
    tt = datetime.now()
    return tt.strftime("%d-%m-%Y"), tt.strftime("%H:%M:%S")


def prep_sql(sql: str, mod: str, cls: str, lvl: int = 0) -> str:
    return (
        sql
        + ("" if mod == "All" else where_mod.format(mod))
        + ("" if cls == "All" else where_cls.format(cls))
        + (and_level if lvl else "")
        + group_by
    )


def add_row(model: QStandardItemModel, row: Iterable, user_data: bool):
    """
    @param: model
    @param: row  - data 
    @param: user_data - True when first item of row is user data
    """
    model.insertRow(0)
    if user_data:
        model.setData(model.index(0, 0), row[0], Qt.UserRole)
        rr = row[1:]
    else:
        rr = row

    for k, item in enumerate(rr):
        model.setData(model.index(0, k), item if item else "")


def fill_in_model(
    model: QStandardItemModel, row_list: Iterable, user_data: bool = True
):
    for cc in row_list:
        add_row(model, cc, user_data)


def set_headers(model, headers):
    for i, header in enumerate(headers.split(",")):
        model.setHeaderData(i, Qt.Horizontal, header)


def set_columns_width(view, proportion=(4, 6, 8, 8, 2, 2, 3, 5)):
    ss = sum(proportion)
    model = view.model()
    n = model.columnCount()
    w = view.width()
    for k in range(n):
        view.setColumnWidth(k, w / ss * proportion[k])


if __name__ == "__main__":
    import sys

    logger.remove()
    fmt = (
        "<green>{time:HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> "
        "- <level>{message}</level>"
    )
    logger.add(sys.stderr, level="DEBUG", format=fmt, enqueue=True)

    app = QApplication(sys.argv)
    DB = Path.cwd() / "prj.db"
    logger.debug(DB)
    conn = sqlite3.connect(DB)

    window = Window(conn)
    model = QStandardItemModel(0, len(main_headers.split(",")), window)
    qq = conn.cursor()
    qq.execute(qsel2)
    vv = ((x[0], memb_type[x[1]], *x[2:-2], x[-2].rjust(4), x[-1]) for x in qq)
    fill_in_model(model, vv)
    window.setSourceModel(model)
    window.show()

    sys.exit(app.exec_())
