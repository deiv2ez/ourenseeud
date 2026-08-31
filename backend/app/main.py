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
    Carga os datos de tempada e INXECTA desde Supabase (se hai):
      - as cuotas persistidas nos partidos de 'remaining',
      - os RESULTADOS metidos a man (móvense de 'remaining' a 'played'),
      - os APRAZAMENTOS (sácanse de 'remaining' a unha lista 'postponed').
    Así todo sobrevive aos reinicios de Render e os aprazamentos non descuadran
    nada (razoamos partido a partido, non por xornada completa).
    Calquera fallo de Supabase é silencioso.
    """
    data = _store_load()
    data.setdefault("postponed", [])
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

    # resultados/aprazamentos manuais (Supabase) → aplicar sobre os datos base
    try:
        from . import odds_store
        results = odds_store.load_results()
        if results:
            by_key = {(r["home"], r["away"]): r for r in results}
            new_remaining, moved_played, postponed = [], [], []
            for m in data.get("played", []):
                r = by_key.get((m["home"], m["away"]))
                if r and r.get("status") == "played" and r.get("hg") is not None:
                    m = {**m, "hg": r["hg"], "ag": r["ag"]}   # corrección manual
                moved_played.append(m)
            for m in data.get("remaining", []):
                r = by_key.get((m["home"], m["away"]))
                if not r:
                    new_remaining.append(m)
                elif r.get("status") == "postponed":
                    # IMPORTANTE: un partido aprazado SEGUE sendo pendente (vaise xogar
                    # máis tarde), así que queda en 'remaining' para que o simulador e as
                    # predicións o conten. Só se marca cun flag para resaltalo no panel.
                    mm = {**m, "postponed": True}
                    new_remaining.append(mm)
                    postponed.append(mm)
                elif r.get("status") == "played" and r.get("hg") is not None:
                    moved_played.append({**m, "hg": r["hg"], "ag": r["ag"]})
                else:
                    new_remaining.append(m)
            data["played"] = moved_played
            data["remaining"] = new_remaining
            data["postponed"] = postponed
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

    # estatísticas do modelo (Monte Carlo): probabilidade de cada obxectivo e posición
    # media proxectada. Reutiliza a simulación que xa corre a app.
    model_stats = None
    try:
        sim = model.simulate(data.get("played", []), data.get("remaining", []), n_sims=n_sims)
        if team in sim:
            s = sim[team]
            model_stats = {
                "p_champion": s.get("pChamp", 0),
                "p_playoff": s.get("pPO", 0),
                "p_safety": round(100 - s.get("pRel", 0), 1),   # prob. de NON descender
                "proj_pos": s.get("avgPos"),
                "pos_best": s.get("posBest"),
                "pos_worst": s.get("posWorst"),
                "oPts": s.get("oPts"),
            }
    except Exception:
        model_stats = None

    return {
        "team": team, "slug": SLUG_BY_NAME[team],
        "current_pts": cur, "played": played, "remaining": remaining_games,
        "champion": need(thr["champion"]),
        "playoff": need(thr["playoff"]),
        "safety": need(thr["safety"]),
        "model": model_stats,
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
    # MESMO cálculo que a sección Xornada (/api/matchday): match_probs coas cuotas
    # do partido. Así a previa da UD Ourense e a de Xornada son IDÉNTICAS.
    odds = m.get("odds")
    p = model.match_probs(m["home"], m["away"], odds=odds)
    return {
        "team": team,
        "next": {
            "jornada": m["jornada"],
            "home": m["home"], "home_slug": SLUG_BY_NAME[m["home"]],
            "away": m["away"], "away_slug": SLUG_BY_NAME[m["away"]],
            "odds": odds,
            # mesmos campos que matchday, para que o frontend os use igual
            "likely_score": p["likely_score"],
            "likely_1x2": p["likely_1x2"],
            "oGoals_home": p["oGoals_home"], "oGoals_away": p["oGoals_away"],
            "p_home": round(p["home_win"] * 100),
            "p_draw": round(p["draw"] * 100),
            "p_away": round(p["away_win"] * 100),
            "expected": p,   # compat: mantense o obxecto completo por se acaso
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
            "likely_score": p["likely_score"],
            "likely_1x2": p["likely_1x2"],           # resultado máis probable (1/X/2) — logit
            "oGoals_home": p["oGoals_home"],
            "oGoals_away": p["oGoals_away"],
            "p_home": round(p["home_win"] * 100),         # 1
            "p_draw": round(p["draw"] * 100),             # X
            "p_away": round(p["away_win"] * 100),         # 2
        })
    return {"jornada": j, "matches": matches}


@app.get("/api/matchdays")
def next_matchdays(count: int = Query(3, ge=1, le=5)):
    """
    Devolve as próximas `count` xornadas pendentes (para o simulador multi-xornada).
    Cada xornada cos seus partidos e predicións (mesmo formato que /api/matchday).
    """
    data = load()
    if not data["remaining"]:
        return {"jornadas": []}
    model = _fit_model(data)
    js = sorted({m["jornada"] for m in data["remaining"]})[:count]
    out = []
    for j in js:
        matches = []
        for m in data["remaining"]:
            if m["jornada"] != j:
                continue
            p = model.match_probs(m["home"], m["away"], odds=m.get("odds"))
            matches.append({
                "home": m["home"], "home_slug": SLUG_BY_NAME[m["home"]],
                "away": m["away"], "away_slug": SLUG_BY_NAME[m["away"]],
                "date": m.get("date"),
                "likely_score": p["likely_score"],
                "likely_1x2": p["likely_1x2"],
                "oGoals_home": p["oGoals_home"], "oGoals_away": p["oGoals_away"],
                "p_home": round(p["home_win"] * 100),
                "p_draw": round(p["draw"] * 100),
                "p_away": round(p["away_win"] * 100),
            })
        out.append({"jornada": j, "matches": matches})
    return {"jornadas": out}


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
        p = model.match_probs(nm["home"], nm["away"], odds=nm.get("odds"))
        is_home = nm["home"] == name
        next_match = {
            "jornada": nm["jornada"], "home": nm["home"], "away": nm["away"],
            "home_slug": SLUG_BY_NAME[nm["home"]], "away_slug": SLUG_BY_NAME[nm["away"]],
            "date": nm.get("date"), "is_home": is_home,
            "likely_score": p["likely_score"],
            "likely_1x2": p["likely_1x2"],
            "oGoals_home": p["oGoals_home"], "oGoals_away": p["oGoals_away"],
            # PERSPECTIVA DO EQUIPO da ficha: vitoria / empate / derrota (o usuario
            # quere ver o punto de vista de cada equipo, mesmo indo de visitante).
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

    # --- capa de análise xG (descriptiva, non toca o motor) -----------------
    xg_block = _team_xg_block(name, data, slug)

    return {
        "team": name, "slug": slug, "pos": pos[name],
        "pld": row["pld"], "w": row["w"], "d": row["d"], "l": row["l"],
        "gf": row["gf"], "ga": row["ga"], "gd": row["gd"], "pts": row["pts"],
        "oPts": round(opts, 1), "form": row["form"],
        "elo": round(model.strength[name].elo),
        "style": model.team_style(data["played"]).get(name),
        "style_note": data.get("style_notes", {}).get(slug),  # nota cualitativa editable (admin)
        "next": next_match, "fixtures": fixtures,
        "xg": xg_block,   # None se non hai estatísticas metidas
    }


# caché do análise Gemini por (slug, nº de partidos con stats) para non repetir
# a chamada en cada visita. Renóvase cando entran novas estatísticas.
_xg_cache: dict = {}

def _team_xg_cache_clear():
    """Limpa a caché de análises xG (ao entrar novos datos)."""
    _xg_cache.clear()

def _team_xg_block(name: str, data: dict, slug: str) -> dict | None:
    """
    Constrúe o bloque de análise xG dun equipo: números agregados + texto (Gemini
    ou fallback por umbrais). Cacheado. Devolve None se non hai estatísticas.
    """
    from . import odds_store, xg_analysis, gemini
    stats_rows = odds_store.load_stats()
    if not stats_rows:
        return None
    agg = xg_analysis.team_xg_stats(name, stats_rows, data["played"])
    if not agg:
        return None
    cache_key = (slug, agg["matches"])
    if cache_key in _xg_cache:
        text = _xg_cache[cache_key]
    else:
        text = gemini.analyze_team(name, agg, lang="gl")  # None se non hai clave
        _xg_cache[cache_key] = text
    return {
        "stats": agg,
        "analysis": text,                                   # texto rico (Gemini) ou None
        "insights": xg_analysis.fallback_insights(name, agg, lang="gl"),  # etiquetas sempre
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
    Plantilla da UD Ourense. Combina tres fontes:
      1. squad.json (base: nomes de Sofascore, dorsal e posición por defecto).
      2. player_ratings de Supabase → oRating real agregado por xogador.
      3. squad_meta de Supabase → edicións do admin (apodo/nick, dorsal, posición,
         nota/adxectivo) e FICHAXES engadidos.
    Sen datos, oRating None (nada de mock).
    """
    from pathlib import Path
    import json as _json
    squad_file = Path(__file__).resolve().parent.parent / "data" / "squad.json"
    squad = _json.loads(squad_file.read_text(encoding="utf-8")) if squad_file.exists() else []

    from . import odds_store
    ratings = odds_store.load_ratings()
    meta_rows = odds_store.load_squad_meta()

    def norm(s):
        return (s or "").lower().strip()

    by_player: dict = {}
    for r in ratings:
        by_player.setdefault(norm(r["player"]), []).append(r)
    meta_by_name = {norm(m["name"]): m for m in meta_rows}

    def tokens(s):
        # palabras significativas (>=3 letras) para casar por apelido
        return {w for w in norm(s).replace(".", " ").split() if len(w) >= 3}

    def find_ratings(p):
        # 1) match exacto por nome ou alias (rápido e fiable)
        candidates = [p.get("name")] + (p.get("aliases", []) or [])
        # o apodo/nick tamén conta como alias de busca
        if p.get("nick"):
            candidates.append(p["nick"])
        for c in candidates:
            if norm(c) in by_player:
                return by_player[norm(c)]
        # 2) match flexible por tokens compartidos (apelido en común).
        #    Ex.: "Manuel Vizoso Rodas" (Sofascore) ↔ "Manu Vizoso" (squad) comparten "vizoso".
        p_tokens = set()
        for c in candidates:
            p_tokens |= tokens(c)
        best = None
        for key, recs in by_player.items():
            shared = tokens(key) & p_tokens
            if shared:
                # esixir polo menos un token de >=4 letras compartido (evita falsos por "del")
                if any(len(w) >= 4 for w in shared):
                    best = recs
                    break
        return best

    def apply_ratings(p):
        recs = find_ratings(p)
        if recs:
            vals = [x["orating"] for x in recs if x.get("orating") is not None]
            p["oRating"] = round(sum(vals) / len(vals), 1) if vals else None
            p["games"] = len(vals)
            p["form"] = [x["orating"] for x in sorted(recs, key=lambda x: x["jornada"])[-5:]]
        else:
            p["oRating"], p["games"], p["form"] = None, 0, []
        p.pop("match_ratings", None)
        return p

    out = []
    seen = set()
    for p in squad:
        m = meta_by_name.get(norm(p["name"]))
        if m:
            # aplicar edicións do admin (apodo, dorsal, posición, nota, alias)
            if m.get("nick"): p["nick"] = m["nick"]
            if m.get("dorsal") is not None: p["dorsal"] = m["dorsal"]
            if m.get("pos"): p["pos"] = m["pos"]
            if m.get("note"): p["note"] = m["note"]
            if m.get("alias"):
                # o alias pode ser unha lista separada por comas: engádese aos candidatos
                extra = [a.strip() for a in str(m["alias"]).split(",") if a.strip()]
                p["aliases"] = (p.get("aliases") or []) + extra
                p["alias"] = m["alias"]   # cru, para editar no admin
        p["display"] = p.get("nick") or p["name"]   # nome a amosar no frontend
        out.append(apply_ratings(p))
        seen.add(norm(p["name"]))

    # fichaxes: xogadores en squad_meta con signing=True que non están no squad.json
    for m in meta_rows:
        if m.get("signing") and norm(m["name"]) not in seen:
            p = {"name": m["name"], "nick": m.get("nick"),
                 "display": m.get("nick") or m["name"],
                 "dorsal": m.get("dorsal"), "pos": m.get("pos") or "?",
                 "note": m.get("note"), "signing": True, "nat": "—"}
            out.append(apply_ratings(p))
    return out


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
    """
    Recarga datos desde a API (ingest). Se a API falla (clave, cobertura da categoría,
    nomes...), NON rompe: avisa e o admin pode seguir metendo resultados a man.
    """
    from .ingest import run as ingest_run
    has_key = bool(os.environ.get("API_FOOTBALL_KEY"))
    if not has_key:
        return {"ok": False, "source": "none",
                "message": "Non hai API_FOOTBALL_KEY en Render. Podes meter os resultados a man."}
    try:
        result = ingest_run(real=True)
        found = result.get("results_found", 0)
        # persistir os resultados en Supabase (sobreviven a reinicios de Render)
        saved = 0
        try:
            from . import odds_store
            if odds_store.enabled():
                # reconstruír os resultados dos partidos que quedaron 'played'
                base = _store_load()
                base_played = {(m["home"], m["away"]) for m in base.get("played", [])}
                for m in result.get("played", []):
                    key = (m["home"], m["away"])
                    if key not in base_played and m.get("hg") is not None:
                        odds_store.save_result(m["jornada"], m["home"], m["away"],
                                               m["hg"], m["ag"], status="played")
                        saved += 1
        except Exception:
            pass
        _cached_sim.cache_clear()
        return {"ok": True, "by": user["username"], "source": "api",
                "results_found": found, "saved_supabase": saved,
                "message": (f"Atopados {found} resultados na API"
                            + (f", {saved} novos gardados." if saved else ", sen novidades."))}
    except Exception as exc:
        return {"ok": False, "source": "api", "error": str(exc)[:200],
                "message": ("A API fallou. Podes meter os resultados a man na pestana Resultados.")}


