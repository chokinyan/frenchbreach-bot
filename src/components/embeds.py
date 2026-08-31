import discord

try:
    from ..leak.api import (
        FrenchBreachesClient,
        FrenchBreachesError,
        FrenchBreachesRateLimitError,
    )
    from ..types.leak import DetailLeak, Leak
except ImportError:
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from src.leak.api import (
        FrenchBreachesClient,
        FrenchBreachesError,
        FrenchBreachesRateLimitError,
    )
    from src.types.leak import DetailLeak, Leak

# Discord limite la description d'un embed à 4096 caractères. L'endpoint
# /dernieres tronque déjà à 500 car., mais /detail renvoie le texte complet
# qui peut largement dépasser : on reclampe ici pour éviter un 400 (50035).
EMBED_DESCRIPTION_LIMIT = 4096


def _truncate(text: str, limit: int = EMBED_DESCRIPTION_LIMIT) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _safe_url(value: str | None) -> str | None:
    """Ne garde une URL que si Discord l'acceptera. Une URL malformée ou un
    chemin relatif dans `url` / `set_image` / `set_thumbnail` fait rejeter
    TOUT l'embed en HTTP 400 — on préfère un embed sans image qu'un échec."""
    if value and value.startswith(("http://", "https://")):
        return value
    return None


def _format_volume(gb: float) -> str:
    """Volume lisible : bascule en Mo sous 1 Go, en To au-delà de 1024 Go, et
    supprime les décimales inutiles ("12.00" -> "12", "1.50" -> "1.5")."""
    if gb < 1:
        return f"{round(gb * 1024)} Mo"
    value, unit = (gb / 1024, "To") if gb >= 1024 else (gb, "Go")
    text = f"{value:,.2f}".replace(",", " ").rstrip("0").rstrip(".")
    return f"{text} {unit}"


def leak_embed(leak: Leak, description: str | None = None) -> discord.Embed:

    color = 0xFF2C2C if leak.affected_count >= 1_000_000 else 0xE67E22

    # On passe un DetailLeak quand on veut le logo + la bannière, mais la
    # description affichée reste toujours le résumé court de /dernieres
    # (`description=...`) : la version longue de /detail est trop verbeuse.
    embed = discord.Embed(
        title=_truncate(leak.title, 256),
        url=_safe_url(leak.url),
        description=_truncate(
            description if description is not None else leak.description
        ),
        color=color,
    )

    # Champs présents uniquement sur DetailLeak (endpoint /detail)
    logo = _safe_url(getattr(leak, "logo", None))
    header_image = _safe_url(getattr(leak, "header_image", None))
    if logo:
        embed.set_thumbnail(url=logo)
    if header_image:
        embed.set_image(url=header_image)

    embed.add_field(
        name="Personnes concernées",
        value=f"{leak.affected_count:,}".replace(",", " ")
        if leak.affected_count
        else "Non communiqué",
        inline=True,
    )
    embed.add_field(name="Secteur", value=leak.sector or "Inconnu", inline=True)

    if leak.data_volume_gb:
        embed.add_field(
            name="Volume", value=_format_volume(leak.data_volume_gb), inline=True
        )

    if leak.data_types:
        embed.add_field(
            name="Types de données",
            value=", ".join(leak.data_types)[:1024],
            inline=False,
        )

    embed.set_footer(text=f"FrenchBreaches — {leak.date}")
    return embed


class LeakListView(discord.ui.View):
    """Pagination client-side sur un batch déjà récupéré (max 25 éléments).

    Chaque page est enrichie à la volée via /detail (description longue + logo
    + bannière) : un seul appel API par fuite consultée, mémorisé ensuite."""

    def __init__(
        self,
        leaks: list[Leak],
        author: discord.User | discord.Member,
        leak_client: FrenchBreachesClient,
        per_page: int = 1,
    ):
        super().__init__(timeout=120)
        self.leaks = leaks
        self.author = author
        self.leak_client = leak_client
        self.per_page = per_page
        self.page = 0
        self.total_pages = (len(leaks) - 1) // per_page + 1
        self.message: discord.Message | None = None
        self._details: dict[str, DetailLeak | None] = {}

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.author:
            await interaction.response.send_message(
                "Ce n'est pas ton menu !", ephemeral=True
            )
            return False
        return True

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        # Sans ça, les flèches restent visuellement cliquables et renvoient
        # "This interaction failed" une fois la vue expirée.
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass

    async def _enriched(self, leak: Leak) -> Leak:
        """Récupère le DetailLeak (pour logo + bannière) ; repli sur la fuite
        courte si /detail échoue."""
        if leak.id not in self._details:
            try:
                self._details[leak.id] = await self.leak_client.detail(leak.id)
            except (FrenchBreachesError, FrenchBreachesRateLimitError):
                self._details[leak.id] = None
        return self._details[leak.id] or leak

    async def current_embed(self) -> discord.Embed:
        base = self.leaks[self.page]
        enriched = await self._enriched(base)
        # enriched -> logo/bannière ; base.description -> résumé court conservé.
        embed = leak_embed(enriched, description=base.description)
        embed.set_footer(
            text=f"{embed.footer.text} • Page {self.page + 1}/{self.total_pages}"
        )
        return embed

    @discord.ui.button(emoji="⬅️", style=discord.ButtonStyle.secondary)
    async def previous(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.page = (self.page - 1) % self.total_pages
        # defer d'abord : l'enrichissement /detail peut dépasser les 3 s
        # allouées à une réponse d'interaction.
        await interaction.response.defer()
        await interaction.edit_original_response(
            embed=await self.current_embed(), view=self
        )

    @discord.ui.button(emoji="➡️", style=discord.ButtonStyle.secondary)
    async def next(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.page = (self.page + 1) % self.total_pages
        await interaction.response.defer()
        await interaction.edit_original_response(
            embed=await self.current_embed(), view=self
        )
