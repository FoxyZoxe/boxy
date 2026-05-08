"""
voice/text_to_speech.py — Synthèse vocale avec edge-tts + interruption.

Deux façons d'interrompre Boxy pendant qu'il parle :
1. Appuyer sur ESPACE  → arrêt immédiat
2. Parler dans le micro → arrêt si énergie vocale détectée (barge-in)

speak() retourne True si la lecture s'est terminée normalement,
False si elle a été interrompue — jarvis.py utilise ce retour
pour relancer l'écoute immédiatement.
"""

import asyncio
import tempfile
import os
import time
import threading
import keyboard
import sounddevice as sd
import numpy as np
import pygame
import edge_tts
from utils.logger import print_error, print_system
from config import Config


class TextToSpeech:
    """Convertit du texte en parole, interruptible par ESPACE ou par la voix."""

    # Seuil d'énergie micro pour détecter une interruption vocale.
    # Valeur plus haute = moins sensible (évite que les haut-parleurs
    # déclenchent une fausse interruption par rétroaction acoustique).
    BARGE_IN_THRESHOLD = 0.06

    def __init__(self):
        pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
        self.voice = Config.TTS_VOICE
        print_system(f"TTS initialisé — voix : {self.voice}")

    def speak(self, text: str) -> bool:
        """
        Lit le texte à voix haute.

        Returns:
            True  — lecture terminée normalement
            False — interrompue (ESPACE ou voix détectée)
        """
        if not text or not text.strip():
            return True
        try:
            return asyncio.run(self._speak_async(text))
        except Exception as e:
            print_error(f"TTS — erreur : {e}")
            return True

    async def _speak_async(self, text: str) -> bool:
        tmp_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp_path = tmp_file.name
        tmp_file.close()

        interrupted = False
        stop_event = threading.Event()

        def monitor():
            """
            Surveille ESPACE et le micro — version allégée.
            - Délai de 0.6s au départ (laisse le TTS commencer vraiment)
            - Polling toutes les 100ms au lieu de 30ms (CPU /3)
            - Blocs audio plus grands = moins de lectures par seconde
            """
            time.sleep(0.6)

            SAMPLE_RATE = 16000
            BLOCK_SIZE  = 2048   # Plus grand = moins de lectures CPU

            try:
                with sd.InputStream(
                    samplerate=SAMPLE_RATE,
                    channels=1,
                    blocksize=BLOCK_SIZE,
                    dtype="float32"
                ) as stream:
                    while not stop_event.is_set():
                        if keyboard.is_pressed("space"):
                            stop_event.set()
                            break

                        audio, _ = stream.read(BLOCK_SIZE)
                        energy = float(np.sqrt(np.mean(audio ** 2)))
                        if energy > self.BARGE_IN_THRESHOLD:
                            stop_event.set()
                            break

                        time.sleep(0.10)   # 100ms au lieu de 30ms
            except Exception:
                pass

        try:
            communicate = edge_tts.Communicate(text, self.voice)
            await communicate.save(tmp_path)

            monitor_thread = threading.Thread(target=monitor, daemon=True)
            monitor_thread.start()

            pygame.mixer.music.load(tmp_path)
            pygame.mixer.music.play()

            clock = pygame.time.Clock()
            while pygame.mixer.music.get_busy():
                clock.tick(30)
                if stop_event.is_set():
                    pygame.mixer.music.stop()
                    interrupted = True
                    break

            stop_event.set()
            monitor_thread.join(timeout=0.5)

        finally:
            pygame.mixer.music.unload()
            try:
                os.unlink(tmp_path)
            except FileNotFoundError:
                pass

        return not interrupted  # True = normal, False = interrompu

    def stop(self) -> None:
        pygame.mixer.music.stop()

    def set_voice(self, voice: str) -> None:
        self.voice = voice
        print_system(f"Voix changée : {voice}")
