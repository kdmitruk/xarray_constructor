import sys

from PySide6.QtCore import QCoreApplication, QCommandLineParser, QCommandLineOption

from .scanner import Scanner
from .gui import Gui

from PySide6.QtWidgets import QApplication

def init():
    app = QApplication(sys.argv)

    QCoreApplication.setOrganizationName("Krzysztof Dmitruk")
    QCoreApplication.setApplicationName("XArray Constructor")
    parser = QCommandLineParser()
    benchmark_option = QCommandLineOption(
        ["benchmark"],
        "Enable benchmark timing output"
    )
    parser.addOption(benchmark_option)
    parser.addPositionalArgument("file", "Scanner configuration file to open")
    parser.process(app)

    benchmark = parser.isSet(benchmark_option)

    positional_args = parser.positionalArguments()
    file_path = positional_args[0] if positional_args else None

    scanner = Scanner()
    if file_path:
        scanner.configure_from_file(file_path)

    gui = Gui(scanner, benchmark)
    gui.show()

    return app.exec()