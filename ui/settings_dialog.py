"""
ui/settings_dialog.py — Fenêtre de paramètres de Boxy.

Onglets :
  • Général  — nom assistant / utilisateur
  • IA       — provider, modèle, URL Ollama
  • Voix     — activer/désactiver, modèle Whisper, touche PTT
  • Interface — thème, taille police
"""

import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QLineEdit, QComboBox, QCheckBox, QSlider,
    QPushButton, QGroupBox, QFormLayout, QSpacerItem,
    QSizePolicy, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPixmap, QFont

from ui.themes import THEMES, build_stylesheet


# ─── Helpers ──────────────────────────────────────────────────────────

def _sep() -> QFrame:
    """Ligne séparatrice horizontale."""
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet("color: #1a3555; margin: 6px 0;")
    return f


def _label(text: str, dim=False) -> QLabel:
    lbl = QLabel(text)
    if dim:
        lbl.setStyleSheet("color: #3a5570; font-size: 11px;")
    return lbl


# ─── ThemeButton ──────────────────────────────────────────────────────

class ThemeButton(QPushButton):
    """Bouton carré affichant l'aperçu d'un thème (accent + bg)."""

    def __init__(self, theme_key: str, theme: dict, parent=None):
        super().__init__(parent)
        self.theme_key = theme_key
        self._theme    = theme
        self.setFixedSize(54, 54)
        self.setToolTip(theme["name"])
        self.setCheckable(True)
        self._build_icon()

    def _build_icon(self) -> None:
        px = QPixmap(48, 48)
        px.fill(QColor(self._theme["bg"]))
        p = QPainter(px)
        p.setPen(QColor(self._theme["accent"]))
        p.setBrush(QColor(self._theme["accent"]))
        p.drawRoundedRect(4, 4, 40, 40, 6, 6)
        p.setPen(QColor(self._theme["bg"]))
        f = QFont("Consolas", 12, QFont.Weight.Bold)
        p.setFont(f)
        p.drawText(px.rect(), Qt.AlignmentFlag.AlignCenter,
                   self._theme["name"][0])
        p.end()
        from PyQt6.QtGui import QIcon
        self.setIcon(QIcon(px))
        self.setIconSize(px.size())
        self.setText("")
        self.setStyleSheet(f"""
            QPushButton {{
                background: {self._theme['bg']};
                border: 2px solid {self._theme['border']};
                border-radius: 6px;
                padding: 0;
            }}
            QPushButton:hover {{
                border-color: {self._theme['accent']};
            }}
            QPushButton:checked {{
                border: 3px solid {self._theme['accent']};
            }}
        """)


# ─── SettingsDialog ───────────────────────────────────────────────────