@app.get("/api/admin/matches")
def admin_list_matches(user: dict = Depends(require_admin)):
    """
    Lista os partidos co seu ESTADO para o panel (razoando partido a partido, non por
    xornada). Devolve: pendentes próximos, xogados recentes (para corrixir) e aprazados.
    Así o admin mete resultados en calquera orde e os aprazamentos non descuadran nada.
    """
    data = load()
    played = data.get("played", [])
    remaining = data.get("remaining", [])
    postponed = data.get("postponed", [])

    def light(m, status):
        return {"jornada": m["jornada"], "home": m["home"], "away": m["away"],
                "date": m.get("date"), "hg": m.get("hg"), "ag": m.get("ag"),
                "status": status}

    # pendentes = remaining SEN os aprazados (que se amosan á parte)
    postponed_keys = {(m["home"], m["away"]) for m in postponed}
    pend = sorted([m for m in remaining if (m["home"], m["away"]) not in postponed_keys],
                  key=lambda x: (x.get("date") or "", x["jornada"]))
    # xogados: os últimos por xornada (para corrección)
    playd = sorted(played, key=lambda x: x["jornada"])
    return {
        "pending": [light(m, "pending") for m in pend[:40]],
        "played": [light(m, "played") for m in playd[-20:]],
        "postponed": [light(m, "postponed") for m in postponed],
        "counts": {"pending": len(remaining), "played": len(played), "postponed": len(postponed)},
    }


