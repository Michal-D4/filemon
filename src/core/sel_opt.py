# sel_opt.py

from collections import namedtuple

from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtWidgets import QDialog, QAbstractItemView

import src.core.utilities as ut
from src.ui.ui_sel_opt import Ui_SelOpt


def get_items_id(view: QAbstractItemView) -> str:
    """
    :param view:
    :return: str - a list of indexes of selected items as comma separated string
    """
    sel_idx = view.selectedIndexes()
    model = view.model()
    aux = []
    for id_ in sel_idx:
        aux.append(model.data(id_, Qt.UserRole))
    aux.sort()
    return ','.join([str(id_) for id_ in aux])


def get_selected_items(view: QAbstractItemView) -> str:
    idxs = view.selectedIndexes()
    if idxs:
        model = view.model()
        items_str = ', '.join(model.data(i, Qt.DisplayRole) for i in idxs)
    else:
        items_str = ''
    return items_str


class SelOpt(QDialog):

    def __init__(self, controller, parent=None):
        super(SelOpt, self).__init__(parent)
        self.ui = Ui_SelOpt()
        self.ui.setupUi(self)

        self.ctrl = controller

        self.not_older: int = 5
        self._restore_state()

        self.ui.chAuthor.stateChanged.connect(self.author_toggle)
        self.ui.chDate.stateChanged.connect(self.date_toggle)
        self.ui.chDirs.stateChanged.connect(self.dir_toggle)
        self.ui.chExt.stateChanged.connect(self.ext_toggle)
        self.ui.chTags.stateChanged.connect(self.tag_toggle)
        self.ui.eDate.textEdited.connect(self._text_edited)

    def _text_edited(self, ed_str: str):
        self.not_older = int(ed_str)

    def _restore_state(self):
        settings = QSettings()
        _state = settings.value('SelectionOptions',
                                (False, False, False, True, False, True, '5', True))
        try:
            self._set_state(_state)
        except TypeError:
            _state = (False, False, False, True, False, True, '5', True)
            self._set_state(_state)
        except (AttributeError, IndexError)
        print("!!! Something is wrong")

    def _set_state(self, saved_state):
        self.ui.chDirs.setChecked(saved_state[0])
        self.ui.chExt.setChecked(saved_state[1])
        self.ui.chTags.setChecked(saved_state[2])
        self.ui.tagAll.setChecked(saved_state[3])
        self.ui.chAuthor.setChecked(saved_state[4])
        self.ui.chDate.setChecked(saved_state[5])
        if saved_state[6]:
            self.not_older = int(saved_state[6])
        else:
            self.not_older = 5
        self.ui.eDate.setText(str(self.not_older))
        self.ui.eDate.setEnabled(saved_state[5])
        self.ui.dateFile.setChecked(saved_state[7])

    def author_toggle(self, author_list):
        if self.ui.chAuthor.isChecked():
            self.ui.eAuthors.setText(
                get_selected_items(self.ctrl.ui.authorsList))
        else:
            self.ui.eAuthors.setText('')

    def date_toggle(self):
        state = self.ui.chDate.isChecked()
        self.ui.eDate.setEnabled(state)
        self.ui.dateBook.setEnabled(state)
        self.ui.dateFile.setEnabled(state)

        if state:
            if not self.ui.eDate.text():
                self.ui.eDate.setText(str(self.not_older))
        else:
            self.ui.eDate.setText('')

    def dir_toggle(self):
        if self.ui.chDirs.isChecked():
            self.ui.lDir.setText(get_selected_items(self.ctrl.ui.dirTree))
        else:
            self.ui.lDir.setText('')

    def ext_toggle(self):
        if self.ui.chExt.isChecked():
            self.ui.eExt.setText(get_selected_items(self.ctrl.ui.extList))
        else:
            self.ui.eExt.setText('')

    def tag_toggle(self):
        state = self.ui.chTags.isChecked()
        if state:
            self.ui.eTags.setText(get_selected_items(self.ctrl.ui.tagsList))
        else:
            self.ui.eTags.setText('')

        self.ui.tagAll.setEnabled(state)
        self.ui.tagAny.setEnabled(state)

    def get_result(self) -> dict:
        """
        Returns the options chosen in the dialog
        :rtype: dict of the following keys:
            'dir' - list of dir IDs as a str,
            'ext' - list of ext IDs as a str,
            'tag' - list of tag IDs as a str,
            'author' - list of author IDs as a str,
            'use_date' - date of recent opening the file,
            'not_older' - number of years before current date,
            'is_file_date' - if True then used date of file creation,
                             else the year of book issue
        """
        result = dict()

        result['dir'] = self._get_dir_ids()
        result['ext'] = self._get_ext_ids()
        result['file'] = self._get_file_id()

        result['date'] = (self.ui.chDate.isChecked(),
                          self.ui.eDate.text(),
                          self.ui.dateFile.isChecked()
                          )

        self._save_state()
        return result

    def _save_state(self):
        settings = QSettings()
        settings.setValue('SelectionOptions',
                          (self.ui.chDirs.isChecked(),
                           self.ui.chExt.isChecked(),
                           self.ui.chTags.isChecked(),
                           self.ui.tagAll.isChecked(),
                           self.ui.chAuthor.isChecked(),
                           self.ui.chDate.isChecked(),
                           self.ui.eDate.text(),
                           self.ui.dateFile.isChecked()))

    def _get_file_id(self) -> str:
        """
        create an intersection of two list of file IDs
        1 - associated with selected tags
        2 - associated with selected authors
        :return: str - list of file IDs as comma separated string
        """
        # not exactly what need because list will be
        # EMPTY in case if any of choices NOT set
        s = set()
        if self.ui.chTags.isChecked():
            s.update(self._get_file_ids_4_tags())
            if self.ui.chAuthor.isChecked():
                s.intersection(self._get_file_ids_4_authors())
        elif self.ui.chAuthor.isChecked():
            s.update(self._get_file_ids_4_authors())

        return ','.join(s)

    def _get_dir_ids(self) -> str:
        """
        returns list of selected IDs as string separated by coma
        """
        if self.ui.chDirs.isChecked():
            lvl = 0
            idx = self.ctrl.ui.dirTree.currentIndex()
            root_id = int(self.ctrl.ui.dirTree.model().data(
                idx, Qt.UserRole)[0])

            ids = ','.join([str(id_[0])
                            for id_ in ut.dir_ids_select(root_id, lvl)])
            return ids
        return ''

    def _get_ext_ids(self) -> str:
        """
        returns list of selected IDs as string separated by coma
        """
        if self.ui.chExt.isChecked():
            sel_idx = self.ctrl.ui.extList.selectedIndexes()
            model = self.ctrl.ui.extList.model()
            aux = []
            for id_ in sel_idx:
                aux.append(model.data(id_, Qt.UserRole))

            idx = []
            for id_ in aux:
                if id_[0] > ut.EXT_ID_INCREMENT:
                    idx.append(id_[0] - ut.EXT_ID_INCREMENT)
                else:
                    idx += self._ext_in_group(id_[0])

            idx.sort()
            return ','.join([str(id_) for id_ in idx])
        return ''

    def _ext_in_group(self, gr_id) -> list:
        curr = ut.select_other('EXT_ID_IN_GROUP', (gr_id,))
        idx = []
        for id_ in curr:
            idx.append(id_[0])

        return idx

    def _get_file_ids_4_tags(self) -> list:
        """
        Select all file IDs that associated with selected tags
        taking into account whether all tags or any tags
        associated with file.
        :return: list of file IDs as comma separated string
        """
        tags = get_items_id(self.ctrl.ui.tagsList)
        if tags:
            if self.ui.tagAll.isChecked():
                num = len(tags.split(','))
                res = ut.select_other2(
                    'FILE_IDS_ALL_TAG', (tags, num)).fetchall()
            else:
                res = ut.select_other2('FILE_IDS_ANY_TAG', (tags,)).fetchall()
            return res

        return []

    def _get_file_ids_4_authors(self) -> list:
        auth_ids = get_items_id(self.ctrl.ui.authorsList)
        file_ids = ut.select_other2('FILE_IDS_AUTHORS', (auth_ids,)).fetchall()
        return file_ids


if __name__ == "__main__":
    pass
