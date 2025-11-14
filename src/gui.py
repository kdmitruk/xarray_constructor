import sys
import subprocess

from PySide6 import  QtCore
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QLabel, QLineEdit, QCheckBox, QPushButton, QDoubleSpinBox,
                               QComboBox, QFileDialog, QGroupBox, QGridLayout, QScrollArea, QFrame,
                               QProgressDialog, QListWidget, QMenu, QToolButton, QMessageBox)
from PySide6.QtCore import Qt, QSettings, QDir, QThread, Signal, QFileInfo
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as NavigationToolbar

from .card import Card
from .tube import Tube

class Gui(QMainWindow):
    def __init__(self, scanner):
        super().__init__()
        self.case_changed = True
        self.view_generated_box = None
        self.viewer_edit = None
        self.separate_box = None
        self.prefix_edit = None
        self.path_edit = None
        self.auto_update_box = None
        self.scanner = scanner
        self.setWindowTitle("XArray Constructor")
        self.setWindowState(Qt.WindowMaximized)
        self.setMinimumSize(800, 600)

        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.layout = QGridLayout(self.main_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.fig = Figure()
        self.ax = self.fig.add_subplot(111)
        self.ax.set_aspect('equal')
        self.canvas = FigureCanvas(self.fig)
        self.toolbar = NavigationToolbar(self.canvas, self)

        self.layout.addWidget(self.canvas, 0, 0, 1, 1)
        self.layout.addWidget(self.toolbar, 1, 0, 1, 1)

        toolbox = self.init_toolbox()
        self.layout.addWidget(toolbox, 0, 1, 1, 1)

        self.layout.setColumnStretch(0, 100)

        self.restore_settings()
        self.recalculate()

    def restore_settings(self):
        self.settings = QSettings()
        self.auto_update_box.setChecked(self.settings.value("auto_update", True, type=bool))

    def plot(self):
        self.ax.set_xlim(self.current_xlim)
        self.ax.set_ylim(self.current_ylim)
        self.scanner.plot(self.ax)
        self.canvas.draw()

    def recalculate(self):
        if self.case_changed:
            margin = self.scanner.case_size_x / 10
            self.current_xlim = (self.scanner.case_offset_x - margin,
                             self.scanner.case_offset_x + self.scanner.case_size_x + margin)
            self.current_ylim = (self.scanner.case_offset_z - margin,
                                 self.scanner.case_offset_z + self.scanner.case_size_z + margin)
            self.case_changed = False
        else:
            self.current_xlim = self.ax.set_xlim()
            self.current_ylim = self.ax.set_ylim()

        self.ax.clear()
        self.scanner.calculate_array()
        self.plot()

    def save(self):
        self.scanner.save_configuration(self.scanner_name.text())

    def get_filename(self):
        self.scanner_name.text()

    def _show_saved_message(self, path: str):
        msg = QMessageBox(self)
        msg.setWindowTitle("File Saved")
        msg.setText(f"The file has been successfully saved:\n\n{path}")
        msg.setIcon(QMessageBox.Information)
        msg.exec()

    def _prepare_output_path(self, subdir: str, extension: str = ".json"):
        info = QFileInfo(self.scanner_name.text())
        filename = info.baseName()

        output_dir = QDir(subdir)
        if not output_dir.exists():
            QDir().mkpath(subdir)

        return output_dir.filePath(filename + extension)

    def _show_saved_message(self, path: str):
        msg = QMessageBox(self)
        msg.setWindowTitle("File Saved")
        msg.setText(f"The file has been successfully saved:\n\n{path}")
        msg.setIcon(QMessageBox.Information)
        msg.exec()

    def export(self):
        output_path = self._prepare_output_path("output")
        self.scanner.export_array(output_path)
        self._show_saved_message(output_path)

    def export_simulation_input(self):
        output_path = self._prepare_output_path("simulation")
        self.scanner.export_simulation_input(output_path)
        self._show_saved_message(output_path)

    def on_result_paths(self, result_paths):
        self.progress_dialog.close()

        if self.view_generated_box.isChecked():
            for result_path in result_paths:
                subprocess.Popen([self.viewer_edit.text(), result_path])

    def init_toolbox(self):
        area = QScrollArea()
        self.toolbox = QWidget()
        area.setWidget(self.toolbox)
        area.setWidgetResizable(True)
        area.setFrameShape(QFrame.NoFrame)
        area.setMinimumWidth(380)

        self.toolbox_layout = QVBoxLayout(self.toolbox)

        widgets = [
            self.init_title(),
            self.init_case(),
            self.init_tunnel(),
            self.init_tube(),
            self.init_card(),
            self.init_array(),
            self.init_calc(),
            QWidget()
        ]
        for widget in widgets:
            self.toolbox_layout.addWidget(widget)
        self.toolbox_layout.addStretch(self.toolbox_layout.count()-1)
        return area


    def init_title(self):
        group_box = QGroupBox("Scanner")
        layout = QHBoxLayout()

        self.scanner_name = QLineEdit(self.scanner.name)
        layout.addWidget(self.scanner_name)

        save_button = QPushButton("Save")
        save_button.setFixedWidth(84)
        layout.addWidget(save_button)
        save_button.clicked.connect(self.save)

        group_box.setLayout(layout)
        return group_box

    def get_variable(self, path):
        pos = self.scanner.config
        for key in path[:-1]:
            pos = pos[key]
        return pos[path[-1]]

    def update_variable(self, path, var):
        pos = self.scanner.config
        for key in path[:-1]:
            pos = pos[key]

        pos[path[-1]] = var

        self.scanner.update_configuration()

        if self.auto_update_box.isChecked():
            self.recalculate()

    def __create_spinbox(self,):
        spinbox = QDoubleSpinBox()
        spinbox.setRange(-1000000, 10000)
        spinbox.setFixedWidth(84)
        return spinbox

    def create_spinbox(self, path):
        spinbox = self.__create_spinbox()
        spinbox.setValue(self.get_variable(path))
        spinbox.valueChanged.connect(lambda value: self.update_variable(path, value))

        spinbox.setSingleStep(1.0)
        spinbox.setDecimals(2)
        return spinbox

    def create_combobox(self, path, items):
        box = QComboBox()
        box.addItems(items)
        box.setCurrentText(self.get_variable(path))
        box.currentTextChanged.connect(lambda text: self.update_variable(path, text))
        return box

    def create_checkbox(self, path, text):
        box = QCheckBox(text)
        box.setChecked(self.get_variable(path))
        box.toggled.connect(lambda state: self.update_variable(path, state))
        return box

    def set_case_changed(self):
        self.case_changed = True

    def init_case(self):
        group_box = QGroupBox("Case")
        layout = QGridLayout()

        x_offset_box = self.create_spinbox(["case", "offset_x"])
        z_offset_box = self.create_spinbox(["case", "offset_z"])
        x_size_box = self.create_spinbox(["case", "size_x"])
        z_size_box = self.create_spinbox(["case", "size_z"])

        for box in [x_offset_box, z_offset_box, x_size_box, z_size_box]:
            box.valueChanged.connect(self.set_case_changed)

        layout.addWidget(QLabel("Offset"), 0, 0)
        layout.addWidget(QLabel("X"), 0, 2)
        layout.addWidget(x_offset_box, 0, 3)
        layout.addWidget(QLabel("Z"), 0, 4)
        layout.addWidget(z_offset_box, 0, 5)

        layout.addWidget(QLabel("Size"), 1, 0)
        layout.addWidget(QLabel("W"), 1, 2)
        layout.addWidget(x_size_box, 1, 3)
        layout.addWidget(QLabel("H"), 1, 4)
        layout.addWidget(z_size_box, 1, 5)

        layout.setColumnStretch(1, 100)

        group_box.setLayout(layout)
        return group_box

    def init_tunnel(self):
        group_box = QGroupBox("Tunnel")
        layout = QGridLayout()

        x_offset_box = self.create_spinbox(["tunnel", "offset_x"])
        z_offset_box = self.create_spinbox(["tunnel", "offset_z"])
        x_size_box = self.create_spinbox(["tunnel", "size_x"])
        z_size_box = self.create_spinbox(["tunnel", "size_z"])

        layout.addWidget(QLabel("Offset"), 0, 0)
        layout.addWidget(QLabel("X"), 0, 2)
        layout.addWidget(x_offset_box, 0, 3)
        layout.addWidget(QLabel("Z"), 0, 4)
        layout.addWidget(z_offset_box, 0, 5)

        layout.addWidget(QLabel("Size"), 1, 0)
        layout.addWidget(QLabel("W"), 1, 2)
        layout.addWidget(x_size_box, 1, 3)
        layout.addWidget(QLabel("H"), 1, 4)
        layout.addWidget(z_size_box, 1, 5)

        layout.setColumnStretch(1, 100)

        group_box.setLayout(layout)
        return group_box

    def init_tube(self):
        group_box = QGroupBox("Tube")
        layout = QVBoxLayout()

        combo_layout = QHBoxLayout()
        box = self.create_combobox(["tube", "model"], Tube.get_tubes_list())
        combo_layout.addWidget(box)

        layout.addLayout(combo_layout)

        x_offset_box = self.create_spinbox(["tube", "offset_x"])
        z_offset_box = self.create_spinbox(["tube", "offset_z"])
        z_shift_box = self.create_spinbox(["tube", "shift_z"])

        grid_layout = QGridLayout()
        grid_layout.addWidget(QLabel("Offset"), 0, 0)
        grid_layout.addWidget(QLabel("X"), 0, 2)
        grid_layout.addWidget(x_offset_box, 0, 3)
        grid_layout.addWidget(QLabel("Z"), 0, 4)
        grid_layout.addWidget(z_offset_box, 0, 5)

        grid_layout.addWidget(QLabel("Shift"), 1, 0)
        grid_layout.addWidget(QLabel("Z"), 1, 4)
        grid_layout.addWidget(z_shift_box, 1, 5)

        grid_layout.setColumnStretch(1, 100)


        layout.addLayout(grid_layout)
        group_box.setLayout(layout)
        return group_box

    def init_card(self):
        group_box = QGroupBox("Card")
        layout = QVBoxLayout()

        combo_layout = QHBoxLayout()
        box = self.create_combobox(["card", "model"], Card.get_cards_list())
        combo_layout.addWidget(box)

        layout.addLayout(combo_layout)
        group_box.setLayout(layout)
        return group_box

    def init_array(self):
        group_box = QGroupBox("Array")
        layout = QGridLayout()

        mode_box = self.create_combobox(["array", "mode"], ["compact", "arc"])


        x_offset_box = self.create_spinbox(["array", "offset_x"])
        z_offset_box = self.create_spinbox(["array", "offset_z"])
        x_size_box = self.create_spinbox(["array", "length"])
        z_size_box = self.create_spinbox(["array", "height"])

        self.left_side_box = self.create_checkbox(["array", "left_side", "enabled"], "Left side")
        left_x_size_box = self.create_spinbox(["array", "left_side", "length"])
        left_z_size_box = self.create_spinbox(["array", "left_side", "height"])

        self.right_side_box = self.create_checkbox(["array", "right_side", "enabled"], "Right side")
        right_x_size_box = self.create_spinbox(["array", "right_side", "length"])
        right_z_size_box = self.create_spinbox(["array", "right_side", "height"])

        layout.addWidget(QLabel("Mode"), 0, 0)
        layout.addWidget(mode_box, 0, 3, 1, 3)

        layout.addWidget(QLabel("Offset"), 1, 0)
        layout.addWidget(QLabel("X"), 1, 2)
        layout.addWidget(x_offset_box, 1, 3)
        layout.addWidget(QLabel("Z"), 1, 4)
        layout.addWidget(z_offset_box, 1, 5)

        layout.addWidget(QLabel("Size"), 2, 0)
        layout.addWidget(QLabel("L"), 2, 2)
        layout.addWidget(x_size_box, 2, 3)
        layout.addWidget(QLabel("H"), 2, 4)
        layout.addWidget(z_size_box, 2, 5)

        layout.addWidget(self.left_side_box, 3, 0)
        layout.addWidget(QLabel("L"), 3, 2)
        layout.addWidget(left_z_size_box, 3, 3)
        layout.addWidget(QLabel("H"), 3, 4)
        layout.addWidget(left_x_size_box, 3, 5)

        layout.addWidget(self.right_side_box, 4, 0)
        layout.addWidget(QLabel("L"), 4, 2)
        layout.addWidget(right_z_size_box, 4, 3)
        layout.addWidget(QLabel("H"), 4, 4)
        layout.addWidget(right_x_size_box, 4, 5)

        layout.setColumnStretch(1, 100)

        group_box.setLayout(layout)
        return group_box

    def init_calc(self):
        group_box = QGroupBox("Calculation")

        self.auto_update_box = QCheckBox("Auto update")
        self.auto_update_box.toggled.connect(lambda checked: self.settings.setValue("auto_update", checked))

        layout = QGridLayout()

        update_button = QPushButton("Update")
        update_button.clicked.connect(self.recalculate)
        update_button.setFixedWidth(84)

        x_offset_box = self.create_spinbox(["array", "initial_card_offset"])
        layout.addWidget(self.auto_update_box, 0, 0, 1, 1)
        layout.addWidget(update_button, 0, 2, 1, 1)
        layout.addWidget(QLabel("Initial card offset"), 1, 0, 1, 1)
        layout.addWidget(x_offset_box, 1, 2, 1, 1)

        export_button = QPushButton("Export")

        menu = QMenu(export_button)
        menu.addAction(f"Export detector positions to the output directory", self.export)
        menu.addAction(f"Export simulation input to the simulation directory", self.export_simulation_input)
        menu.addAction(f"Display a 3D plot of the detectors", lambda: self.scanner.array.plot3d(self.scanner.tube.focal_spot)
)
        export_button.setMenu(menu)

        layout.addWidget(export_button, 2, 0, 1, 3)

        group_box.setLayout(layout)
        return group_box

if __name__ == '__main__':
    from scanner import Scanner

    app = QApplication(sys.argv)
    scanner = Scanner()
    gui = Gui(scanner)
    gui.show()
    sys.exit(app.exec())