class ResultEntry(BaseModel):
    jornada: int
    home: str
    away: str
    hg: int | None = None       # goles local (None se aprazado)
    ag: int | None = None       # goles visitante
    status: str = "played"      # "played" | "postponed" | "pending" (borra)


@app.post("/api/admin/result")
def admin_set_result(payload: ResultEntry, user: dict = Depends(require_admin)):
    """
    Mete/edita o resultado dun partido, ou márcao como aprazado, ou devólveo a pendente.
    Persiste en Supabase (sobrevive a reinicios). Non depende do número de xornada:
    cada partido é independente.
    """
    from . import odds_store
    if not odds_store.enabled():
        raise HTTPException(400, "Fai falta Supabase configurado para gardar resultados a man.")
    try:
        if payload.status == "pending":
            odds_store.delete_result(payload.jornada, payload.home, payload.away)
        elif payload.status == "postponed":
            odds_store.save_result(payload.jornada, payload.home, payload.away,
                                   None, None, status="postponed")
        else:  # played
            if payload.hg is None or payload.ag is None:
                raise HTTPException(400, "Un partido xogado precisa os dous goles (hg e ag).")
            odds_store.save_result(payload.jornada, payload.home, payload.away,
                                   int(payload.hg), int(payload.ag), status="played")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, f"Erro gardando o resultado: {exc}")
    _cached_sim.cache_clear()
    return {"ok": True, "by": user["username"], "match": f"{payload.home} vs {payload.away}",
            "status": payload.status}


class OddsEntry(BaseModel):
    home: str          # nome do equipo local (como no calendario)
    away: str          # nome do equipo visitante
    c_home: float      # cuota decimal 1
    c_draw: float      # cuota decimal X
    c_away: float      # cuota decimal 2
    jornada: int | None = None   # xornada dese partido (para partidos mesturados)


