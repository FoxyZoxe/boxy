"""
ai/base_provider.py — Interface abstraite pour les providers IA.

Pourquoi une classe abstraite ?
C'est un "contrat". Tout provider IA (Ollama, OpenAI, Gemini...)
DOIT implémenter ces méthodes. Ça garantit qu'on peut les interchanger
sans toucher au reste du code.

C'est le principe SOLID : dépendre d'abstractions, pas de concrets.
"""

from abc import ABC, abstractmethod


class BaseAIProvider(ABC):
    """
    Interface que tout provider IA doit respecter.
    ABC = Abstract Base Class — ne peut pas être instanciée directement.
    """

    @abstractmethod
    def chat(self, messages: list[dict], stream: bool = True,
             token_callback=None) -> str:
        """
        Envoie une liste de messages et retourne la réponse.

        Args:
            messages:       Liste de dicts {"role": "...", "content": "..."}
            stream:         Si True, génère la réponse token par token
            token_callback: callable(token: str) appelé à chaque token streamé

        Returns:
            str — La réponse complète du modèle
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Vérifie si le service est accessible.

        Returns:
            bool — True si le provider répond, False sinon
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Nom du provider pour les logs."""
        pass