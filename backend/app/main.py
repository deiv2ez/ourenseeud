"""
main.py — API FastAPI de "Ourense é UD".

Expone al frontend lo que calcula el motor, sin que el navegador tenga que correr
ninguna simulación. Endpoints:

  GET /api/standings              → clasificación real + oPts/oGoals/forma
  GET /api/probs                  → probabilidades Monte Carlo por equipo
  GET /api/match/next?team=...    → próximo partido + expected result (con cuotas)
  POST /api/simulate              → simulador "qué pasa si": resultados hipotéticos
  GET /api/teams                  → catálogo de equipos (slug, color)

El Monte Carlo es caro (~5s por 10k sims), así que se cachea el resultado y solo
se recalcula cuando cambian los datos de temporada (hash del JSON). El simulador
interactivo usa menos simulaciones para responder rápido.

Arrancar en local:
    uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations
import os
import hashlib
import json
from functools import lru_cache

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .store import load as _store_load, NAMES, SLUG_BY_NAME, match_key
from .models.montecarlo import SeasonModel
from .auth import verify_login, make_token, decode_token
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

app = FastAPI(title="Ourense é UD · API", version="0.1.0")

# El frontend (Vite/Next en Vercel) llama desde otro origen → habilitamos CORS.
# En producción se restringe al dominio real vía ALLOWED_ORIGIN; en local, todo.
_allowed = os.environ.get("ALLOWED_ORIGIN")
_origins = [_allowed] if _allowed else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------- utilidades ----
def load() -> dict:
    """
    Carga os datos de tempada e INXECTA as cuotas persistidas en Supabase (se hai)
    nos partidos de 'remaining'. Así as cuotas sobreviven aos reinicios de Render.
    Se Supabase non está activo, devolve os datos tal cal (coas cuotas do JSON local,
    se as houber). Calquera fallo de Supabase é silencioso: seguimos sen cuotas.
    """
    data = _store_load()
    try:
        from . import odds_store
        remote = odds_store.load_odds()
        if remote:
            for m in data.get("remaining", []):
                key = (m["home"], m["away"])
                if key in remote:
                    m["odds"] = remote[key]
    except Exception:
        pass
    return data


def _data_hash(data: dict) -> str:
    """Huella de los datos de temporada para invalidar la caché al cambiar.
    Inclúe as cuotas: se cambian, o Monte Carlo e as features recalcúlanse."""
    odds = {f'{m["home"]}|{m["away"]}': m.get("odds") for m in data.get("remaining", [])}
    raw = json.dumps({"p": data["played"], "r": data["remaining"], "o": odds}, sort_keys=True)
    return hashlib.md5(raw.encode()).hexdigest()


def _fit_model(data: dict) -> SeasonModel:
    return SeasonModel(NAMES).fit(data["played"])


@lru_cache(maxsize=8)
def _cached_sim(data_hash: str, n_sims: int) -> str:
    """
    Cachea el Monte Carlo por (hash de datos, nº de sims). Devuelve JSON como str
    porque lru_cache exige valores hashables/inmutables y el dict no lo es.
    """
    data = load()
    model = _fit_model(data)
    res = model.simulate(data["played"], data["remaining"], n_sims=n_sims)
    return json.dumps(res)


def _standings(data: dict) -> list[dict]:
    """Clasificación real calculada desde los partidos jugados, + forma."""
    rows = {n: {"team": n, "slug": SLUG_BY_NAME[n], "pld": 0, "w": 0, "d": 0,
                "l": 0, "gf": 0, "ga": 0, "pts": 0, "form": []} for n in NAMES}
    # partidos en orden cronológico para calcular la forma (últimos 5)
    for m in sorted(data["played"], key=lambda x: x["jornada"]):
        h, a, hg, ag = m["home"], m["away"], m["hg"], m["ag"]
        for t, gf, ga in ((h, hg, ag), (a, ag, hg)):
            r = rows[t]
            r["pld"] += 1; r["gf"] += gf; r["ga"] += ga
            if gf > ga: r["w"] += 1; r["pts"] += 3; res = "W"
            elif gf < ga: r["l"] += 1; res = "L"
            else: r["d"] += 1; r["pts"] += 1; res = "D"
            r["form"].append(res)
    for r in rows.values():
        r["gd"] = r["gf"] - r["ga"]
        r["form"] = r["form"][-5:]
    return _rank_with_tiebreakers(list(rows.values()), data["played"])


def _rank_with_tiebreakers(rows: list[dict], played: list[dict]) -> list[dict]:
    """
    Ordena a clasificación cos criterios OFICIAIS da RFEF.

    Primeiro por puntos. Dentro de cada grupo empatado a puntos, aplícase o
    desempate oficial:
      · Entre 2+ equipos: mini-liga só cos partidos ENTRE eles →
        1) puntos nesa mini-liga, 2) dif. goles entre eles,
        3) dif. goles xeral, 4) goles a favor xeral.
      · O enfrontamento directo SÓ conta se xa se xogaron TODOS os partidos
        entre os implicados; se non, vaise directo á dif. de goles xeral.
    """
    # índice de partidos xogados entre cada par de equipos
    def matches_between(teams: set[str]) -> list[dict]:
        return [m for m in played if m["home"] in teams and m["away"] in teams]

    # cantos cruces DEBERÍAN existir entre N equipos nunha liga a dobre volta:
    # cada par xoga 2 veces → N*(N-1) partidos en total.
    def all_h2h_played(teams: set[str]) -> bool:
        n = len(teams)
        return len(matches_between(teams)) >= n * (n - 1)

    def mini_league(teams: set[str]) -> dict:
        """Táboa (pts, dif. goles) só cos partidos entre os equipos do grupo."""
        sub = {t: {"pts": 0, "gf": 0, "ga": 0} for t in teams}
        for m in matches_between(teams):
            h, a, hg, ag = m["home"], m["away"], m["hg"], m["ag"]
            sub[h]["gf"] += hg; sub[h]["ga"] += ag
            sub[a]["gf"] += ag; sub[a]["ga"] += hg
            if hg > ag: sub[h]["pts"] += 3
            elif hg < ag: sub[a]["pts"] += 3
            else: sub[h]["pts"] += 1; sub[a]["pts"] += 1
        return sub

    # 1) orde base por puntos (descendente)
    rows_sorted = sorted(rows, key=lambda r: -r["pts"])

    # 2) agrupar por puntos e desempatar dentro de cada grupo
    result = []
    i = 0
    while i < len(rows_sorted):
        j = i
        while j < len(rows_sorted) and rows_sorted[j]["pts"] == rows_sorted[i]["pts"]:
            j += 1
        group = rows_sorted[i:j]
        if len(group) == 1:
            result.append(group[0])
        else:
            teams = {r["team"] for r in group}
            if all_h2h_played(teams):
                sub = mini_league(teams)
                # 1) pts mini-liga, 2) dif goles mini-liga, 3) dif goles xeral, 4) GF xeral
                group.sort(key=lambda r: (
                    -sub[r["team"]]["pts"],
                    -(sub[r["team"]]["gf"] - sub[r["team"]]["ga"]),
                    -r["gd"],
                    -r["gf"],
                ))
            else:
                # aínda non se xogaron todos os cruces → dif goles xeral, logo GF
                group.sort(key=lambda r: (-r["gd"], -r["gf"]))
            result.extend(group)
        i = j
    return result


# ---------------------------------------------------------------- endpoints --
@app.get("/api/teams")
def get_teams():
    return load()["teams"]


@app.get("/api/standings")
def get_standings():
    data = load()
    table = _standings(data)
    model = _fit_model(data)
    opts = model._expected_points_played(
        data["played"], {t: i for i, t in enumerate(NAMES)}, len(NAMES)
    )
    idx = {t: i for i, t in enumerate(NAMES)}
    for r in table:
        r["oPts"] = round(float(opts[idx[r["team"]]]), 1)
        r["elo"] = round(model.strength[r["team"]].elo)
    return table


@app.get("/api/probs")
def get_probs(n_sims: int = Query(10000, ge=1000, le=50000)):
    data = load()
    res = json.loads(_cached_sim(_data_hash(data), n_sims))
    # adjuntamos slug para que el frontend pinte escudos
    return [{"team": t, "slug": SLUG_BY_NAME[t], **v} for t, v in res.items()]


@app.get("/api/merited")
def merited_table(n_sims: int = Query(10000, ge=1000, le=50000)):
    """
    Idea 4 — Táboa MERECIDA: clasificación ordenada por oPts (puntos merecidos
    polo modelo) en vez dos puntos reais. Amosa a posición real e a merecida,
    e canto sobe/baixa cada equipo se contase o merecido.
    """
    data = load()
    res = json.loads(_cached_sim(_data_hash(data), n_sims))
    table = _standings(data)
    real_pos = {r["team"]: i + 1 for i, r in enumerate(table)}
    real_pts = {r["team"]: r["pts"] for r in table}
    rows = [{"team": t, "slug": SLUG_BY_NAME[t],
             "pts": real_pts[t], "oPts": v["oPts"],
             "realPos": real_pos[t]} for t, v in res.items()]
    rows.sort(key=lambda r: -r["oPts"])
    for i, r in enumerate(rows):
        r["meritedPos"] = i + 1
        r["delta"] = r["realPos"] - r["meritedPos"]  # +sube na merecida, -baixa
    return rows


@app.get("/api/objectives")
def objectives(team: str = "UD Ourense", n_sims: int = Query(10000, ge=1000, le=50000)):
    """
    Idea 12 — Que necesita a UDO?: limiares de puntos estimados (media das sims)
    para campión, playoff e permanencia, e cantos puntos lle faltan ao equipo
    dado desde os que xa ten.
    """
    if team not in NAMES:
        raise HTTPException(404, f"Equipo desconocido: {team}")
    data = load()
    # aseguramos simulación feita (enche self._thresholds) e collémolos
    model = _fit_model(data)
    sim = model.simulate(data["played"], data["remaining"], n_sims=n_sims)
    sim_thr = getattr(model, "_thresholds", {"champion": 0, "playoff": 0, "safety": 0})
    # Limiares REAIS históricos (media 5 tempadas 1ª RFEF, fonte BDFutbol):
    #   campión 73, playoff (5º) 60, permanencia (15º) 45.
    # Ancorámonos a eles porque a simulación soa subestima (asume equipos máis
    # iguais do que acaban sendo). MELLORA FUTURA: mesturar real+simulación
    # dándolle máis peso á simulación segundo avanza a liga.
    REAL_THR = {"champion": 73, "playoff": 60, "safety": 45}
    table = _standings(data)
    row = next(r for r in table if r["team"] == team)
    cur = row["pts"]
    played = row["pld"]
    # BLEND: ao principio (poucos partidos) fiámonos do histórico real; segundo
    # avanza a liga, damos máis peso á simulación (que xa ten datos desta tempada).
    # Con 30+ xornadas xogadas, fiámonos só da simulación.
    w_sim = min(1.0, played / 30.0)
    thr = {k: round((1 - w_sim) * REAL_THR[k] + w_sim * sim_thr.get(k, REAL_THR[k]))
           for k in REAL_THR}
    remaining_games = 38 - played
    def need(target):
        n = max(0, target - cur)
        return {"threshold": target, "need": n,
                "reachable": n <= remaining_games * 3}
    return {
        "team": team, "slug": SLUG_BY_NAME[team],
        "current_pts": cur, "played": played, "remaining": remaining_games,
        "champion": need(thr["champion"]),
        "playoff": need(thr["playoff"]),
        "safety": need(thr["safety"]),
    }


@app.get("/api/match/next")
def next_match(team: str = "UD Ourense", blend: float = Query(0.5, ge=0, le=1)):
    if team not in NAMES:
        raise HTTPException(404, f"Equipo desconocido: {team}")
    data = load()
    upcoming = [m for m in sorted(data["remaining"], key=lambda x: x["jornada"])
                if team in (m["home"], m["away"])]
    if not upcoming:
        return {"team": team, "next": None}
    m = upcoming[0]
    model = _fit_model(data)
    odds = data["odds"].get(match_key(m["home"], m["away"]))
    xr = model.expected_result(m["home"], m["away"], odds=odds, blend=blend)
    return {
        "team": team,
        "next": {
            "jornada": m["jornada"],
            "home": m["home"], "home_slug": SLUG_BY_NAME[m["home"]],
            "away": m["away"], "away_slug": SLUG_BY_NAME[m["away"]],
            "odds": odds,
            "expected": xr,
        },
    }


# --------------------------------------------------- simulador interactivo ---
class HypoMatch(BaseModel):
    home: str
    away: str
    hg: int
    ag: int


class SimRequest(BaseModel):
    # resultados hipotéticos que el usuario fija; el resto se simula
    fixtures: list[HypoMatch] = []
    n_sims: int = 4000  # menos sims para respuesta rápida en el simulador


@app.post("/api/simulate")
def simulate_whatif(req: SimRequest):
    """
    'Qué pasa si...': el usuario fija algunos resultados y el motor simula el resto,
    devolviendo las probabilidades actualizadas. Los partidos fijados salen del
    conjunto 'remaining' y entran como jugados para esta simulación puntual.
    """
    data = load()
    fixed = {match_key(f.home, f.away): f for f in req.fixtures}

    played = list(data["played"])
    remaining = []
    for m in data["remaining"]:
        key = match_key(m["home"], m["away"])
        if key in fixed:
            f = fixed[key]
            played.append({**m, "hg": f.hg, "ag": f.ag})
        else:
            remaining.append(m)

    model = SeasonModel(NAMES).fit(data["played"])  # fuerzas con datos reales
    res = model.simulate(played, remaining, n_sims=req.n_sims)
    probs = [{"team": t, "slug": SLUG_BY_NAME[t], **v} for t, v in res.items()]

    # tabla proyectada incluyendo los resultados hipotéticos ya fijados
    table = _standings({"played": played})
    return {"table": table, "probs": probs}


@app.get("/api/resume")
def resume_board():
    """
    Currículum (Resume Board): ranking polo 'valor real' dos puntos, ponderando
    dificultade do rival e onde se xogou. Devuelve filas ordenadas por currículum,
    coa diferenza fronte aos puntos reais (quen mereceu camiño máis duro/doado).
    """
    data = load()
    model = _fit_model(data)
    board = model.resume_board(data["played"])
    rows = []
    for name, v in board.items():
        rows.append({
            "team": name, "slug": SLUG_BY_NAME[name],
            "pts": v["pts"], "resume": v["resume"], "played": v["played"],
            "diff": round(v["resume"] - v["pts"], 1),
        })
    rows.sort(key=lambda r: -r["resume"])
    return rows


@app.get("/api/matchday")
def current_matchday():
    """
    Devuelve la próxima jornada pendiente completa (todos sus partidos), cada uno
    con a súa PREDICIÓN: marcador esperado, oGoals e probabilidades 1-X-2.
    Serve tanto para o simulador como para a sección 'Xornada' de previas.
    """
    data = load()
    if not data["remaining"]:
        return {"jornada": None, "matches": []}
    j = min(m["jornada"] for m in data["remaining"])
    model = _fit_model(data)
    matches = []
    for m in data["remaining"]:
        if m["jornada"] != j:
            continue
        p = model.match_probs(m["home"], m["away"], odds=m.get("odds"))
        matches.append({
            "home": m["home"], "home_slug": SLUG_BY_NAME[m["home"]],
            "away": m["away"], "away_slug": SLUG_BY_NAME[m["away"]],
            "date": m.get("date"),
            # predición do modelo
            "likely_score": p["likely_score"],           # marcador máis probable [h, a]
            "oGoals_home": p["oGoals_home"],
            "oGoals_away": p["oGoals_away"],
            "p_home": round(p["home_win"] * 100),         # 1
            "p_draw": round(p["draw"] * 100),             # X
            "p_away": round(p["away_win"] * 100),         # 2
        })
    return {"jornada": j, "matches": matches}


@app.get("/api/team/{slug}/evolution")
def team_evolution(slug: str):
    """
    Evolución jornada a jornada de la UD Ourense (o cualquier equipo): puntos
    reales acumulados vs oPts acumulados (puntos esperados del modelo). El desfase
    entre ambas líneas es la historia de 'merecido vs conseguido' (estilo Torvik).
    """
    name = next((n for n, s in SLUG_BY_NAME.items() if s == slug), None)
    if not name:
        raise HTTPException(404, f"Slug desconocido: {slug}")
    data = load()
    model = _fit_model(data)

    played = sorted(data["played"], key=lambda x: x["jornada"])
    pts_cum, opts_cum, points = 0.0, 0.0, []
    for m in played:
        if name not in (m["home"], m["away"]):
            continue
        is_home = m["home"] == name
        gf, ga = (m["hg"], m["ag"]) if is_home else (m["ag"], m["hg"])
        pts_cum += 3 if gf > ga else 1 if gf == ga else 0
        p = model.match_probs(m["home"], m["away"], odds=m.get("odds"))
        opts_cum += (3 * p["home_win"] + p["draw"]) if is_home else (3 * p["away_win"] + p["draw"])
        points.append({
            "jornada": m["jornada"],
            "pts": round(pts_cum, 1),
            "oPts": round(opts_cum, 1),
            "rival": m["away"] if is_home else m["home"],
            "home": is_home,
            "gf": gf, "ga": ga,
        })
    return {"team": name, "slug": slug, "evolution": points}


@app.get("/api/team/{slug}")
def team_profile(slug: str):
    """
    Ficha completa dun equipo: resumo (posición, PX, V-E-D, goles, forma, oPts),
    próximo partido con predición, e calendario (xogados con resultado + pendentes).
    """
    name = next((n for n, s in SLUG_BY_NAME.items() if s == slug), None)
    if not name:
        raise HTTPException(404, f"Slug desconocido: {slug}")
    data = load()
    table = _standings(data)
    pos = {r["team"]: i + 1 for i, r in enumerate(table)}
    row = next(r for r in table if r["team"] == name)
    model = _fit_model(data)

    # oPts (puntos merecidos) acumulados na tempada
    opts = 0.0
    for m in sorted(data["played"], key=lambda x: x["jornada"]):
        if name not in (m["home"], m["away"]):
            continue
        p = model.match_probs(m["home"], m["away"], odds=m.get("odds"))
        is_home = m["home"] == name
        opts += (3 * p["home_win"] + p["draw"]) if is_home else (3 * p["away_win"] + p["draw"])

    # próximo partido con predición
    upcoming = [m for m in sorted(data["remaining"], key=lambda x: x["jornada"])
                if name in (m["home"], m["away"])]
    next_match = None
    if upcoming:
        nm = upcoming[0]
        p = model.match_probs(nm["home"], nm["away"])
        is_home = nm["home"] == name
        next_match = {
            "jornada": nm["jornada"], "home": nm["home"], "away": nm["away"],
            "home_slug": SLUG_BY_NAME[nm["home"]], "away_slug": SLUG_BY_NAME[nm["away"]],
            "date": nm.get("date"), "is_home": is_home,
            "likely_score": p["likely_score"],
            "oGoals_home": p["oGoals_home"], "oGoals_away": p["oGoals_away"],
            "p_win": round((p["home_win"] if is_home else p["away_win"]) * 100),
            "p_draw": round(p["draw"] * 100),
            "p_loss": round((p["away_win"] if is_home else p["home_win"]) * 100),
        }

    # calendario: xogados (con resultado) + pendentes
    fixtures = []
    for m in sorted(data["played"], key=lambda x: x["jornada"]):
        if name not in (m["home"], m["away"]):
            continue
        is_home = m["home"] == name
        gf, ga = (m["hg"], m["ag"]) if is_home else (m["ag"], m["hg"])
        rival = m["away"] if is_home else m["home"]
        fixtures.append({
            "jornada": m["jornada"], "rival": rival, "rival_slug": SLUG_BY_NAME[rival],
            "is_home": is_home, "gf": gf, "ga": ga, "played": True,
            "result": "W" if gf > ga else "L" if gf < ga else "D",
        })
    for m in sorted(data["remaining"], key=lambda x: x["jornada"]):
        if name not in (m["home"], m["away"]):
            continue
        is_home = m["home"] == name
        rival = m["away"] if is_home else m["home"]
        fixtures.append({
            "jornada": m["jornada"], "rival": rival, "rival_slug": SLUG_BY_NAME[rival],
            "is_home": is_home, "played": False, "date": m.get("date"),
        })

    return {
        "team": name, "slug": slug, "pos": pos[name],
        "pld": row["pld"], "w": row["w"], "d": row["d"], "l": row["l"],
        "gf": row["gf"], "ga": row["ga"], "gd": row["gd"], "pts": row["pts"],
        "oPts": round(opts, 1), "form": row["form"],
        "elo": round(model.strength[name].elo),
        "style": model.team_style(data["played"]).get(name),
        "style_note": data.get("style_notes", {}).get(slug),  # nota cualitativa editable (admin)
        "next": next_match, "fixtures": fixtures,
    }


@app.get("/api/team/{slug}/vs")
def head_to_head(slug: str):
    """Comparativa del equipo con su próximo rival: posición, forma, goles, Elo."""
    name = next((n for n, s in SLUG_BY_NAME.items() if s == slug), None)
    if not name:
        raise HTTPException(404, f"Slug desconocido: {slug}")
    data = load()
    upcoming = [m for m in sorted(data["remaining"], key=lambda x: x["jornada"])
                if name in (m["home"], m["away"])]
    if not upcoming:
        return {"team": name, "rival": None}
    m = upcoming[0]
    rival = m["away"] if m["home"] == name else m["home"]

    table = _standings(data)
    pos = {r["team"]: i + 1 for i, r in enumerate(table)}
    by_team = {r["team"]: r for r in table}
    model = _fit_model(data)

    def card(tm):
        r = by_team[tm]
        return {
            "team": tm, "slug": SLUG_BY_NAME[tm], "pos": pos[tm],
            "pts": r["pts"], "gf": r["gf"], "ga": r["ga"], "gd": r["gd"],
            "form": r["form"], "elo": round(model.strength[tm].elo),
        }

    return {
        "jornada": m["jornada"],
        "home": m["home"], "away": m["away"],
        "us": card(name), "them": card(rival),
    }


class LineupRequest(BaseModel):
    players: list[str]                 # 11 nombres, orden por líneas (portero primero)
    formation: str = "4-3-3"
    numbers: list[int] | None = None   # dorsales opcionales
    title: str = "UD Ourense"
    subtitle: str = ""


@app.post("/api/lineup.png")
def lineup_png(req: LineupRequest):
    """Genera el PNG del once (16:9) y lo devuelve como imagen para descargar/compartir."""
    from io import BytesIO
    from fastapi.responses import Response
    from .lineup import build_lineup, FORMATIONS

    if req.formation not in FORMATIONS:
        raise HTTPException(400, f"Formación no soportada. Opciones: {list(FORMATIONS)}")
    try:
        img = build_lineup(
            players=req.players, formation=req.formation,
            title=req.title, subtitle=req.subtitle, numbers=req.numbers,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png")


@app.get("/api/formations")
def formations():
    """Lista de formaciones disponibles y cuántos jugadores necesita cada una."""
    from .lineup import FORMATIONS
    return {f: 1 + sum(lines) for f, lines in FORMATIONS.items()}


@app.get("/api/squad")
def get_squad():
    """
    Plantilla de la UD Ourense con oRating (media de temporada por jugador).
    Los datos de plantilla salen de un JSON editable por el admin; los oRating
    se calculan a partir de las notas por partido con app.rating.
    """
    from pathlib import Path
    import json as _json
    squad_file = Path(__file__).resolve().parent.parent / "data" / "squad.json"
    if not squad_file.exists():
        return []
    squad = _json.loads(squad_file.read_text(encoding="utf-8"))
    from .rating import season_rating
    for p in squad:
        s = season_rating(p.get("match_ratings", []))
        p["oRating"] = s["avg"]
        p["games"] = s["games"]
        p["form"] = s["form"]
    return squad


## ----------------------------------------------------------- auth ----------
security = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    username: str
    password: str


def current_user(cred: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Dependencia: extrae o usuario do token. 401 se non hai token válido."""
    if not cred:
        raise HTTPException(401, "Falta o token de acceso")
    user = decode_token(cred.credentials)
    if not user:
        raise HTTPException(401, "Token inválido ou caducado")
    return user