class OddsUpload(BaseModel):
    jornada: int
    entries: list[OddsEntry]


@app.get("/api/admin/matchday-odds")
def admin_get_matchday_odds(user: dict = Depends(require_admin)):
    """
    Devolve os PRÓXIMOS partidos pendentes ordenados por data (non unha xornada fixa),
    coas súas cuotas actuais, para que o admin as edite. Así os aprazamentos e os
    partidos adiantados de distintas xornadas aparecen todos, sen descuadres.
    Inclúe a xornada de cada partido para amosala como etiqueta.
    """
    data = load()
    rem = data.get("remaining", [])
    if not rem:
        return {"jornada": None, "matches": []}
    # ordenar por data (e xornada como desempate); amosar os próximos ~20
    rem_sorted = sorted(rem, key=lambda x: (x.get("date") or "9999", x["jornada"]))
    matches = []
    for m in rem_sorted[:20]:
        od = m.get("odds") or {}
        matches.append({
            "jornada": m["jornada"], "date": m.get("date"),
            "postponed": bool(m.get("postponed")),
            "home": m["home"], "away": m["away"],
            "home_slug": SLUG_BY_NAME[m["home"]], "away_slug": SLUG_BY_NAME[m["away"]],
            "c_home": od.get("home"), "c_draw": od.get("draw"), "c_away": od.get("away"),
        })
    # xornada "de referencia" = a do primeiro partido (só informativa)
    j0 = matches[0]["jornada"] if matches else None
    return {"jornada": j0, "matches": matches}


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
    data = load()
    # mapa (home,away) → xornada real do calendario (para non depender dunha global)
    jornada_by_match = {(m["home"], m["away"]): m["jornada"] for m in data.get("remaining", [])}

    entries = []
    for e in payload.entries:
        if not (e.c_home >= 1 and e.c_draw >= 1 and e.c_away >= 1):
            continue
        j = e.jornada or jornada_by_match.get((e.home, e.away)) or payload.jornada
        entries.append({"home": e.home, "away": e.away, "jornada": j,
                        "c_home": e.c_home, "c_draw": e.c_draw, "c_away": e.c_away})

    # 1) persistencia en Supabase (cada partido coa súa xornada real)
    saved_remote = 0
    try:
        # agrupar por xornada para o save (a táboa ten PK jornada+home+away)
        by_j = {}
        for e in entries:
            by_j.setdefault(e["jornada"], []).append(e)
        for j, es in by_j.items():
            saved_remote += odds_store.save_odds(j, es)
    except Exception as exc:
        raise HTTPException(502, f"Erro gardando en Supabase: {exc}")

    # 2) tamén no JSON local (para esta sesión aínda sen Supabase)
    idx = {(m["home"], m["away"]): m for m in data["remaining"]}
    updated = 0
    for e in entries:
        m = idx.get((e["home"], e["away"]))
        if m:
            m["odds"] = {"home": e["c_home"], "draw": e["c_draw"], "away": e["c_away"]}
            updated += 1
    save(data)
    _cached_sim.cache_clear()
    return {"ok": True, "by": user["username"],
            "updated": updated, "persisted": saved_remote,
            "storage": "supabase" if odds_store.enabled() else "local"}


class StatEntry(BaseModel):
    home: str
    away: str
    raw: str            # volcado cru do Web Scraper de Sofascore


class StatsUpload(BaseModel):
    jornada: int
    entries: list[StatEntry]


@app.get("/api/admin/previous-matches")
def admin_previous_matches(user: dict = Depends(require_admin)):
    """
    Últimos partidos XOGADOS (ordenados por data), para meter as estatísticas xG. Non se
    limita a unha xornada fixa: así os aprazamentos non descuadran nada (pode haber
    partidos xogados de distintas xornadas mesturados). Devolve se xa hai stats por partido.
    """
    data = load()
    from . import odds_store
    stats_rows = odds_store.load_stats()
    have = {(s["home"], s["away"]) for s in stats_rows}
    played = data.get("played", [])
    if played:
        # ordenar por data (desc) e xornada; amosar os últimos ~15 partidos xogados
        src = sorted(played, key=lambda x: (x.get("date") or "0000", x["jornada"]))[-15:]
        src = list(reversed(src))
        j = src[0]["jornada"] if src else None
    else:
        j = min((m["jornada"] for m in data.get("remaining", [])), default=None)
        src = [m for m in data.get("remaining", []) if m["jornada"] == j]
    matches = [{
        "jornada": m["jornada"], "date": m.get("date"),
        "home": m["home"], "away": m["away"],
        "home_slug": SLUG_BY_NAME[m["home"]], "away_slug": SLUG_BY_NAME[m["away"]],
        "has_stats": (m["home"], m["away"]) in have,
    } for m in src]
    return {"jornada": j, "matches": matches}


@app.post("/api/admin/stats")
def admin_set_stats(payload: StatsUpload, user: dict = Depends(require_admin)):
    """
    Recibe volcados crus de Sofascore por partido, PARSÉAOS e garda as estatísticas
    (xG, tiros, posesión...) en Supabase. Non toca o motor de predición: é capa de
    análise. Só admin.
    """
    from . import odds_store
    from .sofascore_parser import parse_match
    saved = 0
    parsed_out = []
    for e in payload.entries:
        if not e.raw or not e.raw.strip():
            continue
        parsed = parse_match(e.raw)
        if not parsed["home"] or "xg" not in parsed["home"]:
            continue   # sen xG útil, ignoramos
        try:
            ok = odds_store.save_stats(payload.jornada, e.home, e.away,
                                       parsed["home"], parsed["away"])
            if ok:
                saved += 1
        except Exception as exc:
            raise HTTPException(502, f"Erro gardando stats en Supabase: {exc}")
        parsed_out.append({"home": e.home, "away": e.away,
                           "xg": [parsed["home"].get("xg"), parsed["away"].get("xg")]})
    return {"ok": True, "by": user["username"], "jornada": payload.jornada,
            "saved": saved, "parsed": parsed_out,
            "storage": "supabase" if odds_store.enabled() else "sen persistencia (configura Supabase)"}


