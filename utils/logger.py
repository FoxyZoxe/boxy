"""
utils/logger.py — Système de logs colorés avec Rich.

Pourquoi Rich au lieu de print() ?
print() c'est basique. Rich permet des couleurs, des tableaux, des spinners,
de la mise en forme — parfait pour l'interface terminal de Boxy.
"""

from rich.console import Console
from rich.theme import Theme
from rich.text import Text
from datetime import datetime

# Thème de couleurs style Iron Man / HUD
BOXY_THEME = Theme({
    "jarvis": "bold cyan",           # Messages de Boxy
    "user": "bold white",            # Messages de l'utilisateur
    "system": "bold yellow",         # Messages système
    "error": "bold red",             # Erreurs
    "success": "bold green",         # Succès
    "info": "dim cyan",              # Infos techniques
    "dim": "dim white",              # Texte secondaire
})

# Console principale — utilisée dans tout le projet
console = Console(theme=BOXY_THEME)


def print_jarvis(message: str) -> None:
    """Affiche un message de Boxy avec son style."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    console.print(f"[dim]{timestamp}[/dim] [jarvis]BOXY ▸[/jarvis] {message}")


def print_user(message: str) -> None:
    """Affiche un message de l'utilisateur."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    console.print(f"[dim]{timestamp}[/dim] [user]YOU    ▸[/user] {message}")


def print_system(message: str) -> None:
    """Affiche un message système (démarrage, connexion, etc.)."""
    console.print(f"[system]  ◈  {message}[/system]")


def print_error(message: str) -> None:
    """Affiche une erreur."""
    console.print(f"[error]  ✗  ERREUR : {message}[/error]")


def print_success(message: str) -> None:
    """Affiche un succès."""
    console.print(f"[success]  ✓  {message}[/success]")


def print_separator() -> None:
    """Ligne de séparation visuelle."""
    console.print("[dim]" + "─" * 60 + "[/dim]")


def print_banner() -> None:
    """Bannière de démarrage de Boxy."""
    console.print()
    console.print("[jarvis]" + "═" * 60 + "[/jarvis]")
    console.print("[jarvis]              B  O  X  Y  — v0.1.0[/jarvis]")
    console.print("[jarvis]         Brilliant Omniscient eXpert AI[/jarvis]")
    console.print("[jarvis]" + "═" * 60 + "[/jarvis]")
    console.print()