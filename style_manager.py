# -*- coding: utf-8 -*-

from qgis.PyQt.QtGui import QColor
from qgis.core import (
    QgsSymbol, QgsFillSymbol, QgsLineSymbol, QgsMarkerSymbol,
    QgsSimpleFillSymbolLayer, QgsCategorizedSymbolRenderer
)


class StyleManager:
    STYLES = {
        "default": {
            "sector surface": {"outline": "#000000", "width": 0.2},
            "outer ring road": {"color": "#000000", "width": 0.5},
            "collection point": {"color": "#FF0000", "size": 2.0},
            "coordinate lines": {"color": "#000000", "width": 0.3},
            "closed surface": {"outline": "#000000", "width": 0.2},  # No filler, remains transparent
            "wind direction frequency": {}
        },
        "warm": {
            "sector surface": {"outline": "#BF360C", "width": 0.2},
            "outer ring road": {"color": "#FF6F00", "width": 0.5},
            "collection point": {"color": "#D32F2F", "size": 2.0},
            "coordinate lines": {"color": "#757575", "width": 0.3},
            "closed surface": {"outline": "#FF6F00", "width": 0.2},
        },
        "cool": {
            "sector surface": {"outline": "#0288D1", "width": 0.2},
            "outer ring road": {"color": "#01579B", "width": 0.5},
            "collection point": {"color": "#0D47A1", "size": 2.0},
            "coordinate lines": {"color": "#BDBDBD", "width": 0.3},
            "closed surface": {"outline": "#01579B", "width": 0.2},
        }
    }

    @classmethod
    def get_style_names(cls):
        return list(cls.STYLES.keys())

    @classmethod
    def apply_style_to_layers(cls, layers, style_name, opacity=1.0):
        if style_name not in cls.STYLES:
            return
        style_def = cls.STYLES[style_name]
        for layer in layers:
            layer_name = layer.name()
            if layer_name not in style_def:
                continue
            props = style_def[layer_name]
            renderer = layer.renderer()
            if renderer is None:
                continue

            if isinstance(renderer, QgsCategorizedSymbolRenderer):
                for cat in renderer.categories():
                    symbol = cat.symbol()
                    if symbol is None:
                        continue
                    if isinstance(symbol, QgsFillSymbol):
                        if "outline" in props:
                            cls._set_fill_outline_color(symbol, QColor(props["outline"]))
                        if "width" in props:
                            cls._set_fill_outline_width(symbol, props["width"])
                        symbol.setOpacity(opacity)
            else:
                symbol = renderer.symbol()
                if symbol is None:
                    continue

                if isinstance(symbol, QgsFillSymbol):
                    # Do not modify fill color, only modify outline and opacity
                    if "outline" in props:
                        cls._set_fill_outline_color(symbol, QColor(props["outline"]))
                    if "width" in props:
                        cls._set_fill_outline_width(symbol, props["width"])
                    symbol.setOpacity(opacity)
                elif isinstance(symbol, QgsLineSymbol):
                    if "color" in props:
                        symbol.setColor(QColor(props["color"]))
                    if "width" in props:
                        symbol.setWidth(props["width"])
                elif isinstance(symbol, QgsMarkerSymbol):
                    if "color" in props:
                        symbol.setColor(QColor(props["color"]))
                    if "size" in props:
                        symbol.setSize(props["size"])

            layer.triggerRepaint()

    @staticmethod
    def _set_fill_outline_color(symbol, color):
        if hasattr(symbol, 'setStrokeColor'):
            symbol.setStrokeColor(color)
            return
        for i in range(symbol.symbolLayerCount()):
            layer = symbol.symbolLayer(i)
            if isinstance(layer, QgsSimpleFillSymbolLayer):
                layer.setStrokeColor(color)
                break

    @staticmethod
    def _set_fill_outline_width(symbol, width):
        if hasattr(symbol, 'setStrokeWidth'):
            symbol.setStrokeWidth(width)
            return
        for i in range(symbol.symbolLayerCount()):
            layer = symbol.symbolLayer(i)
            if isinstance(layer, QgsSimpleFillSymbolLayer):
                layer.setStrokeWidth(width)
                break
