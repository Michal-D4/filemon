# view.input_date.py

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog

from src.ui.ui_input_date import Ui_DateInputDialog


class DateInputDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.ui = Ui_DateInputDialog()
        self.ui.setupUi(self)

    @staticmethod
    def getDate(value, parent = None):
        dialog = DateInputDialog(parent)
        dialog.ui.date.setDate(value)
        result = dialog.exec_()
        date_ = dialog.ui.date.date().toString(Qt.ISODate)
        return (date_, result == QDialog.Accepted)

if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import QDate
    breakpoint()
    app = QApplication(sys.argv)

    date, ok = DateInputDialog.getDate(QDate.currentDate())
    print("{} {}".format(date, ok))
    # if ok:
    #     app.exit()
    sys.exit(app.exec_())

