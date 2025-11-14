import sys

from PySide6.QtCore import QCoreApplication

from .scanner import Scanner
from .gui import Gui

from PySide6.QtWidgets import QApplication

def init():
    app = QApplication(sys.argv)

    QCoreApplication.setOrganizationName("Krzysztof Dmitruk")
    QCoreApplication.setApplicationName("XArray Constructor")

    scanner = Scanner()
    scanner.configure_from_file(sys.argv[1])
    gui = Gui(scanner)
    gui.show()

    return app.exec()