"""
theme.py – Centralised theme tokens, stylesheet builder, and icon loader
for Immich-Go GUI.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication


# ---------------------------------------------------------------------------
# Theme token definitions
# ---------------------------------------------------------------------------

def theme_tokens(theme: str = "dark") -> dict[str, str]:
    """Return a flat dict of colour tokens for the requested theme."""
    dark = {
        "bg":              "#1e1e2e",
        "bg_alt":          "#181825",
        "surface":         "#313244",
        "surface_hover":   "#45475a",
        "border":          "#585b70",
        "text":            "#cdd6f4",
        "text_muted":      "#a6adc8",
        "accent":          "#89b4fa",
        "accent_hover":    "#74c7ec",
        "danger":          "#f38ba8",
        "warning":         "#fab387",
        "success":         "#a6e3a1",
        "sidebar_bg":      "#11111b",
        "sidebar_text":    "#bac2de",
        "sidebar_active":  "#89b4fa",
        "input_bg":        "#1e1e2e",
        "input_border":    "#585b70",
        "input_focus":     "#89b4fa",
        "scrollbar":       "#45475a",
        "scrollbar_hover": "#585b70",
        "card_bg":         "#1e1e2e",
        "card_border":     "#313244",
        "tooltip_bg":      "#313244",
        "tooltip_text":    "#cdd6f4",
        "selection_bg":    "#89b4fa",
        "selection_text":  "#1e1e2e",
    }
    light = {
        "bg":              "#eff1f5",
        "bg_alt":          "#e6e9ef",
        "surface":         "#ccd0da",
        "surface_hover":   "#bcc0cc",
        "border":          "#9ca0b0",
        "text":            "#4c4f69",
        "text_muted":      "#6c6f85",
        "accent":          "#1e66f5",
        "accent_hover":    "#2a6ef5",
        "danger":          "#d20f39",
        "warning":         "#fe640b",
        "success":         "#40a02b",
        "sidebar_bg":      "#dce0e8",
        "sidebar_text":    "#4c4f69",
        "sidebar_active":  "#1e66f5",
        "input_bg":        "#eff1f5",
        "input_border":    "#9ca0b0",
        "input_focus":     "#1e66f5",
        "scrollbar":       "#bcc0cc",
        "scrollbar_hover": "#9ca0b0",
        "card_bg":         "#eff1f5",
        "card_border":     "#ccd0da",
        "tooltip_bg":      "#ccd0da",
        "tooltip_text":    "#4c4f69",
        "selection_bg":    "#1e66f5",
        "selection_text":  "#eff1f5",
    }
    return dark if theme == "dark" else light


# ---------------------------------------------------------------------------
# Stylesheet builder
# ---------------------------------------------------------------------------

def build_stylesheet(theme: str = "dark") -> str:
    """Build the full QSS stylesheet for the given theme."""
    t = theme_tokens(theme)
    return f"""
    /* ---- Global ---- */
    QMainWindow, QDialog {{
        background-color: {t['bg']};
        color: {t['text']};
    }}
    QWidget {{
        font-family: "Inter", "Segoe UI", "Noto Sans", "Noto Color Emoji",
                     "Apple Color Emoji", "Segoe UI Emoji", sans-serif;
        font-size: 13px;
        color: {t['text']};
    }}

    /* ---- Sidebar ---- */
    #sidebar {{
        background-color: {t['sidebar_bg']};
        border: none;
    }}
    NavItem {{
        background: transparent;
        color: {t['sidebar_text']};
        border: none;
        border-radius: 6px;
        padding: 8px 12px;
        text-align: left;
    }}
    NavItem:hover {{
        background-color: {t['surface_hover']};
    }}
    NavItem[checked="true"] {{
        background-color: {t['surface']};
        color: {t['sidebar_active']};
        font-weight: bold;
    }}
    NavGroup > QLabel {{
        color: {t['text_muted']};
        font-size: 11px;
        font-weight: bold;
        text-transform: uppercase;
        padding: 12px 12px 4px 12px;
    }}

    /* ---- Cards ---- */
    Card {{
        background-color: {t['card_bg']};
        border: 1px solid {t['card_border']};
        border-radius: 10px;
    }}
    Card > QLabel {{
        font-size: 15px;
        font-weight: bold;
        padding: 4px 0;
    }}

    /* ---- Form sections ---- */
    FormSection > QLabel {{
        font-size: 12px;
        font-weight: 600;
        color: {t['text_muted']};
        padding-top: 8px;
    }}

    /* ---- Inputs ---- */
    QLineEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
        background-color: {t['input_bg']};
        border: 1px solid {t['input_border']};
        border-radius: 6px;
        padding: 6px 10px;
        color: {t['text']};
        selection-background-color: {t['selection_bg']};
        selection-color: {t['selection_text']};
    }}
    QLineEdit:focus, QPlainTextEdit:focus, QSpinBox:focus,
    QDoubleSpinBox:focus, QComboBox:focus {{
        border: 1px solid {t['input_focus']};
    }}
    QLineEdit:disabled, QPlainTextEdit:disabled, QSpinBox:disabled,
    QComboBox:disabled {{
        color: {t['text_muted']};
        background-color: {t['surface']};
    }}

    /* ---- ComboBox drop-down arrow ---- */
    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 24px;
        border-left: 1px solid {t['input_border']};
        border-top-right-radius: 6px;
        border-bottom-right-radius: 6px;
    }}
    QComboBox::down-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 5px solid {t['text_muted']};
        margin-right: 6px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {t['surface']};
        border: 1px solid {t['border']};
        border-radius: 6px;
        color: {t['text']};
        selection-background-color: {t['selection_bg']};
        selection-color: {t['selection_text']};
    }}

    /* ---- Buttons ---- */
    QPushButton {{
        background-color: {t['surface']};
        border: 1px solid {t['border']};
        border-radius: 6px;
        padding: 8px 16px;
        color: {t['text']};
        font-weight: 600;
    }}
    QPushButton:hover {{
        background-color: {t['surface_hover']};
    }}
    QPushButton:pressed {{
        background-color: {t['border']};
    }}
    QPushButton#primaryBtn {{
        background-color: {t['accent']};
        color: {t['bg']};
        border: none;
    }}
    QPushButton#primaryBtn:hover {{
        background-color: {t['accent_hover']};
    }}
    QPushButton#dangerBtn {{
        background-color: {t['danger']};
        color: {t['bg']};
        border: none;
    }}

    /* ---- Tool buttons (trailing icons in line-edits) ---- */
    QToolButton {{
        background: transparent;
        border: none;
        padding: 2px;
    }}
    QToolButton:hover {{
        background-color: {t['surface_hover']};
        border-radius: 4px;
    }}

    /* ---- Checkboxes & Radio ---- */
    QCheckBox, QRadioButton {{
        spacing: 8px;
        color: {t['text']};
    }}
    QCheckBox::indicator, QRadioButton::indicator {{
        width: 16px;
        height: 16px;
        border: 1px solid {t['border']};
        border-radius: 4px;
        background-color: {t['input_bg']};
    }}
    QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
        background-color: {t['accent']};
        border-color: {t['accent']};
    }}
    QRadioButton::indicator {{
        border-radius: 8px;
    }}

    /* ---- Spin boxes ---- */
    QSpinBox::up-button, QSpinBox::down-button,
    QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
        background-color: {t['surface']};
        border: none;
        width: 18px;
    }}
    QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-bottom: 5px solid {t['text_muted']};
    }}
    QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 5px solid {t['text_muted']};
    }}

    /* ---- Scroll bars ---- */
    QScrollBar:vertical {{
        background: {t['bg']};
        width: 8px;
        border: none;
    }}
    QScrollBar::handle:vertical {{
        background: {t['scrollbar']};
        border-radius: 4px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {t['scrollbar_hover']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QScrollBar:horizontal {{
        background: {t['bg']};
        height: 8px;
        border: none;
    }}
    QScrollBar::handle:horizontal {{
        background: {t['scrollbar']};
        border-radius: 4px;
        min-width: 30px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {t['scrollbar_hover']};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0;
    }}

    /* ---- Tab widget ---- */
    QTabWidget::pane {{
        border: 1px solid {t['card_border']};
        border-radius: 8px;
        background-color: {t['card_bg']};
    }}
    QTabBar::tab {{
        background-color: {t['surface']};
        color: {t['text_muted']};
        border: 1px solid {t['card_border']};
        border-bottom: none;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        padding: 8px 18px;
        margin-right: 2px;
    }}
    QTabBar::tab:selected {{
        background-color: {t['card_bg']};
        color: {t['accent']};
        font-weight: bold;
    }}
    QTabBar::tab:hover:!selected {{
        background-color: {t['surface_hover']};
    }}

    /* ---- Group box ---- */
    QGroupBox {{
        border: 1px solid {t['card_border']};
        border-radius: 8px;
        margin-top: 12px;
        padding-top: 16px;
        font-weight: bold;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
        color: {t['accent']};
    }}

    /* ---- Progress bar ---- */
    QProgressBar {{
        border: 1px solid {t['border']};
        border-radius: 6px;
        background-color: {t['surface']};
        text-align: center;
        color: {t['text']};
        height: 20px;
    }}
    QProgressBar::chunk {{
        background-color: {t['accent']};
        border-radius: 5px;
    }}

    /* ---- Tool tips ---- */
    QToolTip {{
        background-color: {t['tooltip_bg']};
        color: {t['tooltip_text']};
        border: 1px solid {t['border']};
        border-radius: 4px;
        padding: 6px 10px;
    }}

    /* ---- Warning hint (SSL, etc.) ---- */
    QLabel[cssClass="WarningHint"] {{
        color: {t['warning']};
        font-size: 11px;
        padding: 2px 0;
    }}
    QLabel[cssClass="DangerHint"] {{
        color: {t['danger']};
        font-size: 11px;
        font-weight: bold;
        padding: 2px 0;
    }}

    /* ---- Status bar ---- */
    QStatusBar {{
        background-color: {t['bg_alt']};
        color: {t['text_muted']};
        border-top: 1px solid {t['card_border']};
    }}

    /* ---- Menu bar ---- */
    QMenuBar {{
        background-color: {t['bg_alt']};
        color: {t['text']};
    }}
    QMenuBar::item:selected {{
        background-color: {t['surface']};
    }}
    QMenu {{
        background-color: {t['surface']};
        color: {t['text']};
        border: 1px solid {t['border']};
    }}
    QMenu::item:selected {{
        background-color: {t['accent']};
        color: {t['bg']};
    }}
    """


# ---------------------------------------------------------------------------
# Palette helper (for native dialogs)
# ---------------------------------------------------------------------------

def apply_base_palette(app: QApplication, theme: str = "dark") -> None:
    """Apply a QPalette that matches the QSS theme so native dialogs blend in."""
    from PySide6.QtGui import QPalette

    t = theme_tokens(theme)
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window,          QColor(t["bg"]))
    p.setColor(QPalette.ColorRole.WindowText,      QColor(t["text"]))
    p.setColor(QPalette.ColorRole.Base,            QColor(t["input_bg"]))
    p.setColor(QPalette.ColorRole.AlternateBase,   QColor(t["surface"]))
    p.setColor(QPalette.ColorRole.Text,            QColor(t["text"]))
    p.setColor(QPalette.ColorRole.Button,          QColor(t["surface"]))
    p.setColor(QPalette.ColorRole.ButtonText,      QColor(t["text"]))
    p.setColor(QPalette.ColorRole.Highlight,       QColor(t["accent"]))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor(t["bg"]))
    p.setColor(QPalette.ColorRole.ToolTipBase,     QColor(t["tooltip_bg"]))
    p.setColor(QPalette.ColorRole.ToolTipText,     QColor(t["tooltip_text"]))
    p.setColor(QPalette.ColorRole.PlaceholderText, QColor(t["text_muted"]))
    app.setPalette(p)


# ---------------------------------------------------------------------------
# Icon loader with HiDPI support and caching
# ---------------------------------------------------------------------------

_icon_cache: dict[str, QIcon] = {}


def load_themed_icon(name: str, theme: str = "dark", size: int = 20) -> QIcon:
    """
    Load an SVG/PNG icon from the icons/ directory, tint it to the theme
    accent colour, and return a QIcon with HiDPI-aware pixmap sizes.

    Results are cached so repeated calls are cheap.
    """
    cache_key = f"{name}:{theme}:{size}"
    if cache_key in _icon_cache:
        return _icon_cache[cache_key]

    t = theme_tokens(theme)
    icon_dir = Path(__file__).parent / "icons"
    icon_path = icon_dir / f"{name}.svg"
    if not icon_path.exists():
        icon_path = icon_dir / f"{name}.png"

    icon = QIcon()
    if icon_path.exists():
        # Load at multiple sizes for HiDPI displays
        for scale in (1, 1.5, 2):
            px_size = int(size * scale)
            pixmap = QPixmap(str(icon_path))
            if not pixmap.isNull():
                pixmap = pixmap.scaled(
                    px_size, px_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                # Tint with accent colour
                tinted = QPixmap(pixmap.size())
                tinted.fill(Qt.GlobalColor.transparent)
                painter = QPainter(tinted)
                painter.drawPixmap(0, 0, pixmap)
                painter.setCompositionMode(
                    QPainter.CompositionMode.CompositionMode_SourceIn
                )
                painter.fillRect(tinted.rect(), QColor(t["accent"]))
                painter.end()
                tinted.setDevicePixelRatio(scale)
                icon.addPixmap(tinted)
    else:
        # Fallback: generate a simple coloured square
        for scale in (1, 1.5, 2):
            px_size = int(size * scale)
            pixmap = QPixmap(px_size, px_size)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QColor(t["accent"]))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(2, 2, px_size - 4, px_size - 4, 3, 3)
            painter.end()
            pixmap.setDevicePixelRatio(scale)
            icon.addPixmap(pixmap)

    _icon_cache[cache_key] = icon
    return icon


def clear_icon_cache() -> None:
    """Clear the icon cache (call when switching themes)."""
    _icon_cache.clear()