class RatingsUpload(BaseModel):
    jornada: int
    raw: str            # volcado cru da páxina de estatísticas de xogadores (UDO)


@app.get("/api/admin/udo-last-match")
def admin_udo_last_match(user: dict = Depends(require_admin)):
    """
    Devolve o ÚLTIMO partido xogado pola UD Ourense (para asociar correctamente os
    oRatings). Así non depende dunha 'xornada anterior' abstracta que os aprazamentos
    poderían descuadrar: os oRatings van sempre ao partido real que xogou a UDO.
    """
    data = load()
    udo_played = [m for m in data.get("played", [])
                  if "UD Ourense" in (m["home"], m["away"])]
    if not udo_played:
        # aínda sen partidos: usar o próximo como referencia informativa
        upcoming = sorted([m for m in data.get("remaining", [])
                           if "UD Ourense" in (m["home"], m["away"])],
                          key=lambda x: (x.get("date") or "9999", x["jornada"]))
        if upcoming:
            m = upcoming[0]
            return {"jornada": m["jornada"], "home": m["home"], "away": m["away"],
                    "played": False, "date": m.get("date")}
        return {"jornada": None, "played": False}
    last = sorted(udo_played, key=lambda x: (x.get("date") or "0000", x["jornada"]))[-1]
    rival = last["away"] if last["home"] == "UD Ourense" else last["home"]
    return {"jornada": last["jornada"], "home": last["home"], "away": last["away"],
            "rival": rival, "played": True, "date": last.get("date"),
            "score": [last.get("hg"), last.get("ag")]}


@app.post("/api/admin/ratings")
def admin_set_ratings(payload: RatingsUpload, user: dict = Depends(require_admin)):
    """
    Recibe o volcado das estatísticas de xogador da UD Ourense, calcula o oRating de
    cada un e gárdao (Supabase). Só admin. É unha capa de análise (non toca o motor).
    """
    from . import odds_store
    from .orating import parse_lineup
    players = parse_lineup(payload.raw)
    if not players:
        raise HTTPException(400, "Non se puido parsear ningún xogador do volcado.")
    saved = 0
    try:
        saved = odds_store.save_ratings(payload.jornada, players)
    except Exception as exc:
        raise HTTPException(502, f"Erro gardando oRatings en Supabase: {exc}")
    _team_xg_cache_clear()
    ranked = sorted(players, key=lambda p: -p["oRating"])
    return {"ok": True, "by": user["username"], "jornada": payload.jornada,
            "count": len(players), "saved": saved,
            "ratings": [{"name": p["name"], "oRating": p["oRating"], "pos": p["pos"]} for p in ranked],
            "storage": "supabase" if odds_store.enabled() else "sen persistencia (configura Supabase)"}


class SquadMetaEntry(BaseModel):
    name: str                    # nome de Sofascore (referencia interna)
    nick: str | None = None      # apodo/nome a amosar no frontend
    dorsal: int | None = None
    pos: str | None = None       # GK/DEF/MED/DEL
    note: str | None = None      # frase/adxectivo curto
    alias: str | None = None     # nome(s) alt. para casar co volcado (separados por comas)
    signing: bool = False        # True se é un fichaxe engadido a man


class SquadMetaUpload(BaseModel):
    players: list[SquadMetaEntry]


@app.get("/api/admin/squad")
def admin_get_squad(user: dict = Depends(require_admin)):
    """Plantilla completa (base + edicións + fichaxes) para editar no panel."""
    return get_squad()


@app.post("/api/admin/squad")
def admin_save_squad(payload: SquadMetaUpload, user: dict = Depends(require_admin)):
    """Garda edicións da plantilla (apodo, dorsal, posición, nota) e fichaxes."""
    from . import odds_store
    players = [e.model_dump() for e in payload.players]
    saved = 0
    try:
        saved = odds_store.save_squad_meta(players)
    except Exception as exc:
        raise HTTPException(502, f"Erro gardando a plantilla en Supabase: {exc}")
    return {"ok": True, "by": user["username"], "saved": saved,
            "storage": "supabase" if odds_store.enabled() else "sen persistencia (configura Supabase)"}


@app.delete("/api/admin/squad/{name}")
def admin_delete_signing(name: str, user: dict = Depends(require_admin)):
    """Borra un fichaxe engadido a man."""
    from . import odds_store
    try:
        odds_store.delete_squad_meta(name)
    except Exception as exc:
        raise HTTPException(502, f"Erro borrando: {exc}")
    return {"ok": True, "deleted": name}


