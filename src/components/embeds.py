import re
from datetime import datetime

import discord

try:
    from ..types.fuite import Article, ArticlesResponse
except ImportError:
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parents[2]))

    from src.types.fuite import Article, ArticlesResponse


def get_first_paragraph(text: str | None, fallback_length: int = 300) -> str:
    if text is None:
        return ""

    lines = text.split("\n")
    candidates = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):  # ignore les titres Markdown
            continue
        if stripped.startswith(">"):  # ignore les citations
            continue
        if re.match(r"^[-#*_]{3,}$", stripped):  # ignore les séparateurs ---
            continue
        candidates.append(stripped)

    if not candidates:
        return ""

    first = candidates[0]

    # Nettoyage du markdown inline restant
    first = re.sub(r"\*\*(.+?)\*\*", r"\1", first)  # **gras** -> gras
    first = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", first)  # [texte](lien) -> texte

    if len(first) > fallback_length:
        first = first[:fallback_length].rsplit(" ", 1)[0] + "..."

    return first


def leak_embed(
    title: str,
    url: str,
    logo: str,
    description: str | None = None,
    volume: float = 0,
    date: str | None = None,
    status: str | None = None,
    affected_count: int = 0,
    data_types: list[str] | None = None,
    footer: str | None = None,
) -> discord.Embed:

    embed = discord.Embed(
        title=f"{title}",
        url=url,
        description=get_first_paragraph(description),
        color=discord.Color(0xFF2C2C),
    )

    logo_url: str = f"https://frenchbreaches.com/{re.sub(r'^(\.\./?)+', '', logo)}"

    embed.set_thumbnail(url=logo_url)

    if volume is not None and volume != 0:
        embed.add_field(name="volume", value=f"{volume}Gb", inline=False)

    if status is not None:
        embed.add_field(name="status", value=status, inline=False)

    if affected_count != 0:
        embed.add_field(name="Affected Count", value=f"{affected_count}", inline=False)

    if data_types:
        data_list = "\n".join(f"- {t}" for t in data_types if t)
        embed.add_field(name="data leak", value=data_list, inline=False)

    if date is not None:
        leaked_date: datetime = datetime.fromisoformat(date)
        embed.timestamp = leaked_date

    if footer is not None:
        embed.set_footer(text=footer)

    return embed


class LeakListView(discord.ui.View):
    def __init__(
        self,
        leak_data: ArticlesResponse,
    ) -> None:
        super().__init__(timeout=None)
        self.leak_list: list[Article] = leak_data.articles
        self.total: int = len(self.leak_list)
        self.stage = 0

        if self.total <= 1:
            self.previous.disabled = True
            self.next.disabled = True

    def set_embed(self) -> discord.Embed:
        leak = self.leak_list[self.stage]
        return leak_embed(
            title=leak.title,
            url=leak.shortUrl,
            logo=leak.logo,
            volume=leak.dataVolumeGb,
            date=leak.date,
            status=leak.breachStatus,
            affected_count=leak.affectedCount,
            data_types=leak.dataTypes,
            footer=f"{self.stage + 1} / {self.total}",
            description=leak.description,
        )

    @discord.ui.button(emoji="⬅️", style=discord.ButtonStyle.secondary)
    async def previous(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.stage = (self.stage - 1) % self.total
        await interaction.response.edit_message(embed=self.set_embed(), view=self)

    @discord.ui.button(emoji="➡️", style=discord.ButtonStyle.secondary)
    async def next(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.stage = (self.stage + 1) % self.total
        await interaction.response.edit_message(embed=self.set_embed(), view=self)
