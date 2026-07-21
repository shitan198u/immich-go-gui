from PySide6.QtWidgets import QApplication, QStyleFactory
from PySide6.QtGui import QGuiApplication, QPalette, QColor, QIcon, QPixmap, QPainter
from PySide6.QtCore import Qt, QByteArray
from PySide6.QtSvg import QSvgRenderer
from functools import lru_cache
import os

THEME_SYSTEM = "System"
THEME_LIGHT = "Light"
THEME_DARK = "Dark"

def normalize_theme_mode(mode):
    m = str(mode).strip().lower()
    if m == "system": return THEME_SYSTEM
    if m == "light": return THEME_LIGHT
    if m == "dark": return THEME_DARK
    return THEME_SYSTEM

def set_fusion_style():
    app = QApplication.instance()
    if not app: return
    style = QStyleFactory.create("Fusion")
    if style: app.setStyle(style)

def detect_system_theme() -> str:
    try:
        hints = QGuiApplication.styleHints()
        if hasattr(hints, "colorScheme"):
            scheme = hints.colorScheme()
            if scheme == Qt.ColorScheme.Dark: return "dark"
            if scheme == Qt.ColorScheme.Light: return "light"
    except Exception: pass

    app = QApplication.instance()
    if app is None: return "dark"
    pal = app.palette()
    bg = pal.color(QPalette.ColorRole.Window)
    fg = pal.color(QPalette.ColorRole.WindowText)
    return "dark" if fg.lightness() > bg.lightness() else "light"

@lru_cache(maxsize=8)
def theme_tokens(theme: str) -> dict:
    if theme == "dark":
        return {
            "bg": "#0E1113", "sidebar": "#121619", "surface": "#151A1E", "surface_alt": "#1B2126",
            "input_bg": "#1B2126", "input_focus_bg": "#20272D", "border": "#262D34", "border_strong": "#343C43",
            "text": "#E8ECEF", "text_muted": "#97A1AA", "text_faint": "#6B757D",
            "accent": "#4FB3A4", "accent_hover": "#6FD6C5", "accent_subtle": "#17332F",
            "primary": "#E1512E", "primary_hover": "#F1603D", "primary_subtle": "#3A1D15", "on_primary": "#FFFFFF",
            "warning": "#E5C07B",
            "button_bg": "#20262B", "button_hover": "#2A3238", "scrollbar": "#0E1113", "scrollbar_handle": "#3A434B",
            "terminal_bg": "#0B0D0E", "terminal_text": "#ECE7DD",
        }
    return {
        "bg": "#F5F7F9", "sidebar": "#FFFFFF", "surface": "#FFFFFF", "surface_alt": "#F8FAFC",
        "input_bg": "#F8FAFC", "input_focus_bg": "#FFFFFF", "border": "#D8DEE4", "border_strong": "#C7CED6",
        "text": "#18222C", "text_muted": "#5D6B7A", "text_faint": "#7C8794",
        "accent": "#0F766E", "accent_hover": "#14B8A6", "accent_subtle": "#E4F5F2",
        "primary": "#C2410C", "primary_hover": "#EA580C", "primary_subtle": "#FFEDD5", "on_primary": "#FFFFFF",
        "warning": "#B45309",
        "button_bg": "#EEF1F4", "button_hover": "#E2E7EC", "scrollbar": "#EEF1F4", "scrollbar_handle": "#AEB8C2",
        "terminal_bg": "#111827", "terminal_text": "#F9FAFB",
    }