@app.get("/api/player/{name}")
def player_detail(name: str):
    """
    Detalle dun xogador para a súa ficha: agrega TODAS as estatísticas gardadas dos
    seus partidos (goles, asistencias, minutos, pases, duelos...) e deriva métricas
    (goles/90, asist/90, % pases, % duelos gañados, oRating medio, forma...).
    """
    from . import odds_store
    import json as _json
    import urllib.parse
    ratings = odds_store.load_ratings()

    def norm(s):
        return (s or "").lower().strip()

    # recoller as filas detalladas do xogador (o campo 'detail' garda o parse completo)
    mine = []
    if odds_store.enabled():
        # pedimos o detalle completo (non só o resumo de load_ratings)
        try:
            import httpx
            url = (f"{odds_store.SUPABASE_URL}/rest/v1/{odds_store.RATINGS_TABLE}"
                   f"?player=eq.{urllib.parse.quote(name)}"
                   f"&select=jornada,orating,detail")
            with httpx.Client(timeout=15) as client:
                r = client.get(url, headers=odds_store._headers())
                r.raise_for_status()
                for row in r.json():
                    d = row.get("detail")
                    if isinstance(d, str):
                        d = _json.loads(d)
                    if d:
                        d["jornada"] = row["jornada"]
                        d["oRating"] = row.get("orating")
                        mine.append(d)
        except Exception:
            mine = []

    if not mine:
        return {"name": name, "games": 0, "stats": None}

    n = len(mine)
    tot_min = sum(p.get("mins", 0) for p in mine) or 1
    goals = sum(p.get("goals", 0) for p in mine)
    assists = sum(p.get("assists", 0) for p in mine)
    pass_ok = sum(p.get("pass_ok", 0) for p in mine)
    pass_tot = sum(p.get("pass_tot", 0) for p in mine)
    duels_w = sum(p.get("duels_won", 0) + p.get("aerial_won", 0) for p in mine)
    duels_t = sum(p.get("duels_tot", 0) + p.get("aerial_tot", 0) for p in mine)
    tackles = sum(p.get("tackles_won", 0) for p in mine)
    oratings = [p["oRating"] for p in mine if p.get("oRating") is not None]

    stats = {
        "games": n,
        "minutes": tot_min,
        "goals": goals,
        "assists": assists,
        "ga": goals + assists,                                   # contribucións
        "goals_per90": round(goals / tot_min * 90, 2),
        "assists_per90": round(assists / tot_min * 90, 2),
        "ga_per90": round((goals + assists) / tot_min * 90, 2),
        "min_per_goal": round(tot_min / goals) if goals else None,
        "passes_pg": round(pass_ok / n, 1),
        "pass_pct": round(pass_ok / pass_tot * 100) if pass_tot else None,
        "duels_won_pct": round(duels_w / duels_t * 100) if duels_t else None,
        "duels_won_pg": round(duels_w / n, 1),
        "tackles_pg": round(tackles / n, 1),
        "orating_avg": round(sum(oratings) / len(oratings), 1) if oratings else None,
        "orating_best": max(oratings) if oratings else None,
        "form": [{"jornada": p["jornada"], "oRating": p.get("oRating")} for p in sorted(mine, key=lambda x: x["jornada"])],
    }
    return {"name": name, "games": n, "stats": stats}


@app.get("/api/report/next")
def report_next(team: str = "UD Ourense"):
    """
    Xera o informe técnico previo ao próximo partido da UDO en PDF (2 páxinas).
    Recompila datos reais: predición, xG do rival e da UDO, oRatings dos xogadores,
    contexto casa/fóra. Devolve o PDF como descarga.
    """
    from fastapi.responses import Response
    from pathlib import Path
    from . import odds_store, xg_analysis
    from .report import build_report

    data_all = load()
    if team not in NAMES:
        raise HTTPException(404, "Equipo descoñecido")
    upcoming = [m for m in sorted(data_all["remaining"], key=lambda x: x["jornada"])
                if team in (m["home"], m["away"])]
    if not upcoming:
        raise HTTPException(404, "Non hai próximo partido")
    m = upcoming[0]
    model = _fit_model(data_all)
    is_home = m["home"] == team
    rival = m["away"] if is_home else m["home"]
    p = model.match_probs(m["home"], m["away"], odds=m.get("odds"))

    # xG agregado (se hai estatísticas)
    stats_rows = odds_store.load_stats()
    udo_xg = xg_analysis.team_xg_stats(team, stats_rows, data_all["played"]) or {}
    rival_xg = xg_analysis.team_xg_stats(rival, stats_rows, data_all["played"]) or {}

    # clasificación para goles reais a favor/contra
    standings = {r["team"]: r for r in _standings(data_all)}
    udo_s = standings.get(team, {})
    rival_s = standings.get(rival, {})

    # oRatings dos nosos xogadores (con apodo/posición do squad_meta se existe)
    ratings = odds_store.load_ratings()
    meta_rows = odds_store.load_squad_meta()

    def _norm(s):
        return (s or "").lower().strip()

    meta_by_name = {_norm(mm["name"]): mm for mm in meta_rows}
    # tamén cargamos o squad.json base para a posición por defecto
    from pathlib import Path as _Path
    import json as _json
    squad_file = _Path(__file__).resolve().parent.parent / "data" / "squad.json"
    base_squad = _json.loads(squad_file.read_text(encoding="utf-8")) if squad_file.exists() else []
    base_by_name = {_norm(p["name"]): p for p in base_squad}

    def display_name(name):
        m = meta_by_name.get(_norm(name))
        if m and m.get("nick"):
            return m["nick"]
        return name

    def display_pos(name, fallback):
        m = meta_by_name.get(_norm(name))
        if m and m.get("pos"):
            return m["pos"]
        b = base_by_name.get(_norm(name))
        if b and b.get("pos"):
            return b["pos"]
        return fallback

    by_player = {}
    for r in ratings:
        by_player.setdefault(r["player"], []).append(r)
    players = []
    for name, recs in by_player.items():
        vals = [x["orating"] for x in recs if x.get("orating") is not None]
        if vals:
            last = sorted(recs, key=lambda x: x["jornada"])[-2:]
            players.append({
                "name": display_name(name),
                "pos": display_pos(name, recs[-1].get("pos", "—")),
                "oRating": round(sum(vals) / len(vals), 1),
                "form_txt": " · ".join(str(x["orating"]) for x in last),
                "_avg": sum(vals) / len(vals),
            })
    players.sort(key=lambda x: -x["_avg"])

    pw = round((p["home_win"] if is_home else p["away_win"]) * 100)
    pl = round((p["away_win"] if is_home else p["home_win"]) * 100)
    def lbl_finish(s):
        d = s.get("off_diff", 0)
        return "Sobresaínte" if d >= 2 else "Escasa (xera máis do que marca)" if d <= -2 else "Axustada"

    def lbl_def(s):
        d = s.get("def_diff", 0)
        return "Sólida" if d >= 2 else "Permisiva" if d <= -2 else "Correcta"

    from . import report_copy as rc
    seed = m["jornada"]   # mesmo partido → mesmo informe; xornadas distintas varían

    # análise do rival: Gemini (datos reais, sen inventar) ou fallback ao repertorio
    rival_block = {
        "gf": rival_s.get("gf", "—"), "ga": rival_s.get("ga", "—"),
        "xgf": rival_xg.get("xgf", "—"), "xga": rival_xg.get("xga", "—"),
        "form_label": "".join(rival_s.get("form", [])[-4:]) or "—",
    }
    udo_block = {
        "gf": udo_s.get("gf", "—"), "ga": udo_s.get("ga", "—"),
        "xgf": udo_xg.get("xgf", "—"),
        "finish_label": lbl_finish(udo_xg), "defense_label": lbl_def(udo_xg),
    }
    keys_for = _report_keys_for(rival_xg, rival_s, seed)
    venue_analysis = rc.venue_analysis(is_home, seed)
    context_news = None
    try:
        from . import gemini
        gm = gemini.report_matchup(m["home"], m["away"], is_home,
                                   rival_block, udo_block, pw, round(p["draw"]*100), pl, lang="gl")
        if gm:
            # a clave de Gemini vai a primeira posición; mantense o resto do repertorio
            keys_for = [gm["key_for"]] + keys_for[:2]
            venue_analysis = gm["venue_analysis"]
        # contexto de dinámica recente a partir de noticias (só dinámica, sen rumores)
        rival_name = m["away"] if is_home else m["home"]
        context_news = gemini.context_from_news(rival_name, is_home, lang="gl")
    except Exception:
        pass

    data = {
        "jornada": m["jornada"], "home": m["home"], "away": m["away"], "is_home": is_home,
        "venue_label": "En casa" if is_home else "Fóra",
        "venue_place": ("no Couto" if is_home else "a domicilio"),
        "venue_context": ("O Couto" if is_home else "a domicilio"),
        "p_win": pw, "p_draw": round(p["draw"] * 100), "p_loss": pl,
        "expected_score": p["likely_score"],
        "og_home": p["oGoals_home"], "og_away": p["oGoals_away"],
        "og_home_label": m["home"], "og_away_label": m["away"],
        "favor_text": rc.favor_text(pw, pl, seed),
        "venue_text": rc.venue_text(is_home, seed),
        "rival": rival_block,
        "udo": udo_block,
        "players": players,
        "keys_for": keys_for,
        "keys_against": rc.keys_against(seed),
        "venue_analysis": venue_analysis,
        "context_news": context_news,
        "scenario_lead": rc.scenario_lead(seed),
        "scenario_behind": rc.scenario_behind(seed),
        "advice": rc.advice(seed),
    }

    logo = Path(__file__).resolve().parent.parent.parent / "frontend" / "public" / "escudos" / "logo.png"
    pdf = build_report(data, logo_path=str(logo) if logo.exists() else None)

    def _slugify(s):
        import unicodedata, re as _re
        s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
        return _re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

    fname = f"informe-j{m['jornada']}-{_slugify(m['home'])}-{_slugify(m['away'])}.pdf"
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{fname}"'})


