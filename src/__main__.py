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

from src.core.gov_files import FilesCrt
from src.core.main_window import AppWindow
from src.core.db_choice import DBChoice


__all__ = ('main',)

_excepthook = sys.excepthook


def my_exception_hook(exc_, value, traceback):
    # Print the error and traceback
    logger.debug(f'{exc_}, {value}, {traceback}')
    # Call the normal Exception hook after
    _excepthook(exc_, value, traceback)
    sys.exit(1)

sys.excepthook = my_exception_hook


def main():
    from PyQt5.QtCore import pyqtRemoveInputHook

    pyqtRemoveInputHook()
    # logger.add("cucu_{time}.log", enqueue=True)
    logger.remove()
    fmt = '<green>{time:HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | ' \
          '<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> '   \
          '- <level>{message}</level>'
    logger.add(sys.stderr, format=fmt, enqueue = True)
    # logger.add("cucu_{time:MMM-DD_HH-mm}.log", format=fmt, enqueue=True)

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
