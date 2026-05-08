"""
memory/memory_manager.py — Système de mémoire de Boxy.

Deux types de mémoire :
1. Court-terme (RAM) : historique de la conversation actuelle
2. Long-terme (disque) : faits importants à retenir entre les sessions
"""

import json
from pathlib import Path
from datetime import datetime
from config import Config
from utils.logger import print_system, print_error


class MemoryManager:
    """Gère la mémoire à court et long terme de Boxy."""

    def __init__(self):
        # Court-terme : liste de messages de la session en cours
        # Format : [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
        self._short_term: list[dict] = []

        # Long-terme : dictionnaire de faits persistants
        # Format : {"clé": {"value": "...", "timestamp": "..."}}
        self._long_term: dict = {}

        # Assure que les dossiers existent
        Config.MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        Config.CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)

        # Charge la mémoire long-terme depuis le disque
        self._load_long_term()

    # --- COURT-TERME (conversation en cours) ---

    def add_message(self, role: str, content: str) -> None:
        """
        Ajoute un message à l'historique de la session.

        Args:
            role: "user", "assistant", ou "system"
            content: Texte du message
        """
        self._short_term.append({
            "role": role,
            "content": content
        })

        # Garde seulement les N derniers échanges pour ne pas dépasser
        # la fenêtre de contexte du modèle
        if len(self._short_term) > Config.MAX_HISTORY_LENGTH:
            # Supprime les plus anciens, mais garde toujours le system prompt
            # (le premier message est toujours le system prompt)
            self._short_term = self._short_term[-Config.MAX_HISTORY_LENGTH:]

    def get_messages_for_ai(self) -> list[dict]:
        """
        Retourne l'historique complet à envoyer à l'IA.
        Inclut le system prompt (+ mémoire long-terme) + l'historique.
        """
        prompt = Config.SYSTEM_PROMPT

        # Injecte les souvenirs long-terme dans le system prompt
        if self._long_term:
            memories_text = "\n".join(
                f"- {k}: {v['value']}"
                for k, v in list(self._long_term.items())[-10:]  # 10 derniers
            )
            prompt = prompt + f"\n\nMémoire long-terme (faits importants sur l'utilisateur) :\n{memories_text}"

        system_message = {
            "role": "system",
            "content": prompt,
        }
        return [system_message] + self._short_term

    def clear_short_term(self) -> None:
        """Efface la conversation en cours (nouvelle session)."""
        self._short_term = []

    # --- LONG-TERME (persistant entre sessions) ---

    def remember(self, key: str, value: str) -> None:
        """
        Mémorise une information importante de façon permanente.

        Exemple : remember("favorite_language", "Python")
        """
        self._long_term[key] = {
            "value": value,
            "timestamp": datetime.now().isoformat()
        }
        self._save_long_term()

    def recall(self, key: str) -> str | None:
        """
        Récupère une information mémorisée.

        Returns:
            str — La valeur mémorisée, ou None si introuvable
        """
        entry = self._long_term.get(key)
        return entry["value"] if entry else None

    def forget(self, key: str) -> bool:
        """
        Supprime une information mémorisée.

        Returns:
            bool — True si la clé existait, False sinon
        """
        if key in self._long_term:
            del self._long_term[key]
            self._save_long_term()
            return True
        return False

    def get_all_memories(self) -> dict:
        """Retourne toute la mémoire long-terme."""
        return {k: v["value"] for k, v in self._long_term.items()}

    # --- PERSISTANCE ---

    def _save_long_term(self) -> None:
        """Sauvegarde la mémoire sur le disque."""
        try:
            with open(Config.MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self._long_term, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print_error(f"Impossible de sauvegarder la mémoire : {e}")

    def _load_long_term(self) -> None:
        """Charge la mémoire depuis le disque au démarrage."""
        if not Config.MEMORY_FILE.exists():
            return  # Première utilisation — fichier inexistant, c'est normal

        try:
            with open(Config.MEMORY_FILE, "r", encoding="utf-8") as f:
                self._long_term = json.load(f)
            if self._long_term:
                print_system(f"Mémoire chargée : {len(self._long_term)} entrées")
        except json.JSONDecodeError:
            print_error("Fichier mémoire corrompu — réinitialisation.")
            self._long_term = {}

    def save_conversation(self) -> None:
        """Sauvegarde la conversation actuelle dans un fichier horodaté."""
        if not self._short_term:
            return

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filepath = Config.CONVERSATIONS_DIR / f"conversation_{timestamp}.json"

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self._short_term, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print_error(f"Impossible de sauvegarder la conversation : {e}")