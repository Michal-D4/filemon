from PyQt5.QtCore import (QDate, QDateTime, QRegExp, QSortFilterProxyModel, Qt,
                          QTime)
from PyQt5.QtGui import QStandardItemModel
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, QDateEdit,
                             QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QTreeView,
                             QVBoxLayout, QWidget)


class MySortFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super(MySortFilterProxyModel, self).__init__(parent)

        self.minDate = QDate()
        self.maxDate = QDate()

    def setFilterMinimumDate(self, date):
        self.minDate = date
        self.invalidateFilter()

    def filterMinimumDate(self):
        return self.minDate

    def setFilterMaximumDate(self, date):
        self.maxDate = date
        self.invalidateFilter()

    def filterMaximumDate(self):
        return self.maxDate

    def filterAcceptsRow(self, sourceRow, sourceParent):
        index0 = self.sourceModel().index(sourceRow, 0, sourceParent)
        index1 = self.sourceModel().index(sourceRow, 1, sourceParent)
        index2 = self.sourceModel().index(sourceRow, 2, sourceParent)

        return ((self.filterRegExp().indexIn(self.sourceModel().data(index0)) >= 0
                 or self.filterRegExp().indexIn(self.sourceModel().data(index1)) >= 0)
                and self.dateInRange(self.sourceModel().data(index2)))

    def lessThan(self, left, right):
        leftData = self.sourceModel().data(left)
        rightData = self.sourceModel().data(right)

        if not isinstance(leftData, QDate):
            emailPattern = QRegExp("([\\w\\.]*@[\\w\\.]*)")

            if left.column() == 1 and emailPattern.indexIn(leftData) != -1:
                leftData = emailPattern.cap(1)

            if right.column() == 1 and emailPattern.indexIn(rightData) != -1:
                rightData = emailPattern.cap(1)

        return leftData < rightData

    def dateInRange(self, date):
        if isinstance(date, QDateTime):
            date = date.date()

        return ((not self.minDate.isValid() or date >= self.minDate)
                and (not self.maxDate.isValid() or date <= self.maxDate))


class Window(QWidget):
    def __init__(self):
        super(Window, self).__init__()

        self.proxyModel = MySortFilterProxyModel(self)
        self.proxyModel.setDynamicSortFilter(True)

        self.sourceView = QTreeView()
        self.sourceView.setRootIsDecorated(False)
        self.sourceView.setAlternatingRowColors(True)

        sourceLayout = QHBoxLayout()
        sourceLayout.addWidget(self.sourceView)
        sourceGroupBox = QGroupBox("Original Model")
        sourceGroupBox.setLayout(sourceLayout)

        self.filterCaseSensitivityCheckBox = QCheckBox("Case sensitive filter")
        self.filterCaseSensitivityCheckBox.setChecked(True)
        self.filterPatternLineEdit = QLineEdit()
        self.filterPatternLineEdit.setText("Grace|Sports")
        filterPatternLabel = QLabel("&Filter pattern:")
        filterPatternLabel.setBuddy(self.filterPatternLineEdit)
        self.filterSyntaxComboBox = QComboBox()
        self.filterSyntaxComboBox.addItem("Regular expression", QRegExp.RegExp)
        self.filterSyntaxComboBox.addItem("Wildcard", QRegExp.Wildcard)
        self.filterSyntaxComboBox.addItem("Fixed string", QRegExp.FixedString)
        self.fromDateEdit = QDateEdit()
        self.fromDateEdit.setDate(QDate(2006, 12, 22))
        self.fromDateEdit.setCalendarPopup(True)
        fromLabel = QLabel("F&rom:")
        fromLabel.setBuddy(self.fromDateEdit)
        self.toDateEdit = QDateEdit()
        self.toDateEdit.setDate(QDate(2007, 1, 5))
        self.toDateEdit.setCalendarPopup(True)
        toLabel = QLabel("&To:")
        toLabel.setBuddy(self.toDateEdit)

        self.filterPatternLineEdit.textChanged.connect(self.textFilterChanged)
        self.filterSyntaxComboBox.currentIndexChanged.connect(self.textFilterChanged)
        self.filterCaseSensitivityCheckBox.toggled.connect(self.textFilterChanged)
        self.fromDateEdit.dateChanged.connect(self.dateFilterChanged)
        self.toDateEdit.dateChanged.connect(self.dateFilterChanged)

        self.proxyView = QTreeView()
        self.proxyView.setRootIsDecorated(False)
        self.proxyView.setAlternatingRowColors(True)
        self.proxyView.setModel(self.proxyModel)
        self.proxyView.setSortingEnabled(True)
        self.proxyView.sortByColumn(1, Qt.AscendingOrder)

        self.textFilterChanged()
        self.dateFilterChanged()

        proxyLayout = QGridLayout()
        proxyLayout.addWidget(self.proxyView, 0, 0, 1, 3)
        proxyLayout.addWidget(filterPatternLabel, 1, 0)
        proxyLayout.addWidget(self.filterPatternLineEdit, 1, 1)
        proxyLayout.addWidget(self.filterSyntaxComboBox, 1, 2)
        proxyLayout.addWidget(self.filterCaseSensitivityCheckBox, 2, 0, 1, 3)
        proxyLayout.addWidget(fromLabel, 3, 0)
        proxyLayout.addWidget(self.fromDateEdit, 3, 1, 1, 2)
        proxyLayout.addWidget(toLabel, 4, 0)
        proxyLayout.addWidget(self.toDateEdit, 4, 1, 1, 2)
        proxyGroupBox = QGroupBox("Sorted/Filtered Model")
        proxyGroupBox.setLayout(proxyLayout)

        mainLayout = QVBoxLayout()
        mainLayout.addWidget(sourceGroupBox)
        mainLayout.addWidget(proxyGroupBox)
        self.setLayout(mainLayout)

        self.setWindowTitle("Custom Sort/Filter Model")
        self.resize(500, 450)

    def setSourceModel(self, model):
        self.proxyModel.setSourceModel(model)
        self.sourceView.setModel(model)

    def textFilterChanged(self):
        syntax = QRegExp.PatternSyntax(
            self.filterSyntaxComboBox.itemData(
                self.filterSyntaxComboBox.currentIndex()))
        caseSensitivity = (
                self.filterCaseSensitivityCheckBox.isChecked()
                and Qt.CaseSensitive or Qt.CaseInsensitive)
        regExp = QRegExp(self.filterPatternLineEdit.text(), caseSensitivity, syntax)
        self.proxyModel.setFilterRegExp(regExp)

    def dateFilterChanged(self):
        self.proxyModel.setFilterMinimumDate(self.fromDateEdit.date())
        self.proxyModel.setFilterMaximumDate(self.toDateEdit.date())


