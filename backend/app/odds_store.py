"""
odds_store.py — Persistencia das cuotas en Supabase (PostgreSQL na nube).

Por que Supabase e non o disco de Render: o plan gratuíto de Render borra o disco
ao reiniciar/durmir, así que as cuotas metidas o martes perderíanse. Supabase
gárdaas de verdade.

Usa a API REST de Supabase (sen dependencias pesadas, só httpx que xa temos vía
FastAPI). A CLAVE SECRETA vai nunha variable de entorno de Render, NUNCA no frontend.

FALLBACK: se non hai variables de entorno de Supabase configuradas, todas as
funcións devolven None/[] e o resto do sistema segue co JSON local. Así non se
rompe nada; a persistencia actívase só cando poñas as claves en Render.

Configuración en Render (Environment):
  SUPABASE_URL     = https://<proxecto>.supabase.co
  SUPABASE_KEY     = sb_secret_xxx  (clave secreta, ou service_role legacy)

Táboa esperada en Supabase (créase co SQL que se indica no PROCESO.md):
  create table odds (
    jornada int, home text, away text,
    c_home float8, c_draw float8, c_away float8,
    updated_at timestamptz default now(),
    primary key (jornada, home, away)
  );
"""
import os
import httpx

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
TABLE = "odds"


def enabled() -> bool:
    """True se Supabase está configurado. Se non, o sistema usa o JSON local."""
    return bool(SUPABASE_URL and SUPABASE_KEY)


def _headers() -> dict:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }


def save_odds(jornada: int, entries: list[dict]) -> int:
    """
    Garda (upsert) as cuotas dunha xornada. `entries` = [{home,away,c_home,c_draw,c_away}].
    Devolve cantas se gardaron. Se Supabase non está activo, devolve 0.
    """
    if not enabled() or not entries:
        return 0
    rows = [{
        "jornada": jornada,
        "home": e["home"], "away": e["away"],
        "c_home": e["c_home"], "c_draw": e["c_draw"], "c_away": e["c_away"],
    } for e in entries]
    url = f"{SUPABASE_URL}/rest/v1/{TABLE}"
    # Prefer: resolution=merge-duplicates → upsert pola clave primaria
    headers = {**_headers(), "Prefer": "resolution=merge-duplicates,return=minimal"}
    with httpx.Client(timeout=15) as client:
        r = client.post(url, json=rows, headers=headers)
        r.raise_for_status()
    return len(rows)


def load_odds() -> dict:
    """
    Le todas as cuotas gardadas. Devolve un dict {(home,away): {home,draw,away}}
    para inxectar rápido no calendario. Se Supabase non está activo, devolve {}.
    """
    if not enabled():
        return {}
    url = f"{SUPABASE_URL}/rest/v1/{TABLE}?select=jornada,home,away,c_home,c_draw,c_away"
    try:
        with httpx.Client(timeout=15) as client:
            r = client.get(url, headers=_headers())
            r.raise_for_status()
            data = r.json()
    except Exception:
        return {}   # ante calquera fallo, seguimos co modelo só (sen cuotas)
    out = {}
    for row in data:
        out[(row["home"], row["away"])] = {
            "home": row["c_home"], "draw": row["c_draw"], "away": row["c_away"],
        }
    return out


# ---------------------------------------------------------------- match stats --
STATS_TABLE = "match_stats"


def save_stats(jornada: int, home: str, away: str,
               stats_home: dict, stats_away: dict) -> bool:
    """
    Garda (upsert) as estatísticas dun partido (xG, tiros, posesión, etc.) como
    dous JSON (local e visitante). Se Supabase non está activo, devolve False.
    """
    if not enabled():
        return False
    import json as _json
    row = {
        "jornada": jornada, "home": home, "away": away,
        "stats_home": _json.dumps(stats_home), "stats_away": _json.dumps(stats_away),
    }
    url = f"{SUPABASE_URL}/rest/v1/{STATS_TABLE}"
    headers = {**_headers(), "Prefer": "resolution=merge-duplicates,return=minimal"}
    with httpx.Client(timeout=15) as client:
        r = client.post(url, json=[row], headers=headers)
        r.raise_for_status()
    return True


def load_stats() -> list[dict]:
    """
    Le todas as estatísticas de partidos gardadas. Devolve unha lista de
    {jornada, home, away, stats_home, stats_away}. Se non hai Supabase, [].
    """
    if not enabled():
        return []
    import json as _json
    url = f"{SUPABASE_URL}/rest/v1/{STATS_TABLE}?select=jornada,home,away,stats_home,stats_away"
    try:
        with httpx.Client(timeout=15) as client:
            r = client.get(url, headers=_headers())
            r.raise_for_status()
            data = r.json()
    except Exception:
        return []
    out = []
    for row in data:
        try:
            sh = _json.loads(row["stats_home"]) if isinstance(row["stats_home"], str) else row["stats_home"]
            sa = _json.loads(row["stats_away"]) if isinstance(row["stats_away"], str) else row["stats_away"]
        except Exception:
            sh, sa = {}, {}
        out.append({"jornada": row["jornada"], "home": row["home"],
                    "away": row["away"], "stats_home": sh, "stats_away": sa})
    return out


# ---------------------------------------------------- player oRatings (UDO) ----
RATINGS_TABLE = "player_ratings"


