"""
apifootball.py — Cliente de API-Football (api-sports.io) con caché en disco.

Por que así:
  - API-Football (plan FREE) dá 100 peticións/día. Cacheando en disco, unha web de
    uso persoal non se achega nin de lonxe ao límite: clasificación e resultados
    cámbianse 1 vez por semana, así que se garda a resposta e reutilízase.
  - Modo MOCK: mentres non teñas a chave (ou para desenvolver sen gastar cota), o
    cliente devolve datos simulados co mesmo formato. Cámbiase cunha variable.

Uso:
    client = ApiFootball(api_key="a túa chave")          # modo real
    client = ApiFootball(api_key=None, mock=True)          # modo mock (desenvolvemento)
    standings = client.standings(league=SPAIN_1RFEF_G1, season=2026)

Config real:
  - Endpoint base: https://v3.football.api-sports.io
  - Cabeceira: x-apisports-key: <chave>
  - A chave gárdase en variable de entorno API_FOOTBALL_KEY (NUNCA no código).

IDs (a confirmar no dashboard de API-Football cando teñas conta; poño placeholders):
  - SPAIN_1RFEF_G1: id da liga "Primera Federación - Group 1"
"""

from __future__ import annotations
import json
import time
import hashlib
import os
from pathlib import Path
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

BASE_URL = "https://v3.football.api-sports.io"
CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "api_cache"
CACHE_TTL = 6 * 3600  # 6 horas por defecto; a clasificación cambia semanalmente

# Placeholder: substituír polo id real do dashboard de API-Football.
SPAIN_1RFEF_G1 = 435  # EXEMPLO — confirmar id real
SEASON = 2026


class ApiFootball:
    def __init__(self, api_key: str | None = None, mock: bool = False,
                cache_ttl: int = CACHE_TTL):
        self.api_key = api_key or os.environ.get("API_FOOTBALL_KEY")
        self.mock = mock or not self.api_key
        self.cache_ttl = cache_ttl
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------- caché ----
    def _cache_path(self, endpoint: str, params: dict) -> Path:
        key = endpoint + "?" + "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        h = hashlib.md5(key.encode()).hexdigest()[:16]
        return CACHE_DIR / f"{endpoint.replace('/', '_')}_{h}.json"

    def _get_cached(self, path: Path):
        if path.exists() and (time.time() - path.stat().st_mtime) < self.cache_ttl:
            return json.loads(path.read_text(encoding="utf-8"))
        return None

    # ---------------------------------------------------------- petición -----
    def _request(self, endpoint: str, params: dict) -> dict:
        """Petición GET con caché. En modo mock, delega en el generador mock."""
        cache_path = self._cache_path(endpoint, params)
        cached = self._get_cached(cache_path)
        if cached is not None:
            return cached

        if self.mock:
            data = _mock_response(endpoint, params)
        else:
            url = f"{BASE_URL}/{endpoint}?" + "&".join(f"{k}={v}" for k, v in params.items())
            req = urlrequest.Request(url, headers={"x-apisports-key": self.api_key})
            try:
                with urlrequest.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode())
            except (HTTPError, URLError) as e:
                # degradación elegante: se hai caché vella, úsase; se non, erro claro
                if cache_path.exists():
                    return json.loads(cache_path.read_text(encoding="utf-8"))
                raise RuntimeError(f"API-Football fallou ({e}) e non hai caché.") from e

        cache_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return data

    # ----------------------------------------------------------- endpoints ---
    def standings(self, league: int = SPAIN_1RFEF_G1, season: int = SEASON) -> dict:
        return self._request("standings", {"league": league, "season": season})

    def fixtures(self, league: int = SPAIN_1RFEF_G1, season: int = SEASON) -> dict:
        return self._request("fixtures", {"league": league, "season": season})

    def players(self, team: int, season: int = SEASON) -> dict:
        return self._request("players", {"team": team, "season": season})

    def league_coverage(self, league: int = SPAIN_1RFEF_G1, season: int = SEASON) -> dict:
        """Comproba QUE datos ten dispoñibles a liga (importante en 1ª RFEF)."""
        return self._request("leagues", {"id": league, "season": season})


# ------------------------------------------------- respostas mock (desenv.) --
def _mock_response(endpoint: str, params: dict) -> dict:
    """Devolve datos co MESMO formato que API-Football, para desenvolver sen chave."""
    if endpoint == "standings":
        return _mock_standings()
    if endpoint == "fixtures":
        return {"response": []}
    if endpoint == "players":
        return {"response": []}
    if endpoint == "leagues":
        return {"response": [{"league": {"id": params.get("id"), "name": "Primera Federación - Group 1"},
                              "seasons": [{"year": SEASON, "coverage": {
                                  "standings": True, "players": True, "fixtures": {"events": True,
                                  "lineups": True, "statistics_fixtures": False, "statistics_players": False}}}]}]}
    return {"response": []}


def _mock_standings() -> dict:
    """Clasificación mock co formato real de API-Football (response[0].league.standings)."""
    teams = [
        "SD Ponferradina", "Racing Ferrol", "AD Mérida", "Zamora CF", "Pontevedra CF",
        "UD Ourense", "CD Extremadura", "Bilbao Athletic", "CP Cacereño", "CD Mirandés",
        "Barakaldo CF", "CyD Leonesa", "Real Avilés", "Real Unión", "RC Deportivo Fabril",
        "UD Logroñés", "Unionistas", "CD Coria", "CD Lugo", "Arenas Club",
    ]
    rows = []
    for i, t in enumerate(teams):
        pts = 20 - i
        rows.append({
            "rank": i + 1,
            "team": {"id": 1000 + i, "name": t, "logo": f"https://media.api-sports.io/football/teams/{1000+i}.png"},
            "points": pts,
            "goalsDiff": 8 - i,
            "all": {"played": 8, "win": max(0, 6 - i // 3), "draw": 2, "lose": i // 3,
                    "goals": {"for": 15 - i // 2, "against": 6 + i // 2}},
            "form": ["W", "W", "D", "L", "W"][i % 5:] + ["W", "W", "D", "L", "W"][:i % 5],
        })
    return {"response": [{"league": {"id": SPAIN_1RFEF_G1, "name": "Primera Federación - Group 1",
                                     "season": SEASON, "standings": [rows]}}]}
