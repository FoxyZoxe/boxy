"""
ui/jarvis_thread.py — Thread background pour Boxy.

Qt impose que l'interface graphique tourne dans le thread principal.
Boxy (IA, voix, commandes) tourne ici dans un thread séparé.

Communication :
  UI → Boxy : via self.send_text() et self.trigger_voice()
  Boxy → UI : via les signaux Qt (on_response, on_status, etc.)
"""

import queue
from PyQt6.QtCore import QThread, pyqtSignal


class BoxyThread(QThread):
    """Fait tourner Boxy en arrière-plan et expose des signaux Qt."""

    # Signaux émis vers l'interface (thread-safe)
    on_response     = pyqtSignal(str)   # Réponse finale complète
    on_user_message = pyqtSignal(str)   # L'utilisateur a parlé/écrit
    on_status       = pyqtSignal(str)   # "idle"|"listening"|"thinking"|"speaking"
    on_ready        = pyqtSignal()      # Boxy est initialisé et prêt
    on_token        = pyqtSignal(str)   # Token streamé (mot par mot)
    on_stream_start = pyqtSignal()      # Début du streaming
    on_stream_end   = pyqtSignal(str)   # Fin streaming (texte nettoyé)
    on_error        = pyqtSignal(str)   # Erreur à afficher dans l'UI
    on_timing       = pyqtSignal(float) # Durée de génération (secondes)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._queue: queue.Queue = queue.Queue()
        self._jarvis = None
        self._running = True

    def run(self) -> None:
        """Point d'entrée du thread — initialise Boxy puis lance sa boucle."""
        from core.jarvis import Boxy
        from config import Config
        import keyboard

        self._jarvis = Boxy(
            on_response=self.on_response.emit,
            on_user_message=self.on_user_message.emit,
            on_status=self.on_status.emit,
            on_token=self.on_token.emit,
            on_stream_start=self.on_stream_start.emit,
            on_stream_end=self.on_stream_end.emit,
            on_error=self.on_error.emit,
            on_timing=self.on_timing.emit,
        )

        # ── Hotkey global (Ctrl+Space par défaut) ─────────────────────
        # Fonctionne depuis n'importe quelle application, même si Boxy est en arrière-plan
        try:
            hotkey = Config.GLOBAL_HOTKEY
            keyboard.add_hotkey(hotkey, self._on_global_hotkey, suppress=False)
        except Exception:
            pass  # Hotkey non critique — on continue sans

        self.on_ready.emit()
        self._jarvis.run_ui(self._queue)

    def _on_global_hotkey(self) -> None:
        """Appelé depuis n'importe où — déclenche l'écoute vocale."""
        self._queue.put(("voice", None))

    # --- API publique appelée depuis l'UI ---

    def send_text(self, text: str) -> None:
        """Envoie un message texte à Boxy."""
        self._queue.put(("text", text))

    def trigger_voice(self) -> None:
        """Déclenche une écoute vocale."""
        self._queue.put(("voice", None))

    def stop(self) -> None:
        """Arrête proprement le thread."""
        try:
            import keyboard
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass
        self._queue.put(("quit", None))
        self.wait(3000)
