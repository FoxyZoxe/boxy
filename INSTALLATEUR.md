# Installer Boxy

## Fichier a donner

Le site doit proposer uniquement ce fichier :

```text
Boxy-Setup.bat
```

L'utilisateur double-clique dessus, confirme l'installation, puis le script :

- telecharge la derniere version depuis GitHub ;
- installe Boxy dans `%LOCALAPPDATA%\Boxy` ;
- cree un environnement Python `.venv` ;
- installe les dependances ;
- cree le fichier `.env` ;
- demande la cle Groq si l'utilisateur veut configurer l'IA tout de suite ;
- ajoute un raccourci `Boxy` sur le Bureau ;
- propose de lancer Boxy a la fin.

## Depot du setup

Le fichier `Boxy-Setup.bat` peut etre heberge seul dans ce depot :

```text
https://github.com/FoxyZoxe/Boxy-Setup1
```

Lien direct utilise par le site :

```text
https://github.com/FoxyZoxe/Boxy-Setup1/raw/refs/heads/main/Boxy-Setup.bat
```

## Important avant de le partager

Le setup telecharge ensuite l'application Boxy complete depuis :

```text
https://github.com/FoxyZoxe/boxy/archive/refs/heads/main.zip
```

Il faut donc garder les deux depots a jour :

- `Boxy-Setup1` pour le fichier `Boxy-Setup.bat` ;
- `boxy` pour l'application complete telechargee pendant l'installation.

## Lancement local

Sur votre machine de developpement, `start.bat` lance maintenant directement l'interface graphique :

```text
start.bat
```

## Pre-requis utilisateur

L'utilisateur doit avoir :

- Windows ;
- Python 3.11, 3.12 ou 3.13 ;
- une connexion internet pendant l'installation ;
- une cle Groq si `AI_PROVIDER=groq`.

Python 3.14 est volontairement evite pour l'instant, car certaines dependances
comme `pygame` ne fournissent pas encore de paquet Windows compatible.
