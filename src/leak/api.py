import asyncio
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import httpx
from diskcache import Cache

try:
    from ..types.leak import DetailLeak, Leak
except ImportError:
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from src.types.leak import DetailLeak, Leak

BASE_URL = "https://frenchbreaches.com/api/bot.php"

cache_dir: Path = Path(__file__).resolve().parents[1] / "cache"
cache: Cache = Cache(str(cache_dir))

CACHE_TTL_BY_ACTION: dict[str, int] = {
    "fuite": 120,  # 2 min — recherche, peut évoluer si nouvelles fuites
    "dernieres": 60,  # 1 min — doit rester réactif pour le mode alerte
    "detail": 1800,  # 30 min — contenu figé une fois publié
    "stats": 300,  # 5 min — change lentement
}

# Paramètres "texte libre" qu'on normalise (les autres — since, id, limit — sont
# structurés et ne doivent pas être touchés).
_TEXT_PARAMS: frozenset[str] = frozenset({"q", "sector"})

# Leetspeak *minimal* : uniquement des symboles qui ne peuvent jamais faire
# partie d'un nom d'entreprise réel. Les chiffres (0 1 3 4 5 7 8) sont exclus
# volontairement : les substituer casserait des marques comme TF1, C8, M6, 3M
# (elles fusionneraient avec du bruit dans le cache).
_LEET_MAP: dict[int, str] = str.maketrans({"@": "a", "$": "s", "€": "e", "£": "l"})


def _normalize_text(value: str) -> str:
    """Réduit une requête utilisateur à une forme canonique : deux variantes
    "équivalentes" (casse, accents, espaces, ponctuation, caractères invisibles,
    répétitions) produisent la même chaîne — donc la même entrée de cache et la
    même requête envoyée à l'API."""
    # 1. NFKC : plie les caractères de compatibilité — pleine chasse "ＦＲＥＥ",
    #    ligatures "ﬀ", exposants, espace insécable -> espace normale...
    text = unicodedata.normalize("NFKC", value)

    # 2. casefold : minuscule "agressive" et compatible Unicode (ß -> ss...).
    text = text.casefold()

    # 3. Supprime les caractères de contrôle / format invisibles (catégorie
    #    Unicode commençant par "C") : espace zéro-largeur, BOM, soft-hyphen,
    #    marques de direction RTL/LTR — des grands classiques du contournement.
    text = "".join(ch for ch in text if unicodedata.category(ch)[0] != "C")

    # 4. Retire les accents : décomposition NFD puis suppression des diacritiques
    #    combinants (catégorie "Mn"). "é"->"e", "ç"->"c". L'API FrenchBreaches
    #    est elle-même insensible aux accents (cf. bot_api.md).
    text = "".join(
        ch
        for ch in unicodedata.normalize("NFD", text)
        if unicodedata.category(ch) != "Mn"
    )

    # 5. Leetspeak symbolique (voir _LEET_MAP). Fait AVANT l'étape 6 pour que
    #    "@"/"$" deviennent des lettres au lieu d'être écrasés en espace.
    text = text.translate(_LEET_MAP)

    # 6. Tout ce qui n'est pas [a-z0-9] devient un séparateur : ponctuation,
    #    emoji, et scripts non-latins (un "а" cyrillique dans "аpple" est isolé
    #    ici plutôt que confondu avec le "a" latin).
    text = re.sub(r"[^a-z0-9]+", " ", text)

    # 7. Espaces multiples -> un seul, bords rognés.
    text = re.sub(r"\s+", " ", text).strip()

    # 8. Recolle les suites de lettres isolées : "f r e e" -> "free",
    #    "s f r" -> "sfr". Contre l'évasion "j'espace mes lettres".
    text = re.sub(r"(?<=\b\w) (?=\w\b)", "", text)

    # 9. Répétitions de 3 caractères ou plus ramenées à 2 : "freeeee" -> "free".
    #    On garde 2 (et pas 1) pour que "free" et "freeeee" convergent SANS
    #    abîmer les doublons légitimes ("google", "coop" restent intacts).
    text = re.sub(r"(.)\1{2,}", r"\1\1", text)

    # 10. Jette les jetons d'un seul caractère restants (résidus d'apostrophe /
    #     ponctuation : "l'oreal" -> "l oreal" -> "oreal").
    return " ".join(tok for tok in text.split() if len(tok) > 1)


