"""
ui/themes.py — Système de thèmes pour l'interface Boxy.

Chaque thème est un dictionnaire de couleurs.
build_stylesheet(theme) génère le QSS complet.
"""

# ─── Définition des thèmes ──────────────────────────────────────────

THEMES: dict[str, dict] = {
    "cyan": {
        "name":    "Cyan — Iron Man",
        "bg":      "#07090e",
        "panel":   "#0c1020",
        "border":  "#1a3555",
        "accent":  "#00d4ff",
        "accent2": "#0066aa",
        "text":    "#b8d8ff",
        "dim":     "#3a5570",
        "success": "#00ff88",
        "warn":    "#ffaa00",
        "error":   "#ff4444",
    },
    "red": {
        "name":    "Rouge — Danger",
        "bg":      "#0e0709",
        "panel":   "#1a0a0a",
        "border":  "#551a1a",
        "accent":  "#ff3355",
        "accent2": "#aa1122",
        "text":    "#ffb8c0",
        "dim":     "#703040",
        "success": "#00ff88",
        "warn":    "#ffaa00",
        "error":   "#ff6666",
    },
    "green": {
        "name":    "Vert — Matrix",
        "bg":      "#070e09",
        "panel":   "#0a1a0c",
        "border":  "#1a4a20",
        "accent":  "#00ff55",
        "accent2": "#007722",
        "text":    "#b8ffc8",
        "dim":     "#3a703f",
        "success": "#00ff88",
        "warn":    "#ffaa00",
        "error":   "#ff4444",
    },
    "purple": {
        "name":    "Violet — Mystère",
        "bg":      "#09070e",
        "panel":   "#130a1a",
        "border":  "#3a1555",
        "accent":  "#bb44ff",
        "accent2": "#7711aa",
        "text":    "#e0b8ff",
        "dim":     "#5a3570",
        "success": "#00ff88",
        "warn":    "#ffaa00",
        "error":   "#ff4444",
    },
    "orange": {
        "name":    "Orange — Soleil",
        "bg":      "#0e0a07",
        "panel":   "#1a1208",
        "border":  "#552a00",
        "accent":  "#ff8800",
        "accent2": "#aa4400",
        "text":    "#ffd8b8",
        "dim":     "#705030",
        "success": "#00ff88",
        "warn":    "#ffdd00",
        "error":   "#ff4444",
    },
    "white": {
        "name":    "Clair — Minimal",
        "bg":      "#f0f2f5",
        "panel":   "#ffffff",
        "border":  "#c0cce0",
        "accent":  "#0088cc",
        "accent2": "#005599",
        "text":    "#1a2a3a",
        "dim":     "#8899aa",
        "success": "#009944",
        "warn":    "#cc7700",
        "error":   "#cc2222",
    },
}


def get_theme(name: str) -> dict:
    """Retourne le thème par son nom (cyan par défaut si introuvable)."""
    return THEMES.get(name, THEMES["cyan"])


def build_stylesheet(t: dict) -> str:
    """Génère le QSS complet à partir d'un dictionnaire de thème."""
    return f"""
QMainWindow, QWidget {{
    background-color: {t['bg']};
    color: {t['text']};
    font-family: Consolas, 'Courier New', monospace;
    font-size: 13px;
}}
QFrame#panel {{
    background-color: {t['panel']};
    border: 1px solid {t['border']};
    border-radius: 4px;
}}
QLabel#title {{
    color: {t['accent']};
    font-size: 20px;
    font-weight: bold;
    letter-spacing: 4px;
}}
QLabel#section {{
    color: {t['accent']};
    font-size: 10px;
    letter-spacing: 2px;
    padding: 4px 0px;
}}
QLabel#stat {{
    color: {t['text']};
    font-size: 12px;
    padding: 2px 0px;
}}
QTextEdit {{
    background-color: transparent;
    border: none;
    color: {t['text']};
    font-family: Consolas, 'Courier New', monospace;
    font-size: 13px;
    padding: 8px;
}}
QLineEdit {{
    background-color: {t['panel']};
    border: 1px solid {t['border']};
    border-radius: 4px;
    color: {t['text']};
    font-family: Consolas, 'Courier New', monospace;
    font-size: 13px;
    padding: 8px 12px;
    selection-background-color: {t['accent2']};
}}
QLineEdit:focus {{
    border: 1px solid {t['accent']};
}}
QPushButton {{
    background-color: {t['panel']};
    border: 1px solid {t['border']};
    border-radius: 4px;
    color: {t['accent']};
    font-size: 16px;
    padding: 8px 14px;
    min-width: 40px;
}}
QPushButton:hover {{
    background-color: {t['accent2']};
    border-color: {t['accent']};
}}
QPushButton:pressed {{
    background-color: {t['accent']};
    color: {t['bg']};
}}
QPushButton#mic_active {{
    background-color: {t['error']};
    border-color: {t['error']};
    color: white;
}}
QScrollBar:vertical {{
    background: {t['bg']};
    width: 6px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {t['border']};
    border-radius: 3px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QTabWidget::pane {{
    border: 1px solid {t['border']};
    background: {t['panel']};
    border-radius: 4px;
}}
QTabBar::tab {{
    background: {t['bg']};
    color: {t['dim']};
    border: 1px solid {t['border']};
    padding: 6px 16px;
    font-size: 12px;
}}
QTabBar::tab:selected {{
    background: {t['panel']};
    color: {t['accent']};
    border-bottom: 2px solid {t['accent']};
}}
QTabBar::tab:hover {{
    color: {t['text']};
}}
QComboBox {{
    background-color: {t['panel']};
    border: 1px solid {t['border']};
    border-radius: 4px;
    color: {t['text']};
    padding: 4px 8px;
}}
QComboBox:focus {{
    border: 1px solid {t['accent']};
}}
QComboBox QAbstractItemView {{
    background: {t['panel']};
    color: {t['text']};
    selection-background-color: {t['accent2']};
    border: 1px solid {t['border']};
}}
QCheckBox {{
    color: {t['text']};
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {t['border']};
    border-radius: 3px;
    background: {t['panel']};
}}
QCheckBox::indicator:checked {{
    background: {t['accent']};
    border-color: {t['accent']};
}}
QSlider::groove:horizontal {{
    background: {t['border']};
    height: 4px;
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {t['accent']};
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}
QSlider::sub-page:horizontal {{
    background: {t['accent']};
    border-radius: 2px;
}}
QDialog {{
    background-color: {t['bg']};
    color: {t['text']};
}}
QGroupBox {{
    border: 1px solid {t['border']};
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 8px;
    color: {t['accent']};
    font-size: 11px;
    letter-spacing: 1px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
}}
"""
