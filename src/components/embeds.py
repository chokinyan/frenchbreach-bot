import re
from datetime import datetime

import discord

try:
    from src.types.fuite import ArticlesResponse
except ImportError:
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parents[2]))


def leak_embed(
    title: str,
    url: str,
    logo: str,
    volume: float = 0,
    date: str | None = None,
    status: str | None = None,
    affected_count: int = 0,
    data_types: list[str] | None = None,
    footer : str | None = None
) -> discord.Embed:

    embed = discord.Embed(title=f"{title}", url=url, color=discord.Color(0xFF2C2C))

    logo_url: str = f"https://frenchbreaches.com/{re.sub(r'^(\.\./?)+', '', logo)}"

    embed.set_thumbnail(url=logo_url)

    if volume is not None and volume != 0:
        embed.add_field(name="volume", value=f"{volume}Gb", inline=False)

    if status is not None:
        embed.add_field(name="status", value=status, inline=False)

    if affected_count != 0:
        embed.add_field(name="Affected Count", value=f"{affected_count}", inline=False)

    if data_types is not None and data_types.__len__() != 0:
        data_list = ",\n".join(data_types)
        embed.add_field(name="data leak", value=data_list, inline=False)

    if date is not None:
        leaked_date: datetime = datetime.fromisoformat(date)
        embed.timestamp = leaked_date
        
    if footer is not None:
        embed.set_footer(footer)

    return embed


class ComplexEmbed(discord.ui.View):
    def __init__(self, leak_data: ArticlesResponse,):
        super().__init__(timeout=None)
