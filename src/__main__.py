# -*- encoding: utf-8 -*-
# Copyright © 2019, Mihas Davidovich.


import sys

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QCoreApplication

from core.gov_files import FilesCrt
from core.main_window import AppWindow


APP_NAME = 'File manager'
ORG_DOMAIN = 'fake_domain.org'
ORG_NAME = 'Fake organization'


__all__ = ('main',)


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
