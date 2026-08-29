import asyncio
import os

import discord
from discord.abc import GuildChannel
from dotenv import load_dotenv
from pymongo import AsyncMongoClient
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.server_api import ServerApi

import components.loadsCogs as cogs
import fuite.fuite as fuite_processor
import handlers.handlers as setup_event_handlers
from src.components.embeds import leak_embed
from src.components.setInterval import SetInterval
from src.fuite.fuite import check_new_leak
from src.types.customBot import CustomClient
from src.types.db import database_model

intents = discord.Intents.default()
intents.message_content = True
client = CustomClient(command_prefix="*", intents=intents)


async def send_new_leak(client: CustomClient) -> None:

    new_leaks = await check_new_leak()

    print("checking ...")

    if new_leaks is None:
        print("Nothing found")
        return

    guilds_channels = await client.collection.find().to_list(length=None)

    print("new check with leaks")

    for information in guilds_channels:
        channel_id = information["channel_id"]
        guild_id = information["guild_id"]

        guild: discord.Guild | None = client.get_guild(guild_id)
        if guild is None:
            print(f"Guild not found : {guild_id}")
            continue

        channel: GuildChannel | None = guild.get_channel(channel_id)
        if channel is None:
            print(f"Channel not found for guild : {guild_id}")
            continue

        for leak in new_leaks:
            embed: discord.Embed = leak_embed(
                title=leak.title,
                url=leak.shortUrl,
                logo=leak.logo,
                volume=leak.dataVolumeGb,
                date=leak.date,
                status=leak.breachStatus,
                affected_count=leak.affectedCount,
                data_types=leak.dataTypes,
            )

            await channel.send(embed=embed)

    await fuite_processor.write_leak_list()


async def main() -> None:
    load_dotenv()

    mongo_uri: str | None = os.getenv("MONGO_URL")
    mongo_db: str | None = os.getenv("MONGO_DB")
    mongo_collection: str | None = os.getenv("MONGO_COLLECTION")

    if not mongo_uri or not mongo_db or not mongo_collection:
        raise ValueError("MONGO_URL, MONGO_DB and MONGO_COLLECTION must be defined")

    mongo_client: AsyncMongoClient = AsyncMongoClient(
        mongo_uri, server_api=ServerApi("1")
    )

    try:
        await mongo_client.admin.command("ping")
        print("Pinged your deployment. You successfully connected to MongoDB!")
    except Exception as e:  # noqa: BLE001
        print(e)

    database: AsyncDatabase = mongo_client[mongo_db]
    collection: AsyncCollection[database_model] = database[mongo_collection]

    client.collection = collection

    setup_event_handlers.setup_handlers(client)

    SetInterval(60*30, send_new_leak, client, event_loop=asyncio.get_running_loop())

    await cogs.load_extensions(client)
    await fuite_processor.write_leak_list()
    await client.start(os.getenv("TOKEN"))


if __name__ == "__main__":
    asyncio.run(main())
