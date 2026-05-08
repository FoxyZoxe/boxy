"""
ai/vision_provider.py — Analyse d'images avec un modèle de vision.

Fonctionnement :
1. On prend une image (screenshot ou fichier)
2. On la convertit en base64
3. On l'envoie au modèle de vision (moondream, llava, gpt-4o...)
4. Le modèle retourne une description en texte

Modèles supportés :
- Ollama : moondream (léger), llava (puissant), llava-phi3
- OpenAI : gpt-4o, gpt-4-turbo (si clé API disponible)

Ollama vision utilise le même format que le chat normal,
mais avec un champ "images" contenant le base64.
"""

import base64
import tempfile
import os
from pathlib import Path
from config import Config
from utils.logger import print_system, print_error


class VisionProvider:
    """Analyse des images avec un modèle de vision IA."""

    def __init__(self):
        print_system(f"Vision : {Config.VISION_PROVIDER} / {Config.VISION_MODEL}")

    def analyze_image_file(self, image_path: str, prompt: str = None) -> str:
        """
        Analyse une image depuis un fichier.

        Args:
            image_path: Chemin vers l'image (PNG, JPG, etc.)
            prompt: Question spécifique (sinon description générale)

        Returns:
            str — Description de l'image par l'IA
        """
        if not Path(image_path).exists():
            return f"Image introuvable : {image_path}"

        prompt = prompt or "Décris précisément ce que tu vois sur cette image en français."

        try:
            image_b64 = self._to_base64(image_path)

            if Config.VISION_PROVIDER == "openai":
                return self._analyze_openai(image_b64, prompt)
            else:
                return self._analyze_ollama(image_b64, prompt)

        except Exception as e:
            print_error(f"Vision — erreur : {e}")
            return "Je n'ai pas pu analyser cette image."

    def analyze_screenshot(self, prompt: str = None) -> str:
        """
        Prend un screenshot et l'analyse immédiatement.

        Args:
            prompt: Question spécifique sur ce qui est affiché

        Returns:
            str — Description de l'écran
        """
        prompt = prompt or "Décris précisément ce qui est affiché sur cet écran en français. Mentionne les applications ouvertes, le texte visible, et ce que fait l'utilisateur."

        # Capture l'écran dans un fichier temporaire
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp_path = tmp.name
        tmp.close()

        try:
            self._capture_screen(tmp_path)
            result = self.analyze_image_file(tmp_path, prompt)
            return result
        finally:
            try:
                os.unlink(tmp_path)
            except FileNotFoundError:
                pass

    def read_screen_text(self) -> str:
        """
        Lit et retourne uniquement le texte visible à l'écran (OCR).
        Utilise le modèle de vision pour extraire le texte.

        Returns:
            str — Tout le texte visible à l'écran
        """
        prompt = "Liste tout le texte visible sur cet écran, mot par mot. Ne décris pas les images, extrais seulement le texte écrit."
        return self.analyze_screenshot(prompt)

    # ─── Méthodes privées ──────────────────────────────────────────

    def _capture_screen(self, output_path: str) -> None:
        """Prend un screenshot avec PIL (method la plus fiable)."""
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab()
            # Réduit la résolution pour accélérer l'analyse
            # (les modèles de vision n'ont pas besoin de 4K)
            max_size = (1280, 720)
            img.thumbnail(max_size)
            img.save(output_path, "PNG")
            return
        except ImportError:
            pass

        try:
            import mss
            with mss.mss() as sct:
                sct.shot(output=output_path)
        except ImportError:
            raise RuntimeError("Installe Pillow ou mss : pip install Pillow mss")

    def _to_base64(self, image_path: str) -> str:
        """Convertit une image en chaîne base64."""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _analyze_ollama(self, image_b64: str, prompt: str) -> str:
        """Envoie l'image à Ollama (llava, moondream, etc.)."""
        import ollama

        client = ollama.Client(host=Config.OLLAMA_BASE_URL)
        response = client.chat(
            model=Config.VISION_MODEL,
            messages=[{
                "role": "user",
                "content": prompt,
                "images": [image_b64]   # Ollama accepte le base64 directement
            }]
        )
        # Compatible avec les deux versions de l'API Ollama
        msg = response.get("message", {}) if isinstance(response, dict) else response.message
        content = msg.get("content", "") if isinstance(msg, dict) else msg.content
        return content.strip()

    def _analyze_openai(self, image_b64: str, prompt: str) -> str:
        """Envoie l'image à OpenAI GPT-4o."""
        from openai import OpenAI

        client = OpenAI(api_key=Config.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_b64}",
                            "detail": "low"  # "low" = plus rapide et moins cher
                        }
                    }
                ]
            }],
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
