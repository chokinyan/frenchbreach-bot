import asyncio
import json
from datetime import datetime
from pathlib import Path

import httpx
from pydantic import ValidationError

try:
    from ..types.fuite import ArticlesResponse
except ImportError:
    # Allow running this file directly in debug mode.
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from src.types.fuite import ArticlesResponse

base_url: str = "https://frenchbreaches.com/api/articles_api.php?year="
json_path: Path = Path(__file__).resolve().parents[1] / "json" / "data.json"
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


async def get_leak(year: int = datetime.now().year) -> ArticlesResponse | None:  # noqa: DTZ005
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
    insert_data: ArticlesResponse | None = None,
) -> ArticlesResponse | None:
    data: ArticlesResponse | None = insert_data
    if data is None:
        data = await get_leak()
        if data is None:
            return
    json_path.open("w").close()
    string_info: str = data.model_dump_json().encode("utf-8")
    await asyncio.to_thread(json_path.write_bytes, string_info)
    print("fichier crée avec succès")
    return data


async def read_leak_list() -> ArticlesResponse | None:
    if not (json_path.exists()):
        data: ArticlesResponse | None = await write_leak_list()
        return data
    try:
        data: ArticlesResponse = ArticlesResponse.model_validate(
            json.loads(json_path.read_text("utf-8"))
        )
    except ValidationError as e:
        print(f"cant read correct data : {e}")
        return
    return data


async def check_new_leak() -> ArticlesResponse.articles | None:
    if not (json_path.exists()):
        print("Fichier data non existant !")
        return
    new_data: ArticlesResponse | None = await get_leak()
    old_data: ArticlesResponse | None = await read_leak_list()
    if new_data is None or old_data is None:
        print("Erreur lors de la récuperation des articles")
        return

    nb_difference: int = new_data.stats.count - old_data.stats.count

    if nb_difference != 0:
        await write_leak_list(new_data)
        return new_data.articles[0 : abs(nb_difference)]

    return
