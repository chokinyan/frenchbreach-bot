from discord.ext import commands


def setup_handlers(client: commands.Bot) -> None:
    @client.event
    async def on_ready() -> None:
        for guild in client.guilds:
            client.tree.copy_global_to(guild=guild)
            await client.tree.sync(guild=guild)
        print(f"bot pret : {client.user}")

    @client.event
    async def on_error(event, *args, **kwargs) -> None:
        print(event)
