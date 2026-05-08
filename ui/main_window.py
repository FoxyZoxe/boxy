"""
ui/main_window.py — Interface graphique HUD de Boxy.

Design : dark cyberpunk / Iron Man
Layout :
  ┌─────────────────────────────────────────┐
  │  BOXY                        [─][□][✕]  │
  ├──────────────┬──────────────────────────┤
  │  SYSTÈME     │  CONVERSATION            │
  │  CPU / RAM   │  messages                │
  │  VOL / MODE  │                          │
  ├──────────────┴──────────────────────────┤
  │  [~~~~ waveform ~~~~]  STATUS           │
  ├─────────────────────────────────────────┤
  │  ▸ saisie...                  [🎤][→]   │
  └─────────────────────────────────────────┘
"""

import math
import os
import random
import time
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QLabel,
    QFrame, QSplitter, QSizePolicy, QSystemTrayIcon, QMenu, QApplication,
    QDialog, QListWidget, QListWidgetItem, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, QTimer, pyqtSlot, QPropertyAnimation, QEasingCurve, pyqtSignal, QMimeData, QUrl
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QFont, QFontDatabase, QIcon,
    QPixmap, QAction, QTextCharFormat, QDragEnterEvent, QDropEvent
)

from ui.jarvis_thread import BoxyThread
from ui.compact_window import CompactWindow
from ui.themes import THEMES, get_theme, build_stylesheet
from ui.settings_dialog import SettingsDialog
from config import Config

# ─── Palette active (mise à jour par _apply_theme) ─────────────────
# Ces variables sont lues par StatusPanel et ChatDisplay pour colorier
# dynamiquement les labels rich-text.  Elles reflètent toujours le thème actif.
_THEME = get_theme(os.getenv("THEME", "cyan"))

def _t(key: str) -> str:
    """Retourne la couleur du thème actif pour la clé donnée."""
    return _THEME[key]


# Alias courts utilisés dans les widgets
C_BG      = _THEME["bg"]
C_PANEL   = _THEME["panel"]
C_BORDER  = _THEME["border"]
C_ACCENT  = _THEME["accent"]
C_ACCENT2 = _THEME["accent2"]
C_TEXT    = _THEME["text"]
C_DIM     = _THEME["dim"]
C_BOXY    = _THEME["accent"]
C_USER    = "#ffffff"
C_SUCCESS = _THEME["success"]
C_ERROR   = _THEME["error"]
C_WARN    = _THEME["warn"]