@lru_cache(maxsize=8)
def build_stylesheet(theme: str) -> str:
    t = theme_tokens(theme)
    check_icon = os.path.join(os.path.dirname(__file__), "assets", "icons", "check.svg").replace("\\", "/")
    return f"""
        QMainWindow, QDialog {{
            background-color: {t['bg']};
            color: {t['text']};
        }}
        QWidget {{
            color: {t['text']};
            font-family: "Segoe UI", system-ui, sans-serif;
            font-size: 14px;
            background: transparent;
        }}

QToolTip {{
    background-color: {t['surface']};
    color: {t['text']};
    border: 1px solid {t['border']};
    padding: 6px 8px;
    border-radius: 6px;
}}

/* Header and footer */
#HeaderFrame, #FooterFrame {{
    background-color: {t['bg']};
    border: none;
}}

#HeaderFrame {{
    border-bottom: 1px solid {t['border']};
}}

#FooterFrame {{
    border-top: 1px solid {t['border']};
}}

QLabel#AppName {{
    font-family: "Consolas", monospace;
    font-weight: 600;
    font-size: 16px;
    color: {t['text']};
}}

QLabel#Crumb {{
    font-family: "Consolas", monospace;
    font-size: 12px;
    color: {t['text_muted']};
}}

QLabel#ModeLabel {{
    font-family: "Consolas", monospace;
    font-size: 12px;
    color: {t['text_muted']};
    padding-right: 8px;
}}

/* Sidebar */
#Sidebar {{
    background-color: {t['sidebar']};
    border-right: 1px solid {t['border']};
}}

QPushButton#NavBtn {{
    text-align: left;
    padding: 10px 12px;
    font-size: 14px;
    font-weight: 500;
    color: {t['text_muted']};
    border: 1px solid transparent;
    border-radius: 6px;
    background: transparent;
}}

QPushButton#NavBtn:hover {{
    background-color: {t['surface_alt']};
    color: {t['text']};
}}

QPushButton#NavBtn:checked {{
    background-color: {t['accent_subtle']};
    color: {t['accent']};
    border: 1px solid {t['accent']};
}}

QLabel#NavTitle {{
    font-family: "Consolas", monospace;
    font-size: 10px;
    font-weight: 600;
    color: {t['text_faint']};
    padding: 0 12px;
    margin-top: 16px;
}}

/* Status area */
#StatusFrame {{
    border-top: 1px solid {t['border']};
    padding: 16px;
    background-color: {t['sidebar']};
}}

QFrame#StatusCard {{
    background-color: {t['surface_alt']};
    border: 1px solid {t['border']};
    border-radius: 8px;
}}

QLabel#StatusText {{
    font-size: 12px;
    color: {t['text_muted']};
}}

QPushButton#ActionLink {{
    color: {t['accent']};
    background: transparent;
    border: none;
    font-size: 11px;
    font-family: "Consolas", monospace;
    text-align: left;
    padding: 0;
}}

QPushButton#ActionLink:hover {{
    color: {t['accent_hover']};
}}

/* Cards */
QFrame#Card {{
    background-color: {t['surface']};
    border: 1px solid {t['border']};
    border-radius: 8px;
}}

QLabel#CardTitle {{
    font-family: "Consolas", monospace;
    font-size: 12px;
    font-weight: 600;
    color: {t['text_muted']};
    letter-spacing: 0.4px;
    margin-bottom: 12px;
}}

QLabel#ReqBadge {{
    font-size: 10px;
    color: {t['primary']};
    background-color: {t['primary_subtle']};
    border: 1px solid {t['primary']};
    padding: 2px 6px;
    border-radius: 4px;
    font-family: "Segoe UI", sans-serif;
    font-weight: normal;
}}

QLabel#Subhead {{
    font-family: "Consolas", monospace;
    font-size: 11px;
    color: {t['text_faint']};
    letter-spacing: 0.4px;
    margin-top: 16px;
    margin-bottom: 8px;
    border-top: 1px solid {t['border']};
    padding-top: 12px;
}}

QLabel#FieldLabel {{
    font-size: 13px;
    font-weight: 500;
    color: {t['text']};
}}

QLabel#Hint {{
    font-size: 12px;
    color: {t['text_muted']};
}}

QLabel#WarningHint {{
    font-size: 12px;
    font-weight: 500;
    color: {t['warning']};
}}

/* Inputs */
QLineEdit,
QComboBox,
QSpinBox,
QPlainTextEdit {{
    background-color: {t['input_bg']};
    border: 1px solid {t['border_strong']};
    color: {t['text']};
    padding: 9px 11px;
    border-radius: 6px;
    font-size: 14px;
    selection-background-color: {t['accent']};
    selection-color: {t['on_primary']};
}}

QLineEdit:hover,
QComboBox:hover,
QSpinBox:hover,
QPlainTextEdit:hover {{
    border-color: {t['accent']};
}}

QLineEdit:focus,
QComboBox:focus,
QSpinBox:focus,
QPlainTextEdit:focus {{
    border: 1px solid {t['accent']};
    background-color: {t['input_focus_bg']};
}}

QLineEdit:disabled,
QComboBox:disabled,
QSpinBox:disabled,
QPlainTextEdit:disabled {{
    background-color: {t['surface_alt']};
    color: {t['text_faint']};
    border-color: {t['border']};
}}

QLineEdit[readOnly="true"],
QPlainTextEdit[readOnly="true"] {{
    background-color: {t['surface_alt']};
    color: {t['text_muted']};
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox QAbstractItemView {{
    background-color: {t['surface']};
    color: {t['text']};
    selection-background-color: {t['accent_subtle']};
    selection-color: {t['accent']};
    border: 1px solid {t['border']};
}}

QCheckBox {{
    color: {t['text']};
    spacing: 8px;
}}

QCheckBox:disabled {{
    color: {t['text_faint']};
}}

        /* ---- Check / radio indicators: explicit so they survive QSS styled-mode ---- */
        QCheckBox::indicator,
        QRadioButton::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {t['border_strong']};
            border-radius: 4px;
            background-color: {t['input_bg']};
        }}
        QCheckBox::indicator:hover,
        QRadioButton::indicator:hover {{
            border-color: {t['accent']};
        }}
        QCheckBox::indicator:checked,
        QRadioButton::indicator:checked {{
            background-color: {t['accent']};
            border-color: {t['accent']};
        }}
        QCheckBox::indicator:checked {{
            image: url("{check_icon}");
        }}
        QCheckBox::indicator:disabled,
        QRadioButton::indicator:disabled {{
            background-color: {t['surface_alt']};
            border-color: {t['border']};
        }}
        QRadioButton::indicator {{
            border-radius: 8px;
        }}
        /* ---- Combo / spin arrows: CSS triangles, no image files needed ---- */
        QComboBox::down-arrow {{
            width: 0; height: 0;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid {t['text_muted']};
            margin-right: 6px;
        }}
        QSpinBox::up-arrow {{
            width: 0; height: 0;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-bottom: 5px solid {t['text_muted']};
        }}
        QSpinBox::down-arrow {{
            width: 0; height: 0;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid {t['text_muted']};
        }}

/* Buttons */
QPushButton {{
    background-color: {t['button_bg']};
    color: {t['text']};
    border: 1px solid {t['border']};
    border-radius: 6px;
    padding: 8px 16px;
}}

QPushButton:hover {{
    background-color: {t['button_hover']};
}}

QPushButton:disabled {{
    background-color: {t['surface_alt']};
    color: {t['text_faint']};
    border-color: {t['border']};
}}

QPushButton#BtnRun {{
    background-color: {t['primary']};
    color: {t['on_primary']};
    border: none;
    border-radius: 7px;
    padding: 10px 18px;
    font-weight: 600;
    font-size: 13.5px;
}}

QPushButton#BtnRun:hover {{
    background-color: {t['primary_hover']};
}}

QPushButton#BtnRun:disabled {{
    background-color: {t['surface_alt']};
    color: {t['text_faint']};
    border: 1px solid {t['border']};
}}

QPushButton#BtnPreview {{
    background-color: {t['accent_subtle']};
    color: {t['accent']};
    border: 1px solid {t['accent']};
    border-radius: 7px;
    padding: 10px 18px;
    font-weight: 600;
    font-size: 13.5px;
}}

QPushButton#BtnPreview:hover {{
    background-color: {t['button_hover']};
}}

QPushButton#BtnPreview:disabled {{
    background-color: {t['surface_alt']};
    color: {t['text_faint']};
    border-color: {t['border']};
}}

        /* ---- Tabs (Upload / Archive sub-navigation) ---- */
        QTabWidget {{
            background: transparent;
            border: none;
        }}
        QTabWidget::pane {{
            border: none;
            background: transparent;
        }}
        QTabBar {{
            background: transparent;
            spacing: 6px;
        }}
        QTabBar::tab {{
            background: transparent;
            color: {t['text_muted']};
            border: 1px solid transparent;
            border-radius: 7px;
            padding: 8px 18px;
            font-size: 13.5px;
            font-weight: 600;
        }}
        QTabBar::tab:hover:!selected {{
            color: {t['text']};
            background-color: {t['button_hover']};
        }}
        QTabBar::tab:selected {{
            color: {t['accent']};
            background-color: {t['accent_subtle']};
            border: 1px solid {t['accent']};
        }}

/* Dialogs */
QDialog {{
    background-color: {t['surface']};
    color: {t['text']};
    border: 1px solid {t['border']};
    border-radius: 12px;
}}

QLabel#DlgKicker {{
    font-family: "Consolas", monospace;
    font-size: 11px;
    color: {t['text_faint']};
    letter-spacing: 0.4px;
}}

QLabel#DlgTitle {{
    font-size: 18px;
    font-weight: 600;
    color: {t['text']};
}}

QLabel#DlgDesc {{
    font-size: 13px;
    color: {t['text_muted']};
}}

QPlainTextEdit#CmdBlock {{
    background-color: {t['terminal_bg']};
    border: 1px solid {t['border']};
    color: {t['terminal_text']};
    font-family: "Consolas", monospace;
    font-size: 13px;
    border-radius: 8px;
    padding: 16px;
}}

/* Progress */
QProgressBar {{
    border: 1px solid {t['border']};
    border-radius: 6px;
    background-color: {t['surface_alt']};
    color: {t['text']};
    height: 18px;
    text-align: center;
}}

QProgressBar::chunk {{
    background-color: {t['accent']};
    border-radius: 5px;
}}

/* Scroll areas */
QScrollArea {{
    border: none;
    background-color: {t['bg']};
}}

QScrollBar:vertical {{
    border: none;
    background: {t['scrollbar']};
    width: 8px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: {t['scrollbar_handle']};
    min-height: 20px;
    border-radius: 4px;
}}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    border: none;
    background: {t['scrollbar']};
    height: 8px;
    margin: 0;
}}

QScrollBar::handle:horizontal {{
    background: {t['scrollbar_handle']};
    min-width: 20px;
    border-radius: 4px;
}}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* Menus */
QMenuBar {{
    background-color: {t['bg']};
    color: {t['text']};
    border-bottom: 1px solid {t['border']};
}}

QMenuBar::item {{
    background: transparent;
    padding: 6px 10px;
}}

QMenuBar::item:selected {{
    background-color: {t['surface_alt']};
}}

QMenu {{
    background-color: {t['surface']};
    color: {t['text']};
    border: 1px solid {t['border']};
}}

QMenu::item {{
    padding: 6px 24px;
}}

QMenu::item:selected {{
    background-color: {t['accent_subtle']};
    color: {t['accent']};
}}
"""

