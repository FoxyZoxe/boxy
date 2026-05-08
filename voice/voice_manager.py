"""
voice/voice_manager.py — Orchestrateur vocal.

Ce module coordonne :
- La synthèse vocale (TTS)
- La reconnaissance vocale (STT)
- La détection de wake word

Il propose deux modes :
  1. push_to_talk : maintiens ESPACE → parle → relâche
  2. wake_word    : dis "Boxy" → parle → silence automatique

Pourquoi un orchestrateur séparé ?
Parce que jarvis.py ne doit pas connaître les détails de
chaque composant vocal. Il appelle voice_manager.listen()
et ça suffit.
"""

import keyboard
import threading
from utils.logger import print_system, print_error, print_jarvis, console
from config import Config


class VoiceManager:
    """Gère toute la couche vocale de Boxy."""

    def __init__(self):
        self._tts            = None
        self._stt            = None
        self._wake_word      = None
        self._wake_word_error = None
        self._enabled        = Config.VOICE_ENABLED
        self._mode           = Config.VOICE_MODE

        if self._enabled:
            self._initialize()

    def _initialize(self) -> None:
        """Initialise les composants vocaux selon le mode."""
        # TTS toujours initialisé si la voix est activée
        from voice.text_to_speech import TextToSpeech
        self._tts = TextToSpeech()

        # STT toujours initialisé (pour push-to-talk ET wake word)
        from voice.speech_to_text import SpeechToText
        self._stt = SpeechToText()

        # Wake word uniquement en mode wake_word
        if self._mode == "wake_word":
            try:
                from voice.wake_word import WakeWordDetector
                self._wake_word = WakeWordDetector()
            except ImportError as e:
                print_error(
                    f"openWakeWord non installé.\n"
                    f"  → Relance l'installateur Boxy pour installer les dependances.\n"
                    f"  → Puis redémarre Boxy."
                )
                print_system("Basculement automatique en push-to-talk.")
                self._mode = "push_to_talk"
                self._wake_word_error = str(e)
            except Exception as e:
                print_error(f"Wake word désactivé : {e}")
                print_system("Basculement en mode push-to-talk.")
                self._mode = "push_to_talk"
                self._wake_word_error = str(e)
        else:
            self._wake_word_error = None

        model = getattr(Config, "WAKE_WORD_MODEL", "hey_jarvis")
        mode_label = (
            f"push-to-talk [{Config.PTT_KEY.upper()}]"
            if self._mode == "push_to_talk"
            else f"wake word [{model}]"
        )
        print_system(f"Mode vocal : {mode_label}")

    # --- API publique ---

    def speak(self, text: str) -> bool:
        """
        Fait parler Boxy.

        Returns:
            True  — lecture terminée normalement
            False — interrompue par l'utilisateur
        """
        if self._tts and self._enabled:
            return self._tts.speak(text)
        return True

    def listen(self) -> str:
        """
        Lance le cycle d'écoute complet selon le mode actif.

        En push-to-talk : attend que l'utilisateur appuie sur ESPACE
        En wake word    : attend "Boxy" puis écoute

        Returns:
            str — Texte reconnu (peut être vide)
        """
        if not self._stt or not self._enabled:
            return ""

        if self._mode == "push_to_talk":
            return self._listen_push_to_talk()
        else:
            return self._listen_wake_word()

    def toggle(self) -> bool:
        """
        Active/désactive la voix.

        Returns:
            bool — Nouvel état (True = activé)
        """
        self._enabled = not self._enabled
        state = "activée" if self._enabled else "désactivée"
        print_system(f"Voix {state}.")
        return self._enabled

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    # --- Modes d'écoute ---

    def _listen_push_to_talk(self) -> str:
        """
        Écoute et transcrit — l'attente de ESPACE est gérée dans core/jarvis.py.
        S'arrête automatiquement dès que l'utilisateur arrête de parler (VAD).
        """
        console.print("[dim]  → Écoute... parle maintenant[/dim]")
        return self._stt.listen_and_transcribe()

    def _listen_wake_word(self) -> str:
        """
        Écoute en mode wake word.

        Écoute en permanence, déclenche après "Boxy".
        """
        console.print("[dim]  → En attente de 'Boxy'...[/dim]")

        # Attend le wake word
        self._wake_word.wait_for_wake_word()

        # Feedback audio + visuel
        console.print("[bold cyan]  → Wake word détecté ! Je vous écoute...[/bold cyan]")
        self.speak("Yes?")  # Courte confirmation vocale

        # Écoute la commande
        text = self._stt.listen_and_transcribe()
        return text

    def cleanup(self) -> None:
        """Libère toutes les ressources audio."""
        if self._wake_word:
            self._wake_word.cleanup()
