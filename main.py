"""
main.py — Point d'entrée de Boxy.

Ce fichier ne fait qu'une chose : vérifier l'environnement
et lancer le programme. La logique est dans les autres modules.
"""

import sys
from pathlib import Path

# Supprime les "Exception ignored in:" de comtypes lors du nettoyage mémoire.
# Ces erreurs VTable sont inoffensives mais polluent l'affichage.
# sys.unraisablehook est le bon endroit pour les intercepter.
def _unraisable_hook(unraisable):
    if "VTable" in str(unraisable.exc_value):
        return  # Ignore silencieusement
    sys.__unraisablehook__(unraisable)  # Laisse passer les vraies erreurs

sys.unraisablehook = _unraisable_hook

# Ajoute la racine du projet au PATH Python
# (permet d'importer nos modules depuis n'importe quel sous-dossier)
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from utils.logger import print_banner, print_error, console


def main():
    """Point d'entrée principal."""

    # Mode interface graphique : python main.py --ui
    use_ui = "--ui" in sys.argv

    if not use_ui:
        print_banner()

    # Valide la configuration avant de démarrer
    errors = Config.validate()
    if errors:
        for error in errors:
            print_error(error)
        console.print("\n[yellow]Corrige ces erreurs dans ton fichier .env puis relance.[/yellow]")
        sys.exit(1)

    if use_ui:
        from PyQt6.QtWidgets import QApplication
        from ui.main_window import MainWindow

        app = QApplication(sys.argv)
        app.setApplicationName(Config.ASSISTANT_NAME)
        window = MainWindow()
        window.show()
        sys.exit(app.exec())

    else:
        from core.jarvis import Boxy
        boxy = Boxy()

        # Lance le bot Discord en arrière-plan si token configuré
        discord_bot = None
        if Config.DISCORD_TOKEN:
            from integrations.discord_bot import DiscordBot
            discord_bot = DiscordBot(boxy)
            discord_bot.start()

        try:
            boxy.run()
        finally:
            if discord_bot:
                discord_bot.stop()


if __name__ == "__main__":
    main()