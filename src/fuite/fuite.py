from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path

import httpx
from diskcache import Cache
from pydantic import ValidationError

try:
    from ..types.fuite import ArticlesResponse
except ImportError:
    # Allow running this file directly in debug mode.
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from src.types.fuite import ArticlesResponse

"""
Module de récupération et de mise en cache des articles de fuites de données
depuis l'API frenchbreaches.com.

Le cache est géré via `diskcache`, avec une expiration (TTL) automatique.
Le cache est partitionné par année : chaque année dispose de sa propre
clé de cache (`_cache_key(year)`), ce qui permet de conserver plusieurs
années en cache simultanément sans qu'elles s'écrasent entre elles.

Flux typique :
    1. `read_leak_list(year)` : lit le cache pour l'année donnée, ou le
       peuple si absent/expiré.
    2. `check_new_leak(year)` : compare le cache existant avec un nouveau
       fetch pour détecter les nouveaux articles publiés depuis la
       dernière écriture, pour l'année donnée.
"""

base_url: str = "https://frenchbreaches.com/api/articles_api.php?year="
cache_dir: Path = Path(__file__).resolve().parents[1] / "cache"
cache: Cache = Cache(str(cache_dir))

CACHE_KEY_PREFIX: str = "leak_data"

CACHE_TTL: int = 60 * 30  # 30 min

"""{
    "articles" : Array<
        {
            "id" : str,
            "title" : str,
            "description" : str,
            "date" : str,
            "source" : str,
            "logo" : str,
            "slug" : str,
            "status" : str,
            "is_scheduled" : int,
            "published_at" : ?,
            "seo_title" : str,
            "google_index_hash" : str,
            "dataTypes" : Array<str>,
            "affectedCount" : int,
            "dataVolumeGb" : ?,
            "headerImage" : str,
            "lastModified" : str,
            "breachStatus" : str,
            "shortUrl" : str
        }
    >,
    "pagination" : {
        "page" : int,
        "limit" : int,
        "total" : int,
        "pages" : int
    },
    "stats" : {
        "count" : int
    }
}"""


def _cache_key(year: int) -> str:
    return f"{CACHE_KEY_PREFIX}:{year}"


async def _get_leak(year: int = datetime.now().year) -> ArticlesResponse | None:  # noqa: DTZ005
    url: str = base_url + str(year)
    client = httpx.AsyncClient()

    rep = await client.get(url)

    await client.aclose()

    try:
        data: ArticlesResponse = ArticlesResponse.model_validate(rep.json())
    except ValidationError as e:
        print(f"erreur lors du parsing des data : {e}")
        return

    return data


async def write_leak_list(
        year: int = datetime.now().year,  # noqa: DTZ005
        insert_data: ArticlesResponse | None = None,
) -> ArticlesResponse | None:
    data: ArticlesResponse | None = insert_data
    if data is None:
        data = await _get_leak(year)
        if data is None:
            return None

    await asyncio.to_thread(cache.set, _cache_key(year), data, CACHE_TTL)
    print(f"cache mis à jour avec succès pour {year}")
    return data


async def read_leak_list(
        year: int = datetime.now().year,  # noqa: DTZ005
) -> ArticlesResponse | None:
    """Lit les données depuis le cache pour une année, en le peuplant si absent/expiré.

    Args:
        year: Année à lire depuis le cache. Par défaut, l'année en cours.

    Returns:
        Les données en cache si présentes et valides, sinon le résultat
        d'un nouvel appel API via `write_leak_list(year)`.
    """
    data: ArticlesResponse | None = await asyncio.to_thread(cache.get, _cache_key(year))
    return await write_leak_list(year) if data is None else data


async def check_new_leak(
        year: int = datetime.now().year,  # noqa: DTZ005
) -> list[ArticlesResponse] | None:
    """Compare les données en cache avec un nouveau fetch pour détecter les nouveautés.

    Ne fonctionne que si le cache est déjà peuplé pour l'année donnée (ne
    déclenche pas de premier fetch si le cache est vide). Si le nombre
    total d'articles (`stats.count`) diffère entre l'ancien et le nouveau
    fetch, le cache est mis à jour et les nouveaux articles sont retournés.

    Args:
        year: Année à vérifier. Par défaut, l'année en cours.

    Returns:
        La liste des nouveaux articles détectés si `stats.count` a changé,
        `None` si le cache est vide pour cette année, si le fetch échoue,
        ou si aucun changement n'est détecté.
    """
    old_data: ArticlesResponse | None = await asyncio.to_thread(cache.get, _cache_key(year))
    if old_data is None:
        print(f"Cache non existant pour {year} !")
        return None

    new_data: ArticlesResponse | None = await _get_leak(year)
    if new_data is None:
        print("Erreur lors de la récuperation des articles")
        return None

    nb_difference: int = new_data.stats.count - old_data.stats.count

    if nb_difference != 0:
        await write_leak_list(year, new_data)
        return new_data.articles[0: abs(nb_difference)]

    return None