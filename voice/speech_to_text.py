"""
voice/speech_to_text.py — Reconnaissance vocale avec faster-whisper.

faster-whisper est une version optimisée de Whisper d'OpenAI.
Il tourne localement, sans internet, et est beaucoup plus rapide
que la version originale grâce à CTranslate2.

Fonctionnement de l'enregistrement :
1. On capture l'audio en petits blocs (frames)
2. On calcule l'énergie sonore de chaque bloc (RMS)
3. Quand l'énergie dépasse un seuil → l'utilisateur a commencé à parler
4. Quand l'énergie reste sous le seuil pendant N secondes → il a fini
5. On envoie l'audio complet à Whisper pour transcription
"""

import sounddevice as sd
import numpy as np
import soundfile as sf
import tempfile
import os
from faster_whisper import WhisperModel
from utils.logger import print_system, print_error
from config import Config


class SpeechToText:
    """Capture audio et transcrit en texte avec Whisper."""

    # Paramètres audio
    SAMPLE_RATE = 16000    # 16kHz requis par Whisper
    CHANNELS = 1           # Mono
    BLOCK_SIZE = 512       # Taille d'un bloc audio (32ms à 16kHz)

    # Paramètres de détection de silence
    SILENCE_THRESHOLD = 0.02    # Énergie RMS sous laquelle = silence
    SILENCE_DURATION = 1.5      # Secondes de silence pour arrêter l'enregistrement
    MAX_DURATION = 30.0         # Durée max d'un enregistrement

    def __init__(self):
        print_system(f"Chargement de Whisper ({Config.WHISPER_MODEL})... (premier lancement = téléchargement)")
        # device="cpu" : utilise le processeur (pas besoin de GPU)
        # compute_type="int8" : compression qui accélère x2-3 avec peu de perte de qualité
        self.model = WhisperModel(
            Config.WHISPER_MODEL,
            device="cpu",
            compute_type="int8"
        )
        print_system("Whisper prêt.")

    def record(self, max_duration: float = None) -> np.ndarray | None:
        """
        Enregistre l'audio depuis le micro jusqu'à détection de silence.

        Returns:
            np.ndarray — Audio enregistré (float32, 16kHz)
            None — Si rien n'a été capturé
        """
        max_duration = max_duration or self.MAX_DURATION
        frames: list[np.ndarray] = []
        silence_frames = 0
        speaking_started = False

        # Nombre de blocs consécutifs silencieux pour décider d'arrêter
        # Ex: 1.5s / (512/16000s) = ~47 blocs
        silence_threshold_frames = int(
            self.SILENCE_DURATION / (self.BLOCK_SIZE / self.SAMPLE_RATE)
        )
        max_frames = int(max_duration / (self.BLOCK_SIZE / self.SAMPLE_RATE))

        def callback(indata, frame_count, time_info, status):
            """Appelée automatiquement à chaque bloc audio capturé."""
            nonlocal silence_frames, speaking_started

            # indata est un tableau 2D (frames x channels), on prend la 1ère colonne
            audio_block = indata[:, 0].copy()
            rms = float(np.sqrt(np.mean(audio_block ** 2)))

            if rms > self.SILENCE_THRESHOLD:
                speaking_started = True
                silence_frames = 0
                frames.append(audio_block)
            elif speaking_started:
                silence_frames += 1
                frames.append(audio_block)  # Garde le silence de fin pour naturel

        try:
            with sd.InputStream(
                samplerate=self.SAMPLE_RATE,
                channels=self.CHANNELS,
                blocksize=self.BLOCK_SIZE,
                dtype="float32",
                callback=callback
            ):
                # Attend que l'enregistrement se termine
                while True:
                    sd.sleep(50)  # Vérifie toutes les 50ms

                    # Arrêt si silence détecté après début de parole
                    if speaking_started and silence_frames >= silence_threshold_frames:
                        break

                    # Arrêt si durée max atteinte
                    if len(frames) >= max_frames:
                        break

        except sd.PortAudioError as e:
            print_error(f"Microphone — erreur PortAudio : {e}")
            return None

        if not frames or not speaking_started:
            return None

        return np.concatenate(frames)

    def transcribe(self, audio: np.ndarray) -> str:
        """
        Transcrit un tableau audio en texte.

        Args:
            audio: Audio numpy float32 à 16kHz

        Returns:
            str — Texte transcrit, ou "" si inaudible
        """
        if audio is None or len(audio) == 0:
            return ""

        # Whisper nécessite un fichier audio — on crée un WAV temporaire
        tmp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp_path = tmp_file.name
        tmp_file.close()

        try:
            # Sauvegarde l'audio numpy en fichier WAV
            sf.write(tmp_path, audio, self.SAMPLE_RATE)

            # Transcription avec Whisper
            # beam_size=5 : cherche les 5 meilleures hypothèses (plus précis)
            # vad_filter=True : filtre automatiquement les parties silencieuses
            # language="fr" : force le français — sans ça, Whisper peut détecter
            #                  du japonais ou de l'anglais sur des phrases courtes
            segments, info = self.model.transcribe(
                tmp_path,
                beam_size=5,
                language=Config.STT_LANGUAGE,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 500}
            )

            # Concatène tous les segments transcrits
            text = " ".join(segment.text.strip() for segment in segments)
            return text.strip()

        except Exception as e:
            print_error(f"Whisper — erreur de transcription : {e}")
            return ""
        finally:
            try:
                os.unlink(tmp_path)
            except FileNotFoundError:
                pass

    def listen_and_transcribe(self) -> str:
        """
        Raccourci : enregistre et transcrit en une seule étape.

        Returns:
            str — Texte reconnu, ou "" si rien détecté
        """
        audio = self.record()
        if audio is None:
            return ""
        return self.transcribe(audio)