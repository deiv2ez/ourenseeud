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

from .store import load, NAMES, SLUG_BY_NAME, match_key
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
def _data_hash(data: dict) -> str:
    """Huella de los datos de temporada para invalidar la caché al cambiar."""
    raw = json.dumps({"p": data["played"], "r": data["remaining"]}, sort_keys=True)
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
    return sorted(rows.values(), key=lambda r: (-r["pts"], -r["gd"], -r["gf"]))


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


@app.get("/api/matchday")
def current_matchday():
    """
    Devuelve la próxima jornada pendiente completa (todos sus partidos), para que
    el simulador la muestre y el usuario fije resultados hipotéticos.
    """
    data = load()
    if not data["remaining"]:
        return {"jornada": None, "matches": []}
    j = min(m["jornada"] for m in data["remaining"])
    matches = [
        {
            "home": m["home"], "home_slug": SLUG_BY_NAME[m["home"]],
            "away": m["away"], "away_slug": SLUG_BY_NAME[m["away"]],
        }
        for m in data["remaining"] if m["jornada"] == j
    ]
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
        p = model.match_probs(m["home"], m["away"])
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
