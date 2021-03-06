# db_choice.py

from PyQt5.QtCore import pyqtSignal, QSettings, QCoreApplication
from PyQt5.QtWidgets import QDialog, QFileDialog, QListWidgetItem

from src.ui.ui_db_choice import Ui_ChoiceDB


class DBChoice(QDialog):
    """
     str  - DB file_name
     bool - Create DB if True, otherwise - Open
     bool - True if last used db is opened
    """
    DB_connect_signal = pyqtSignal(str, bool, bool)

    def __init__(self, parent=None):
        super(DBChoice, self).__init__(parent)

        self.ui_db_choice = Ui_ChoiceDB()
        self.ui_db_choice.setupUi(self)

        self.ui_db_choice.okButton.clicked.connect(self.accept)
        self.ui_db_choice.newButton.clicked.connect(self.new_db)
        self.ui_db_choice.addButton.clicked.connect(self.add)
        self.ui_db_choice.delButton.clicked.connect(self.delete)
        self.ui_db_choice.listOfBDs.currentRowChanged.connect(self.row_changed)

        self.ui_db_choice.listOfBDs.setSelectionMode(1)

        self.init_data = None
        self.last_db_no = -1
        self.restore_settings()

    def showEvent(self, ev):
        if not ev.spontaneous():
            self.initiate_window()
        return QDialog.showEvent(self, ev)

    def row_changed(self, curr_row):
        self.init_data[0] = curr_row

    def add(self):
        """
        the program is called by click of 'Add' button of this dialog
        :return:
        """
        options = QFileDialog.Options(QFileDialog.HideNameFilterDetails |
                                      QFileDialog.DontConfirmOverwrite)
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Create DB", "", options=options)
        if file_name:
            self.create_new_db(file_name)

    def delete(self):
        idx = self.ui_db_choice.listOfBDs.currentIndex()
        if idx.isValid():
            i = idx.row()
            self.ui_db_choice.listOfBDs.takeItem(idx.row())
            self.init_data[1].remove(self.init_data[1][i])

    def accept(self):
        self.emit_open_dialog()
        self._save_settings()
        super(DBChoice, self).accept()

    def new_db(self):
        """
        the program is called by click of 'New' button
        and shows the file dialog to enter new file name
        :return:
        """
        options = QFileDialog.Options(QFileDialog.HideNameFilterDetails |
                                      QFileDialog.DontConfirmOverwrite)
        file_name, _ = QFileDialog.getSaveFileName(self, "Create DB", "",
                                                   options=options)
        if file_name:
            if (self.init_data[1]) or (file_name not in self.init_data[1]):
                self.create_db_(file_name)
                self.DB_connect_signal.emit(file_name, True, False)
                self.accept()
            else:
                self.ui_db_choice.listOfBDs.setCurrentRow(
                    self.init_data[1].index(file_name))

    def create_new_db(self, file_name):
        if not file_name in self.init_data[1]:
            self.create_db_(file_name)
        else:
            self.ui_db_choice.listOfBDs.setCurrentRow(
                self.init_data[1].index(file_name))

    def create_db_(self, file_name):
        self.init_data[1].append(file_name)
        item = QListWidgetItem(file_name)
        self.ui_db_choice.listOfBDs.addItem(item)
        self.ui_db_choice.listOfBDs.setCurrentItem(item)
        self.ui_db_choice.okButton.setDisabled(False)

    def emit_open_dialog(self):
        if self.ui_db_choice.listOfBDs.currentIndex().isValid():
            file_name = self.ui_db_choice.listOfBDs.currentItem().text()
            # todo - if self.last_db_no == self.init_data[1]: not create new connection -
            # the last param not need
            self.DB_connect_signal.emit(
                file_name, False, self.last_db_no == self.init_data[0])

    def initiate_window(self):
        '''
        Initiate data in widgets
        :param init_data: list of 2 items:
            0 - index of last used DB
            1 - list of DBs
        :return: None
        '''
        if self.init_data:
            db_index = self.init_data[0]
            if self.init_data[1]:
                self.ui_db_choice.listOfBDs.clear()
                for db in self.init_data[1]:
                    self.ui_db_choice.listOfBDs.addItem(db)
                self.ui_db_choice.listOfBDs.setCurrentRow(db_index)
            if self.ui_db_choice.listOfBDs.count() == 0:
                self.ui_db_choice.okButton.setDisabled(True)

    def restore_settings(self):
        setting = QSettings()
        _data = [setting.value('DB/current_index', 0, type=int),
                 setting.value('DB/list_of_DB', [], type=list)]
        self.last_db_no = _data[0]
        self.init_data = _data
        self.initiate_window()

    def _save_settings(self):
        setting = QSettings()
        setting.setValue('DB/current_index', self.init_data[0])
        setting.setValue('DB/list_of_DB', self.init_data[1])