def _report_keys_for(rival_xg: dict, rival_s: dict, seed: int = 0) -> list[str]:
    """Xera as claves ofensivas segundo as debilidades do rival (datos + variantes)."""
    from . import report_copy as rc
    keys = []
    if rival_xg.get("def_diff", 0) <= -1.5 or (rival_s.get("ga") or 0) >= 2:
        keys.append(rc._pick(rc.KEY_RIVAL_CONCEDE, seed))
    if rival_xg.get("xga", 0) and rival_xg.get("xga", 0) >= 1.5:
        keys.append(rc._pick(rc.KEY_RIVAL_XGA, seed))
    keys.append(rc._pick(rc.KEY_FINISH, seed))
    return keys[:3]


# =========================== ONCE INICIAL (aliñacións) =======================

@app.get("/api/lineup/formations")
def lineup_formations():
    """Devolve as formacións dispoñibles coas coordenadas (X,Y en %) de cada slot."""
    from .formations import FORMATIONS
    return {"formations": FORMATIONS}


@app.get("/api/lineup/matchdays")
def lineup_matchdays():
    """
    Lista as xornadas relevantes para o once: as XOGADAS pola UDO (con rival e marcador)
    e a PRÓXIMA. Indica cales xa teñen aliñación gardada.
    """
    data = load()
    from . import odds_store
    saved = {l["jornada"] for l in odds_store.load_all_lineups()}

    def udo_side(m):
        is_home = m["home"] == "UD Ourense"
        rival = m["away"] if is_home else m["home"]
        return is_home, rival

    played = []
    for m in sorted([x for x in data.get("played", []) if "UD Ourense" in (x["home"], x["away"])],
                    key=lambda x: x["jornada"]):
        is_home, rival = udo_side(m)
        played.append({"jornada": m["jornada"], "rival": rival, "is_home": is_home,
                       "rival_slug": SLUG_BY_NAME.get(rival), "score": [m.get("hg"), m.get("ag")],
                       "has_lineup": m["jornada"] in saved, "kind": "played"})
    upcoming = sorted([x for x in data.get("remaining", []) if "UD Ourense" in (x["home"], x["away"])],
                      key=lambda x: (x.get("date") or "9999", x["jornada"]))
    nxt = None
    if upcoming:
        m = upcoming[0]
        is_home, rival = udo_side(m)
        nxt = {"jornada": m["jornada"], "rival": rival, "is_home": is_home,
               "rival_slug": SLUG_BY_NAME.get(rival), "date": m.get("date"),
               "has_lineup": m["jornada"] in saved, "kind": "next"}
    return {"played": played, "next": nxt}


