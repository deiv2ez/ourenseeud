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
