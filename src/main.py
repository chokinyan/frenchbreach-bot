import asyncio
import logging
import os
from logging import Logger
from logging.handlers import RotatingFileHandler
from pathlib import Path

import discord
from dotenv import load_dotenv

# Doit tourner avant les imports applicatifs : certains modules lisent
# os.getenv(...) au niveau module, à l'import.
load_dotenv()

import components.load_cogs as cogs
import handlers.handlers as setup_event_handlers
from leak.api import FrenchBreachesClient
from src.components.db import load_last_seen, setup_db
from src.components.leak import send_new_leak
from src.components.set_interval import SetInterval
from src.types.customBot import CustomClient

intents = discord.Intents.default()
intents.message_content = True
client = CustomClient(command_prefix="*", intents=intents)

LOG_DIR = Path(__file__).resolve().parent / "log"

# Clé interne (client.logger[...]) -> nom du logger standard capturé dans le
# fichier. On se greffe sur les loggers de discord.py et du driver MySQL pour
# récupérer aussi leurs messages internes ; "frenchbreaches" = code applicatif.
_LOG_TARGETS: dict[str, str] = {
    "discord": "discord",
    "database": "mysql.connector",
    "api": "frenchbreaches",
}


def setup_logging() -> dict[str, Logger]:
    """Un logger par domaine, écrivant dans log/<clé>.log (rotation 1 Mo x3,
    en append) + la console. Retourne le mapping consommé par client.logger."""
    LOG_DIR.mkdir(exist_ok=True)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)-8s %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S"
    )
    console = logging.StreamHandler()
    console.setFormatter(formatter)

    loggers: dict[str, Logger] = {}
    for key, name in _LOG_TARGETS.items():
        file_handler = RotatingFileHandler(
            LOG_DIR / f"{key}.log",
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)

        log = logging.getLogger(name)
        log.setLevel(logging.INFO)
        log.addHandler(file_handler)
        log.addHandler(console)
        log.propagate = False  # pas de remontée au root (évite le double log)
        loggers[key] = log
    return loggers


async def main() -> None:
    token = os.getenv("TOKEN")
    if not token:
        raise RuntimeError(
            "La variable d'environnement TOKEN est absente (voir .env.example)"
        )

    client.logger.update(setup_logging())

    await setup_db(client)

    client.leak_client = FrenchBreachesClient()

    setup_event_handlers.setup_handlers(client)

    client.last_seen = await load_last_seen(client)
    SetInterval(60 * 5, send_new_leak, client, event_loop=asyncio.get_running_loop())

    await cogs.load_extensions(client)
    try:
        await client.start(token)
    finally:
        await client.leak_client.close()
        await client.mysql_client.close()


if __name__ == "__main__":
    asyncio.run(main())
