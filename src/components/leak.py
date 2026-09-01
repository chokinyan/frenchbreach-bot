from datetime import datetime, timezone

import discord
from discord.abc import GuildChannel

try:
    from ..components.embeds import leak_embed
    from ..leak.api import FrenchBreachesError, FrenchBreachesRateLimitError
    from ..types.customBot import CustomClient
    from ..types.leak import Leak
except ImportError:
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from src.components.embeds import leak_embed
    from src.leak.api import FrenchBreachesError, FrenchBreachesRateLimitError
    from src.types.customBot import CustomClient
    from src.types.leak import Leak


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


async def _filter_already_sent(client: CustomClient, leaks: list[Leak]) -> list[Leak]:
    """Retire les fuites déjà annoncées (table `sent_leaks`)."""
    ids = [leak.id for leak in leaks]
    placeholders = ",".join(["%s"] * len(ids))

    async with client.db_lock:
        cursor = await client.mysql_client.cursor()
        try:
            await cursor.execute(
                f"SELECT leak_id FROM `{client.sent_leaks_table}` "
                f"WHERE leak_id IN ({placeholders})",
                tuple(ids),
            )
            known = {row[0] for row in await cursor.fetchall()}
        finally:
            await cursor.close()

    return [leak for leak in leaks if leak.id not in known]


async def _mark_sent(client: CustomClient, leaks: list[Leak]) -> None:
    async with client.db_lock:
        cursor = await client.mysql_client.cursor()
        try:
            await cursor.executemany(
                f"INSERT IGNORE INTO `{client.sent_leaks_table}` (leak_id) VALUES (%s)",
                [(leak.id,) for leak in leaks],
            )
            await client.mysql_client.commit()
        finally:
            await cursor.close()


async def _save_last_seen(client: CustomClient, value: str) -> None:
    async with client.db_lock:
        cursor = await client.mysql_client.cursor()
        try:
            await cursor.execute(
                f"INSERT INTO `{client.state_table}` (k, v) VALUES (%s, %s) "
                "ON DUPLICATE KEY UPDATE v = VALUES(v)",
                ("last_seen", value),
            )
            await client.mysql_client.commit()
        finally:
            await cursor.close()
    client.last_seen = value


async def send_new_leak(client: CustomClient) -> None:
    # Horodatage du poll (UTC ISO 8601) : sert de `since` au prochain appel.
    # On ne réutilise pas `leak.date` renvoyé par l'API : il est exprimé dans le
    # fuseau du site et dans un format non garanti (cf. bot_api.md §4).
    poll_started_at = _utc_now_iso()

    try:
        new_leaks = await client.leak_client.latest(since=client.last_seen, limit=25)
    except FrenchBreachesRateLimitError as e:
        client.logger["api"].warning(f"Rate limit atteint, retry dans {e.retry}s")
        return
    except FrenchBreachesError as e:
        client.logger["api"].warning(f"Erreur API : {e}")
        return

    # Déduplication par id : `since` seul (fenêtre temporelle) est sensible aux
    # bornes inclusives et aux décalages d'horloge.
    if new_leaks:
        new_leaks = await _filter_already_sent(client, new_leaks)

    if not new_leaks:
        await _save_last_seen(client, poll_started_at)
        client.logger["api"].info("Nothing new")
        return

    # L'API trie par date décroissante ; on repasse en ordre chronologique
    # pour un fil de lecture naturel.
    new_leaks = list(reversed(new_leaks))

    async with client.db_lock:
        cursor = await client.mysql_client.cursor(dictionary=True)
        try:
            await cursor.execute(
                f"SELECT guilds_id, auto_send_channel FROM `{client.guilds_table}`"
            )
            guilds_channels = await cursor.fetchall()
        finally:
            await cursor.close()

    # /detail = logo + bannière uniquement (on garde la description courte de
    # /dernieres). Construits une fois puis réutilisés pour chaque serveur ;
    # peu de nouvelles fuites par poll et /detail est mis en cache 30 min.
    embeds = []
    for leak in new_leaks:
        try:
            detail = await client.leak_client.detail(leak.id)
        except (FrenchBreachesError, FrenchBreachesRateLimitError) as e:
            client.logger["api"].info(f"Detail indisponible pour {leak.id} : {e}")
            detail = None
        embeds.append(leak_embed(detail or leak, description=leak.description))

    for information in guilds_channels:
        channel_id = information["auto_send_channel"]
        guild_id = information["guilds_id"]

        if channel_id is None:
            continue

        guild: discord.Guild | None = client.get_guild(guild_id)
        if guild is None:
            client.logger["discord"].warning(f"Guild not found : {guild_id}")
            continue

        channel: GuildChannel | None = guild.get_channel(channel_id)
        if channel is None:
            client.logger["discord"].warning(
                f"Channel not found for guild : {guild_id}"
            )
            continue

        for embed in embeds:
            try:
                await channel.send(embed=embed)
            except discord.DiscordException as e:
                # Un serveur qui échoue (permissions, salon supprimé) ne doit
                # pas empêcher les autres ni bloquer la mise à jour de l'état.
                client.logger["discord"].error(
                    f"Envoi impossible (guild {guild_id}, channel {channel_id}) : {e}"
                )
                break

    # Marque comme envoyées même si certains serveurs ont échoué : on ne veut
    # pas re-spammer tout le monde au prochain poll.
    await _mark_sent(client, new_leaks)
    await _save_last_seen(client, poll_started_at)
