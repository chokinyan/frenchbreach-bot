import os
from datetime import datetime, timezone

import mysql.connector
from mysql.connector import errorcode
from mysql.connector.aio import connect

try:
    from ..types.customBot import CustomClient
except ImportError:
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from src.types.customBot import CustomClient

DB_NAME: str = os.getenv("MYSQL_DB") or "frenchbreach_bot"

GUILDS_TABLE: str = "guilds_config"
STATE_TABLE: str = "bot_state"
SENT_LEAKS_TABLE: str = "sent_leaks"

# `guilds_id` et `auto_send_channel` sont des snowflakes Discord (64 bits) :
# un INT signé MySQL (max 2 147 483 647) déborde -> BIGINT UNSIGNED obligatoire.
TABLES: dict[str, str] = {
    GUILDS_TABLE: (
        f"CREATE TABLE IF NOT EXISTS `{GUILDS_TABLE}` ("
        "`guilds_id` BIGINT UNSIGNED NOT NULL,"
        "`auto_send_channel` BIGINT UNSIGNED,"
        "PRIMARY KEY (`guilds_id`)"
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
    ),
    # Clé/valeur pour l'état du bot (ex. `last_seen` du mode alerte),
    # afin de survivre à un redémarrage.
    STATE_TABLE: (
        f"CREATE TABLE IF NOT EXISTS `{STATE_TABLE}` ("
        "`k` VARCHAR(64) NOT NULL,"
        "`v` TEXT,"
        "PRIMARY KEY (`k`)"
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
    ),
    # Fuites déjà annoncées : déduplication indépendante de `since`
    # (fenêtre temporelle sensible aux décalages d'horloge).
    SENT_LEAKS_TABLE: (
        f"CREATE TABLE IF NOT EXISTS `{SENT_LEAKS_TABLE}` ("
        "`leak_id` VARCHAR(128) NOT NULL,"
        "`sent_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,"
        "PRIMARY KEY (`leak_id`)"
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
    ),
}


async def setup_db(client: CustomClient) -> None:
    config: dict[str, object] = {
        "user": os.getenv("MYSQL_USER"),
        "password": os.getenv("MYSQL_PASS"),
        "host": os.getenv("MYSQL_HOST"),
    }

    if os.getenv("MYSQL_PORT"):
        config["port"] = int(os.getenv("MYSQL_PORT"))

    if os.getenv("MYSQL_CA") is not None:
        from mysql.connector.constants import ClientFlag

        config.update(
            {
                "ssl_ca": os.getenv("MYSQL_CA"),
                "client_flags": [ClientFlag.SSL],
                "ssl_cert": os.getenv("MYSQL_CERT"),
                "ssl_key": os.getenv("SSL_KEY"),
            }
        )

    try:
        client.mysql_client = await connect(**config)
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            raise RuntimeError(
                "Identifiants MySQL invalides (MYSQL_USER / MYSQL_PASS)"
            ) from err
        raise

    cursor = await client.mysql_client.cursor()
    try:
        try:
            await cursor.execute(f"USE `{DB_NAME}`")
        except mysql.connector.Error as err:
            if err.errno != errorcode.ER_BAD_DB_ERROR:
                raise
            client.logger["database"].info(f"Database {DB_NAME} does not exist, creating it.")
            await cursor.execute(
                f"CREATE DATABASE `{DB_NAME}` DEFAULT CHARACTER SET utf8mb4"
            )
            # `USE` doit être rejoué : sans ça les CREATE TABLE suivants
            # tournent sans base sélectionnée.
            await cursor.execute(f"USE `{DB_NAME}`")
            client.logger["database"].info(f"Database {DB_NAME} created successfully.")

        for table_name, table_ddl in TABLES.items():
            client.logger["database"].info(f"Creating table {table_name}...")
            try:
                await cursor.execute(table_ddl)
                client.logger["database"].info("OK")
            except mysql.connector.Error as err:
                if err.errno == errorcode.ER_TABLE_EXISTS_ERROR:
                    client.logger["database"].info("already exists.")
                else:
                    raise
    finally:
        await cursor.close()

    client.guilds_table = GUILDS_TABLE
    client.state_table = STATE_TABLE
    client.sent_leaks_table = SENT_LEAKS_TABLE


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


async def load_last_seen(client: CustomClient) -> str:
    """Reprend le `last_seen` persisté, ou l'instant présent au premier
    démarrage (on n'annonce pas rétroactivement tout l'historique)."""
    async with client.db_lock:
        cursor = await client.mysql_client.cursor()
        try:
            await cursor.execute(
                f"SELECT v FROM `{STATE_TABLE}` WHERE k = %s", ("last_seen",)
            )
            row = await cursor.fetchone()
        finally:
            await cursor.close()

    if row and row[0]:
        return row[0]
    return _utc_now_iso()
