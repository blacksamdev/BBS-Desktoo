# bbs_desktoo/app.py
# BBS desktOO — amorçage de l'application Qt.

import sys

from PyQt6.QtWidgets import QApplication

from bbs_desktoo.core.theme import build_qss
from bbs_desktoo.ui.main_window import MainWindow


def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("BBS desktOO")
    app.setOrganizationName("blacksamdev")
    app.setStyleSheet(build_qss())

    window = MainWindow()
    window.show()
    return app.exec()
