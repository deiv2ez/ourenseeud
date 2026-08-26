"""
store.py — Capa de datos de la temporada.

Fuente ÚNICA de verdad para la API. Lee/escribe un JSON con:
  - teams:      lista de equipos del grupo
  - played:     partidos ya disputados [{jornada, home, away, hg, ag}]
  - remaining:  calendario pendiente   [{jornada, home, away}]
  - odds:       cuotas por partido      {"home|away": {home, draw, away}}

Diseño deliberadamente simple (un fichero JSON, no una base de datos) porque:
  - el volumen es minúsculo (380 partidos/temporada como mucho),
  - se recalcula por jornada, no en tiempo real,
  - facilita versionar los datos en git y editarlos a mano si hace falta.

Cuando el scraping esté listo, un job semanal reescribe este JSON y la API sirve
lo nuevo sin cambios. El frontend nunca habla con este módulo: habla con la API.
"""

from __future__ import annotations
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "season_2026_27.json"

# Los 20 equipos del Grupo 1 2026-27, con su slug (para escudos) y color.
TEAMS = [
    {"slug": "arenas",        "name": "Arenas Club",         "color": "#111111"},
    {"slug": "bilbao-ath",    "name": "Bilbao Athletic",     "color": "#c10000"},
    {"slug": "barakaldo",     "name": "Barakaldo CF",        "color": "#e0b000"},
    {"slug": "coria",         "name": "CD Coria",            "color": "#123f8c"},
    {"slug": "extremadura",   "name": "CD Extremadura",      "color": "#0b6e3b"},
    {"slug": "lugo",          "name": "CD Lugo",             "color": "#9b1b30"},
    {"slug": "mirandes",      "name": "CD Mirandés",         "color": "#b1121b"},
    {"slug": "leonesa",       "name": "CyD Leonesa",         "color": "#0a1b3d"},
    {"slug": "merida",        "name": "AD Mérida",           "color": "#0b0b0b"},
    {"slug": "pontevedra",    "name": "Pontevedra CF",       "color": "#1a3a7a"},
    {"slug": "racing-ferrol", "name": "Racing Ferrol",       "color": "#0a7a2f"},
    {"slug": "fabril",        "name": "RC Deportivo Fabril", "color": "#1874c4"},
    {"slug": "aviles",        "name": "Real Avilés",         "color": "#111111"},
    {"slug": "real-union",    "name": "Real Unión",          "color": "#c8102e"},
    {"slug": "ponferradina",  "name": "SD Ponferradina",     "color": "#1f5fbf"},
    {"slug": "logrones",      "name": "UD Logroñés",         "color": "#c8102e"},
    {"slug": "ourense",       "name": "UD Ourense",          "color": "#C8102E", "udo": True},
    {"slug": "unionistas",    "name": "Unionistas",          "color": "#0a1b3d"},
    {"slug": "cacereno",      "name": "CP Cacereño",         "color": "#0b6e3b"},
    {"slug": "zamora",        "name": "Zamora CF",           "color": "#c8102e"},
]

NAMES = [t["name"] for t in TEAMS]
SLUG_BY_NAME = {t["name"]: t["slug"] for t in TEAMS}


def load() -> dict:
    """Carga el JSON de temporada. Si no existe, arranca uno vacío coherente."""
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return {"teams": TEAMS, "played": [], "remaining": [], "odds": {}}


def save(data: dict) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def match_key(home: str, away: str) -> str:
    """Clave estable para localizar un partido (y sus cuotas)."""
    return f"{home}|{away}"