def apply_base_palette(theme: str):
    app = QApplication.instance()
    if app is None: return
    t = theme_tokens(theme)
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor(t["bg"]))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(t["text"]))
    pal.setColor(QPalette.ColorRole.Base, QColor(t["input_bg"]))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor(t["surface_alt"]))
    pal.setColor(QPalette.ColorRole.Text, QColor(t["text"]))
    pal.setColor(QPalette.ColorRole.Button, QColor(t["button_bg"]))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(t["text"]))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(t["accent"]))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(t["on_primary"]))
    pal.setColor(QPalette.ColorRole.ToolTipBase, QColor(t["surface"]))
    pal.setColor(QPalette.ColorRole.ToolTipText, QColor(t["text"]))
    pal.setColor(QPalette.ColorRole.Link, QColor(t["accent"]))
    pal.setColor(QPalette.ColorRole.LinkVisited, QColor(t["accent"]))
    pal.setColor(QPalette.ColorRole.PlaceholderText, QColor(t["text_faint"]))
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(t["text_faint"]))
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(t["text_faint"]))
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(t["text_faint"]))
    app.setPalette(pal)

def apply_application_theme(mode: str) -> str:
    mode = normalize_theme_mode(mode)
    resolved = detect_system_theme() if mode == THEME_SYSTEM else mode.lower()
    app = QApplication.instance()
    if app is None: return resolved
    app.setProperty("theme", resolved)
    apply_base_palette(resolved)
    app.setStyleSheet(build_stylesheet(resolved))
    return resolved