def save_ratings(jornada: int, players: list[dict]) -> int:
    """
    Garda (upsert) os oRatings dos xogadores dunha xornada. `players` = lista de
    dicts con polo menos {name, oRating, pos, mins, goals, assists}. Devolve cantos.
    """
    if not enabled() or not players:
        return 0
    import json as _json
    rows = [{
        "jornada": jornada, "player": p["name"],
        "orating": p["oRating"], "pos": p.get("pos"), "mins": p.get("mins"),
        "detail": _json.dumps(p),
    } for p in players]
    url = f"{SUPABASE_URL}/rest/v1/{RATINGS_TABLE}"
    headers = {**_headers(), "Prefer": "resolution=merge-duplicates,return=minimal"}
    with httpx.Client(timeout=15) as client:
        r = client.post(url, json=rows, headers=headers)
        r.raise_for_status()
    return len(rows)


def load_ratings() -> list[dict]:
    """
    Le todos os oRatings gardados. Devolve lista de {jornada, player, orating, pos, mins}.
    Se non hai Supabase, [].
    """
    if not enabled():
        return []
    url = f"{SUPABASE_URL}/rest/v1/{RATINGS_TABLE}?select=jornada,player,orating,pos,mins"
    try:
        with httpx.Client(timeout=15) as client:
            r = client.get(url, headers=_headers())
            r.raise_for_status()
            return r.json()
    except Exception:
        return []


# ------------------------------------------------- squad meta (edición admin) --
SQUAD_TABLE = "squad_meta"


def save_squad_meta(players: list[dict]) -> int:
    """
    Garda (upsert) os datos editables da plantilla: apodo (nome no frontend), dorsal,
    posición, nota/adxectivo, e se é un fichaxe. Clave: name (o nome de Sofascore, ou
    o nome dado para fichaxes). Devolve cantos.
    """
    if not enabled() or not players:
        return 0
    rows = [{
        "name": p["name"],
        "nick": p.get("nick"), "dorsal": p.get("dorsal"),
        "pos": p.get("pos"), "note": p.get("note"),
        "signing": bool(p.get("signing", False)),
    } for p in players]
    url = f"{SUPABASE_URL}/rest/v1/{SQUAD_TABLE}"
    headers = {**_headers(), "Prefer": "resolution=merge-duplicates,return=minimal"}
    with httpx.Client(timeout=15) as client:
        r = client.post(url, json=rows, headers=headers)
        r.raise_for_status()
    return len(rows)


def load_squad_meta() -> list[dict]:
    """Le os datos editables da plantilla. Se non hai Supabase, []."""
    if not enabled():
        return []
    url = f"{SUPABASE_URL}/rest/v1/{SQUAD_TABLE}?select=name,nick,dorsal,pos,note,signing"
    try:
        with httpx.Client(timeout=15) as client:
            r = client.get(url, headers=_headers())
            r.raise_for_status()
            return r.json()
    except Exception:
        return []


def delete_squad_meta(name: str) -> bool:
    """Borra un xogador engadido (fichaxe) da táboa squad_meta."""
    if not enabled():
        return False
    import urllib.parse
    q = urllib.parse.quote(name)
    url = f"{SUPABASE_URL}/rest/v1/{SQUAD_TABLE}?name=eq.{q}"
    with httpx.Client(timeout=15) as client:
        r = client.delete(url, headers=_headers())
        r.raise_for_status()
    return True


# ---------------------------------------------- resultados por partido -------
# Cada partido ten estado independente: "played" (con goles) ou "postponed".
# Isto fai que os aprazamentos e a carga parcial NON descuadren nada: non se
# razoa por "xornada completa" senón partido a partido.
RESULTS_TABLE = "match_results"


def save_result(jornada: int, home: str, away: str,
                hg: int | None, ag: int | None, status: str = "played") -> bool:
    """
    Garda (upsert) o resultado dun partido. status: "played" (con hg/ag) ou
    "postponed" (aprazado, sen goles). Clave: jornada+home+away.
    """
    if not enabled():
        return False
    row = {"jornada": jornada, "home": home, "away": away,
           "hg": hg, "ag": ag, "status": status}
    url = f"{SUPABASE_URL}/rest/v1/{RESULTS_TABLE}"
    headers = {**_headers(), "Prefer": "resolution=merge-duplicates,return=minimal"}
    with httpx.Client(timeout=15) as client:
        r = client.post(url, json=[row], headers=headers)
        r.raise_for_status()
    return True


def delete_result(jornada: int, home: str, away: str) -> bool:
    """Borra un resultado (para volver a marcalo como pendente)."""
    if not enabled():
        return False
    import urllib.parse
    q = lambda s: urllib.parse.quote(str(s))
    url = (f"{SUPABASE_URL}/rest/v1/{RESULTS_TABLE}"
           f"?jornada=eq.{q(jornada)}&home=eq.{q(home)}&away=eq.{q(away)}")
    with httpx.Client(timeout=15) as client:
        r = client.delete(url, headers=_headers())
        r.raise_for_status()
    return True


def load_results() -> list[dict]:
    """
    Le todos os resultados/aprazamentos gardados a man. Devolve lista de
    {jornada, home, away, hg, ag, status}. Sen Supabase, [].
    """
    if not enabled():
        return []
    url = f"{SUPABASE_URL}/rest/v1/{RESULTS_TABLE}?select=jornada,home,away,hg,ag,status"
    try:
        with httpx.Client(timeout=15) as client:
            r = client.get(url, headers=_headers())
            r.raise_for_status()
            return r.json()
    except Exception:
        return []