def _canonical_params(params: dict[str, Any]) -> dict[str, Any]:
    """Applique _normalize_text aux paramètres texte, en gardant une valeur
    non vide (repli sur la version simplement 'strip'ée) pour ne pas envoyer un
    paramètre vide à l'API."""
    out: dict[str, Any] = {}
    for key, value in params.items():
        if value is None:
            continue
        if key in _TEXT_PARAMS:
            value = _normalize_text(str(value)) or str(value).strip().casefold()
        out[key] = value
    return out


def _cache_key(action: str, params: dict[str, Any]) -> str:
    # `params` est déjà canonique (cf. _canonical_params) : on se contente d'un
    # hash déterministe.
    serialized: str = json.dumps(params, sort_keys=True, default=str)
    hashed: str = hashlib.sha256(serialized.encode()).hexdigest()[:16]
    return f"api:{action}:{hashed}"


class FrenchBreachesRateLimitError(Exception):
    def __init__(self, retry: int = 3600) -> None:
        self.retry = retry
        super().__init__(f"Rate limit exceeded : {retry}")


class FrenchBreachesError(Exception):
    def __init__(self, payload: str):
        self.payload = payload
        super().__init__(f"FrenchBreaches API Error : {payload}")


class FrenchBreachesClient:
    # Attribut de classe : le client HTTP est créé paresseusement au premier
    # appel. Ça permet aussi de le remplacer facilement par un mock en test.
    _client: httpx.AsyncClient | None = None

    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=BASE_URL, timeout=10)
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _get(self, action: str, **params: Any) -> dict:
        # Forme canonique unique : sert À LA FOIS de clé de cache et de requête
        # réseau. Indispensable pour que "fr€€!" et "Free" tapent le même cache
        # ET interrogent l'API à l'identique (sinon une requête "trollée" peut
        # empoisonner l'entrée de cache d'une requête honnête).
        clean_params = _canonical_params(params)

        key = _cache_key(action, clean_params)

        cached = await asyncio.to_thread(cache.get, key)
        if cached is not None:
            return cached

        query: dict[str, Any] = {"action": action, **clean_params}

        resp: httpx.Response = await self._http().get("", params=query)

        if resp.status_code == 429:
            try:
                retry: int = resp.json().get("retry_after") or 3600
            except ValueError:
                retry = 3600
            raise FrenchBreachesRateLimitError(retry)

        if resp.status_code >= 400:
            try:
                message = resp.json().get("error")
            except ValueError:
                message: str = f"HTTP {resp.status_code}"

            raise FrenchBreachesError(message)

        try:
            data = resp.json()
        except ValueError as err:
            raise FrenchBreachesError(
                f"Réponse non-JSON (HTTP {resp.status_code})"
            ) from err

        # Certaines API renvoient 200 + {"success": false} : on ne met pas ça
        # en cache, sinon on sert l'erreur pendant tout le TTL.
        if isinstance(data, dict) and data.get("success") is False:
            raise FrenchBreachesError(data.get("error") or "Requête refusée par l'API")

        ttl: int = CACHE_TTL_BY_ACTION.get(action, 60)
        await asyncio.to_thread(cache.set, key, data, ttl)

        return data

    async def search(self, query: str, sector: str | None = None) -> list[Leak]:
        raw: dict[Any, Any] = await self._get("fuite", q=query, sector=sector)
        return [Leak.model_validate(item) for item in raw.get("data") or []]

    async def detail(self, id: str) -> DetailLeak | None:
        raw: dict[Any, Any] = await self._get("detail", id=id)
        data = raw.get("data")
        # /detail renvoie une seule fuite, mais l'API l'enveloppe parfois dans
        # une liste (comme les autres endpoints).
        if isinstance(data, list):
            data = data[0] if data else None
        return DetailLeak.model_validate(data) if data else None

    async def latest(
        self, limit: int = 10, since: str | None = None, sector: str | None = None
    ) -> list[Leak]:
        raw: dict[Any, Any] = await self._get(
            "dernieres", limit=25, since=since, sector=sector
        )
        leaks: list[Leak] = [
            Leak.model_validate(item) for item in raw.get("data") or []
        ]
        # En mode alerte (since), on veut toutes les fuites remontées, pas une
        # troncature arbitraire. Sinon on respecte la limite demandée.
        return leaks if since else leaks[:limit]

    async def stats(self) -> dict:
        return await self._get("stats")
