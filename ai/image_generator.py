"""
ai/image_generator.py — Génération d'images IA.

Providers supportés :
  - pollinations  : GRATUIT, sans clé API, basé sur Flux/SDXL
                    Juste une requête HTTP → image PNG
  - openai        : DALL-E 3, très haute qualité, ~0.04€/image

Pollinations.ai est recommandé pour commencer — aucune inscription.
"""

import os
import time
import requests
from pathlib import Path
from urllib.parse import quote
from config import Config
from utils.logger import print_system, print_error


class ImageGenerator:
    """Génère des images à partir d'un prompt textuel."""

    # Styles prédéfinis qu'on peut ajouter au prompt
    STYLES = {
        "réaliste":    "photorealistic, 8k, detailed",
        "anime":       "anime style, detailed, vibrant",
        "cyberpunk":   "cyberpunk, neon lights, futuristic, dark atmosphere",
        "aquarelle":   "watercolor painting, artistic, soft colors",
        "cartoon":     "cartoon style, colorful, fun",
        "minimaliste": "minimalist, clean, simple design",
        "boxy":        "holographic HUD, blue cyan glowing, iron man style, futuristic",
    }

    def __init__(self):
        Config.IMAGE_SAVE_DIR.mkdir(parents=True, exist_ok=True)
        print_system(f"Image generator : {Config.IMAGE_PROVIDER}")

    def generate(self, prompt: str, style: str = None, open_after: bool = True) -> tuple[bool, str]:
        """
        Génère une image et la sauvegarde.

        Args:
            prompt:     Description de l'image à créer
            style:      Style prédéfini (réaliste, anime, cyberpunk...)
            open_after: Ouvre l'image dans la visionneuse après génération

        Returns:
            (True, chemin_fichier) ou (False, message_erreur)
        """
        # Enrichit le prompt avec le style si demandé
        full_prompt = self._apply_style(prompt, style)

        print_system(f"Génération : {full_prompt[:60]}...")

        if Config.IMAGE_PROVIDER == "openai":
            success, result = self._generate_openai(full_prompt)
        else:
            success, result = self._generate_pollinations(full_prompt)

        if success and open_after:
            self._open_image(result)

        return success, result

    # ─── Providers ────────────────────────────────────────────────

    def _generate_pollinations(self, prompt: str) -> tuple[bool, str]:
        """
        Génère via Pollinations.ai — totalement gratuit, sans clé.

        L'API est simple : GET https://image.pollinations.ai/prompt/{prompt}
        Elle retourne directement l'image PNG.
        """
        try:
            encoded = quote(prompt)
            # nologo=true : retire le watermark Pollinations
            # model=flux   : meilleur modèle disponible (Flux.1)
            url = f"https://image.pollinations.ai/prompt/{encoded}?nologo=true&model=flux&width=1024&height=1024"

            response = requests.get(url, timeout=60, stream=True)
            response.raise_for_status()

            # Sauvegarde l'image
            filepath = self._get_save_path()
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            return True, str(filepath)

        except requests.Timeout:
            return False, "Délai dépassé — Pollinations.ai est lent, réessaie."
        except requests.RequestException as e:
            print_error(f"Pollinations — erreur réseau : {e}")
            return False, "Impossible de joindre Pollinations.ai."
        except Exception as e:
            print_error(f"Image generation error : {e}")
            return False, str(e)

    def _generate_openai(self, prompt: str) -> tuple[bool, str]:
        """Génère via DALL-E 3 (OpenAI)."""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=Config.OPENAI_API_KEY)

            response = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1
            )

            # Télécharge l'image depuis l'URL retournée
            image_url = response.data[0].url
            img_response = requests.get(image_url, timeout=30)
            img_response.raise_for_status()

            filepath = self._get_save_path()
            with open(filepath, "wb") as f:
                f.write(img_response.content)

            return True, str(filepath)

        except Exception as e:
            print_error(f"DALL-E 3 — erreur : {e}")
            return False, f"Erreur DALL-E : {e}"

    # ─── Utilitaires ──────────────────────────────────────────────

    def _apply_style(self, prompt: str, style: str = None) -> str:
        """Ajoute les mots-clés de style au prompt."""
        if not style:
            return prompt
        style_keywords = self.STYLES.get(style.lower(), style)
        return f"{prompt}, {style_keywords}"

    def _get_save_path(self) -> Path:
        """Génère un chemin de fichier unique horodaté."""
        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        return Config.IMAGE_SAVE_DIR / f"image_{timestamp}.png"

    def _open_image(self, filepath: str) -> None:
        """Ouvre l'image dans la visionneuse Windows."""
        try:
            os.startfile(filepath)
        except Exception:
            pass
