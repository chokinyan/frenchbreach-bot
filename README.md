# FrenchBreaches Bot

Bot Discord qui surveille [FrenchBreaches](https://frenchbreaches.com) et affiche les dernières fuites de données directement dans votre serveur.

## Fonctionnalités

- `/lastleak` — affiche la dernière fuite recensée (titre, logo, volume de données, statut, nombre de comptes affectés, types de données concernées).
- Récupération automatique de la liste des fuites au démarrage du bot, mise en cache dans `src/json/data.json`.
- Chargement automatique des cogs présents dans `src/cogs/`.

## Prérequis

- Python 3.11+
- Un token de bot Discord ([Discord Developer Portal](https://discord.com/developers/applications))

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # Linux/macOS

pip install -r requirements.txt
```

Copiez `.env.example` en `.env` et renseignez votre token :

```
TOKEN=votre_token_discord
```

## Lancer le bot

```bash
python src/main.py
```

Une configuration de lancement VS Code (`.vscode/launch.json`) est déjà fournie ("Run bot").

## Structure du projet

```
src/
├── main.py              # Point d'entrée du bot
├── cogs/                # Commandes slash (ex: fuite.py -> /lastleak)
├── components/          # Utilitaires (embeds, chargement des cogs, intervalles)
├── handlers/             # Événements du client Discord (on_ready, on_error)
├── fuite/                # Récupération et cache des données FrenchBreaches
├── types/                # Modèles Pydantic des réponses de l'API
└── json/                 # Cache local des données (ignoré par git)
```

## Configuration

Variable d'environnement requise dans `.env` :

| Variable | Description                          |
| -------- | ------------------------------------- |
| `TOKEN`  | Token du bot Discord                  |

## Licence

Ce projet est distribué sous licence [MIT](LICENSE). Vous êtes libre de l'utiliser, le modifier et le redistribuer, tant que la notice de copyright est conservée.
