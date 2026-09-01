"""
Suite de tests pour src/leak/api.py.

Exécution :
    pytest tests/test_leak.py -v
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from diskcache import Cache

try:
    from src.leak import api
    from src.types.leak import DetailLeak, Leak
except ImportError:
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from src.leak import api
    from src.types.leak import DetailLeak, Leak


def make_leak_payload(id_: str = "abc123", **overrides: Any) -> dict[str, Any]:
    base = {
        "id": id_,
        "title": "Free",
        "description": "5,1 millions de personnes",
        "date": "2024-10-25",
        "affected_count": 5_100_000,
        "data_volume_gb": None,
        "source": "test-source",
        "sector": "telecom",
        "data_types": ["Adresse e-mail", "IBAN"],
        "url": "https://frenchbreaches.com/alertes/free",
        "short_url": "https://frenchbreaches.com/r/xyz",
    }
    base.update(overrides)
    return base


def make_api_response(
    action: str, data: list[dict] | dict | None, success: bool = True
) -> dict[str, Any]:
    return {
        "success": success,
        "endpoint": action,
        "count": len(data) if isinstance(data, list) else (1 if data else 0),
        "data": data,
        "generated_at": "2026-08-30T12:00:00Z",
    }


class FakeHTTPResponse:
    def __init__(self, payload: dict[str, Any], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> dict[str, Any]:
        return self._payload


def install_fake_client(
    monkeypatch: pytest.MonkeyPatch,
    payload: dict[str, Any],
    status_code: int = 200,
) -> MagicMock:
    fake_response = FakeHTTPResponse(payload, status_code=status_code)
    fake_get = AsyncMock(return_value=fake_response)

    monkeypatch.setattr(
        api.FrenchBreachesClient,
        "_client",
        MagicMock(get=fake_get),
        raising=False,
    )
    return fake_get


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    test_cache = Cache(str(tmp_path / "cache"))
    monkeypatch.setattr(api, "cache", test_cache)
    yield test_cache
    test_cache.close()


@pytest.fixture
def client() -> api.FrenchBreachesClient:
    return api.FrenchBreachesClient()


# --- search() ---


@pytest.mark.asyncio
async def test_search_returns_valid_leaks(monkeypatch, client) -> None:
    payload = make_api_response(
        "fuite", [make_leak_payload(), make_leak_payload(id_="def456")]
    )
    install_fake_client(monkeypatch, payload)

    results = await client.search("free")

    assert len(results) == 2
    assert isinstance(results[0], Leak)
    assert results[0].title == "Free"


@pytest.mark.asyncio
async def test_search_returns_empty_list_when_no_data(monkeypatch, client) -> None:
    payload = make_api_response("fuite", data=[])
    install_fake_client(monkeypatch, payload)

    results = await client.search("entreprise-inconnue-xyz")

    assert results == []


# --- detail() ---


@pytest.mark.asyncio
async def test_detail_returns_detail_leak_with_extra_fields(
    monkeypatch, client
) -> None:
    payload = make_api_response(
        "detail",
        make_leak_payload(
            header_image="https://x.com/header.png", logo="https://x.com/logo.png"
        ),
    )
    install_fake_client(monkeypatch, payload)

    result = await client.detail("abc123")

    assert result is not None
    assert isinstance(result, DetailLeak)
    assert result.header_image == "https://x.com/header.png"
    assert result.logo == "https://x.com/logo.png"


@pytest.mark.asyncio
async def test_detail_returns_none_when_not_found(monkeypatch, client) -> None:
    payload = make_api_response("detail", data=None)
    install_fake_client(monkeypatch, payload)

    result = await client.detail("id-inexistant")

    assert result is None


# --- latest() ---


@pytest.mark.asyncio
async def test_latest_truncates_to_requested_limit(monkeypatch, client) -> None:
    payload = make_api_response(
        "dernieres", [make_leak_payload(id_=str(i)) for i in range(25)]
    )
    install_fake_client(monkeypatch, payload)

    results = await client.latest(limit=3)

    assert len(results) == 3


@pytest.mark.asyncio
async def test_latest_always_requests_25_regardless_of_limit(
    monkeypatch, client
) -> None:
    payload = make_api_response("dernieres", [make_leak_payload()])
    fake_get = install_fake_client(monkeypatch, payload)

    await client.latest(limit=1)

    called_params = fake_get.call_args.kwargs["params"]
    assert called_params["limit"] == 25


# --- Rate limit / erreurs ---


@pytest.mark.asyncio
async def test_rate_limit_raises_with_retry_after(monkeypatch, client) -> None:
    payload = {"success": False, "error": "Too Many Requests", "retry_after": 42}
    install_fake_client(monkeypatch, payload, status_code=429)

    with pytest.raises(api.FrenchBreachesRateLimitError) as exc_info:
        await client.latest()

    assert exc_info.value.retry == 42


@pytest.mark.asyncio
async def test_rate_limit_defaults_retry_after_when_missing(
    monkeypatch, client
) -> None:
    payload = {"success": False, "error": "Too Many Requests"}  # pas de retry_after
    install_fake_client(monkeypatch, payload, status_code=429)

    with pytest.raises(api.FrenchBreachesRateLimitError) as exc_info:
        await client.latest()

    assert exc_info.value.retry == 3600  # valeur de secours


@pytest.mark.asyncio
async def test_client_error_raises_with_message(monkeypatch, client) -> None:
    payload = {"success": False, "error": "`q` must be between 2 and 80 characters"}
    install_fake_client(monkeypatch, payload, status_code=400)

    with pytest.raises(api.FrenchBreachesError, match="between 2 and 80"):
        await client.search("a")


# --- Cache ---


@pytest.mark.asyncio
async def test_second_identical_call_uses_cache(monkeypatch, client) -> None:
    payload = make_api_response("fuite", [make_leak_payload()])
    fake_get = install_fake_client(monkeypatch, payload)

    await client.search("free")
    await client.search("free")  # même query -> devrait taper le cache

    assert fake_get.call_count == 1


@pytest.mark.asyncio
async def test_different_params_bypass_cache(monkeypatch, client) -> None:
    payload = make_api_response("fuite", [make_leak_payload()])
    fake_get = install_fake_client(monkeypatch, payload)

    await client.search("free")
    await client.search("orange")  # query différente -> pas de cache

    assert fake_get.call_count == 2


@pytest.mark.asyncio
async def test_equivalent_query_variants_share_cache_key(monkeypatch, client) -> None:
    payload = make_api_response("fuite", [make_leak_payload()])
    fake_get = install_fake_client(monkeypatch, payload)

    await client.search("Free")
    await client.search("  frée  ")  # casse + accent + espaces
    await client.search("F R E E !!")  # ponctuation + espaces parasites
    await client.search("freeeeee")  # répétitions (>= 3)
    await client.search("fr€€")  # leet symbolique (€ -> e)

    assert fake_get.call_count == 1


@pytest.mark.asyncio
async def test_normalized_query_is_sent_to_the_api(monkeypatch, client) -> None:
    """La requête réseau est la forme canonique, pas la saisie brute :
    empêche une requête 'trollée' d'empoisonner le cache d'une requête honnête."""
    payload = make_api_response("fuite", [make_leak_payload()])
    fake_get = install_fake_client(monkeypatch, payload)

    await client.search("FRÉÉ !!!")

    assert fake_get.call_args.kwargs["params"]["q"] == "free"


@pytest.mark.asyncio
async def test_digits_in_names_are_not_leet_substituted(monkeypatch, client) -> None:
    """TF1 ne doit pas devenir "tfl" : les noms de marque à chiffres restent
    distincts (pas de fusion de cache avec du bruit)."""
    payload = make_api_response("fuite", [make_leak_payload()])
    fake_get = install_fake_client(monkeypatch, payload)

    await client.search("TF1")
    await client.search("TFL")

    assert fake_get.call_count == 2


@pytest.mark.asyncio
async def test_lastleak_and_leaks_share_same_cache_entry(monkeypatch, client) -> None:
    """/lastleak (limit=1) et /leaks (limit=25) doivent partager le cache,
    puisque latest() force toujours limit=25 en interne."""
    payload = make_api_response(
        "dernieres", [make_leak_payload(id_=str(i)) for i in range(25)]
    )
    fake_get = install_fake_client(monkeypatch, payload)

    await client.latest(limit=1)
    await client.latest(limit=25)

    assert fake_get.call_count == 1


@pytest.mark.asyncio
async def test_cache_respects_ttl_per_action(monkeypatch, client) -> None:
    monkeypatch.setitem(api.CACHE_TTL_BY_ACTION, "fuite", 1)
    payload = make_api_response("fuite", [make_leak_payload()])
    fake_get = install_fake_client(monkeypatch, payload)

    await client.search("free")
    await asyncio.sleep(1.5)
    await client.search("free")

    assert fake_get.call_count == 2  # cache expiré -> deuxième vrai appel


@pytest.mark.asyncio
async def test_errors_are_never_cached(monkeypatch, client) -> None:
    install_fake_client(
        monkeypatch, {"success": False, "error": "boom"}, status_code=500
    )

    with pytest.raises(api.FrenchBreachesError):
        await client.search("free")

    # Un deuxième appel doit retaper le réseau, pas servir une erreur en cache
    payload = make_api_response("fuite", [make_leak_payload()])
    fake_get = install_fake_client(monkeypatch, payload)

    results = await client.search("free")
    assert len(results) == 1