def require_admin(user: dict = Depends(current_user)) -> dict:
    """Dependencia: esixe rol admin (o usuario 'david')."""
    if user.get("role") != "admin":
        raise HTTPException(403, "Só o admin pode facer isto")
    return user


@app.post("/api/login")
def login(req: LoginRequest):
    user = verify_login(req.username, req.password)
    if not user:
        raise HTTPException(401, "Usuario ou contrasinal incorrectos")
    return {"token": make_token(user), "user": user}


@app.get("/api/me")
def me(user: dict = Depends(current_user)):
    return user


@app.post("/api/admin/reload")
def admin_reload(user: dict = Depends(require_admin)):
    """Exemplo de ruta protexida só-admin: recarga datos desde a fonte (ingest)."""
    from .ingest import run as ingest_run
    result = ingest_run(real=bool(os.environ.get("API_FOOTBALL_KEY")))
    _cached_sim.cache_clear()
    return {"ok": True, "by": user["username"],
            "standings": len(result["standings"]), "played": len(result["played"])}


class OddsEntry(BaseModel):
    home: str          # nome do equipo local (como no calendario)
    away: str          # nome do equipo visitante
    c_home: float      # cuota decimal 1
    c_draw: float      # cuota decimal X
    c_away: float      # cuota decimal 2