def addMail(model, subject, sender, date):
    model.insertRow(0)
    model.setData(model.index(0, 0), subject)
    model.setData(model.index(0, 1), sender)
    model.setData(model.index(0, 2), date)


def createMailModel(parent):
    model = QStandardItemModel(0, 3, parent)

    model.setHeaderData(0, Qt.Horizontal, "Subject")
    model.setHeaderData(1, Qt.Horizontal, "Sender")
    model.setHeaderData(2, Qt.Horizontal, "Date")

    addMail(model, "Happy New Year!", "Grace K. <grace@software-inc.com>",
            QDateTime(QDate(2006, 12, 31), QTime(17, 3)))
    addMail(model, "Radically new concept", "Grace K. <grace@software-inc.com>",
            QDateTime(QDate(2006, 12, 22), QTime(9, 44)))
    addMail(model, "Accounts", "pascale@nospam.com",
            QDateTime(QDate(2006, 12, 31), QTime(12, 50)))
    addMail(model, "Expenses", "Joe Bloggs <joe@bloggs.com>",
            QDateTime(QDate(2006, 12, 25), QTime(11, 39)))
    addMail(model, "Re: Expenses", "Andy <andy@nospam.com>",
            QDateTime(QDate(2007, 1, 2), QTime(16, 5)))
    addMail(model, "Re: Accounts", "Joe Bloggs <joe@bloggs.com>",
            QDateTime(QDate(2007, 1, 3), QTime(14, 18)))
    addMail(model, "Re: Accounts", "Andy <andy@nospam.com>",
            QDateTime(QDate(2007, 1, 3), QTime(14, 26)))
    addMail(model, "Sports", "Linda Smith <linda.smith@nospam.com>",
            QDateTime(QDate(2007, 1, 5), QTime(11, 33)))
    addMail(model, "AW: Sports", "Rolf Newschweinstein <rolfn@nospam.com>",
            QDateTime(QDate(2007, 1, 5), QTime(12, 0)))
    addMail(model, "RE: Sports", "Petra Schmidt <petras@nospam.com>",
            QDateTime(QDate(2007, 1, 5), QTime(12, 1)))

    return model


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)

    window = Window()
    window.setSourceModel(createMailModel(window))
    window.show()

    sys.exit(app.exec_())