class SettingsDialog(QDialog):
    """Dialogue de paramètres — écrit dans .env à la validation."""

    theme_changed = pyqtSignal(str)   # clé du thème sélectionné

    def __init__(self, current_theme: str = "cyan", parent=None):
        super().__init__(parent)
        self.setWindowTitle("◈  Paramètres — Boxy")
        self.setMinimumSize(540, 500)
        self.setModal(True)
        self._current_theme = current_theme
        self._theme_btns: dict[str, ThemeButton] = {}

        # Lit les valeurs actuelles depuis l'env
        self._load_env()
        self._build_ui()
        self._apply_current_theme()

    # ── Chargement .env ───────────────────────────────────────────────

    def _load_env(self) -> None:
        """Lit toutes les variables pertinentes depuis os.environ."""
        g = os.getenv
        self._vals = {
            "ASSISTANT_NAME":  g("ASSISTANT_NAME", "Boxy"),
            "USER_NAME":       g("USER_NAME", "Sir"),
            "AI_PROVIDER":     g("AI_PROVIDER", "ollama"),
            "OLLAMA_MODEL":    g("OLLAMA_MODEL", "mistral:latest"),
            "OLLAMA_BASE_URL": g("OLLAMA_BASE_URL", "http://localhost:11434"),
            "OPENAI_MODEL":    g("OPENAI_MODEL", "gpt-4o-mini"),
            "GROQ_API_KEY":    g("GROQ_API_KEY", ""),
            "GROQ_MODEL":      g("GROQ_MODEL", "llama-3.3-70b-versatile"),
            "OPENAI_API_KEY":  g("OPENAI_API_KEY", ""),
            "VOICE_ENABLED":   g("VOICE_ENABLED", "true"),
            "WHISPER_MODEL":   g("WHISPER_MODEL", "base"),
            "STT_LANGUAGE":    g("STT_LANGUAGE", "fr"),
            "PTT_KEY":         g("PTT_KEY", "space"),
            "VOICE_MODE":      g("VOICE_MODE", "push_to_talk"),
            "TTS_VOICE":        g("TTS_VOICE", "en-GB-RyanNeural"),
            "WAKE_WORD_MODEL":  g("WAKE_WORD_MODEL", "hey_jarvis"),
            "GLOBAL_HOTKEY":    g("GLOBAL_HOTKEY", "ctrl+space"),
            "THEME":            g("THEME", self._current_theme),
        }

    # ── Construction UI ───────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 12)
        root.setSpacing(10)

        # Titre
        title = QLabel("◈  PARAMÈTRES")
        title.setStyleSheet("color: #00d4ff; font-size: 16px; font-weight: bold; letter-spacing: 3px;")
        root.addWidget(title)
        root.addWidget(_sep())

        # Onglets
        tabs = QTabWidget()
        tabs.addTab(self._tab_general(),   "Général")
        tabs.addTab(self._tab_ia(),        "IA")
        tabs.addTab(self._tab_voice(),     "Voix")
        tabs.addTab(self._tab_interface(), "Interface")
        root.addWidget(tabs, 1)

        # Boutons OK / Annuler
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_cancel = QPushButton("Annuler")
        btn_cancel.setFixedWidth(100)
        btn_cancel.clicked.connect(self.reject)

        btn_ok = QPushButton("✓  Appliquer")
        btn_ok.setFixedWidth(130)
        btn_ok.setDefault(True)
        btn_ok.clicked.connect(self._apply)

        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        root.addLayout(btn_row)

    # ── Onglet Général ────────────────────────────────────────────────

    def _tab_general(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.inp_name = QLineEdit(self._vals["ASSISTANT_NAME"])
        self.inp_user = QLineEdit(self._vals["USER_NAME"])

        form.addRow("Nom de l'assistant :", self.inp_name)
        form.addRow("Votre prénom :", self.inp_user)
        form.addRow(_sep())
        form.addRow(_label("Ces modifications prennent effet au prochain démarrage.", dim=True))
        return w

    # ── Onglet IA ─────────────────────────────────────────────────────

    def _tab_ia(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # ── Provider actif ────────────────────────────────────────────
        grp = QGroupBox("Provider actif")
        grp_form = QFormLayout(grp)

        self.cmb_provider = QComboBox()
        self.cmb_provider.addItems(["ollama", "openai", "groq"])
        self.cmb_provider.setCurrentText(self._vals["AI_PROVIDER"])
        self.cmb_provider.currentTextChanged.connect(self._on_provider_changed)
        grp_form.addRow("Provider :", self.cmb_provider)

        self._provider_note = QLabel()
        self._provider_note.setWordWrap(True)
        grp_form.addRow("", self._provider_note)
        layout.addWidget(grp)

        # ── Ollama (local) ────────────────────────────────────────────
        self._grp_ol = QGroupBox("Ollama  —  IA locale (gratuit, privé)")
        form_ol = QFormLayout(self._grp_ol)
        self.inp_ol_url   = QLineEdit(self._vals["OLLAMA_BASE_URL"])
        self.inp_ol_model = QLineEdit(self._vals["OLLAMA_MODEL"])
        self.inp_ol_model.setPlaceholderText("mistral, llama3, phi3...")
        form_ol.addRow("URL Ollama :", self.inp_ol_url)
        form_ol.addRow("Modèle :", self.inp_ol_model)
        form_ol.addRow("", _label("Démarrage Ollama : ollama serve", dim=True))
        layout.addWidget(self._grp_ol)

        # ── OpenAI (cloud) ────────────────────────────────────────────
        self._grp_oa = QGroupBox("OpenAI  —  ChatGPT (cloud, payant)")
        form_oa = QFormLayout(self._grp_oa)

        self.inp_oa_key = QLineEdit(self._vals["OPENAI_API_KEY"])
        self.inp_oa_key.setPlaceholderText("sk-proj-...")
        self.inp_oa_key.setEchoMode(QLineEdit.EchoMode.Password)

        # Bouton œil pour afficher/masquer la clé
        key_row = QHBoxLayout()
        key_row.setSpacing(4)
        key_row.addWidget(self.inp_oa_key)
        btn_eye = QPushButton("👁")
        btn_eye.setFixedSize(28, 28)
        btn_eye.setCheckable(True)
        btn_eye.setToolTip("Afficher / masquer")
        btn_eye.toggled.connect(
            lambda show: self.inp_oa_key.setEchoMode(
                QLineEdit.EchoMode.Normal if show else QLineEdit.EchoMode.Password
            )
        )
        key_row.addWidget(btn_eye)
        key_widget = QWidget()
        key_widget.setLayout(key_row)
        form_oa.addRow("Clé API :", key_widget)

        self.inp_oa_model = QComboBox()
        self.inp_oa_model.addItems([
            "gpt-4o-mini",          # Rapide, peu cher — recommandé
            "gpt-4o",               # Plus puissant
            "gpt-4.1-mini",         # Très récent
            "gpt-4.1",
            "gpt-3.5-turbo",        # Ancien mais économique
        ])
        self.inp_oa_model.setCurrentText(self._vals["OPENAI_MODEL"])
        form_oa.addRow("Modèle :", self.inp_oa_model)

        # Bouton test de connexion
        self._btn_test = QPushButton("🔌  Tester la connexion")
        self._btn_test.clicked.connect(self._test_openai)
        self._test_result = QLabel("")
        self._test_result.setWordWrap(True)
        form_oa.addRow("", self._btn_test)
        form_oa.addRow("", self._test_result)
        form_oa.addRow("", _label(
            "Clé API : platform.openai.com/api-keys\n"
            "gpt-4o-mini = le plus rapide et économique (conseillé).",
            dim=True
        ))
        layout.addWidget(self._grp_oa)

        # ── Groq (cloud gratuit) ──────────────────────────────────────
        self._grp_groq = QGroupBox("Groq  —  Llama 3 cloud (GRATUIT, sans carte)")
        form_groq = QFormLayout(self._grp_groq)

        self.inp_groq_key = QLineEdit(self._vals["GROQ_API_KEY"])
        self.inp_groq_key.setPlaceholderText("gsk_...")
        self.inp_groq_key.setEchoMode(QLineEdit.EchoMode.Password)

        groq_key_row = QHBoxLayout()
        groq_key_row.setSpacing(4)
        groq_key_row.addWidget(self.inp_groq_key)
        btn_eye_groq = QPushButton("👁")
        btn_eye_groq.setFixedSize(28, 28)
        btn_eye_groq.setCheckable(True)
        btn_eye_groq.toggled.connect(
            lambda show: self.inp_groq_key.setEchoMode(
                QLineEdit.EchoMode.Normal if show else QLineEdit.EchoMode.Password
            )
        )
        groq_key_row.addWidget(btn_eye_groq)
        groq_key_widget = QWidget()
        groq_key_widget.setLayout(groq_key_row)
        form_groq.addRow("Clé API :", groq_key_widget)

        self.inp_groq_model = QComboBox()
        self.inp_groq_model.addItems([
            "llama-3.3-70b-versatile",   # Recommandé — le plus intelligent
            "llama-3.1-8b-instant",      # Ultra-rapide
            "mixtral-8x7b-32768",        # Bon compromis
            "gemma2-9b-it",
        ])
        self.inp_groq_model.setCurrentText(self._vals["GROQ_MODEL"])
        form_groq.addRow("Modèle :", self.inp_groq_model)

        self._btn_test_groq = QPushButton("🔌  Tester Groq")
        self._btn_test_groq.clicked.connect(self._test_groq)
        self._test_result_groq = QLabel("")
        self._test_result_groq.setWordWrap(True)
        form_groq.addRow("", self._btn_test_groq)
        form_groq.addRow("", self._test_result_groq)
        form_groq.addRow("", _label(
            "Clé gratuite : console.groq.com → API Keys\n"
            "llama-3.3-70b-versatile = le plus intelligent, gratuit.",
            dim=True
        ))
        layout.addWidget(self._grp_groq)

        layout.addWidget(_label("⚠  Le changement de provider nécessite un redémarrage de Boxy.", dim=True))
        layout.addStretch()

        # Applique l'état initial (griser les panneaux non-actifs)
        self._on_provider_changed(self._vals["AI_PROVIDER"])
        return w

    def _on_provider_changed(self, provider: str) -> None:
        """Met à jour les notes et grise les panneaux non-actifs."""
        self._grp_ol.setEnabled(provider == "ollama")
        self._grp_oa.setEnabled(provider == "openai")
        self._grp_groq.setEnabled(provider == "groq")
        notes = {
            "ollama": ("✓ Ollama — 100% local, gratuit, sans internet.", "#00d4ff"),
            "openai": ("✓ ChatGPT — cloud, payant, très performant.",    "#00ff88"),
            "groq":   ("✓ Groq — cloud GRATUIT, Llama 3, ultra-rapide.", "#ffaa00"),
        }
        text, color = notes.get(provider, ("", "#888"))
        self._provider_note.setText(text)
        self._provider_note.setStyleSheet(f"color:{color}; font-size:11px;")

    def _test_groq(self) -> None:
        """Teste la clé API Groq en direct."""
        key = self.inp_groq_key.text().strip()
        if not key:
            self._test_result_groq.setText("⚠ Clé vide.")
            self._test_result_groq.setStyleSheet("color:#ffaa00; font-size:11px;")
            return
        self._btn_test_groq.setEnabled(False)
        self._btn_test_groq.setText("Test en cours…")
        self._test_result_groq.setText("")
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()
        try:
            from openai import OpenAI, AuthenticationError, APIConnectionError
            client = OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")
            client.models.list()
            self._test_result_groq.setText("✓ Clé Groq valide — connexion OK !")
            self._test_result_groq.setStyleSheet("color:#00ff88; font-size:11px;")
        except AuthenticationError:
            self._test_result_groq.setText("✗ Clé invalide.")
            self._test_result_groq.setStyleSheet("color:#ff4444; font-size:11px;")
        except APIConnectionError:
            self._test_result_groq.setText("✗ Pas d'accès à internet.")
            self._test_result_groq.setStyleSheet("color:#ff4444; font-size:11px;")
        except Exception as e:
            self._test_result_groq.setText(f"✗ Erreur : {e}")
            self._test_result_groq.setStyleSheet("color:#ff4444; font-size:11px;")
        finally:
            self._btn_test_groq.setEnabled(True)
            self._btn_test_groq.setText("🔌  Tester Groq")

    def _test_openai(self) -> None:
        """Teste la clé API OpenAI en direct."""
        key = self.inp_oa_key.text().strip()
        if not key:
            self._test_result.setText("⚠ Clé vide.")
            self._test_result.setStyleSheet("color:#ffaa00; font-size:11px;")
            return
        self._btn_test.setEnabled(False)
        self._btn_test.setText("Test en cours…")
        self._test_result.setText("")
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()
        try:
            from openai import OpenAI, AuthenticationError, APIConnectionError
            client = OpenAI(api_key=key)
            client.models.list()
            self._test_result.setText("✓ Clé valide — connexion OK !")
            self._test_result.setStyleSheet("color:#00ff88; font-size:11px;")
        except AuthenticationError:
            self._test_result.setText("✗ Clé invalide ou expirée.")
            self._test_result.setStyleSheet("color:#ff4444; font-size:11px;")
        except APIConnectionError:
            self._test_result.setText("✗ Pas d'accès à internet / OpenAI inaccessible.")
            self._test_result.setStyleSheet("color:#ff4444; font-size:11px;")
        except Exception as e:
            self._test_result.setText(f"✗ Erreur : {e}")
            self._test_result.setStyleSheet("color:#ff4444; font-size:11px;")
        finally:
            self._btn_test.setEnabled(True)
            self._btn_test.setText("🔌  Tester la connexion")

    # ── Onglet Voix ───────────────────────────────────────────────────

    def _tab_voice(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.chk_voice = QCheckBox("Activer la voix")
        self.chk_voice.setChecked(self._vals["VOICE_ENABLED"].lower() == "true")
        form.addRow("", self.chk_voice)

        self.cmb_voice_mode = QComboBox()
        self.cmb_voice_mode.addItems(["push_to_talk", "wake_word"])
        self.cmb_voice_mode.setCurrentText(self._vals["VOICE_MODE"])
        form.addRow("Mode vocal :", self.cmb_voice_mode)

        self.cmb_whisper = QComboBox()
        self.cmb_whisper.addItems(["tiny", "base", "small", "medium", "large"])
        self.cmb_whisper.setCurrentText(self._vals["WHISPER_MODEL"])
        form.addRow("Modèle Whisper :", self.cmb_whisper)

        self.cmb_stt_lang = QComboBox()
        self.cmb_stt_lang.setEditable(True)
        self.cmb_stt_lang.addItems(["fr", "en", "es", "de", "it", "pt", "nl", "ja", "zh"])
        self.cmb_stt_lang.setCurrentText(self._vals["STT_LANGUAGE"])
        self.cmb_stt_lang.setToolTip("Code ISO de la langue parlée (fr=français, en=anglais…)")
        form.addRow("Langue vocale :", self.cmb_stt_lang)

        self.inp_ptt = QLineEdit(self._vals["PTT_KEY"])
        self.inp_ptt.setPlaceholderText("space, f2, ctrl, ...")
        form.addRow("Touche PTT :", self.inp_ptt)

        self.inp_tts = QLineEdit(self._vals["TTS_VOICE"])
        self.inp_tts.setPlaceholderText("en-GB-RyanNeural")
        form.addRow("Voix TTS :", self.inp_tts)

        # Wake word (openWakeWord — sans compte)
        self.cmb_wakeword = QComboBox()
        self.cmb_wakeword.addItems([
            "hey_jarvis",
            "alexa",
            "hey_mycroft",
            "hey_rhasspy",
        ])
        self.cmb_wakeword.setCurrentText(self._vals.get("WAKE_WORD_MODEL", "hey_jarvis"))
        form.addRow("Mot-clé (wake word) :", self.cmb_wakeword)

        self.inp_hotkey = QLineEdit(self._vals.get("GLOBAL_HOTKEY", "ctrl+space"))
        self.inp_hotkey.setPlaceholderText("ctrl+space, alt+b, ...")
        form.addRow("Raccourci global :", self.inp_hotkey)

        form.addRow(_sep())
        form.addRow(_label("Whisper 'tiny'/'base' = rapide.  'small'+ = plus précis.", dim=True))
        form.addRow(_label("Wake word : dis le mot-clé choisi (ex: 'hey jarvis') pour activer Boxy.", dim=True))
        form.addRow(_label("⚠  Wake word nécessite :  pip install openwakeword  (à faire une seule fois).", dim=True))
        return w

    # ── Onglet Interface ──────────────────────────────────────────────

    def _tab_interface(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        layout.addWidget(QLabel("Thème de couleurs :"))

        # Grille de boutons thème
        theme_row = QHBoxLayout()
        theme_row.setSpacing(8)
        for key, theme in THEMES.items():
            btn = ThemeButton(key, theme)
            btn.setChecked(key == self._current_theme)
            btn.clicked.connect(lambda checked, k=key: self._preview_theme(k))
            self._theme_btns[key] = btn
            theme_row.addWidget(btn)
        theme_row.addStretch()
        layout.addLayout(theme_row)

        # Nom du thème sélectionné
        self._theme_name_lbl = QLabel(THEMES[self._current_theme]["name"])
        self._theme_name_lbl.setStyleSheet("color: #00d4ff; font-size: 12px; padding: 4px 0;")
        layout.addWidget(self._theme_name_lbl)

        layout.addWidget(_sep())

        # Auto-démarrage Windows
        self.chk_autostart = QCheckBox("Lancer Boxy au démarrage de Windows")
        self.chk_autostart.setChecked(self._is_autostart_enabled())
        layout.addWidget(self.chk_autostart)

        layout.addWidget(_label("Le thème est appliqué immédiatement.", dim=True))
        layout.addStretch()
        return w

    @staticmethod
    def _is_autostart_enabled() -> bool:
        """Vérifie si Boxy est dans les programmes au démarrage."""
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_READ
            )
            winreg.QueryValueEx(key, "Boxy")
            winreg.CloseKey(key)
            return True
        except Exception:
            return False

    @staticmethod
    def _set_autostart(enable: bool) -> None:
        """Ajoute ou supprime Boxy du démarrage automatique Windows."""
        try:
            import winreg
            import sys
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE
            )
            if enable:
                # Lance main.py avec pythonw (sans fenêtre console)
                exe = sys.executable.replace("python.exe", "pythonw.exe")
                script = str(Path(__file__).parent.parent / "main.py")
                winreg.SetValueEx(key, "Boxy", 0, winreg.REG_SZ,
                                  f'"{exe}" "{script}"')
            else:
                try:
                    winreg.DeleteValue(key, "Boxy")
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            print(f"[WARN] Auto-start : {e}")

    # ── Logique thème ─────────────────────────────────────────────────

    def _preview_theme(self, key: str) -> None:
        """Met à jour les boutons et émet le signal pour prévisualiser."""
        self._current_theme = key
        for k, btn in self._theme_btns.items():
            btn.setChecked(k == key)
        self._theme_name_lbl.setText(THEMES[key]["name"])
        self.theme_changed.emit(key)
        self._apply_current_theme()

    def _apply_current_theme(self) -> None:
        """Applique le QSS du thème actuel à la boîte de dialogue."""
        t = THEMES.get(self._current_theme, THEMES["cyan"])
        self.setStyleSheet(build_stylesheet(t))

    # ── Sauvegarde .env ───────────────────────────────────────────────

    def _apply(self) -> None:
        """Écrit les nouvelles valeurs dans le fichier .env et ferme."""
        new_vals = {
            "ASSISTANT_NAME":  self.inp_name.text().strip() or "Boxy",
            "USER_NAME":       self.inp_user.text().strip() or "Sir",
            "AI_PROVIDER":     self.cmb_provider.currentText(),
            "OLLAMA_BASE_URL": self.inp_ol_url.text().strip(),
            "OLLAMA_MODEL":    self.inp_ol_model.text().strip(),
            "OPENAI_API_KEY":  self.inp_oa_key.text().strip(),
            "OPENAI_MODEL":    self.inp_oa_model.currentText(),
            "GROQ_API_KEY":    self.inp_groq_key.text().strip(),
            "GROQ_MODEL":      self.inp_groq_model.currentText(),
            "VOICE_ENABLED":    "true" if self.chk_voice.isChecked() else "false",
            "VOICE_MODE":       self.cmb_voice_mode.currentText(),
            "WHISPER_MODEL":    self.cmb_whisper.currentText(),
            "STT_LANGUAGE":     self.cmb_stt_lang.currentText().strip() or "fr",
            "PTT_KEY":          self.inp_ptt.text().strip() or "space",
            "TTS_VOICE":        self.inp_tts.text().strip(),
            "WAKE_WORD_MODEL":  self.cmb_wakeword.currentText(),
            "GLOBAL_HOTKEY":    self.inp_hotkey.text().strip() or "ctrl+space",
            "THEME":            self._current_theme,
        }
        self._write_env(new_vals)
        # Gère l'auto-démarrage Windows
        self._set_autostart(self.chk_autostart.isChecked())
        self.theme_changed.emit(self._current_theme)
        self.accept()

    @staticmethod
    def _write_env(new_vals: dict) -> None:
        """Met à jour ou crée les lignes dans le fichier .env."""
        env_path = Path(__file__).parent.parent / ".env"

        # Lit les lignes existantes
        if env_path.exists():
            lines = env_path.read_text(encoding="utf-8").splitlines()
        else:
            lines = []

        updated_keys = set()
        new_lines = []

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                new_lines.append(line)
                continue
            if "=" in stripped:
                key = stripped.split("=", 1)[0].strip()
                if key in new_vals:
                    new_lines.append(f"{key}={new_vals[key]}")
                    updated_keys.add(key)
                    continue
            new_lines.append(line)

        # Ajoute les clés absentes du fichier existant
        for key, val in new_vals.items():
            if key not in updated_keys:
                new_lines.append(f"{key}={val}")

        env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    # ── Accesseur ─────────────────────────────────────────────────────

    @property
    def selected_theme(self) -> str:
        return self._current_theme