class OddsUpload(BaseModel):
    jornada: int
    entries: list[OddsEntry]


@app.get("/api/admin/matchday-odds")
def admin_get_matchday_odds(user: dict = Depends(require_admin)):
    """Devuelve os partidos da próxima xornada pendente e as súas cuotas actuais
    (se as houber), para que o admin as edite. Só admin."""
    data = load()
    if not data["remaining"]:
        return {"jornada": None, "matches": []}
    j = min(m["jornada"] for m in data["remaining"])
    matches = []
    for m in data["remaining"]:
        if m["jornada"] != j:
            continue
        od = m.get("odds") or {}
        matches.append({
            "home": m["home"], "away": m["away"],
            "home_slug": SLUG_BY_NAME[m["home"]], "away_slug": SLUG_BY_NAME[m["away"]],
            "c_home": od.get("home"), "c_draw": od.get("draw"), "c_away": od.get("away"),
        })
    return {"jornada": j, "matches": matches}


@app.post("/api/admin/odds")
def admin_set_odds(payload: OddsUpload, user: dict = Depends(require_admin)):
    """
    Garda as cuotas 1X2 dunha xornada e RECALCULA todo (limpa a caché de simulacións).
    As predicións pasarán a usar o blend 70/30. Só admin.

    Persistencia: se Supabase está configurado (variables SUPABASE_URL/KEY en Render),
    gárdanse alí (persistente). Se non, no JSON local (efímero en Render free).
    """
    from .store import save
    from . import odds_store
    entries = [{"home": e.home, "away": e.away,
                "c_home": e.c_home, "c_draw": e.c_draw, "c_away": e.c_away}
               for e in payload.entries
               if e.c_home >= 1 and e.c_draw >= 1 and e.c_away >= 1]

    # 1) persistencia en Supabase (se está activo)
    saved_remote = 0
    try:
        saved_remote = odds_store.save_odds(payload.jornada, entries)
    except Exception as exc:
        raise HTTPException(502, f"Erro gardando en Supabase: {exc}")

    # 2) tamén no JSON local (para que funcione xa nesta sesión aínda sen Supabase)
    data = load()
    idx = {(m["home"], m["away"]): m for m in data["remaining"]
           if m["jornada"] == payload.jornada}
    updated = 0
    for e in entries:
        m = idx.get((e["home"], e["away"]))
        if m:
            m["odds"] = {"home": e["c_home"], "draw": e["c_draw"], "away": e["c_away"]}
            updated += 1
    save(data)
    _cached_sim.cache_clear()   # forza recálculo de simulacións e features
    return {"ok": True, "by": user["username"], "jornada": payload.jornada,
            "updated": updated, "persisted": saved_remote,
            "storage": "supabase" if odds_store.enabled() else "local"}


@app.on_event("startup")
def _ensure_admin():
    """
    Crea/actualiza o usuario admin ao arrancar, lendo de variables de entorno.
    Isto resolve dúas cousas no plan gratuíto de Render:
      - non fai falta a Shell (que é de pago),
      - o usuario recréase en cada arranque, así que sobrevive aos reinicios que
        borran o disco local (onde vive users.json).
    Define en Render: ADMIN_USER e ADMIN_PASSWORD. Se non están, non fai nada.
    """
    admin_user = os.environ.get("ADMIN_USER")
    admin_pass = os.environ.get("ADMIN_PASSWORD")
    if admin_user and admin_pass:
        from .auth import create_user
        create_user(admin_user, admin_pass, role="admin")
        print(f"[startup] usuario admin '{admin_user}' asegurado")


@app.get("/")
def root():
    return {"app": "Ourense é UD", "docs": "/docs"}
