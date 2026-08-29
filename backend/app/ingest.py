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


# Mapa de nomes de API-Football → os nosos nomes canónicos (do calendario).
# OLLO: a cobertura de 1ª RFEF Grupo 1 en API-Football é incompleta (faltan equipos
# como Barakaldo e Ponferradina nas listas), así que a actualización automática pode
# non traer todos os partidos. A entrada manual (pestana Resultados) é a vía fiable.
NAME_MAP: dict[str, str] = {
    "Mérida": "AD Mérida",
    "Arenas Getxo": "Arenas Club",
    "Arenas de Getxo": "Arenas Club",
    "Athletic Club II": "Bilbao Athletic",
    "Athletic Bilbao II": "Bilbao Athletic",
    "CD Coria": "CD Coria",
    "Coria": "CD Coria",
    "Extremadura": "CD Extremadura",
    "Extremadura UD": "CD Extremadura",
    "Lugo": "CD Lugo",
    "Mirandes": "CD Mirandés",
    "Mirandés": "CD Mirandés",
    "Cacereño": "CP Cacereño",
    "Cultural Leonesa": "CyD Leonesa",
    "Cultural y Deportiva Leonesa": "CyD Leonesa",
    "Pontevedra": "Pontevedra CF",
    "Deportivo La Coruña II": "RC Deportivo Fabril",
    "Deportivo Fabril": "RC Deportivo Fabril",
    "Racing Ferrol": "Racing Ferrol",
    "Real Avilés": "Real Avilés",
    "Real Avilés Industrial": "Real Avilés",
    "Real Unión": "Real Unión",
    "Real Union Club": "Real Unión",
    "UD Logroñés": "UD Logroñés",
    "UD Ourense": "UD Ourense",
    "Ourense CF": "UD Ourense",
    "Unionistas de Salamanca": "Unionistas",
    "Unionistas": "Unionistas",
    "Zamora": "Zamora CF",
    # Barakaldo CF e SD Ponferradina: manteñen o mesmo nome (se a API os devolve).
    "Barakaldo": "Barakaldo CF",
    "Barakaldo CF": "Barakaldo CF",
    "Ponferradina": "SD Ponferradina",
    "SD Ponferradina": "SD Ponferradina",
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


def ingest_results_by_team(client) -> list[dict]:
    """
    Busca os partidos POR EQUIPO (máis fiable que por liga en 1ª RFEF) e devolve SÓ os
    resultados dos partidos XOGADOS entre equipos do noso grupo: [{home, away, hg, ag}].
    Non colle stats, non toca o calendario: só marcadores.
    """
    from .apifootball import TEAM_IDS
    canon_teams = set(NAMES)
    seen = set()
    results = []
    for canon, tid in TEAM_IDS.items():
        try:
            data = client.fixtures_by_team(tid)
        except Exception as exc:
            print(f"[ingest] fallo ao pedir {canon} ({tid}): {exc}")
            continue
        for f in data.get("response", []):
            fx = f.get("fixture", {})
            teams = f.get("teams", {})
            goals = f.get("goals", {})
            status = fx.get("status", {}).get("short", "")
            home = _canon(teams.get("home", {}).get("name", ""))
            away = _canon(teams.get("away", {}).get("name", ""))
            # só partidos ENTRE equipos do noso grupo e xa rematados
            if home not in canon_teams or away not in canon_teams:
                continue
            if status != "FT":
                continue
            key = (home, away)
            if key in seen:
                continue
            seen.add(key)
            results.append({"home": home, "away": away,
                            "hg": goals.get("home", 0), "ag": goals.get("away", 0)})
    return results


def run(real: bool = False) -> dict:
    """
    Ingesta de RESULTADOS: busca por equipo (fiable en 1ª RFEF) e actualiza SÓ os goles
    dos partidos xogados, fusionándoos sobre o calendario existente. Non toca as stats
    (esas métense a man e son capa aparte). Non "inventa" calendario: só engade marcadores.
    """
    client = ApiFootball(mock=not real)
    mode = "REAL" if real and client.api_key else "MOCK"
    print(f"[ingest] modo {mode}")

    data = load()
    results = ingest_results_by_team(client) if mode == "REAL" else []
    print(f"[ingest] resultados atopados: {len(results)}")

    if results:
        # índice de resultados por (home, away)
        by_key = {(r["home"], r["away"]): r for r in results}
        played = list(data.get("played", []))
        played_keys = {(m["home"], m["away"]) for m in played}
        new_remaining = []
        for m in data.get("remaining", []):
            r = by_key.get((m["home"], m["away"]))
            if r and (m["home"], m["away"]) not in played_keys:
                played.append({**m, "hg": r["hg"], "ag": r["ag"]})
                played_keys.add((m["home"], m["away"]))
            else:
                new_remaining.append(m)
        data["played"] = played
        data["remaining"] = new_remaining
        save(data)
        print(f"[ingest] {len(played)} xogados, {len(new_remaining)} pendentes · season_*.json actualizado")

    # clasificación só para verificación (non se garda como fonte principal)
    standings = []
    return {"standings": standings, "played": data.get("played", []),
            "remaining": data.get("remaining", []), "results_found": len(results)}


if __name__ == "__main__":
    run(real="--real" in sys.argv)