def connect_system_theme_changes(callback):
    try:
        hints = QGuiApplication.styleHints()
        if hasattr(hints, "colorSchemeChanged"):
            hints.colorSchemeChanged.connect(lambda *_: callback())
            return True
    except Exception: pass
    return False

_ICON_CACHE: dict[tuple[str, str], QIcon] = {}

def load_themed_icon(icon_name: str, theme: str) -> QIcon:
    """Loads an SVG icon from assets/icons and colors it based on the theme."""
    key = (icon_name, theme)
    cached = _ICON_CACHE.get(key)
    if cached is not None:
        return cached

    t = theme_tokens(theme)
    # Using text_muted for a subtle unselected look in sidebar
    color = t["text_muted"]
    
    svg_path = os.path.join(os.path.dirname(__file__), "assets", "icons", f"{icon_name}.svg")
    
    if not os.path.exists(svg_path):
        icon = QIcon()
        _ICON_CACHE[key] = icon
        return icon
        
    with open(svg_path, "r", encoding="utf-8") as f:
        svg_content = f.read()
        
    svg_content = svg_content.replace('currentColor', color)
    
    renderer = QSvgRenderer(QByteArray(svg_content.encode("utf-8")))
    pixmap = QPixmap(20, 20)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    # Improve rendering quality
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter)
    painter.end()
    
    icon = QIcon(pixmap)
    _ICON_CACHE[key] = icon
    return icon

def clear_icon_cache() -> None:
    _ICON_CACHE.clear()