"""
ai/ai_manager.py — Gestionnaire de providers IA.

Son rôle : choisir le bon provider selon la config,
vérifier qu'il est disponible, et basculer sur un fallback si nécessaire.
"""

from config import Config
from ai.base_provider import BaseAIProvider
from ai.ollama_provider import OllamaProvider
from ai.openai_provider import OpenAIProvider
from utils.logger import print_system, print_error, print_success


class AIManager:
    """Gère la sélection et l'utilisation du provider IA actif."""

    def __init__(self):
        self._provider: BaseAIProvider | None = None
        self._initialize()

    def _initialize(self) -> None:
        """Initialise le provider selon la configuration."""
        provider_name = Config.AI_PROVIDER.lower()

        print_system(f"Initialisation du provider IA : {provider_name}")

        if provider_name == "ollama":
            self._provider = OllamaProvider(
                model=Config.OLLAMA_MODEL,
                base_url=Config.OLLAMA_BASE_URL
            )
        elif provider_name == "openai":
            self._provider = OpenAIProvider(
                api_key=Config.OPENAI_API_KEY,
                model=Config.OPENAI_MODEL,
            )
        elif provider_name == "groq":
            self._provider = OpenAIProvider(
                api_key=Config.GROQ_API_KEY,
                model=Config.GROQ_MODEL,
                base_url="https://api.groq.com/openai/v1",
            )
        else:
            print_error(f"Provider inconnu '{provider_name}', utilisation d'Ollama par défaut.")
            self._provider = OllamaProvider(
                model=Config.OLLAMA_MODEL,
                base_url=Config.OLLAMA_BASE_URL
            )

        # Vérifie que le provider répond
        if self._provider.is_available():
            print_success(f"Provider connecté : {self._provider.name}")
        else:
            hints = {
                "ollama": "lance 'ollama serve' dans un terminal.",
                "openai": "vérifie ta clé OPENAI_API_KEY dans .env",
                "groq":   "vérifie ta clé GROQ_API_KEY dans .env (groq.com)",
            }
            hint = hints.get(provider_name, "vérifie ta configuration.")
            print_error(f"{self._provider.name} n'est pas accessible.\n  → {hint}")

    def chat(self, messages: list[dict], stream: bool = True,
             token_callback=None) -> str:
        """
        Envoie une conversation au provider actif.

        Args:
            messages:       Historique complet au format OpenAI
            stream:         Affiche les tokens en temps réel si True
            token_callback: callable(token) pour le streaming vers l'UI

        Returns:
            str — Réponse de l'IA
        """
        if not self._provider:
            return "Aucun provider IA disponible."

        return self._provider.chat(messages, stream=stream,
                                   token_callback=token_callback)

    @property
    def provider_name(self) -> str:
        """Nom du provider actif pour les logs."""
        return self._provider.name if self._provider else "Aucun"