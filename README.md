# FrenchBreaches Bot

Merci beaucoup à [Loukas1212](https://github.com/loukas1212) pour son aide précieuse.

Bot Discord qui surveille [FrenchBreaches](https://frenchbreaches.com) et affiche les dernières fuites de données directement dans votre serveur.

## Fonctionnalités

- `/lastleak` — affiche la dernière fuite recensée (titre, logo, volume de données, nombre de comptes affectés, types de données concernées).
- `/leaks [secteur] [nombre]` — liste paginée des dernières fuites, filtrable par secteur (max 25).
- `/setupchannel <salon>` — configure le salon où les nouvelles fuites sont annoncées automatiquement (admin uniquement).
- `/unlinkchannel` — retire la configuration du salon pour le serveur (admin uniquement).
- `*sync` — commande texte réservée au propriétaire du bot pour resynchroniser l'arbre des slash commands sans redémarrer (`~` guilde courante, `*` copie+sync, `^` clear).
- Vérification automatique des nouvelles fuites toutes les 5 minutes (déduplication par identifiant, `last_seen` persisté en base pour survivre à un redémarrage).
- Configuration multi-serveurs stockée dans MySQL.
- Cache local des réponses de l'API dans `src/cache/` (ignoré par git).
- Chargement automatique des cogs présents dans `src/cogs/`.

## Prérequis

- Python 3.13+
- Un token de bot Discord ([Discord Developer Portal](https://discord.com/developers/applications))
- Une base de données MySQL (l'utilisateur doit pouvoir créer la base et les tables au premier démarrage)

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # Linux/macOS

pip install -r requirements.txt
```

Copiez `.env.example` en `.env` et renseignez vos identifiants (voir le tableau [Configuration](#configuration)).

## Lancer le bot

Depuis la racine du projet :

```bash
python src/main.py
```

Une configuration de lancement VS Code (`.vscode/launch.json`) est déjà fournie ("Run bot").

## Docker

> ⚠️ La configuration Docker (`docker/`) est encore basée sur MongoDB et doit être migrée vers MySQL — voir le suivi Notion.

## Structure du projet

```
src/
├── main.py              # Point d'entrée (setup DB, handlers, boucle d'alerte, start)
├── cache/               # Cache local des réponses API (ignoré par git)
├── cogs/                # Slash commands (leak.py -> /lastleak, /leaks, /setupchannel, /unlinkchannel ; sync.py -> *sync)
├── components/          # db.py, leak.py (boucle d'alerte), embeds.py, load_cogs.py, set_interval.py
├── handlers/            # Événements Discord (on_ready, on_error, erreurs de commandes)
├── leak/                # Client HTTP de l'API FrenchBreaches (api.py) + cache
└── types/               # Modèles Pydantic + client Discord custom (CustomClient)
docker/                  # (à migrer) image et compose pour le bot + la base
```

## Configuration

Variables d'environnement dans `.env` :

| Variable        | Requis | Description                                                        |
| --------------- | ------ | ------------------------------------------------------------------ |
| `TOKEN`         | ✅     | Token du bot Discord                                              |
| `DEV_GUILD_ID`  | ❌     | ID d'un serveur de test → sync **instantané** des commandes. Vide en prod (sync global). |
| `MYSQL_USER`    | ✅     | Utilisateur MySQL                                                 |
| `MYSQL_PASS`    | ✅     | Mot de passe MySQL                                                |
| `MYSQL_HOST`    | ✅     | Hôte MySQL                                                        |
| `MYSQL_PORT`    | ❌     | Port MySQL (défaut : 3306)                                        |
| `MYSQL_DB`      | ❌     | Nom de la base (défaut : `frenchbreach_bot`)                      |
| `MYSQL_CA`      | ❌     | Chemin du certificat CA (active le SSL si renseigné)              |
| `MYSQL_CERT`    | ❌     | Chemin du certificat client                                       |
| `SSL_KEY`       | ❌     | Chemin de la clé privée client                                    |

## Tests

```bash
pytest
```

## Licence

Ce projet est distribué sous licence [MIT](LICENSE). Vous êtes libre de l'utiliser, le modifier et le redistribuer, tant que la notice de copyright est conservée.
