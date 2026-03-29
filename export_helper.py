# -*- coding: utf-8 -*-

from qgis.PyQt.QtCore import QRectF, QSize
from qgis.PyQt.QtGui import QColor, QPainter
from qgis.PyQt.QtSvg import QSvgGenerator
from qgis.core import (
    QgsMapSettings, QgsMapRendererCustomPainterJob
)


class ExportHelper:
    def __init__(self, iface):
        self.iface = iface

    @staticmethod
    def export_layers_as_svg(layers, file_path, iface, dpi=96):
        """
        Export the specified layer list as an SVG file using direct rendering.
        layers: QgsMapLayer list
        """
        if not layers:
            raise Exception("No layers to export")

        # Combine the extents of all layers
        extent = layers[0].extent()
        for layer in layers[1:]:
            extent.combineExtentWith(layer.extent())

        if extent.isEmpty() or extent.isNull():
            raise Exception("Layer extent is empty")

        # Calculate suitable output dimensions
        target_width = 800
        target_height = int(target_width * (extent.height() / extent.width()))

        settings = QgsMapSettings()
        settings.setLayers(layers)
        settings.setExtent(extent)
        settings.setOutputSize(QSize(target_width, target_height))
        settings.setOutputDpi(dpi)
        # Set transparent background
        settings.setBackgroundColor(QColor(0, 0, 0, 0))  # Fully transparent background

        svg_gen = QSvgGenerator()
        svg_gen.setFileName(file_path)
        svg_gen.setSize(QSize(target_width, target_height))
        svg_gen.setViewBox(QRectF(0, 0, target_width, target_height))
        svg_gen.setTitle("WindRose")
        svg_gen.setDescription("Exported from QGIS")

        painter = QPainter()
        painter.begin(svg_gen)
        job = QgsMapRendererCustomPainterJob(settings, painter)
        job.start()
        job.waitForFinished()
        painter.end()

        return True