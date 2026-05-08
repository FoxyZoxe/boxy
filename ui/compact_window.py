"""
ui/compact_window.py — Mode compact : petite fenêtre flottante coin d'écran.

Fenêtre frameless, toujours au-dessus (WindowStaysOnTopHint), non listée
dans la barre des tâches (Qt.Tool).

Fonctionnalités :
- Affiche le statut et la dernière réponse de Boxy (2 lignes max)
- Champ de saisie + bouton micro + bouton envoyer
- Bouton pour passer en mode plein écran
- Bouton × pour masquer (sans quitter — reste dans le tray)
- Déplaçable par glisser-déposer
- Positionnée coin bas-droit par défaut
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton,
)
from PyQt6.QtCore  import Qt, pyqtSignal
from PyQt6.QtGui   import QColor, QPainter, QPen

from config import Config

# ─── Palette (identique à main_window) ───────────────────────────────
C_BG     = "#07090e"
C_PANEL  = "#0c1020"
C_BORDER = "#1a3555"
C_ACCENT = "#00d4ff"
C_TEXT   = "#b8d8ff"
C_DIM    = "#3a5570"
C_WARN   = "#ffaa00"
C_OK     = "#00ff88"
C_ERR    = "#ff4444"

COMPACT_CSS = f"""
QWidget#compact_root {{
    background-color: {C_BG};
    border: 1px solid {C_BORDER};
    border-radius: 8px;
}}
QLabel {{
    background: transparent;
    border: none;
    color: {C_TEXT};
    font-family: Consolas, 'Courier New', monospace;
    font-size: 11px;
}}
QLineEdit {{
    background-color: {C_PANEL};
    border: 1px solid {C_BORDER};
    border-radius: 4px;
    color: {C_TEXT};
    font-family: Consolas, 'Courier New', monospace;
    font-size: 12px;
    padding: 3px 8px;
}}
QLineEdit:focus {{
    border: 1px solid {C_ACCENT};
}}
QPushButton {{
    background-color: {C_PANEL};
    border: 1px solid {C_BORDER};
    border-radius: 4px;
    color: {C_ACCENT};
    font-size: 13px;
    padding: 3px 6px;
    min-width: 26px;
    min-height: 26px;
}}
QPushButton:hover {{
    background-color: {C_ACCENT};
    color: {C_BG};
}}
QPushButton#flat_btn {{
    background: transparent;
    border: none;
    color: {C_DIM};
    font-size: 15px;
    min-width: 22px;
    min-height: 22px;
    padding: 0;
}}
QPushButton#flat_btn:hover {{
    color: {C_ACCENT};
    background: transparent;
}}
"""


class CompactWindow(QWidget):
    """Petite fenêtre flottante toujours visible, style HUD."""

    # ── Signaux vers l'extérieur ──────────────────────────────────────
    expand_requested = pyqtSignal()   # Demande d'affichage plein écran
    text_submitted   = pyqtSignal(str)
    voice_requested  = pyqtSignal()

    # Dimensions fixes
    WIDTH  = 370
    HEIGHT = 138

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint       |  # Pas de bordure
            Qt.WindowType.WindowStaysOnTopHint      |  # Toujours au-dessus
            Qt.WindowType.Tool                         # Pas dans la barre des tâches
        )
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setFixedSize(self.WIDTH, self.HEIGHT)

        self._drag_pos   = None
        self._stream_buf = ""

        self._build_ui()
        self._place_bottom_right()

    # ─── Construction de l'UI ─────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QWidget(self)
        root.setObjectName("compact_root")
        root.setGeometry(0, 0, self.WIDTH, self.HEIGHT)
        root.setStyleSheet(COMPACT_CSS)

        layout = QVBoxLayout(root)
        layout.setContentsMargins(10, 7, 10, 8)
        layout.setSpacing(5)

        layout.addLayout(self._build_header())
        layout.addWidget(self._build_response_label())
        layout.addLayout(self._build_input_row())

    def _build_header(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)

        name = QLabel(f"◈  {Config.ASSISTANT_NAME.upper()}")
        name.setStyleSheet(
            f"color:{C_ACCENT}; font-weight:bold; font-size:11px;"
            "letter-spacing:2px; border:none; background:transparent;"
        )

        self._dot = QLabel("●")
        self._dot.setStyleSheet(f"color:{C_DIM}; font-size:9px;")

        btn_expand = QPushButton("⛶")
        btn_expand.setObjectName("flat_btn")
        btn_expand.setToolTip("Mode plein écran")
        btn_expand.clicked.connect(self.expand_requested.emit)

        btn_hide = QPushButton("×")
        btn_hide.setObjectName("flat_btn")
        btn_hide.setStyleSheet(
            f"background:transparent; border:none; color:{C_DIM};"
            "font-size:17px; min-width:22px; min-height:22px; padding:0;"
        )
        btn_hide.setToolTip("Masquer (reste dans le tray)")
        btn_hide.clicked.connect(self.hide)

        row.addWidget(name)
        row.addWidget(self._dot)
        row.addStretch()
        row.addWidget(btn_expand)
        row.addWidget(btn_hide)
        return row

    def _build_response_label(self) -> QLabel:
        self._response_lbl = QLabel("En attente d'initialisation…")
        self._response_lbl.setWordWrap(True)
        self._response_lbl.setMaximumHeight(38)
        self._response_lbl.setStyleSheet(
            f"color:{C_TEXT}; font-size:11px; border:none;"
            "background:transparent; padding: 0 2px;"
        )
        return self._response_lbl

    def _build_input_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(4)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Message…")
        self._input.setFixedHeight(28)
        self._input.returnPressed.connect(self._on_send)

        btn_mic = QPushButton("🎤")
        btn_mic.setFixedSize(28, 28)
        btn_mic.setToolTip("Parler (F2)")
        btn_mic.clicked.connect(self.voice_requested.emit)

        btn_send = QPushButton("→")
        btn_send.setFixedSize(28, 28)
        btn_send.setToolTip("Envoyer")
        btn_send.clicked.connect(self._on_send)

        row.addWidget(self._input, 1)
        row.addWidget(btn_mic)
        row.addWidget(btn_send)
        return row

    # ─── API publique ─────────────────────────────────────────────────

    def set_response(self, text: str) -> None:
        """Affiche la dernière réponse (tronquée à 100 chars)."""
        self._stream_buf = ""
        short = text[:100] + "…" if len(text) > 100 else text
        self._response_lbl.setText(short)

    def start_stream(self) -> None:
        """Prépare la zone de réponse pour recevoir des tokens en direct."""
        self._stream_buf = ""
        self._response_lbl.setText("▌")  # Curseur clignotant

    def append_token(self, token: str) -> None:
        """Ajoute un token au buffer de streaming."""
        self._stream_buf += token
        # Affiche les 100 derniers caractères + curseur
        display = self._stream_buf[-100:]
        self._response_lbl.setText(display + "▌")

    def finalize_stream(self, final_text: str) -> None:
        """Finalise l'affichage avec le texte nettoyé."""
        self._stream_buf = ""
        self.set_response(final_text)

    def show_error(self, msg: str) -> None:
        """Affiche un message d'erreur en rouge."""
        short = msg[:100] + "…" if len(msg) > 100 else msg
        self._response_lbl.setText(f"⚠ {short}")
        self._response_lbl.setStyleSheet(
            f"color:{C_ERR}; font-size:11px; border:none; background:transparent; padding:0 2px;"
        )

    def set_status(self, status: str) -> None:
        """Change la couleur du point de statut."""
        colors = {
            "idle":      C_DIM,
            "listening": C_ACCENT,
            "thinking":  C_WARN,
            "speaking":  C_OK,
        }
        color = colors.get(status, C_DIM)
        self._dot.setStyleSheet(f"color:{color}; font-size:9px;")

    # ─── Drag pour déplacer la fenêtre ────────────────────────────────

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )

    def mouseMoveEvent(self, event) -> None:
        if self._drag_pos and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_pos = None

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_F2:
            self.voice_requested.emit()
        elif event.key() == Qt.Key.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)

    # ─── Privé ────────────────────────────────────────────────────────

    def _on_send(self) -> None:
        text = self._input.text().strip()
        if text:
            self._input.clear()
            self.text_submitted.emit(text)

    def _place_bottom_right(self) -> None:
        """Positionne la fenêtre dans le coin bas-droit de l'écran."""
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.right()  - self.WIDTH  - 20,
            screen.bottom() - self.HEIGHT - 20,
        )
