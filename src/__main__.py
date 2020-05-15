# -*- encoding: utf-8 -*-
# Copyright © 2019, Mihas Davidovich.


import sys

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QCoreApplication

from src.core.gov_files import FilesCrt
from src.core.main_window import AppWindow


APP_NAME = 'File manager'
ORG_DOMAIN = 'fake_domain.org'
ORG_NAME = 'Fake organization'


__all__ = ('main',)

# ---------------------------------------------------------
# doesn't catch exception without this code in Windows ! ! !
_excepthook = sys.excepthook


def my_exception_hook(exc_, value, traceback):
    # Print the error and traceback
    print(traceback)
    # Call the normal Exception hook after
    _excepthook(exc_, value, traceback)
    sys.exit(1)


sys.excepthook = my_exception_hook
# ---------------------------------------------------------


def main():
    from PyQt5.QtCore import pyqtRemoveInputHook

    QCoreApplication.setApplicationName(APP_NAME)
    QCoreApplication.setOrganizationDomain(ORG_DOMAIN)
    QCoreApplication.setOrganizationName(ORG_NAME)

    pyqtRemoveInputHook()

    app = QApplication(sys.argv)

    main_window = AppWindow()

    _controller = FilesCrt(main_window)
    main_window.scan_files_signal.connect(_controller.on_scan_files)

    # when data changed on any widget
    main_window.change_data_signal.connect(_controller.on_change_data)

    main_window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
