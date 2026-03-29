# -*- coding: utf-8 -*-

from qgis.PyQt import uic
from qgis.PyQt.QtCore import pyqtSignal, Qt, QThread
from qgis.PyQt.QtWidgets import QDialog, QMessageBox, QFileDialog, QApplication, QInputDialog
from qgis.core import QgsProject
import os.path
import tempfile

from .windrose_worker import WindRoseWorker
from .windrose_utils import create_rose_layers
from .style_manager import StyleManager
from .export_helper import ExportHelper

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'windrose_dialog.ui'))


class WindRoseDialog(QDialog, FORM_CLASS):
    """Main Settings Dialog"""

    pick_point_clicked = pyqtSignal()

    def __init__(self, iface, parent=None):
        super(WindRoseDialog, self).__init__(parent)
        self.setupUi(self)
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.project = QgsProject.instance()

        self.current_lon = None
        self.current_lat = None

        self.init_controls()

        self.style_manager = StyleManager()
        self.export_helper = ExportHelper(self.iface)

        # Connect button signals
        self.btn_map_point.clicked.connect(self.on_map_point)
        self.btn_manual.clicked.connect(self.on_manual_input)
        self.btn_generate.clicked.connect(self.generate_rose)
        self.btn_export_svg.clicked.connect(self.export_svg)
        self.btn_browse_svg.clicked.connect(self.browse_svg_path)

        # Fill styles
        self.cmb_style.addItems(self.style_manager.get_style_names())
        # Graph styles
        self.cmb_graph_style.addItems(["Sector-based", "Concentric-circles"])
        # Month selection: clear then add to avoid duplication with UI predefined items
        self.cmb_month.clear()
        self.cmb_month.addItems(["All Year"] + [f"{i}" for i in range(1, 13)])

        # Default values
        self.spin_year.setValue(2024)
        self.cmb_height.setCurrentIndex(0)  # 10m
        self.slider_opacity.setValue(80)
        self.line_svg_path.setText(os.path.join(tempfile.gettempdir(), 'windrose.svg'))

        self.worker = None
        self.thread = None
        self.group_name = None

    def init_controls(self):
        self.line_lon.setReadOnly(True)
        self.line_lat.setReadOnly(True)

    def on_map_point(self):
        self.pick_point_clicked.emit()

    def on_manual_input(self):
        lon, ok1 = QInputDialog.getDouble(self, 'Manual Input', 'Longitude:', 0, -180, 180, 6)
        if not ok1:
            return
        lat, ok2 = QInputDialog.getDouble(self, 'Manual Input', 'Latitude:', 0, -90, 90, 6)
        if not ok2:
            return
        self.set_coordinates(lon, lat)

    def set_coordinates(self, lon, lat):
        self.current_lon = lon
        self.current_lat = lat
        self.update_coord_display()
        self.raise_()
        self.activateWindow()

    def update_coord_display(self):
        if self.current_lon is not None and self.current_lat is not None:
            self.line_lon.setText(f'{self.current_lon:.6f}')
            self.line_lat.setText(f'{self.current_lat:.6f}')
        else:
            self.line_lon.clear()
            self.line_lat.clear()

    def browse_svg_path(self):
        path, _ = QFileDialog.getSaveFileName(
            self, 'Save SVG File', self.line_svg_path.text(), 'SVG files (*.svg)'
        )
        if path:
            self.line_svg_path.setText(path)

    def generate_rose(self):
        # Check thread
        if self.thread is not None:
            try:
                if self.thread.isRunning():
                    QMessageBox.warning(self, 'Warning', 'The previous generation task has not finished, please wait.')
                    return
                else:
                    self.thread = None
                    self.worker = None
            except RuntimeError:
                self.thread = None
                self.worker = None

        if self.current_lon is None or self.current_lat is None:
            QMessageBox.warning(self, 'Error', 'Please select a point first (Map Pick or Manual Input)')
            return

        year = self.spin_year.value()
        height_str = self.cmb_height.currentText()
        height = int(height_str.replace('m', ''))
        self.style_name = self.cmb_style.currentText()
        self.graph_style = self.cmb_graph_style.currentText()
        self.opacity = self.slider_opacity.value() / 100.0
        self.add_to_project = self.cb_add_to_project.isChecked()
        self.export_svg = self.cb_export_svg.isChecked()
        self.svg_path = self.line_svg_path.text() if self.export_svg else None

        month_text = self.cmb_month.currentText()
        if month_text == "All Year":
            month = None
            month_str = "AllYear"
        else:
            month = int(month_text)
            month_str = f"{month:02d}"

        lon_str = f"{self.current_lon:.4f}".replace('.', '_')
        lat_str = f"{self.current_lat:.4f}".replace('.', '_')
        self.group_name = f"WindRose-{year}-{month_str}-{lon_str}_{lat_str}"

        self.btn_generate.setEnabled(False)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        self.worker = WindRoseWorker(
            self.current_lon, self.current_lat, year, month, height
        )
        self.thread = QThread()
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_data_ready)
        self.worker.error.connect(self.on_worker_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    def on_data_ready(self, freq, labels, angles):
        """Data ready, create layers in main thread"""
        QApplication.restoreOverrideCursor()
        self.btn_generate.setEnabled(True)

        try:
            if self.add_to_project:
                show_circles = (self.graph_style == "Concentric-circles")
                layers = create_rose_layers(
                    self.current_lon, self.current_lat, freq, labels, angles,
                    group_name=self.group_name, show_circles=show_circles
                )
                StyleManager.apply_style_to_layers(layers, self.style_name, self.opacity)

                if self.export_svg and layers:
                    # Select layers to export: Sector Area, Closed Area, Coordinate Line, North Arrow
                    export_layer_names = ["Sector Area", "Closed Area", "Coordinate Line", "North Arrow"]
                    export_layers = [lyr for lyr in layers if lyr.name() in export_layer_names]
                    if export_layers:
                        self.export_helper.export_layers_as_svg(export_layers, self.svg_path, self.iface)
                    else:
                        # If not found, export all layers (fallback)
                        self.export_helper.export_layers_as_svg(layers, self.svg_path, self.iface)

            QMessageBox.information(self, 'Complete', 'Wind rose generation completed')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error during generation: {str(e)}')

        self.thread = None
        self.worker = None

    def on_worker_error(self, error_msg):
        QApplication.restoreOverrideCursor()
        self.btn_generate.setEnabled(True)
        QMessageBox.critical(self, 'Error', error_msg)
        self.thread = None
        self.worker = None

    def export_svg(self):
        QMessageBox.information(self, 'Info', 'Please check "Export SVG" when generating to export automatically.')