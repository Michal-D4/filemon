# main_window.py

from PyQt5.QtCore import (pyqtSignal, QSettings, QVariant, QSize, Qt, QUrl, QEvent, QMimeData)
from PyQt5.QtGui import QResizeEvent, QDrag, QPixmap, QDropEvent, QDragMoveEvent
from PyQt5.QtWidgets import QMainWindow, QMenu, QWidget

from src.ui.ui_main_window import Ui_MainWindow
from src.core.helper import (REAL_FOLDER, VIRTUAL_FOLDER, REAL_FILE,
                             VIRTUAL_FILE, MimeTypes, DROP_NO_ACTION,
                             DROP_COPY_FOLDER, DROP_MOVE_FOLDER,
                             DROP_COPY_FILE, Shared)


def restore_obj_state(obj: QWidget, settings_value: QVariant):
    if settings_value:
        obj.restoreState(settings_value)


class AppWindow(QMainWindow):
    change_data_signal = pyqtSignal(str)   # str - name of action
    scan_files_signal = pyqtSignal()

    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        Shared['AppWindow'] = self

        self.old_size = None
        self.old_pos = None
        self.restore_setting()

        self.set_actions()

        self.set_menus()

        self.setup_context_menu()

        self.open_dialog = Shared['DB choice dialog']

    def show_message(self, message, time=3000):
        self.ui.statusbar.showMessage(message, time)

    def set_actions(self):
        """
        Connect handlers to tool bar actions and widgets' events
        :return:
        """
        self.ui.actionOpenDB.triggered.connect(lambda: self.open_dialog.exec_())
        self.ui.actionScanFiles.triggered.connect(lambda: self.scan_files_signal.emit())
        self.ui.actionFileFilter.triggered.connect(lambda: self.change_data_signal.emit('Select files'))
        self.ui.actionFavorites.triggered.connect(lambda: self.change_data_signal.emit('Favorites'))

        self.ui.commentField.anchorClicked.connect(self.ref_clicked)
        self.ui.filesList.doubleClicked.connect(lambda: self.change_data_signal.emit('File_doubleClicked'))

        self.ui.dirTree.startDrag = self._start_drag
        self.ui.dirTree.dropEvent = self._drop_event
        self.ui.dirTree.dragMoveEvent = self._drag_move_event
        self.ui.filesList.startDrag = self._start_drag_files

        self.ui.filesList.resizeEvent = self.resize_event

    def _drag_move_event(self, event: QDragMoveEvent):
        index = self.ui.dirTree.indexAt(event.pos())
        mime_data = event.mimeData()
        if mime_data.hasFormat(MimeTypes[REAL_FOLDER]):
            if not self.ui.dirTree.model().is_virtual(index):
                event.ignore()
            else:
                event.accept()
        else:
            event.accept()

    def _drop_event(self, event: QDropEvent):
        mime_data: QMimeData = event.mimeData()
        index = self.ui.dirTree.indexAt(event.pos())

        act = self._set_action(index, mime_data, event.pos())

        res = self.ui.dirTree.model().dropMimeData(mime_data, act, index)
        if res:
            event.accept()
        else:
            event.ignore()

    def _set_action(self, index, mime_data, pos):
        """
        index: in dirTree at drop position
        mime_data:
        pos: position where menu to be shown
        return: DROP_NO_ACTION, DROP_COPY_FOLDER, DROP_MOVE_FOLDER, DROP_COPY_FILE, DROP_MOVE_FILE
        """
        if mime_data.hasFormat(MimeTypes[REAL_FOLDER]):
            if self.ui.dirTree.model().is_virtual(index):
                return DROP_COPY_FOLDER
            return DROP_NO_ACTION
        if mime_data.hasFormat(MimeTypes[REAL_FILE]):
            if self.ui.dirTree.model().is_virtual(index):
                return DROP_COPY_FILE
            return self._ask_action_file(pos)
        if mime_data.hasFormat(MimeTypes[VIRTUAL_FILE]):
            return self._ask_action_file(pos)
        if mime_data.hasFormat(MimeTypes[VIRTUAL_FOLDER]):
            return self._ask_action_folder(pos)
        return DROP_NO_ACTION

    def _ask_action_file(self, pos):
        """
        Menu: drag-drop action chooser
        when drop file(s) to directory tree item(folder)
        Actions: Copy | Move | Cancel
        Returns: int (DROP_COPY_FILE=4, DROP_MOVE_FILE=8, DROP_NO_ACTION=0)
        """
        return self._ask_action_folder(pos) * 4

    def _ask_action_folder(self, pos):
        """
        Menu: drag-drop action chooser
        when drop folder(s) to directory tree item(folder)
        Actions: Copy | Move | Cancel
        Returns: int (DROP_COPY_FOLDER=1, DROP_MOVE_FOLDER=2, DROP_NO_ACTION=0)
        """
        menu = QMenu(self)
        menu.addAction('Copy')
        menu.addAction('Move')
        menu.addSeparator()
        menu.addAction('Cancel')
        action = menu.exec_(self.ui.dirTree.mapToGlobal(pos))
        if action:
            if action.text() == 'Copy':
                return DROP_COPY_FOLDER
            elif action.text() == 'Move':
                return DROP_MOVE_FOLDER
        return DROP_NO_ACTION

    def _start_drag_files(self, action):
        drag = QDrag(self)
        drag.setPixmap(QPixmap(":/image/List.png"))
        indexes = self.ui.filesList.selectionModel().selectedRows()
        mime_data = self.ui.filesList.model().mimeData(indexes)
        drag.setMimeData(mime_data)
        drag.exec_(Qt.CopyAction)

    def _start_drag(self, action):
        drag = QDrag(self)
        drag.setPixmap(QPixmap(":/image/Folder.png"))
        indexes = self.ui.dirTree.selectionModel().selectedRows()
        mime_data = self.ui.dirTree.model().mimeData(indexes)
        drag.setMimeData(mime_data)
        if mime_data.hasFormat(MimeTypes[REAL_FOLDER]):
            drag.exec_(Qt.CopyAction)
        elif mime_data.hasFormat(MimeTypes[VIRTUAL_FOLDER]):
            drag.exec_(Qt.MoveAction)

    def set_menus(self):
        """
        Set actions of main menu
        :return:
        """
        menu = QMenu(self)
        open_db = menu.addAction('Open DB')
        change_font = menu.addAction('Change Font')
        set_fields = menu.addAction('Set fields')
        self.ui.btnOption.setMenu(menu)
        open_db.triggered.connect(lambda: self.open_dialog.exec_())
        change_font.triggered.connect(lambda: self.change_data_signal.emit('change_font'))
        set_fields.triggered.connect(lambda: self.change_data_signal.emit('Set fields'))

        menu2 = QMenu(self)
        sel_opt = menu2.addAction('Selection options')
        self.ui.btnFilter.setMenu(menu2)
        sel_opt.triggered.connect(lambda: self.change_data_signal.emit('Selection options'))

    def setup_context_menu(self):
        """
        Set context menus for each widget
        :return:
        """
        self.ui.dirTree.customContextMenuRequested.connect(self._dir_menu)
        self.ui.filesList.customContextMenuRequested.connect(self._file_menu)
        self.ui.extList.customContextMenuRequested.connect(self._ext_menu)
        self.ui.tagsList.customContextMenuRequested.connect(self._tag_menu)
        self.ui.authorsList.customContextMenuRequested.connect(self._author_menu)

    def _file_menu(self, pos):
        idx = self.ui.filesList.indexAt(pos)
        if idx.isValid():
            menu = QMenu(self)
            menu.addAction('Open')
            menu.addAction('Open folder')
            menu.addAction('Add to favorites')
            menu.addAction('Delete row')
            menu.addSeparator()
            menu.addAction('Copy file name')
            menu.addAction('Copy path')
            menu.addSeparator()
            menu.addAction('Rename file')
            menu.addAction('Copy file(s)')
            if self.ui.filesList.model().in_real_folder(idx):
                menu.addAction('Move file(s)')
                menu.addAction('Delete file(s)')
            action = menu.exec_(self.ui.filesList.mapToGlobal(pos))
            if action:
                self.change_data_signal.emit('File {}'.format(action.text()))

    def _ext_menu(self, pos):
        menu = QMenu(self)
        menu.addAction('Remove unused')
        menu.addAction('Create group')
        menu.addAction('Delete all files with current extension')
        action = menu.exec_(self.ui.extList.mapToGlobal(pos))
        if action:
            self.change_data_signal.emit('Ext {}'.format(action.text()))

    def _tag_menu(self, pos):
        idx = self.ui.tagsList.indexAt(pos)
        menu = QMenu(self)
        menu.addAction('Remove unused')
        if idx.isValid():
            menu.addAction('Scan in names')
            menu.addAction('Rename')

        action = menu.exec_(self.ui.tagsList.mapToGlobal(pos))
        if action:
            self.change_data_signal.emit('Tag {}'.format(action.text()))

    def _author_menu(self, pos):
        menu = QMenu(self)
        menu.addAction('Remove unused')
        action = menu.exec_(self.ui.authorsList.mapToGlobal(pos))
        if action:
            self.change_data_signal.emit('Author {}'.format(action.text()))

    def _dir_menu(self, pos):
        idx = self.ui.dirTree.indexAt(pos)
        menu = QMenu(self)
        menu.addAction('Remove empty folders')
        if idx.isValid():
            if self.ui.dirTree.model().is_virtual(idx):
                if not self.ui.dirTree.model().is_favorites(idx):
                    menu.addSeparator()
                    menu.addAction('Rename folder')
                    menu.addAction('Delete folder')
            else:
                parent = self.ui.dirTree.model().parent(idx)
                if self.ui.dirTree.model().is_virtual(parent):
                    menu.addSeparator()
                    menu.addAction('Delete folder')
                menu.addAction('Rescan dir')
                menu.addSeparator()
                menu.addAction('Group')
            menu.addSeparator()
            menu.addAction('Create virtual folder')
            menu.addAction('Create virtual folder as child')
        else:
            menu.addAction('Create virtual folder')

        action = menu.exec_(self.ui.dirTree.mapToGlobal(pos))
        if action:
            self.change_data_signal.emit('Dirs {}'.format(action.text()))

    def ref_clicked(self, href):
        """
        Invoke methods to change file information: tags, authors, comment
        :param href:
        :return:
        """
        self.ui.commentField.setSource(QUrl())
        self.change_data_signal.emit(href.toString())

    def resizeEvent(self, event):
        """
        resizeEvent - when changed main window. To save size for next run
        :param event:
        :return:
        """
        super().resizeEvent(event)
        self.old_size = event.oldSize()
        settings = QSettings()
        settings.setValue("MainFlow/Size", QVariant(self.size()))

    def resize_event(self, event: QResizeEvent):
        """
        resizeEvent of filesList, to change width of columns
        :param event:
        :return:
        """
        old_w = event.oldSize().width()
        w = event.size().width()
        if not old_w == w:
            self.change_data_signal.emit('Resize columns')

    def changeEvent(self, event):
        """
        Save size and position of window before it maximized
        :param event:
        :return:
        """
        if event.type() == QEvent.WindowStateChange:
            settings = QSettings()
            if event.oldState() == Qt.WindowMaximized:
                settings.setValue("MainFlow/isFullScreen", QVariant(False))
            elif event.oldState() == Qt.WindowNoState and \
                    self.windowState() == Qt.WindowMaximized:
                settings.setValue("MainFlow/isFullScreen", QVariant(True))
                if self.old_size:
                    settings.setValue("MainFlow/Size", QVariant(self.old_size))
                if self.old_pos:
                    settings.setValue("MainFlow/Position", QVariant(self.old_pos))
        else:
            super().changeEvent(event)

    def moveEvent(self, event):
        """
        Save new position of window
        :param event:
        :return:
        """
        self.old_pos = event.oldPos()
        settings = QSettings()
        settings.setValue("MainFlow/Position", QVariant(self.pos()))
        super().moveEvent(event)

    def restore_setting(self):
        settings = QSettings()
        if settings.contains("MainFlow/Size"):
            size = settings.value("MainFlow/Size", QSize(640, 480))
            self.resize(size)
            position = settings.value("MainFlow/Position")
            self.move(position)
            restore_obj_state(self, settings.value("MainFlow/State"))
            restore_obj_state(self.ui.splitter_files, settings.value("FilesSplitter"))
            restore_obj_state(self.ui.opt_splitter, settings.value("OptSplitter"))
            restore_obj_state(self.ui.main_splitter, settings.value("MainSplitter"))
        else:
            self.ui.main_splitter.setStretchFactor(0, 2)
            self.ui.main_splitter.setStretchFactor(1, 5)
            self.ui.main_splitter.setStretchFactor(2, 1)
            self.ui.splitter_files.setStretchFactor(0, 5)
            self.ui.splitter_files.setStretchFactor(1, 2)

    def first_open_data_base(self):
        """
        Open DB when application starts
        :return:
        """
        if not self.open_dialog.skip_open_dialog():
            self.open_dialog.exec_()
        else:
            self.open_dialog.emit_open_dialog()

    def closeEvent(self, event):
        self.open_dialog.save_init_data()
        settings = QSettings()
        settings.setValue("MainFlow/State", QVariant(self.saveState()))
        settings.setValue("FilesSplitter", QVariant(self.ui.splitter_files.saveState()))
        settings.setValue("OptSplitter", QVariant(self.ui.opt_splitter.saveState()))
        settings.setValue("MainSplitter", QVariant(self.ui.main_splitter.saveState()))
        super(AppWindow, self).closeEvent(event)
