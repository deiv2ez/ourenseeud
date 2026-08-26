"""
ingest.py — Ingesta: trae datos de API-Football e tradúceos ao formato interno.

Capa de illamento: o resto do proxecto (motor, API) NON coñece o formato de
API-Football. Só coñece o noso formato (o de store.py). Se algún día cambiamos de
provedor de datos, só se toca este ficheiro.

Fluxo:
    API-Football  →  ingest (traduce)  →  season_2026_27.json  →  motor / API

Correr manualmente (como acordou o usuario, de momento manual):
    python -m app.ingest            # modo mock
    API_FOOTBALL_KEY=xxx python -m app.ingest --real
"""

from __future__ import annotations
import sys

from .apifootball import ApiFootball
from .store import load, save, NAMES


# Mapa de nomes de API-Football → os nosos nomes canónicos.
# (Complétase cando teñamos os nomes exactos que devolve a API para o Grupo 1.)
NAME_MAP: dict[str, str] = {
    # "Ponferradina": "SD Ponferradina",  # exemplo
}


def _canon(name: str) -> str:
    """Normaliza o nome dun equipo ao noso canon."""
    if name in NAMES:
        return name
    return NAME_MAP.get(name, name)


def ingest_standings(client: ApiFootball) -> list[dict]:
    """Traduce a clasificación de API-Football a filas simples (para verificación)."""
    data = client.standings()
    rows = data["response"][0]["league"]["standings"][0]
    out = []
    for r in rows:
        out.append({
            "rank": r["rank"],
            "team": _canon(r["team"]["name"]),
            "logo": r["team"].get("logo"),
            "played": r["all"]["played"],
            "win": r["all"]["win"], "draw": r["all"]["draw"], "lose": r["all"]["lose"],
            "gf": r["all"]["goals"]["for"], "ga": r["all"]["goals"]["against"],
            "points": r["points"], "goalsDiff": r["goalsDiff"],
            "form": r.get("form", ""),
        })
    return out


def ingest_fixtures(client: ApiFootball) -> tuple[list[dict], list[dict]]:
    """
    Traduce fixtures a played / remaining no noso formato
    ({jornada, home, away[, hg, ag]}). Un fixture con status FT é xogado.
    """
    data = client.fixtures()
    played, remaining = [], []
    for f in data.get("response", []):
        fx = f["fixture"]
        league = f.get("league", {})
        teams = f["teams"]
        goals = f.get("goals", {})
        jornada = _round_num(league.get("round", ""))
        home = _canon(teams["home"]["name"])
        away = _canon(teams["away"]["name"])
        status = fx.get("status", {}).get("short", "")
        if status == "FT":
            played.append({"jornada": jornada, "home": home, "away": away,
                          "hg": goals.get("home", 0), "ag": goals.get("away", 0)})
        else:
            remaining.append({"jornada": jornada, "home": home, "away": away})
    return played, remaining


def _round_num(round_str: str) -> int:
    """'Regular Season - 8' → 8."""
    try:
        return int(round_str.strip().split("-")[-1])
    except (ValueError, AttributeError):
        return 0


def run(real: bool = False) -> dict:
    """Ingesta completa: actualiza season_*.json coa clasificación e fixtures."""
    client = ApiFootball(mock=not real)
    mode = "REAL" if real and client.api_key else "MOCK"
    print(f"[ingest] modo {mode}")

    standings = ingest_standings(client)
    print(f"[ingest] clasificación: {len(standings)} equipos")

    played, remaining = ingest_fixtures(client)
    print(f"[ingest] fixtures: {len(played)} xogados, {len(remaining)} pendentes")

    data = load()
    if played or remaining:
        data["played"] = played
        data["remaining"] = remaining
        save(data)
        print("[ingest] season_*.json actualizado")
    else:
        print("[ingest] sen fixtures (mock ou liga sen comezar); clasificación só para verificación")

    return {"standings": standings, "played": played, "remaining": remaining}


if __name__ == "__main__":
    run(real="--real" in sys.argv)
