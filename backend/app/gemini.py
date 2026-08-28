"""
gemini.py — Xera análise textual dun equipo con Gemini a partir dos datos DUROS
(xG, goles, tiros...). Só se activa se hai GEMINI_API_KEY en Render.

FALLBACK: sen clave, devolve None e o sistema usa as etiquetas por umbrais
(xg_analysis.fallback_insights). Así non depende de Gemini.

Seguridade: a clave vai SÓ no backend (variable de entorno), nunca no frontend.
Antialucinación: o prompt prohíbe inventar; só pode usar os números dados.
"""
import os
import httpx

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"


def enabled() -> bool:
    return bool(GEMINI_API_KEY)


def analyze_team(team_name: str, s: dict, lang: str = "gl") -> str | None:
    """
    Pide a Gemini 2-3 frases de análise cos datos xG do equipo. Devolve o texto,
    ou None se non hai clave ou falla (o chamador usará o fallback por umbrais).
    """
    if not enabled():
        return None
    idioma = "galego" if lang == "gl" else "castelán"
    prompt = (
        f"Es un analista de fútbol experto na Primeira Federación española (1ª RFEF), "
        f"unha categoría moi igualada e defensiva. Escribe unha análise BREVE (2-3 frases, "
        f"máximo 55 palabras) en {idioma} sobre o rendemento do equipo '{team_name}', "
        f"baseándote SÓ nestes datos reais. NON inventes nada nin engadas datos que non estean aquí. "
        f"Datos ({s['matches']} partidos con estatísticas):\n"
        f"- Goles a favor: {s['gf']} | xG xerado: {s['xgf']} (diferenza {s['off_diff']:+})\n"
        f"- Goles en contra: {s['ga']} | xG concedido: {s['xga']} (diferenza {s['def_diff']:+})\n"
        f"- Tiros por partido: {s['shots_pg']} | Posesión media: {s['possession_avg']}%\n"
        f"Interpreta: diferenza ofensiva negativa = desperdicia ocasións (pouca puntería); "
        f"positiva = moi eficaz. Diferenza defensiva positiva = bloque sólido/afortunado. "
        f"Ton informativo e claro, sen floreos. Non uses markdown."
    )
    try:
        with httpx.Client(timeout=20) as client:
            r = client.post(
                URL,
                headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"},
                json={"contents": [{"parts": [{"text": prompt}]}]},
            )
            r.raise_for_status()
            data = r.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        return text or None
    except Exception:
        return None   # calquera fallo → fallback por umbrais
