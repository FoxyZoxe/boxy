"""
create_shortcut.py — Crée un raccourci bureau pour lancer Boxy en mode graphique.

Lance ce script UNE SEULE FOIS :
    python create_shortcut.py

Il va :
1. Générer une icône personnalisée (data/boxy.ico)
2. Créer un raccourci "Boxy.lnk" sur le bureau
3. Le raccourci utilise pythonw.exe (pas de fenêtre noire au lancement)
"""

import sys
import os
from pathlib import Path


def create_icon() -> str:
    """
    Génère une icône .ico style HUD cyberpunk avec Pillow.
    Retourne le chemin du fichier .ico créé.
    """
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("Pillow manquant — pip install Pillow")
        return ""

    SIZE   = 256
    BG     = (7,   9,  14, 255)   # Noir bleuté
    CYAN   = (0,  212, 255, 255)  # Bleu cyan
    CYAN2  = (0,  100, 160, 180)  # Cyan plus sombre
    TRANSP = (0,    0,   0,   0)  # Transparent

    img  = Image.new("RGBA", (SIZE, SIZE), TRANSP)
    draw = ImageDraw.Draw(img)

    # Cercle extérieur (bord lumineux)
    draw.ellipse([8, 8, SIZE-8, SIZE-8], fill=BG, outline=CYAN, width=5)

    # Cercle intérieur (halo)
    draw.ellipse([20, 20, SIZE-20, SIZE-20], fill=None, outline=CYAN2, width=2)

    # Croix HUD (lignes fines)
    cx = cy = SIZE // 2
    draw.line([(cx-70, cy), (cx-25, cy)], fill=CYAN2, width=2)
    draw.line([(cx+25, cy), (cx+70, cy)], fill=CYAN2, width=2)
    draw.line([(cx, cy-70), (cx, cy-25)], fill=CYAN2, width=2)
    draw.line([(cx, cy+25), (cx, cy+70)], fill=CYAN2, width=2)

    # Lettre centrale "J" (ou initiale du nom dans config)
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from config import Config
        letter = Config.ASSISTANT_NAME[0].upper()
    except Exception:
        letter = "B"

    # Taille de police approximative via polygone (pas besoin de font externe)
    # Dessine la lettre avec des rectangles pour un look pixel/HUD
    _draw_hud_letter(draw, letter, cx, cy, CYAN)

    # Petit hexagone décoratif autour
    import math
    for i in range(6):
        angle = math.radians(60 * i - 30)
        r = 90
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        next_angle = math.radians(60 * (i+1) - 30)
        nx = cx + r * math.cos(next_angle)
        ny = cy + r * math.sin(next_angle)
        draw.line([(x, y), (nx, ny)], fill=CYAN2, width=2)

    # Sauvegarde en .ico multi-résolution
    icon_path = Path(__file__).parent / "data" / "boxy.ico"
    icon_path.parent.mkdir(parents=True, exist_ok=True)

    # Génère plusieurs tailles pour un .ico propre
    sizes = [(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)]
    resized = [img.resize(s, Image.LANCZOS) for s in sizes]
    resized[-1].save(
        str(icon_path),
        format="ICO",
        sizes=sizes,
        append_images=resized[:-1]
    )

    print(f"  ✓ Icône créée : {icon_path}")
    return str(icon_path)


def _draw_hud_letter(draw, letter: str, cx: int, cy: int, color) -> None:
    """Dessine une lettre style HUD avec des traits épais."""
    try:
        from PIL import ImageFont
        # Essaie d'utiliser une police système Windows
        font_paths = [
            r"C:\Windows\Fonts\consola.ttf",   # Consolas
            r"C:\Windows\Fonts\arial.ttf",      # Arial
            r"C:\Windows\Fonts\calibri.ttf",    # Calibri
        ]
        font = None
        for path in font_paths:
            if Path(path).exists():
                font = ImageFont.truetype(path, size=110)
                break

        if font is None:
            font = ImageFont.load_default()

        # Centre le texte
        bbox = draw.textbbox((0, 0), letter, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x = cx - w // 2 - bbox[0]
        y = cy - h // 2 - bbox[1]
        draw.text((x, y), letter, font=font, fill=color)

    except Exception:
        # Fallback minimaliste si Pillow ne trouve pas de font
        draw.rectangle([cx-28, cy-40, cx+28, cy+40], fill=color)


def create_shortcut(icon_path: str) -> str:
    """
    Crée un raccourci .lnk sur le bureau Windows.

    Utilise pythonw.exe (= Python sans fenêtre console noire).
    Pointe vers le venv du projet pour que les imports fonctionnent.
    """
    try:
        import win32com.client
    except ImportError:
        print("pywin32 manquant — pip install pywin32")
        print("Relance le script après installation.")
        return ""

    project_dir = Path(__file__).parent.resolve()

    # Cherche pythonw.exe dans le venv du projet d'abord
    venv_pythonw = project_dir / ".venv" / "Scripts" / "pythonw.exe"
    sys_pythonw  = Path(sys.executable).parent / "pythonw.exe"

    if venv_pythonw.exists():
        pythonw = venv_pythonw
    elif sys_pythonw.exists():
        pythonw = sys_pythonw
    else:
        # Dernier recours : python.exe (montrera une console brièvement)
        pythonw = Path(sys.executable)
        print("  ⚠ pythonw.exe introuvable — une console apparaîtra brièvement au lancement.")

    main_py  = project_dir / "main.py"
    desktop  = Path.home() / "Desktop"
    lnk_path = desktop / f"{_get_name()}.lnk"

    shell     = win32com.client.Dispatch("WScript.Shell")
    shortcut  = shell.CreateShortCut(str(lnk_path))

    shortcut.Targetpath      = str(pythonw)
    shortcut.Arguments       = f'"{main_py}" --ui'
    shortcut.WorkingDirectory = str(project_dir)
    shortcut.Description     = f"Lancer {_get_name()} — Assistant IA"

    if icon_path and Path(icon_path).exists():
        shortcut.IconLocation = icon_path

    shortcut.save()
    return str(lnk_path)


def _get_name() -> str:
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from config import Config
        return Config.ASSISTANT_NAME
    except Exception:
        return "Boxy"


def main():
    print()
    print("═" * 50)
    print(f"  Création du raccourci bureau — {_get_name()}")
    print("═" * 50)

    # 1. Icône
    print("\n→ Génération de l'icône...")
    icon_path = create_icon()

    # 2. Raccourci
    print("→ Création du raccourci sur le bureau...")
    shortcut_path = create_shortcut(icon_path)

    if shortcut_path:
        print(f"\n  ✓ Raccourci créé : {shortcut_path}")
        print(f"\n  Double-clique sur '{_get_name()}' sur ton bureau pour lancer l'interface.")
    else:
        print("\n  ✗ Échec de la création du raccourci.")
        print("    Installe pywin32 : pip install pywin32")
        print("    Puis relance : python create_shortcut.py")

    print()


if __name__ == "__main__":
    main()
