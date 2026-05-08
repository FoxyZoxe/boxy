"""
voice/wake_word.py — Détection du wake word avec openWakeWord.

100% GRATUIT, open source, sans compte, sans API key.

Les modèles ONNX doivent être téléchargés une fois depuis GitHub
(~5 Mo chacun). Le téléchargement est automatique au premier lancement.

Installation : pip install openwakeword

Mots-clés disponibles :
    hey_jarvis   → dis "hey jarvis"
    alexa        → dis "alexa"
    hey_mycroft  → dis "hey mycroft"
    hey_rhasspy  → dis "hey rhasspy"

Configuration : WAKE_WORD_MODEL=hey_jarvis dans .env
"""

import os
import pathlib
import numpy as np
import sounddevice as sd
from threading import Event
from utils.logger import print_system, print_error
from config import Config


class WakeWordDetector:
    """Détecte le mot-clé en écoute permanente avec openWakeWord."""

    SAMPLE_RATE = 16_000   # Hz requis par les modèles ONNX
    CHUNK_MS    = 80       # ms par chunk → 1280 samples @ 16kHz
    THRESHOLD   = 0.5      # Score minimum pour déclencher (0–1)

    # Modèles disponibles dans openwakeword v0.6.0
    AVAILABLE_MODELS = ["hey_jarvis", "alexa", "hey_mycroft", "hey_rhasspy"]

    def __init__(self):
        self._model       = None
        self._stop_event  = Event()
        self._detected    = Event()
        self._model_name  = Config.WAKE_WORD_MODEL
        self._initialize()

    # ─── Initialisation ──────────────────────────────────────────────

    def _initialize(self) -> None:
        """Télécharge (si absent) puis charge le modèle ONNX."""
        try:
            import openwakeword
            import openwakeword.utils
        except ImportError:
            raise ImportError(
                "openWakeWord n'est pas installé.\n"
                "Lance : pip install openwakeword"
            )

        if self._model_name not in self.AVAILABLE_MODELS:
            raise ValueError(
                f"Modèle '{self._model_name}' inconnu.\n"
                f"Modèles valides : {', '.join(self.AVAILABLE_MODELS)}"
            )

        # Télécharge les modèles manquants (melspec + embedding + wake word)
        self._ensure_models_downloaded(openwakeword)

        # Charge le modèle
        from openwakeword.model import Model
        self._model = Model(
            wakeword_models=[self._model_name],
            inference_framework="onnx",
        )

        label = self._model_name.replace("_", " ").title()
        print_system(f"Wake word '{label}' prêt — dis '{label}' pour activer {Config.ASSISTANT_NAME}.")

    def _ensure_models_downloaded(self, oww_module) -> None:
        """
        Télécharge les fichiers ONNX si absents.
        Appelle openwakeword.utils.download_models() qui gère tout :
          - melspectrogram.onnx + embedding_model.onnx (features)
          - silero_vad.onnx
          - <wake_word>_v0.1.onnx
        """
        models_dir = pathlib.Path(oww_module.__file__).parent / "resources" / "models"
        model_file = models_dir / f"{self._model_name}_v0.1.onnx"

        if model_file.exists():
            return  # Déjà présent, rien à faire

        print_system(
            f"Modèle '{self._model_name}' absent — téléchargement depuis GitHub...\n"
            f"  (connexion internet requise, ~5 Mo, une seule fois)"
        )

        try:
            oww_module.utils.download_models([self._model_name])
            print_system("Téléchargement terminé.")
        except Exception as e:
            raise RuntimeError(
                f"Impossible de télécharger le modèle '{self._model_name}'.\n"
                f"Vérifie ta connexion internet.\n"
                f"Erreur : {e}\n\n"
                f"Téléchargement manuel :\n"
                f"  URL : https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/{self._model_name}_v0.1.onnx\n"
                f"  Dossier cible : {models_dir}"
            )

    # ─── Écoute ──────────────────────────────────────────────────────

    def wait_for_wake_word(self) -> None:
        """
        Bloque jusqu'à ce que le mot-clé soit détecté.

        Le callback sounddevice traite chaque chunk directement (pas de buffer externe).
        float32 audio → int16 → openWakeWord.predict() → score > THRESHOLD → stop
        """
        self._stop_event.clear()
        self._detected.clear()

        chunk_size = int(self.SAMPLE_RATE * self.CHUNK_MS / 1000)  # 1280 samples

        def _callback(indata: np.ndarray, frames: int, time_info, status) -> None:
            if self._stop_event.is_set():
                raise sd.CallbackStop()

            # float32 [-1,1] → int16
            pcm = (indata[:, 0] * 32_768).clip(-32_768, 32_767).astype(np.int16)

            try:
                preds = self._model.predict(pcm)
            except Exception:
                return  # Ignore les erreurs de prédiction isolées

            for name, score in preds.items():
                # score peut être float ou ndarray selon la version
                val = float(score[-1]) if hasattr(score, "__len__") else float(score)
                if val >= self.THRESHOLD:
                    self._detected.set()
                    raise sd.CallbackStop()

        try:
            with sd.InputStream(
                samplerate=self.SAMPLE_RATE,
                channels=1,
                dtype="float32",
                blocksize=chunk_size,
                callback=_callback,
            ):
                while not self._stop_event.is_set() and not self._detected.is_set():
                    sd.sleep(50)

        except sd.CallbackStop:
            pass  # Sortie normale (détection ou stop demandé)
        except Exception as e:
            print_error(f"Wake word — erreur audio : {e}")

    # ─── Contrôle ────────────────────────────────────────────────────

    def stop(self) -> None:
        """Arrête l'écoute en cours."""
        self._stop_event.set()

    def cleanup(self) -> None:
        """Libère les ressources."""
        self.stop()
        self._model = None