@app.get("/api/lineup/{jornada}")
def get_lineup(jornada: int):
    """
    Devolve a aliñación gardada dunha xornada (formación + xogadores colocados). Se é
    unha xornada xogada, engade o oRating de cada xogador (co seu nome DISPLAY/apodo).
    Se non hai aliñación gardada, devolve os slots baleiros da formación por defecto.
    """
    from . import odds_store
    from .formations import FORMATIONS
    data = load()

    # contexto do partido
    match = next((m for m in data.get("played", []) + data.get("remaining", [])
                  if m["jornada"] == jornada and "UD Ourense" in (m["home"], m["away"])), None)
    ctx = None
    if match:
        is_home = match["home"] == "UD Ourense"
        rival = match["away"] if is_home else match["home"]
        ctx = {"jornada": jornada, "rival": rival, "rival_slug": SLUG_BY_NAME.get(rival),
               "is_home": is_home, "score": [match.get("hg"), match.get("ag")]
               if "hg" in match else None}

    saved = odds_store.load_lineup(jornada)

    # oRatings desa xornada + apodos (display) + minutos
    ratings = odds_store.load_ratings()
    meta = {mm["name"].lower().strip(): mm for mm in odds_store.load_squad_meta()}
    orating_by = {}
    mins_by = {}
    for r in ratings:
        if r["jornada"] == jornada and r.get("orating") is not None:
            orating_by[r["player"].lower().strip()] = r["orating"]
            mins_by[r["player"].lower().strip()] = r.get("mins")

    def display_of(name):
        m = meta.get((name or "").lower().strip())
        return (m.get("nick") if m and m.get("nick") else name)

    if saved:
        players = saved["players"]
        titular_keys = set()
        for p in players:
            key = (p.get("name") or "").lower().strip()
            p["display"] = display_of(p.get("name"))
            if key in orating_by:
                p["oRating"] = orating_by[key]
            if p.get("name"):
                titular_keys.add(key)
        # SUPLENTES: xogadores con nota nesa xornada que NON están no once titular.
        # Amosan a súa nota no panel (xogaron minutos pero non foron titulares).
        subs = []
        for r in ratings:
            if r["jornada"] != jornada or r.get("orating") is None:
                continue
            key = r["player"].lower().strip()
            if key in titular_keys:
                continue
            subs.append({"name": r["player"], "display": display_of(r["player"]),
                         "oRating": r["orating"], "mins": r.get("mins")})
        # ordenar por minutos (máis primeiro), logo por nota
        subs.sort(key=lambda s: (-(s.get("mins") or 0), -(s.get("oRating") or 0)))
        return {"formation": saved["formation"], "players": players,
                "context": ctx, "saved": True, "subs": subs}

    # sen aliñación: slots baleiros da formación por defecto
    formation = "4-2-3-1"
    slots = [{"x": s["x"], "y": s["y"], "role": s["role"], "name": None, "display": None}
             for s in FORMATIONS[formation]]
    return {"formation": formation, "players": slots, "context": ctx, "saved": False, "subs": []}


class LineupPlayer(BaseModel):
    name: str | None = None    # nome canónico (Sofascore/squad) ou None se baleiro
    x: float
    y: float
    role: str | None = None


class LineupUpload(BaseModel):
    jornada: int
    formation: str
    players: list[LineupPlayer]


@app.post("/api/admin/lineup")
def admin_save_lineup(payload: LineupUpload, user: dict = Depends(require_admin)):
    """Garda a aliñación dunha xornada (só admin). Persiste en Supabase."""
    from . import odds_store
    if not odds_store.enabled():
        raise HTTPException(400, "Fai falta Supabase para gardar aliñacións.")
    data = load()
    match = next((m for m in data.get("played", []) + data.get("remaining", [])
                  if m["jornada"] == payload.jornada and "UD Ourense" in (m["home"], m["away"])), None)
    is_home = (match["home"] == "UD Ourense") if match else None
    rival = None
    if match:
        rival = match["away"] if is_home else match["home"]
    players = [p.model_dump() for p in payload.players]
    try:
        odds_store.save_lineup(payload.jornada, payload.formation, players, is_home, rival)
    except Exception as exc:
        raise HTTPException(502, f"Erro gardando a aliñación: {exc}")
    return {"ok": True, "by": user["username"], "jornada": payload.jornada,
            "formation": payload.formation, "count": len(players)}


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


@app.get("/api/admin/health")
def admin_health():
    """
    Diagnóstico do login (NON revela o contrasinal). Serve para saber por que falla
    o acceso admin: se as variables de entorno están postas e se o usuario existe.
    Abrir en: <api>/api/admin/health
    """
    from .auth import _load_users
    env_user = os.environ.get("ADMIN_USER")
    env_pass_set = bool(os.environ.get("ADMIN_PASSWORD"))
    users = _load_users()
    admin_names = [u for u, d in users.items() if d.get("role") == "admin"]
    return {
        "env_ADMIN_USER_set": bool(env_user),
        "env_ADMIN_USER_value": env_user or None,   # o usuario non é secreto
        "env_ADMIN_PASSWORD_set": env_pass_set,
        "users_file_exists": bool(users),
        "admin_users_registered": admin_names,
        "hint": ("Se env_ADMIN_*_set é False, define ADMIN_USER e ADMIN_PASSWORD en Render. "
                 "Se están postas pero admin_users_registered está baleiro, reinicia o servizo. "
                 "Login: usa exactamente o valor de ADMIN_USER e ADMIN_PASSWORD (sen espazos)."),
    }


@app.get("/")
def root():
    return {"app": "Ourense é UD", "docs": "/docs"}
