"""
integrations/obs_control.py — Contrôle OBS Studio via WebSocket.

Prérequis :
1. OBS Studio installé
2. Dans OBS : Outils → WebSocket Server Settings → Activer
3. Définir un mot de passe et le mettre dans .env → OBS_PASSWORD=...

Commandes disponibles via Boxy :
  "lance le stream"         → démarre le streaming
  "arrête le stream"        → arrête le streaming
  "commence l'enregistrement" → démarre l'enregistrement
  "change de scène [nom]"   → change la scène active
  "liste les scènes"        → liste toutes les scènes OBS
"""

from config import Config
from utils.logger import print_system, print_error


class OBSControl:
    """Contrôle OBS Studio via le protocole WebSocket obs-websocket v5."""

    def __init__(self):
        self._client = None
        self._connected = False

    def connect(self) -> bool:
        """Établit la connexion avec OBS."""
        try:
            import obsws_python as obs
            self._client = obs.ReqClient(
                host=Config.OBS_HOST,
                port=Config.OBS_PORT,
                password=Config.OBS_PASSWORD,
                timeout=5
            )
            self._connected = True
            print_system(f"OBS connecté sur {Config.OBS_HOST}:{Config.OBS_PORT}")
            return True
        except ImportError:
            print_error("obsws-python non installé : pip install obsws-python")
            return False
        except Exception as e:
            print_error(f"OBS — connexion impossible : {e}")
            print_error("Vérifie qu'OBS est ouvert et que le WebSocket est activé.")
            return False

    def _ensure_connected(self) -> bool:
        if not self._connected:
            return self.connect()
        return True

    # ─── Stream ────────────────────────────────────────────────────

    def start_streaming(self) -> tuple[bool, str]:
        if not self._ensure_connected():
            return False, "OBS non connecté."
        try:
            self._client.start_stream()
            return True, "Streaming démarré."
        except Exception as e:
            return False, f"Impossible de démarrer le stream : {e}"

    def stop_streaming(self) -> tuple[bool, str]:
        if not self._ensure_connected():
            return False, "OBS non connecté."
        try:
            self._client.stop_stream()
            return True, "Streaming arrêté."
        except Exception as e:
            return False, f"Impossible d'arrêter le stream : {e}"

    def toggle_streaming(self) -> tuple[bool, str]:
        if not self._ensure_connected():
            return False, "OBS non connecté."
        try:
            self._client.toggle_stream()
            return True, "Stream basculé."
        except Exception as e:
            return False, str(e)

    # ─── Enregistrement ────────────────────────────────────────────

    def start_recording(self) -> tuple[bool, str]:
        if not self._ensure_connected():
            return False, "OBS non connecté."
        try:
            self._client.start_record()
            return True, "Enregistrement démarré."
        except Exception as e:
            return False, f"Erreur : {e}"

    def stop_recording(self) -> tuple[bool, str]:
        if not self._ensure_connected():
            return False, "OBS non connecté."
        try:
            self._client.stop_record()
            return True, "Enregistrement arrêté."
        except Exception as e:
            return False, f"Erreur : {e}"

    # ─── Scènes ────────────────────────────────────────────────────

    def get_scenes(self) -> list[str]:
        """Retourne la liste des scènes disponibles."""
        if not self._ensure_connected():
            return []
        try:
            response = self._client.get_scene_list()
            return [s["sceneName"] for s in response.scenes]
        except Exception:
            return []

    def set_scene(self, scene_name: str) -> tuple[bool, str]:
        """Change la scène active."""
        if not self._ensure_connected():
            return False, "OBS non connecté."
        try:
            self._client.set_current_program_scene(scene_name)
            return True, f"Scène '{scene_name}' activée."
        except Exception as e:
            return False, f"Scène introuvable : {scene_name}"

    def get_status(self) -> dict:
        """Retourne l'état actuel d'OBS."""
        if not self._ensure_connected():
            return {"connected": False}
        try:
            stream_status  = self._client.get_stream_status()
            record_status  = self._client.get_record_status()
            current_scene  = self._client.get_current_program_scene()
            return {
                "connected":   True,
                "streaming":   stream_status.output_active,
                "recording":   record_status.output_active,
                "scene":       current_scene.current_program_scene_name,
            }
        except Exception:
            return {"connected": False}

    def disconnect(self) -> None:
        if self._client:
            try:
                self._client.disconnect()
            except Exception:
                pass
            self._connected = False