class VoiceWaveWidget(QWidget):
    """
    Widget animé qui affiche une forme d'onde pendant l'écoute/la parole.
    Utilise QPainter pour dessiner des barres qui bougent.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(50)
        self._bars    = 20           # Réduit de 32 → 20 barres (moins de calculs)
        self._heights = [0.05] * self._bars
        self._target  = [0.05] * self._bars
        self._active  = False
        self._color   = QColor(C_ACCENT)
        self._flat    = True         # True = toutes les barres sont plates → skip repaint

        # 15 fps au lieu de 30 — imperceptible visuellement, CPU divisé par 2
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_wave)
        self._timer.start(66)

    def set_active(self, active: bool, color: str = C_ACCENT) -> None:
        self._active = active
        self._color  = QColor(color)
        if not active:
            self._flat = False  # Déclenche l'animation de retour à plat

    def _update_wave(self) -> None:
        if self._active:
            self._flat = False
            for i in range(self._bars):
                if random.random() < 0.25:  # Moins de mises à jour aléatoires
                    self._target[i] = random.uniform(0.1, 0.9)
        else:
            for i in range(self._bars):
                self._target[i] = 0.05

        # Interpolation
        max_delta = 0.0
        for i in range(self._bars):
            delta = (self._target[i] - self._heights[i]) * 0.2
            self._heights[i] += delta
            max_delta = max(max_delta, abs(delta))

        # Si tout est plat et stable → arrêt du repaint jusqu'à la prochaine activation
        if not self._active and max_delta < 0.001:
            self._flat = True

        if not self._flat:
            self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        bar_w = w / self._bars
        center_y = h / 2

        for i, height_ratio in enumerate(self._heights):
            bar_h = max(2, height_ratio * (h - 8))
            x = i * bar_w + bar_w * 0.15
            bw = bar_w * 0.7

            # Dégradé d'opacité selon la hauteur
            alpha = int(80 + height_ratio * 175)
            color = QColor(self._color)
            color.setAlpha(alpha)
            painter.fillRect(
                int(x), int(center_y - bar_h / 2),
                int(bw), int(bar_h),
                color
            )


class StatusPanel(QFrame):
    """Panneau gauche : informations système en temps réel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("panel")
        self.setFixedWidth(180)
        self._setup_ui()

        # Mise à jour des stats toutes les 6 secondes (psutil est coûteux)
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_stats)
        self._timer.start(6000)
        self._update_stats()  # Appel immédiat au démarrage

        # Timer animation des points "thinking"
        self._dot_count = 0
        self._dot_timer = QTimer()
        self._dot_timer.timeout.connect(self._animate_dots)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(4)
        self._layout = layout  # assigné avant les appels à _add_section

        self._add_section("◈  SYSTÈME")

        self.lbl_cpu  = self._add_stat("CPU", "–%")
        self.lbl_ram  = self._add_stat("RAM", "–%")
        self.lbl_vol  = self._add_stat("VOL", "–%")
        self.lbl_time = self._add_stat("", "")

        layout.addWidget(self._separator())
        self._add_section("◈  IA")

        _ai_colors = {"openai": "#00ff88", "groq": "#ffaa00", "ollama": C_ACCENT}
        _ai_models = {"openai": Config.OPENAI_MODEL, "groq": Config.GROQ_MODEL,
                      "ollama": Config.OLLAMA_MODEL}
        ai_color  = _ai_colors.get(Config.AI_PROVIDER, C_ACCENT)
        ai_label  = Config.AI_PROVIDER.upper()
        ai_model  = _ai_models.get(Config.AI_PROVIDER, Config.OLLAMA_MODEL)
        self.lbl_ai    = self._add_stat("", f"<span style='color:{ai_color}'>{ai_label}</span>")
        self.lbl_model = self._add_stat("", ai_model)

        layout.addWidget(self._separator())
        self._add_section("◈  MODE")

        self.lbl_mode   = self._add_stat("", "VOCAL" if Config.VOICE_ENABLED else "TEXTE")
        self.lbl_status = self._add_stat("", "INACTIF")

        self._layout.addStretch()

        # Horloge
        self.clock_label = QLabel("00:00:00")
        self.clock_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.clock_label.setStyleSheet(f"color: {C_ACCENT}; font-size: 18px; letter-spacing: 2px; padding-top: 8px;")
        self._layout.addWidget(self.clock_label)

        clock_timer = QTimer(self)
        clock_timer.timeout.connect(self._update_clock)
        clock_timer.start(1000)
        self._update_clock()

    def _add_section(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("section")
        self._layout.addWidget(lbl)
        return lbl

    def _add_stat(self, key: str, value: str) -> QLabel:
        if key:
            text = f"<span style='color:{C_DIM}'>{key:<4}</span>  {value}"
        else:
            text = f"<span style='color:{C_TEXT}'>{value}</span>"
        lbl = QLabel(text)
        lbl.setObjectName("stat")
        lbl.setTextFormat(Qt.TextFormat.RichText)
        self._layout.addWidget(lbl)
        return lbl

    def _separator(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"color: {C_BORDER}; margin: 4px 0px;")
        return line

    def _update_clock(self) -> None:
        self.clock_label.setText(datetime.now().strftime("%H:%M:%S"))

    def _update_stats(self) -> None:
        try:
            import psutil
            # interval=None = non-bloquant (utilise la mesure précédente)
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            self.lbl_cpu.setText(f"<span style='color:{C_DIM}'>CPU </span>  <span style='color:{self._stat_color(cpu)}'>{cpu:.0f}%</span>")
            self.lbl_ram.setText(f"<span style='color:{C_DIM}'>RAM </span>  <span style='color:{self._stat_color(ram)}'>{ram:.0f}%</span>")
            self.lbl_cpu.setTextFormat(Qt.TextFormat.RichText)
            self.lbl_ram.setTextFormat(Qt.TextFormat.RichText)
        except ImportError:
            pass

    def changeEvent(self, event) -> None:
        """Pause les timers quand la fenêtre est minimisée."""
        from PyQt6.QtCore import QEvent
        if event.type() == QEvent.Type.WindowStateChange:
            minimized = self.isMinimized()
            if minimized:
                self._timer.stop()
            else:
                self._timer.start(6000)
        super().changeEvent(event)

    def _stat_color(self, value: float) -> str:
        if value > 80: return C_ERROR
        if value > 60: return C_WARN
        return C_SUCCESS

    def set_status(self, status: str) -> None:
        """Met à jour l'indicateur de statut + anime les points si 'thinking'."""
        labels = {
            "idle":      ("INACTIF",   C_DIM),
            "listening": ("ÉCOUTE",    C_ACCENT),
            "thinking":  ("RÉFLEXION", C_WARN),
            "speaking":  ("PAROLE",    C_SUCCESS),
        }
        text, color = labels.get(status, ("–", C_DIM))
        self.lbl_status.setText(f"<span style='color:{color}'>{text}</span>")
        self.lbl_status.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_mode.setText(f"<span style='color:{C_ACCENT}'>{'VOCAL' if Config.VOICE_ENABLED else 'TEXTE'}</span>")
        self.lbl_mode.setTextFormat(Qt.TextFormat.RichText)

        # Animation des points pendant la réflexion
        if status == "thinking":
            self._dot_timer.start(400)
            self._dot_count = 0
        else:
            self._dot_timer.stop()

    def _animate_dots(self) -> None:
        """Anime les points pendant 'thinking'."""
        self._dot_count = (self._dot_count + 1) % 4
        dots = "●" * self._dot_count + "○" * (3 - self._dot_count)
        self.lbl_status.setText(f"<span style='color:{C_WARN}'>RÉFLEXION {dots}</span>")
        self.lbl_status.setTextFormat(Qt.TextFormat.RichText)


class ChatDisplay(QTextEdit):
    """
    Zone d'affichage des messages.

    Supporte le streaming token-par-token via start_stream / append_token / finalize_stream.
    """

    # Signal émis quand un fichier est déposé sur le chat
    file_dropped = pyqtSignal(str)   # chemin absolu du fichier

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setAcceptDrops(True)
        self._streaming      = False
        self._stream_anchor  = None
        self._stream_buffer  = ""
        self._stream_t_start = 0.0

    def add_message(self, role: str, text: str) -> None:
        """
        Ajoute un message formaté (réponse complète ou message utilisateur).

        role: "boxy" | "user" | "system"
        """
        timestamp = datetime.now().strftime("%H:%M:%S")

        if role == "boxy":
            name_html = f"<span style='color:{C_BOXY};font-weight:bold'>BOXY</span>"
            text_html = f"<span style='color:{C_TEXT}'>{self._esc(text)}</span>"
            border    = C_BOXY
        elif role == "user":
            name_html = f"<span style='color:{C_USER};font-weight:bold'>VOUS</span>"
            text_html = f"<span style='color:#dddddd'>{self._esc(text)}</span>"
            border    = "#444"
        else:
            name_html = f"<span style='color:{C_DIM}'>SYS </span>"
            text_html = f"<span style='color:{C_DIM}'>{self._esc(text)}</span>"
            border    = C_DIM

        time_html = f"<span style='color:{C_DIM};font-size:11px'>{timestamp}</span>"
        html = (
            f"<div style='margin:6px 0;padding:6px 8px;"
            f"border-left:2px solid {border};'>"
            f"{time_html}&nbsp;&nbsp;{name_html}"
            f"&nbsp;<span style='color:{C_DIM}'>▸</span>&nbsp;{text_html}"
            f"</div>"
        )
        self.append(html)
        self._scroll_bottom()

    # ── Streaming API ─────────────────────────────────────────────────

    def start_stream(self) -> None:
        """Ouvre une bulle BOXY vide prête à recevoir des tokens."""
        if self._streaming:
            return
        self._streaming = True
        self._stream_buffer  = ""
        self._stream_t_start = time.time()

        timestamp = datetime.now().strftime("%H:%M:%S")
        time_html = f"<span style='color:{C_DIM};font-size:11px'>{timestamp}</span>"
        name_html = f"<span style='color:{C_BOXY};font-weight:bold'>BOXY</span>"

        # Insère l'en-tête de la bulle + curseur texte vide
        header_html = (
            f"<div style='margin:6px 0;padding:6px 8px;"
            f"border-left:2px solid {C_BOXY};'>"
            f"{time_html}&nbsp;&nbsp;{name_html}"
            f"&nbsp;<span style='color:{C_DIM}'>▸</span>&nbsp;"
        )
        cursor = self.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertHtml(header_html)
        # Mémorise la position après l'en-tête pour y insérer les tokens
        self._stream_anchor = cursor.position()
        self._scroll_bottom()

    def append_token(self, token: str) -> None:
        """Insère un token dans la bulle de streaming ouverte."""
        if not self._streaming:
            return
        self._stream_buffer += token
        cursor = self.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        # Insère en texte brut (pas HTML) pour éviter les conflits d'encodage
        fmt = cursor.charFormat()
        from PyQt6.QtGui import QTextCharFormat
        tf = QTextCharFormat()
        tf.setForeground(QColor(C_TEXT))
        cursor.setCharFormat(tf)
        cursor.insertText(token)
        self.setTextCursor(cursor)
        self._scroll_bottom()

    def finalize_stream(self, final_text: str) -> None:
        """
        Ferme la bulle de streaming.

        Remplace le contenu streamé par le texte final nettoyé
        (sans les blocs CMD) puis ferme la div.
        """
        if not self._streaming:
            return
        self._streaming = False

        # Sélectionne tout depuis l'ancre (tokens bruts) jusqu'à la fin
        cursor = self.textCursor()
        cursor.setPosition(self._stream_anchor)
        cursor.movePosition(cursor.MoveOperation.End, cursor.MoveMode.KeepAnchor)

        # Remplace par le texte final nettoyé
        from PyQt6.QtGui import QTextCharFormat
        tf = QTextCharFormat()
        tf.setForeground(QColor(C_TEXT))
        cursor.setCharFormat(tf)
        if final_text:
            cursor.insertText(final_text)
        else:
            cursor.removeSelectedText()

        # Ajoute la durée de génération
        elapsed = time.time() - self._stream_t_start
        cursor.movePosition(cursor.MoveOperation.End)
        timing_html = (
            f"<span style='color:{C_DIM};font-size:10px;'>"
            f"  [{elapsed:.1f}s]</span>"
        )
        cursor.insertHtml(timing_html + "</div><br>")
        self.setTextCursor(cursor)
        self._stream_anchor  = None
        self._stream_buffer  = ""
        self._stream_t_start = 0.0
        self._scroll_bottom()

    # ── Drag & drop de fichiers ───────────────────────────────────────

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path:
                self.file_dropped.emit(path)
        event.acceptProposedAction()

    # ── Menu contextuel (clic droit) ──────────────────────────────────

    def contextMenuEvent(self, event) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu{{background:{C_PANEL};color:{C_TEXT};border:1px solid {C_BORDER};"
            f"border-radius:4px;padding:4px;}}"
            f"QMenu::item:selected{{background:{C_ACCENT2};}}"
        )

        act_copy = menu.addAction("📋  Copier la sélection")
        act_copy.triggered.connect(self.copy)

        act_copy_all = menu.addAction("📋  Tout copier")
        act_copy_all.triggered.connect(self.selectAll)
        act_copy_all.triggered.connect(self.copy)

        menu.addSeparator()
        act_clear = menu.addAction("🗑  Effacer le chat")
        act_clear.triggered.connect(self.clear)

        menu.exec(event.globalPos())

    # ── Helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _esc(text: str) -> str:
        """Échappe les caractères HTML dans le texte."""
        return (text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\n", "<br>"))

    def _scroll_bottom(self) -> None:
        sb = self.verticalScrollBar()
        sb.setValue(sb.maximum())


# ─── SlashCommandPalette ─────────────────────────────────────────────
class SlashCommandPalette(QFrame):
    """
    Palette flottante qui apparaît quand l'utilisateur tape « / ».

    Filtre les commandes en temps réel et permet :
    • Clic sur une entrée → insère la commande dans l'input
    • ↑/↓ dans l'input → sélectionne l'entrée suivante/précédente
    • Échap → ferme sans insérer
    """

    # Émis avec le texte complet à insérer (ex: "/volume ")
    command_selected = pyqtSignal(str)

    # Toutes les commandes : (commande, description, icône)
    ALL_COMMANDS: list[tuple[str, str, str]] = [
        ("/screenshot",  "Capture l'écran",                    "📸"),
        ("/volume",      "Règle le volume  ex: /volume 50",    "🔊"),
        ("/recherche",   "Recherche web",                      "🔍"),
        ("/note",        "Crée une note rapide",               "📝"),
        ("/clipboard",   "Lit le presse-papiers",              "📋"),
        ("/timer",       "Lance un timer en minutes",          "⏱"),
        ("/theme",       "Change le thème  ex: /theme red",    "🎨"),
        ("/export",      "Exporte la conversation",            "💾"),
        ("/historique",  "Conversations passées",              "📂"),
        ("/compact",     "Passe en mode compact",              "⊟"),
        ("/clear",       "Efface l'historique",                "🗑"),
        ("/voix",        "Active/désactive la voix",           "🎤"),
        ("/memoire",     "Affiche la mémoire long-terme",      "🧠"),
        ("/status",      "Affiche le statut système",          "📊"),
        ("/aide",        "Affiche toutes les commandes",       "❓"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("slash_palette")
        self.setWindowFlags(Qt.WindowType.ToolTip)
        self._selected = 0
        self._visible_cmds: list[tuple[str, str, str]] = []
        self._btns: list[QPushButton] = []
        self._build_ui()
        self.hide()

    def _build_ui(self) -> None:
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(4, 4, 4, 4)
        self._layout.setSpacing(1)

        header = QLabel("  COMMANDES  /")
        header.setStyleSheet(
            f"color:{C_ACCENT};font-size:9px;letter-spacing:2px;"
            f"padding:2px 6px;border-bottom:1px solid {C_BORDER};"
        )
        self._layout.addWidget(header)
        self._items_layout = QVBoxLayout()
        self._items_layout.setContentsMargins(0, 2, 0, 2)
        self._items_layout.setSpacing(1)
        self._layout.addLayout(self._items_layout)

    def filter(self, query: str) -> None:
        """
        Met à jour la liste en filtrant par `query` (ce qui suit le « / »).
        Affiche toutes les commandes si query est vide.
        """
        q = query.lower()
        self._visible_cmds = [
            (cmd, desc, ico) for cmd, desc, ico in self.ALL_COMMANDS
            if q in cmd or q in desc.lower()
        ]
        self._selected = 0
        self._rebuild_items()

    def _rebuild_items(self) -> None:
        # Supprime les anciens boutons
        while self._items_layout.count():
            item = self._items_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._btns.clear()

        for i, (cmd, desc, ico) in enumerate(self._visible_cmds[:10]):
            btn = QPushButton(f"  {ico}  {cmd:<16}  {desc}")
            btn.setCheckable(False)
            btn.setFixedHeight(28)
            btn.setStyleSheet(self._btn_style(i == 0))
            btn.clicked.connect(lambda _, c=cmd: self.command_selected.emit(c + " "))
            self._items_layout.addWidget(btn)
            self._btns.append(btn)

        self.adjustSize()

    def _btn_style(self, selected: bool) -> str:
        bg = C_ACCENT2 if selected else "transparent"
        return (
            f"QPushButton{{background:{bg};color:{C_TEXT};border:none;"
            f"border-radius:3px;text-align:left;padding:0 6px;"
            f"font-size:12px;font-family:Consolas,monospace;}}"
            f"QPushButton:hover{{background:{C_ACCENT2};}}"
        )

    def move_selection(self, delta: int) -> None:
        """Déplace la sélection de ±1. Appelé par SmartInput sur ↑/↓."""
        if not self._btns:
            return
        old = self._selected
        self._selected = (self._selected + delta) % len(self._btns)
        self._btns[old].setStyleSheet(self._btn_style(False))
        self._btns[self._selected].setStyleSheet(self._btn_style(True))

    def accept_selected(self) -> None:
        """Insère la commande sélectionnée (Tab ou Entrée si palette visible)."""
        if self._visible_cmds and self._selected < len(self._visible_cmds):
            cmd = self._visible_cmds[self._selected][0]
            self.command_selected.emit(cmd + " ")


# ─── SmartInput ───────────────────────────────────────────────────────
class SmartInput(QTextEdit):
    """
    Champ de saisie multi-ligne intelligent.
    • Entrée             → envoyer
    • Ctrl+Entrée / Shift+Entrée → saut de ligne
    • Ctrl+↑/↓           → naviguer dans l'historique des messages envoyés
    • /  au début        → ouvre la palette de commandes slash
    • ↑/↓ palette ouverte → sélectionne la commande suivante/précédente
    • Tab / Entrée        → insère la commande sélectionnée
    • Échap               → ferme la palette
    • Se redimensionne jusqu'à 3 lignes automatiquement
    """
    submitted = pyqtSignal(str)
    slash_typing = pyqtSignal(str)   # émis à chaque frappe quand en mode "/"
    slash_closed = pyqtSignal()      # émis quand la palette doit se fermer
    MAX_HEIGHT = 80

    def __init__(self, parent=None):
        super().__init__(parent)
        self._history: list[str] = []
        self._hist_idx = -1
        self._slash_mode = False
        self.setFixedHeight(36)
        self.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.document().contentsChanged.connect(self._on_content_changed)

    def keyPressEvent(self, event) -> None:
        mod   = event.modifiers()
        ctrl  = Qt.KeyboardModifier.ControlModifier
        shift = Qt.KeyboardModifier.ShiftModifier
        key   = event.key()

        # ── Palette ouverte : touches de navigation ───────────────
        if self._slash_mode:
            if key == Qt.Key.Key_Escape:
                self._close_slash()
                return
            if key == Qt.Key.Key_Up:
                self.slash_typing.emit("__UP__")
                return
            if key == Qt.Key.Key_Down:
                self.slash_typing.emit("__DOWN__")
                return
            if key == Qt.Key.Key_Tab:
                self.slash_typing.emit("__ACCEPT__")
                return
            # Entrée → si palette visible, insère la commande sélectionnée
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not (mod & (ctrl | shift)):
                self.slash_typing.emit("__ACCEPT__")
                return

        # ── Entrée normale ────────────────────────────────────────
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if mod & (ctrl | shift):
                super().keyPressEvent(event)
            else:
                text = self.toPlainText().strip()
                if text:
                    self._history.insert(0, text)
                    self._hist_idx = -1
                    self._close_slash()
                    self.submitted.emit(text)
                    self.clear()
            return

        if key == Qt.Key.Key_Up and (mod & ctrl):
            self._navigate(+1)
            return
        if key == Qt.Key.Key_Down and (mod & ctrl):
            self._navigate(-1)
            return

        super().keyPressEvent(event)

    def _on_content_changed(self) -> None:
        self._adjust_height()
        text = self.toPlainText()
        if text.startswith("/"):
            self._slash_mode = True
            self.slash_typing.emit(text[1:])   # émet ce qui suit le "/"
        else:
            if self._slash_mode:
                self._close_slash()

    def _close_slash(self) -> None:
        self._slash_mode = False
        self.slash_closed.emit()

    def _navigate(self, direction: int) -> None:
        if not self._history:
            return
        self._hist_idx = max(-1, min(len(self._history) - 1,
                                     self._hist_idx + direction))
        if self._hist_idx >= 0:
            self.setPlainText(self._history[self._hist_idx])
            cursor = self.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.setTextCursor(cursor)
        else:
            self.clear()

    def _adjust_height(self) -> None:
        doc_h = int(self.document().size().height()) + 10
        self.setFixedHeight(max(36, min(self.MAX_HEIGHT, doc_h)))

    # Compatibilité avec l'ancienne API QLineEdit
    def text(self) -> str:
        return self.toPlainText()

    def clear_text(self) -> None:
        self.clear()

    def setPlaceholderText(self, text: str) -> None:
        self.setPlaceholderText_real = text
        super().setPlaceholderText(text)


# ─── HistoryDialog ────────────────────────────────────────────────────
class HistoryDialog(QDialog):
    """Affiche les conversations passées sauvegardées sur disque."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("◈  Historique des conversations")
        self.setMinimumSize(640, 440)
        self.setModal(True)
        self._files: dict[str, object] = {}
        self._build_ui()
        self._load()
        # Hérite du stylesheet du parent
        if parent:
            self.setStyleSheet(parent.styleSheet())

    def _build_ui(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 14, 14, 10)
        lay.setSpacing(8)

        title = QLabel("◈  HISTORIQUE")
        title.setStyleSheet(f"color:{C_ACCENT};font-size:14px;font-weight:bold;letter-spacing:2px;")
        lay.addWidget(title)

        self._list = QListWidget()
        self._list.setStyleSheet(f"background:{C_PANEL};color:{C_TEXT};border:1px solid {C_BORDER};border-radius:4px;")
        self._list.itemClicked.connect(self._preview)
        lay.addWidget(self._list, 1)

        self._preview_box = QTextEdit()
        self._preview_box.setReadOnly(True)
        self._preview_box.setFixedHeight(140)
        self._preview_box.setStyleSheet(f"background:{C_PANEL};color:{C_TEXT};border:1px solid {C_BORDER};border-radius:4px;font-size:12px;")
        lay.addWidget(self._preview_box)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_close = QPushButton("Fermer")
        btn_close.setFixedWidth(100)
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        lay.addLayout(btn_row)

    def _load(self) -> None:
        from config import Config
        conv_dir = Config.CONVERSATIONS_DIR
        if not conv_dir.exists():
            return
        files = sorted(conv_dir.glob("conversation_*.json"), reverse=True)
        for f in files:
            self._list.addItem(f.name)
            self._files[f.name] = f
        if not files:
            self._list.addItem("Aucune conversation sauvegardée.")

    def _preview(self, item: QListWidgetItem) -> None:
        import json
        fpath = self._files.get(item.text())
        if not fpath:
            return
        try:
            with open(fpath, encoding="utf-8") as f:
                msgs = json.load(f)
            lines = []
            for m in msgs[:20]:
                role = m.get("role", "?").upper()
                content = m.get("content", "")[:300]
                lines.append(f"[{role}] {content}")
            self._preview_box.setPlainText("\n─────\n".join(lines))
        except Exception as e:
            self._preview_box.setPlainText(f"Erreur : {e}")


class MainWindow(QMainWindow):
    """Fenêtre principale — HUD de Boxy."""

    def __init__(self):
        super().__init__()
        self._setup_window()
        self._setup_ui()
        self._setup_thread()
        self._setup_compact()
        self._setup_tray()

    def _setup_window(self) -> None:
        self.setWindowTitle(f"◈  {Config.ASSISTANT_NAME.upper()}  —  Interface principale")
        self.setMinimumSize(900, 600)
        self.resize(1100, 700)
        self._active_theme = os.getenv("THEME", "cyan")
        self._apply_theme(self._active_theme)

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # ── Barre de titre custom ──────────────────────────────────
        title_bar = QWidget()
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(8, 4, 8, 4)

        title_lbl = QLabel(f"◈  {Config.ASSISTANT_NAME.upper()}")
        title_lbl.setObjectName("title")

        self.status_lbl = QLabel("● INITIALISATION")
        self.status_lbl.setStyleSheet(f"color: {C_WARN}; font-size: 11px; letter-spacing: 1px;")

        def _hbtn(icon, tip, slot, sz=28):
            b = QPushButton(icon)
            b.setToolTip(tip)
            b.setFixedSize(sz, sz)
            b.setStyleSheet(
                f"QPushButton{{background:transparent;border:1px solid {C_BORDER};"
                f"border-radius:4px;color:{C_DIM};font-size:13px;padding:0;}}"
                f"QPushButton:hover{{color:{C_ACCENT};border-color:{C_ACCENT};}}"
            )
            b.clicked.connect(slot)
            return b

        btn_history  = _hbtn("📋", "Historique des conversations", self._open_history)
        btn_export   = _hbtn("💾", "Exporter la conversation", self._export_conversation)
        btn_clear    = _hbtn("🗑", "Effacer le chat", self._clear_chat)
        btn_settings = _hbtn("⚙",  "Paramètres",               self._open_settings)
        btn_compact  = _hbtn("⊟",  "Mode compact",              self._switch_to_compact)

        title_layout.addWidget(title_lbl)
        title_layout.addStretch()
        title_layout.addWidget(self.status_lbl)
        title_layout.addSpacing(8)
        for btn in (btn_history, btn_export, btn_clear, btn_settings, btn_compact):
            title_layout.addWidget(btn)
            title_layout.addSpacing(2)
        root.addWidget(title_bar)

        # ── Zone principale : sidebar + chat ──────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet(f"QSplitter::handle {{ background: {C_BORDER}; }}")

        self.status_panel = StatusPanel()
        splitter.addWidget(self.status_panel)

        chat_frame = QFrame()
        chat_frame.setObjectName("panel")
        chat_layout = QVBoxLayout(chat_frame)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(0)

        chat_header = QLabel("  ◈  CONVERSATION")
        chat_header.setObjectName("section")
        chat_header.setStyleSheet(f"color:{C_ACCENT}; font-size:10px; letter-spacing:2px; padding:8px 12px; border-bottom: 1px solid {C_BORDER};")

        self.chat = ChatDisplay()
        chat_layout.addWidget(chat_header)
        chat_layout.addWidget(self.chat)
        splitter.addWidget(chat_frame)

        splitter.setSizes([180, 720])
        root.addWidget(splitter, 1)

        # ── Waveform ──────────────────────────────────────────────
        wave_container = QFrame()
        wave_container.setObjectName("panel")
        wave_container.setFixedHeight(62)
        wave_layout = QHBoxLayout(wave_container)
        wave_layout.setContentsMargins(12, 6, 12, 6)

        self.wave = VoiceWaveWidget()
        self.wave_label = QLabel("INACTIF")
        self.wave_label.setFixedWidth(90)
        self.wave_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.wave_label.setStyleSheet(f"color:{C_DIM}; font-size:10px; letter-spacing:1px;")

        wave_layout.addWidget(self.wave, 1)
        wave_layout.addWidget(self.wave_label)
        root.addWidget(wave_container)

        # ── Zone de saisie ────────────────────────────────────────
        input_frame = QFrame()
        input_frame.setObjectName("panel")
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(8, 6, 8, 6)
        input_layout.setSpacing(6)

        prompt = QLabel("▸")
        prompt.setStyleSheet(f"color:{C_ACCENT}; font-size:16px; padding: 0 4px;")
        prompt.setAlignment(Qt.AlignmentFlag.AlignTop)
        prompt.setContentsMargins(0, 6, 0, 0)

        self.input = SmartInput()
        self.input.setPlaceholderText(
            f"Message…  /commande  •  Entrée=envoyer  •  Ctrl+↑↓=historique"
        )
        self.input.submitted.connect(self._send_text)

        # ── Palette slash ──────────────────────────────────────────
        self._palette = SlashCommandPalette(self)
        self._palette.setStyleSheet(
            f"QFrame#slash_palette{{background:{C_PANEL};border:1px solid {C_ACCENT};"
            f"border-radius:6px;}}"
        )
        self._palette.command_selected.connect(self._insert_slash_command)
        self.input.slash_typing.connect(self._on_slash_typing)
        self.input.slash_closed.connect(self._palette.hide)

        self.btn_mic = QPushButton("🎤")
        self.btn_mic.setToolTip("Parler (F2 ou Ctrl+Espace)")
        self.btn_mic.clicked.connect(self._trigger_voice)

        self.btn_send = QPushButton("→")
        self.btn_send.setToolTip("Envoyer (Entrée)")
        self.btn_send.clicked.connect(lambda: self._send_text(self.input.text()))

        input_layout.addWidget(prompt)
        input_layout.addWidget(self.input, 1)
        input_layout.addWidget(self.btn_mic)
        input_layout.addWidget(self.btn_send)
        root.addWidget(input_frame)

        # Drag & drop : fichiers déposés sur le chat → analyse automatique
        self.chat.file_dropped.connect(self._on_file_dropped)

    def _setup_thread(self) -> None:
        """Initialise et lance le thread Boxy en arrière-plan."""
        self.thread = BoxyThread(self)
        self.thread.on_response.connect(self._on_response)
        self.thread.on_user_message.connect(self._on_user_message)
        self.thread.on_status.connect(self._on_status)
        self.thread.on_ready.connect(self._on_ready)
        self.thread.on_token.connect(self._on_token)
        self.thread.on_stream_start.connect(self._on_stream_start)
        self.thread.on_stream_end.connect(self._on_stream_end)
        self.thread.on_error.connect(self._on_error)
        self.thread.on_timing.connect(self._on_timing)
        self.thread.start()

    def _setup_compact(self) -> None:
        """Crée la fenêtre compacte et branche ses signaux sur le thread."""
        self.compact = CompactWindow()

        # Compact → Thread
        self.compact.text_submitted.connect(self.thread.send_text)
        self.compact.voice_requested.connect(self.thread.trigger_voice)
        self.compact.expand_requested.connect(self._switch_to_full)

        # Thread → Compact
        self.thread.on_response.connect(self.compact.set_response)
        self.thread.on_status.connect(self.compact.set_status)
        self.thread.on_stream_start.connect(self.compact.start_stream)
        self.thread.on_token.connect(self.compact.append_token)
        self.thread.on_stream_end.connect(self.compact.finalize_stream)
        self.thread.on_error.connect(self.compact.show_error)

    def _setup_tray(self) -> None:
        """Crée l'icône dans la barre système (system tray)."""
        self._tray = QSystemTrayIcon(self)
        self._tray.setIcon(self._make_tray_icon())
        self._tray.setToolTip(Config.ASSISTANT_NAME)

        menu = QMenu()

        act_show = QAction(f"◈ Afficher {Config.ASSISTANT_NAME}", self)
        act_show.triggered.connect(self._switch_to_full)

        act_compact = QAction("⊟ Mode compact", self)
        act_compact.triggered.connect(self._switch_to_compact)

        act_quit = QAction("✕ Quitter", self)
        act_quit.triggered.connect(self._quit_app)

        menu.addAction(act_show)
        menu.addAction(act_compact)
        menu.addSeparator()
        menu.addAction(act_quit)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _make_tray_icon(self) -> QIcon:
        """Charge boxy.ico ou génère une icône cyan minimaliste."""
        ico = Path(__file__).parent.parent / "data" / "boxy.ico"
        if ico.exists():
            return QIcon(str(ico))

        # Icône de secours : rond cyan avec "B"
        px = QPixmap(32, 32)
        px.fill(QColor("#07090e"))
        painter = QPainter(px)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#00d4ff"), 2))
        painter.drawEllipse(2, 2, 28, 28)
        painter.setPen(QColor("#00d4ff"))
        painter.setFont(QFont("Consolas", 16, QFont.Weight.Bold))
        painter.drawText(px.rect(), Qt.AlignmentFlag.AlignCenter, "B")
        painter.end()
        return QIcon(px)

    # ── Slots Qt (appelés depuis le thread Boxy) ──────────────────

    @pyqtSlot()
    def _on_ready(self) -> None:
        self.status_lbl.setText("● EN LIGNE")
        self.status_lbl.setStyleSheet(f"color: {C_SUCCESS}; font-size: 11px; letter-spacing: 1px;")

    @pyqtSlot(str)
    def _on_response(self, text: str) -> None:
        self.chat.add_message("boxy", text)

    @pyqtSlot(str)
    def _on_user_message(self, text: str) -> None:
        # Enlève le préfixe "(vocal) " pour l'affichage
        display = text.replace("(vocal) ", "").strip()
        self.chat.add_message("user", display)

    @pyqtSlot(str)
    def _on_status(self, status: str) -> None:
        self.status_panel.set_status(status)

        wave_configs = {
            "idle":      (False, C_ACCENT,   "INACTIF"),
            "listening": (True,  C_ACCENT,   "ÉCOUTE"),
            "thinking":  (True,  C_WARN,     "RÉFLEXION"),
            "speaking":  (True,  C_SUCCESS,  "PAROLE"),
        }
        active, color, label = wave_configs.get(status, (False, C_ACCENT, "–"))
        self.wave.set_active(active, color)
        self.wave_label.setText(label)
        self.wave_label.setStyleSheet(f"color:{color}; font-size:10px; letter-spacing:1px;")

        # Bouton micro : rouge pendant l'écoute
        if status == "listening":
            self.btn_mic.setObjectName("mic_active")
        else:
            self.btn_mic.setObjectName("")
        self.btn_mic.setStyleSheet("")  # Force le rechargement du style

    # ── Palette slash ─────────────────────────────────────────────────

    def _on_slash_typing(self, signal: str) -> None:
        """Reçoit les signaux du SmartInput quand l'utilisateur tape après '/'."""
        if signal == "__UP__":
            self._palette.move_selection(-1)
            return
        if signal == "__DOWN__":
            self._palette.move_selection(+1)
            return
        if signal == "__ACCEPT__":
            self._palette.accept_selected()
            return
        # Sinon c'est le texte de filtre
        self._palette.filter(signal)
        if not self._palette.isVisible():
            self._palette.show()
        self._reposition_palette()

    def _reposition_palette(self) -> None:
        """Positionne la palette juste au-dessus du champ de saisie."""
        input_global = self.input.mapToGlobal(self.input.rect().topLeft())
        pal_h = self._palette.sizeHint().height()
        self._palette.move(input_global.x(), input_global.y() - pal_h - 4)
        self._palette.setFixedWidth(self.input.width())

    def _insert_slash_command(self, cmd_text: str) -> None:
        """Insère la commande sélectionnée dans le champ de saisie."""
        self._palette.hide()
        self.input.setPlainText(cmd_text)
        cursor = self.input.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.input.setTextCursor(cursor)
        self.input.setFocus()

    # ── Actions utilisateur ────────────────────────────────────────

    def _send_text(self, text: str = "") -> None:
        if not text:
            text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        self._palette.hide()
        # Commandes UI-only (gérées localement, pas envoyées au thread Boxy)
        if text.startswith("/"):
            cmd = text.strip().split(None, 1)
            if self._handle_ui_command(cmd[0].lower(), cmd[1].strip() if len(cmd) > 1 else ""):
                return
        self.thread.send_text(text)

    def _handle_ui_command(self, cmd: str, args: str) -> bool:
        """
        Commandes traitées directement dans l'UI (sans passer par Boxy).
        Retourne True si la commande a été consommée ici.
        """
        if cmd == "/theme":
            theme = args.strip().lower()
            from ui.themes import THEMES
            if theme in THEMES:
                self._apply_theme(theme)
                # Persiste dans .env
                try:
                    env_path = __import__("pathlib").Path(__file__).parent.parent / ".env"
                    lines = env_path.read_text(encoding="utf-8").splitlines()
                    new_lines = []
                    found = False
                    for line in lines:
                        if line.startswith("THEME="):
                            new_lines.append(f"THEME={theme}")
                            found = True
                        else:
                            new_lines.append(line)
                    if not found:
                        new_lines.append(f"THEME={theme}")
                    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
                except Exception:
                    pass
                self.chat.add_message("system", f"🎨 Thème appliqué : {theme}")
            else:
                from ui.themes import THEMES
                self.chat.add_message("system", f"Thèmes disponibles : {', '.join(THEMES.keys())}")
            return True

        elif cmd == "/export":
            self._export_conversation()
            return True

        elif cmd == "/historique":
            self._open_history()
            return True

        elif cmd == "/compact":
            self._switch_to_compact()
            return True

        return False  # Pas une commande UI → laisser passer au thread

    def _trigger_voice(self) -> None:
        self.thread.trigger_voice()

    def _switch_to_compact(self) -> None:
        """Masque la fenêtre principale et affiche la compacte."""
        self.hide()
        self.compact.show()
        self.compact.raise_()
        self.compact.activateWindow()

    def _switch_to_full(self) -> None:
        """Masque la compacte et affiche la fenêtre principale."""
        self.compact.hide()
        self.show()
        self.raise_()
        self.activateWindow()

    def _on_tray_activated(self, reason) -> None:
        """Double-clic sur l'icône tray → bascule entre compact et plein."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            if self.isVisible():
                self._switch_to_compact()
            elif self.compact.isVisible():
                self._switch_to_full()
            else:
                self._switch_to_full()

    def _quit_app(self) -> None:
        """Arrêt propre depuis le menu tray."""
        self.compact.hide()
        self.chat.add_message("system", "Arrêt en cours...")
        self.thread.stop()
        self._tray.hide()
        QApplication.quit()

    # ── Slots erreur + timing ─────────────────────────────────────────

    @pyqtSlot(str)
    def _on_error(self, msg: str) -> None:
        """Affiche une erreur en rouge dans le chat."""
        self.chat.add_message("system", f"⚠  {msg}")

    @pyqtSlot(float)
    def _on_timing(self, seconds: float) -> None:
        """Met à jour l'indicateur de durée (déjà intégré dans finalize_stream)."""
        pass  # Le timer est affiché inline dans finalize_stream

    # ── Actions titre ─────────────────────────────────────────────────

    def _clear_chat(self) -> None:
        self.chat.clear()
        self.chat.add_message("system", "Chat effacé.")
        self.thread.send_text("/clear")

    def _export_conversation(self) -> None:
        """Exporte la conversation affichée en fichier texte."""
        from datetime import datetime
        from pathlib import Path
        from config import Config

        Config.CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        default = str(Config.CONVERSATIONS_DIR / f"export_{ts}.txt")

        path, _ = QFileDialog.getSaveFileName(
            self, "Exporter la conversation", default,
            "Fichiers texte (*.txt);;Tous les fichiers (*)"
        )
        if not path:
            return
        try:
            content = self.chat.toPlainText()
            Path(path).write_text(content, encoding="utf-8")
            self.chat.add_message("system", f"Conversation exportée → {Path(path).name}")
        except Exception as e:
            self.chat.add_message("system", f"⚠ Erreur export : {e}")

    def _open_history(self) -> None:
        """Ouvre le dialogue d'historique des conversations."""
        dlg = HistoryDialog(parent=self)
        dlg.exec()

    def _on_file_dropped(self, path: str) -> None:
        """Quand un fichier est glissé sur le chat → demande à Boxy de l'analyser."""
        from pathlib import Path
        ext = Path(path).suffix.lower()
        if ext in (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"):
            msg = f'analyse cette image : {path}'
        else:
            msg = f'lis ce fichier et résume-le : {path}'
        self.input.setPlainText(msg)
        self.chat.add_message("system", f"Fichier déposé : {Path(path).name}")

    # ── Streaming slots ───────────────────────────────────────────────

    @pyqtSlot()
    def _on_stream_start(self) -> None:
        """Prépare une bulle de streaming vide dans le chat."""
        self.chat.start_stream()

    @pyqtSlot(str)
    def _on_token(self, token: str) -> None:
        """Ajoute un token dans la bulle de streaming en cours."""
        self.chat.append_token(token)

    @pyqtSlot(str)
    def _on_stream_end(self, final_text: str) -> None:
        """Finalise la bulle de streaming (nettoie les CMD et commandes)."""
        self.chat.finalize_stream(final_text)

    # ── Thème ──────────────────────────────────────────────────────────

    def _apply_theme(self, theme_key: str) -> None:
        """Applique un thème à toute la fenêtre principale."""
        global _THEME, C_BG, C_PANEL, C_BORDER, C_ACCENT, C_ACCENT2
        global C_TEXT, C_DIM, C_BOXY, C_SUCCESS, C_ERROR, C_WARN
        from ui.themes import get_theme, build_stylesheet
        _THEME = get_theme(theme_key)
        C_BG      = _THEME["bg"]
        C_PANEL   = _THEME["panel"]
        C_BORDER  = _THEME["border"]
        C_ACCENT  = _THEME["accent"]
        C_ACCENT2 = _THEME["accent2"]
        C_TEXT    = _THEME["text"]
        C_DIM     = _THEME["dim"]
        C_BOXY    = _THEME["accent"]
        C_SUCCESS = _THEME["success"]
        C_ERROR   = _THEME["error"]
        C_WARN    = _THEME["warn"]
        self.setStyleSheet(build_stylesheet(_THEME))
        self._active_theme = theme_key
        # Rafraîchit la palette si elle existe déjà
        if hasattr(self, "_palette"):
            self._palette.setStyleSheet(
                f"QFrame#slash_palette{{background:{C_PANEL};border:1px solid {C_ACCENT};"
                f"border-radius:6px;}}"
            )

    # ── Paramètres ─────────────────────────────────────────────────────

    def _open_settings(self) -> None:
        """Ouvre la boîte de dialogue des paramètres."""
        dlg = SettingsDialog(current_theme=self._active_theme, parent=self)
        dlg.theme_changed.connect(self._apply_theme)
        dlg.exec()

    def keyPressEvent(self, event) -> None:
        """F2 = déclenche l'écoute vocale (ne conflit pas avec la saisie texte)."""
        if event.key() == Qt.Key.Key_F2 and not self.input.hasFocus():
            self._trigger_voice()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event) -> None:
        """Croix de fermeture → masque dans le tray (ne quitte pas)."""
        event.ignore()          # Annule la fermeture
        self._switch_to_compact()
        self._tray.showMessage(
            Config.ASSISTANT_NAME,
            "Réduit dans la barre système. Clic droit → Quitter pour fermer.",
            QSystemTrayIcon.MessageIcon.Information,
            2500,
        )
