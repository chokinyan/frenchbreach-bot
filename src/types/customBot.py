import asyncio
from logging import Logger

from discord.ext import commands
from mysql.connector.aio.abstracts import MySQLConnectionAbstract
from mysql.connector.aio.pooling import PooledMySQLConnection

try:
    from ..leak.api import FrenchBreachesClient
except ImportError:
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from src.leak.api import FrenchBreachesClient


class CustomClient(commands.Bot):
    leak_client: FrenchBreachesClient | None = None
    last_seen: str | None = None
    mysql_client: MySQLConnectionAbstract | PooledMySQLConnection | None = None
    # Sérialise les accès MySQL : une seule connexion est partagée entre les
    # commandes et la boucle d'alerte, qui tournent sur le même event loop.
    db_lock: asyncio.Lock = asyncio.Lock()
    guilds_table: str | None = None
    state_table: str | None = None
    sent_leaks_table: str | None = None

    # Rempli par setup_logging() dans main.py. Clés : "discord", "database",
    # "api". Défini au niveau classe (comme db_lock) : un seul client existe.
    logger: dict[str, Logger] = {}
