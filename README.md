# FrenchBreaches Bot

Merci beaucoup a [Loukas1212](https://github.com/loukas1212) pour l'aide pour son aide précieuse.

Bot Discord qui surveille [FrenchBreaches](https://frenchbreaches.com) et affiche les dernières fuites de données directement dans votre serveur.

## Fonctionnalités

- `/lastleak` — affiche la dernière fuite recensée (titre, logo, volume de données, statut, nombre de comptes affectés, types de données concernées).
- `/setupchannel` — configure le salon dans lequel les nouvelles fuites seront annoncées automatiquement (admin uniquement).
- `/unlinkchannel` — retire la configuration du salon de notifications pour le serveur (admin uniquement).
- `/leaks` — récupère les fuites d'une année donnée (par défaut l'année en cours).
- Vérification automatique des nouvelles fuites toutes les 10 secondes, avec envoi dans le salon configuré de chaque serveur.
- Configuration multi-serveurs stockée dans MongoDB (association serveur ↔ salon de notification).
- Récupération automatique de la liste des fuites au démarrage du bot, mise en cache dans `src/json/data.json`.
- Chargement automatique des cogs présents dans `src/cogs/`.

## Prérequis

- Python 3.11+
- Un token de bot Discord ([Discord Developer Portal](https://discord.com/developers/applications))
- Une base de données MongoDB (ex: [MongoDB Atlas](https://www.mongodb.com/atlas)) pour stocker la configuration des salons par serveur

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # Linux/macOS

pip install -r requirements.txt
```

Copiez `.env.example` en `.env` et renseignez vos identifiants :

```
TOKEN=votre_token_discord
MONGO_URL=votre_uri_de_connexion_mongodb
MONGO_DB=nom_de_la_base
MONGO_COLLECTION=nom_de_la_collection
```

## Lancer le bot

```bash
python src/main.py
```

Une configuration de lancement VS Code (`.vscode/launch.json`) est déjà fournie ("Run bot").

## Structure du projet

```
src/
├── main.py              # Point d'entrée du bot (connexion Discord + MongoDB, vérification périodique)
├── cogs/                # Commandes slash (ex: fuite.py -> /lastleak, /setupchannel, /unlinkchannel, /leaks)
├── components/          # Utilitaires (embeds, chargement des cogs, intervalles)
├── handlers/             # Événements du client Discord (on_ready, on_error)
├── fuite/                # Récupération et cache des données FrenchBreaches
├── types/                # Modèles Pydantic (réponses de l'API, client Discord custom, modèle MongoDB)
└── json/                 # Cache local des données (ignoré par git)
```

## Configuration

Variables d'environnement requises dans `.env` :

| Variable            | Description                                    |
| ------------------- | ----------------------------------------------- |
| `TOKEN`             | Token du bot Discord                            |
| `MONGO_URL`         | URI de connexion à la base MongoDB              |
| `MONGO_DB`          | Nom de la base de données MongoDB                |
| `MONGO_COLLECTION`  | Nom de la collection stockant serveur ↔ salon    |

## Licence

Ce projet est distribué sous licence [MIT](LICENSE). Vous êtes libre de l'utiliser, le modifier et le redistribuer, tant que la notice de copyright est conservée.
