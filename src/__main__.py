# -*- encoding: utf-8 -*-
# cucumber v0.1.0
# Python files dirs manage
# Copyright © 2019, Mihas Davidovich.
# See /LICENSE for licensing information.

"""
Main routine of cucumber.

:Copyright: © 2019, Mihas Davidovich.
:License: BSD (see /LICENSE).
"""


import sys
from loguru import logger

from PyQt5.QtWidgets import QApplication

from core.gov_files import FilesCrt
from core.main_window import AppWindow
from core.db_choice import DBChoice


__all__ = ('main',)

_excepthook = sys.excepthook


def my_exception_hook(exctype, value, traceback):
    # Print the error and traceback
    print(exctype, value, traceback)
    # Call the normal Exception hook after
    _excepthook(exctype, value, traceback)
    sys.exit(1)

sys.excepthook = my_exception_hook


def main():
    from PyQt5.QtCore import pyqtRemoveInputHook

    pyqtRemoveInputHook()
    logger.add("cucu_{time}.log", enqueue=True)

    logger.debug("logger add")

    app = QApplication(sys.argv)
    DBChoice()
    main_window = AppWindow()

    _controller = FilesCrt()
    main_window.scan_files_signal.connect(_controller.on_scan_files)

    # when data changed on any widget
    main_window.change_data_signal.connect(_controller.on_change_data)

    # signal from open_dialog=dlg
    main_window.open_dialog.DB_connect_signal.connect(_controller.on_db_connection)

    main_window.first_open_data_base()

    main_window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
