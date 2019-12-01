# view/item_edit.py

import re

from PyQt5.QtCore import QItemSelectionModel
from PyQt5.QtWidgets import QDialog

from src.core.table_model import TableModel2
from src.ui.ui_items_edit import Ui_ItemChoice


class ItemEdit(QDialog):
    def __init__(self, titles, items, selected_items, re_=False, parent=None):
        super(ItemEdit, self).__init__(parent)
        self.view = Ui_ItemChoice()
        self.view.setupUi(self)

        self.pattern = re_

        self.view.label_1.setText(titles[0])
        self.view.label_2.setText(titles[1])
        self.setWindowTitle(titles[2])

        self.list_items = items
        self.sel_indexes = [self.list_items.index(item) for item in selected_items]

        model = TableModel2(parent=self.view.items)
        self.view.items.setModel(model)

        self.calc_column_width()

        self.view.items.resizeEvent = self.resize_event

    def calc_column_width(self):
        if self.list_items:
            len_ = 0
            i_max = 0
            for i in range(len(self.list_items)):
                if len(self.list_items[i]) > len_:
                    len_ = len(self.list_items[i])
                    i_max = i

            self.max_width = self.view.items.fontMetrics(). \
                                 boundingRect(self.list_items[i_max]).width() + 20
        else:
            self.max_width = 20

    def get_result(self):
        if self.pattern:
            return re.findall(r"([\w]*\w)", self.view.in_field.toPlainText())
        return [str.lstrip(item) for item in self.view.in_field.toPlainText().split(',')]

    def resize_event(self, event):
        w = event.size().width()
        if w < self.max_width:
            self.max_width = w // 2 - 20
        col_no = w // self.max_width
        col_no = max(1, col_no)
        col_no = min(col_no, 10)
        if col_no != self.view.items.model().columnCount():
            self._setup_model(col_no)

    def selection_changed(self, selected, deselected):
        """
        Changed selection in self.view.table_items
        :param selected:   QList<QModelIndex>
        :param deselected: QList<QModelIndex>
        :return: None
        """
        txt = self.view.in_field.toPlainText()
        id2 = deselected.indexes()
        if id2:
            for jj in id2:
                tt = self.view.items.model().data(jj)
                if tt:
                    txt = re.sub(tt, '', txt)
                    self.sel_indexes.remove(self.list_items.index(tt))
            if set(txt).issubset(' ,'):
                txt = ''
            else:
                txt = txt.strip(' ,')

        idx = selected.indexes()
        if idx:
            for jj in idx:
                tt = self.view.items.model().data(jj)
                if tt:
                    txt = ', '.join((txt, tt)) if txt else tt
                    self.sel_indexes.append(self.list_items.index(tt))

        txt = re.sub(',,', ',', txt)

        self.view.in_field.setText(txt)

    def _setup_model(self, col_no):
        row_no = len(self.list_items) // col_no + 1
        aa = []
        for i in range(row_no):
            aa.append(tuple(self.list_items[i*col_no: (i + 1)*col_no]))

        model = TableModel2(parent=self.view.items)
        model.setColumnCount(col_no)

        for a in aa:
            model.append_row(a)

        self.view.items.setModel(model)

        for i in range(0, col_no):
            self.view.items.horizontalHeader().resizeSection(i, self.max_width)

        self.view.items.selectionModel().selectionChanged.connect(self.selection_changed)
        self.set_selection(col_no)

    def set_selection(self, col_no):
        self.view.items.selectionModel().clearSelection()
        self.view.in_field.setText('')
        model = self.view.items.model()
        tmp = self.sel_indexes.copy()
        self.sel_indexes.clear()
        for idx in tmp:
            row_, col_ = divmod(idx, col_no)
            index_ = model.index(row_, col_)
            self.view.items.selectionModel().select(index_, QItemSelectionModel.Select)


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    labels = ['label1', 'label2', 'Window title']
    table_items = ['item {}'.format(i + 1) for i in range(25)]
    sel_items = [table_items[2], table_items[7]]

    ItemChoice = ItemEdit(labels, table_items, sel_items)
    ItemChoice.resize(500, 300)

    ItemChoice.show()
    sys.exit(app.exec_())


