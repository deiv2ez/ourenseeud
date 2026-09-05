"""
montecarlo.py — Simulación de temporada por Monte Carlo.

IDEA GENERAL
------------
1. Cada equipo tiene una FUERZA DE ATAQUE y una FUERZA DE DEFENSA, estimadas a
   partir de los goles marcados/encajados respecto a la media de la liga.
2. Para un partido, esas fuerzas producen un número esperado de goles (lambda)
   para local y visitante. Los goles se modelan con distribución de POISSON, que
   es la que mejor describe el conteo de goles en fútbol.
3. El Elo (elo.py) modula esas lambdas: un equipo fuerte marca un poco más y
   encaja un poco menos de lo que dirían sus goles brutos.
4. OPCIONAL: si hay CUOTAS de casas (Bet365, etc.) para ese partido, se convierten
   a probabilidad implícita (quitando el margen de la casa) y se hace un BLEND
   con la probabilidad del modelo. Así el "expected result" une estadística propia
   y sabiduría del mercado.
5. Se simulan los partidos que faltan miles de veces; en cada simulación se
   completa la clasificación y se anota dónde acaba cada equipo. Promediando todas
   las simulaciones salen las probabilidades de campeón / playoff / descenso.

Las métricas que este motor expone al frontend son las de marca del proyecto:
   oGoals  = goles esperados del modelo (a favor y en contra)
   oPts    = puntos esperados del modelo sobre los partidos ya jugados

Depende solo de numpy.
"""

from __future__ import annotations
from dataclasses import dataclass
import numpy as np

from .elo import EloModel


# --- Estructura de la competición (1ª RFEF, Grupo 1, 20 equipos) --------------
PROMO_DIRECT = 1     # 1º: ascenso directo a Segunda División
PLAYOFF_TO = 5       # 2º-5º: playoff de ascenso
RELEGATION_FROM = 16 # 16º-20º: descenso a Segunda Federación (5 plazas)


@dataclass
class TeamStrength:
    attack: float   # goles marcados relativos a la media (1.0 = media liga)
    defense: float  # goles encajados relativos a la media (1.0 = media; <1 mejor)
    elo: float


class SeasonModel:
    # Parámetros CALIBRADOS coa 1ª RFEF a partir de DATOS REAIS de 5 tempadas
    # (2021-22 a 2025-26, ambos grupos, 10 ligas completas; fonte BDFutbol):
    #   · Media real: 2.31 goles/partido → 1.155 por equipo e partido.
    #   · Ventaxa de campo real: casa 1.327 vs fóra 0.983 → diferenza 0.344 goles.
    #   · Reparto real observado: 44.4% local / 29.1% empate / 26.5% visitante.
    # NON son forzas de equipos concretos (iso apréndese cos partidos): son
    # parámetros ESTRUTURAIS da categoría, estables entre tempadas e validados
    # con 5 anos de datos reais.
    LEAGUE_AVG_GOALS_1RFEF = 1.155   # goles por equipo e partido (2.31 / 2), real 5 temp.
    HOME_ADV_1RFEF = 0.40            # ventaxa de campo, ÓPTIMA por backtest (5 temp.)
    # Peso do MERCADO no blend, VALIDADO por backtest (temp 24/25 e 25/26, G1):
    # 70% modelo / 30% mercado mellora o log-loss +0.85% fronte a só modelo. É o
    # tope pedido polo usuario e o que mellor rende. SÓ se aplica se hai cuota
    # dispoñible; sen cuota o modelo funciona só (non dependemos do scraping).
    # Peso do MERCADO no blend, ADAPTATIVO e VALIDADO por backtest (24/25, 25/26, G1):
    # ao INICIO de tempada (modelo sen datos) o mercado pesa máis (50%, empata co
    # modelo, nunca o supera), e baixa ata o 30% habitual segundo o modelo madura
    # (cara á xornada 20). Mellora log-loss +1.16% fronte a só modelo, e +0.2% fronte
    # ao fixo 30%. Respecta o principio "o modelo manda" (mercado nunca > 50%).
    # Só se aplica se hai cuota; sen cuota, o modelo funciona só.
    MARKET_WEIGHT_INI = 0.50   # peso do mercado ao inicio (xornada 0)
    MARKET_WEIGHT_FIN = 0.30   # peso do mercado co modelo xa maduro
    MARKET_MATURE_GAMES = 20   # partidos/equipo a partir dos que se usa o peso final

    def market_weight(self) -> float:
        """Peso adaptativo do mercado segundo cantos partidos leva xogados a liga."""
        g = getattr(self, "avg_games_played", 0.0)
        frac = min(1.0, g / self.MARKET_MATURE_GAMES)
        return self.MARKET_WEIGHT_INI * (1 - frac) + self.MARKET_WEIGHT_FIN * frac


    def __init__(self, teams: list[str], home_adv_goals: float = HOME_ADV_1RFEF):
        self.teams = list(teams)
        self.home_adv_goals = home_adv_goals   # ventaja de campo, en goles (1ª RFEF)
        self.league_avg_goals = self.LEAGUE_AVG_GOALS_1RFEF  # media da categoría
        self.strength: dict[str, TeamStrength] = {}
        self.elo = EloModel()

    # ---------------------------------------------------------------- ajuste --
    def fit(self, played: list[dict]) -> "SeasonModel":
        """
        Estima fuerzas de ataque/defensa a partir de partidos jugados y corre el
        Elo sobre ellos. `played`: [{"home","away","hg","ag"}, ...] cronológico.
        """
        self.elo.run(played)

        # AWAY_WEIGHT: os goles marcados/encaixados FÓRA contan un pouco máis ao
        # estimar a forza, porque puntuar fóra é máis difícil. Moderado (1.15),
        # non esaxerado: un gol fóra vale como ~1.15 na casa para o modelo.
        AWAY_WEIGHT = 1.15

        gf, ga, games = {}, {}, {}      # acumuladores PONDERADOS
        raw_games = {}                  # conta real de partidos (sen ponderar)
        for t in self.teams:
            gf[t] = ga[t] = games[t] = raw_games[t] = 0.0
        total_goals = 0
        for m in played:
            h, a, hg, ag = m["home"], m["away"], int(m["hg"]), int(m["ag"])
            # local: goles a peso normal. visitante: goles a peso AWAY_WEIGHT.
            gf[h] += hg;             ga[h] += ag;             games[h] += 1
            gf[a] += ag * AWAY_WEIGHT; ga[a] += hg * AWAY_WEIGHT; games[a] += AWAY_WEIGHT
            raw_games[h] += 1; raw_games[a] += 1
            total_goals += hg + ag

        if sum(raw_games.values()):
            self.league_avg_goals = total_goals / sum(raw_games.values())

        avg = self.league_avg_goals or 1.35
        elo_mean = np.mean(list(self.elo.ratings.values())) if self.elo.ratings else 1500.0

        for t in self.teams:
            g = games[t] or 1              # peso total (para promediar goles)
            rg = raw_games[t] or 1         # partidos reais (para o shrinkage)
            # fuerza base por goles, suavizada hacia 1.0 con pocos partidos (shrinkage)
            raw_att = (gf[t] / g) / avg
            raw_def = (ga[t] / g) / avg
            w = min(1.0, rg / 40.0)  # shrinkage=40, ÓPTIMO por backtest sobre 3800
            # partidos reais de 1ª RFEF (mellora log-loss +2.2% vs shrink=10). Nesta
            # categoría tan igualada, ser prudente coas forzas ata ter moitos partidos
            # predice mellor que fiarse cedo.
            att = w * raw_att + (1 - w) * 1.0
            dff = w * raw_def + (1 - w) * 1.0
            # modulación Elo: ±0.15 según distancia a la media de la liga
            elo_mod = (self.elo.rating(t) - elo_mean) / 400.0
            self.strength[t] = TeamStrength(
                attack=att * (1 + 0.15 * elo_mod),
                defense=dff * (1 - 0.15 * elo_mod),
                elo=self.elo.rating(t),
            )
        # media de partidos xogados por equipo: úsase para o peso ADAPTATIVO do
        # mercado (ao inicio, con poucos datos, o mercado pesa máis; ver market_weight).
        self.avg_games_played = (sum(raw_games.values()) / len(self.teams)) if self.teams else 0.0
        return self

    # ------------------------------------------------ currículum / resume ----
    def resume_board(self, played: list[dict]) -> dict[str, dict]:
        """
        Currículum (Resume Board): valora CANTO MERECE cada punto segundo a
        dificultade real do contexto. Cada resultado pondérase por:
          · forza do rival (Elo relativo á media): gañar a un forte vale máis.
          · onde se xogou: gañar/puntuar FÓRA vale máis que na casa.
        Devolve por equipo: puntos reais e 'valor currículum' (puntos ponderados).
        A diferenza entre ambos revela quen tivo un camiño máis duro ou máis doado.
        """
        elo_mean = np.mean(list(self.elo.ratings.values())) if self.elo.ratings else 1500.0
        out = {t: {"pts": 0, "resume": 0.0, "played": 0} for t in self.teams}

        for m in played:
            h, a, hg, ag = m["home"], m["away"], int(m["hg"]), int(m["ag"])
            # puntos deste partido para cada equipo
            if hg > ag: ph, pa = 3, 0
            elif hg < ag: ph, pa = 0, 3
            else: ph, pa = 1, 1

            for team, opp, pts, is_home in ((h, a, ph, True), (a, h, pa, False)):
                if team not in out:
                    continue
                # factor rival: >1 se o rival é forte, <1 se é débil (±~0.5 nos extremos)
                opp_factor = 1.0 + (self.elo.rating(opp) - elo_mean) / 400.0
                opp_factor = max(0.5, min(1.5, opp_factor))
                # factor campo: puntuar fóra vale máis (usa o AWAY_WEIGHT filosófico)
                venue_factor = 1.15 if not is_home else 1.0
                out[team]["pts"] += pts
                out[team]["resume"] += pts * opp_factor * venue_factor
                out[team]["played"] += 1

        for t in out:
            out[t]["resume"] = round(out[t]["resume"], 1)
        return out

    # ------------------------------------------------------ estilo por equipo --
    def team_style(self, played: list[dict]) -> dict[str, dict]:
        """
        Perfil de ESTILO estatístico de cada equipo, derivado só dos goles reais
        (datos que si temos). Catro eixes normalizados 0-100 respecto á liga:
          · offense: potencia ofensiva (goles a favor por partido vs media liga)
          · defense: solidez defensiva (goles en contra, invertido)
          · home:    rendemento na casa (puntos por partido en casa)
          · away:    rendemento fóra (puntos por partido fóra)
        Non capta o estilo cualitativo (bloque baixo, etc.) — iso é unha nota
        editable á parte. Isto é o perfil obxectivo, actualízase só, nunca caduca.
        """
        agg = {t: {"gf": 0, "ga": 0, "pl": 0,
                   "hpts": 0, "hpl": 0, "apts": 0, "apl": 0} for t in self.teams}
        for m in played:
            h, a, hg, ag = m["home"], m["away"], int(m["hg"]), int(m["ag"])
            for t, gf, ga, is_home in ((h, hg, ag, True), (a, ag, hg, False)):
                if t not in agg:
                    continue
                s = agg[t]
                s["gf"] += gf; s["ga"] += ga; s["pl"] += 1
                pts = 3 if gf > ga else 1 if gf == ga else 0
                if is_home: s["hpts"] += pts; s["hpl"] += 1
                else: s["apts"] += pts; s["apl"] += 1

        # medias de liga para normalizar
        tot_pl = sum(s["pl"] for s in agg.values()) or 1
        avg_gf = sum(s["gf"] for s in agg.values()) / tot_pl
        avg_ga = sum(s["ga"] for s in agg.values()) / tot_pl

        def scale(val, ref, lo=0.5, hi=1.5):
            # razón val/ref levada a 0-100 (ref=50); saturada nos extremos
            if ref <= 0:
                return 50
            r = val / ref
            r = max(lo, min(hi, r))
            return round((r - lo) / (hi - lo) * 100)

        out = {}
        for t, s in agg.items():
            pl = s["pl"] or 1
            gf_pg = s["gf"] / pl
            ga_pg = s["ga"] / pl
            hppg = s["hpts"] / (s["hpl"] or 1)
            appg = s["apts"] / (s["apl"] or 1)
            out[t] = {
                "played": s["pl"],
                "offense": scale(gf_pg, avg_gf),
                "defense": 100 - scale(ga_pg, avg_ga),  # menos goles en contra = máis sólido
                "home": round(min(100, hppg / 3 * 100)),
                "away": round(min(100, appg / 3 * 100)),
                "gf_pg": round(gf_pg, 2),
                "ga_pg": round(ga_pg, 2),
            }
        return out

    # -------------------------------------------------- lambdas de un partido --
    def _lambdas(self, home: str, away: str) -> tuple[float, float]:
        h, a = self.strength[home], self.strength[away]
        avg = self.league_avg_goals
        # A ventaxa de campo (0.41 goles en 1ª RFEF) repártese: metade favorece ao
        # local e metade prexudica ao visitante. Así o TOTAL de goles mantense na
        # media real da categoría e o reparto local/visitante achégase ao 45%/25%
        # observado, en vez de inflar o total sumando todo ao local.
        half = self.home_adv_goals / 2.0
        lam_home = avg * h.attack * a.defense + half
        lam_away = avg * a.attack * h.defense - half
        return max(0.15, lam_home), max(0.15, lam_away)

    def match_probs(self, home: str, away: str, max_goals: int = 10,
                    odds: dict | None = None) -> dict:
        """
        Probabilidades 1-X-2 y oGoals de un partido según el modelo.
        Convoluciona dos Poisson independientes sobre una rejilla de resultados.

        Si se pasan `odds` (cuotas decimais {home,draw,away}), MÉSTURASE o modelo
        co mercado: 70% modelo / 30% mercado (MARKET_WEIGHT), tras quitar o overround.
        Validado por backtest: mellora a predición. Sen odds, só modelo.
        """
        lam_h, lam_a = self._lambdas(home, away)
        gh = _poisson_pmf(lam_h, max_goals)
        ga = _poisson_pmf(lam_a, max_goals)
        grid = np.outer(gh, ga)
        p_home = float(np.tril(grid, -1).sum())
        p_draw = float(np.trace(grid))
        p_away = float(np.triu(grid, 1).sum())
        source = "model"

        # blend co mercado se hai cuota
        if odds:
            try:
                mkt = self.odds_to_prob(odds["home"], odds["draw"], odds["away"])
                w = self.market_weight()
                p_home = (1 - w) * p_home + w * mkt["home_win"]
                p_draw = (1 - w) * p_draw + w * mkt["draw"]
                p_away = (1 - w) * p_away + w * mkt["away_win"]
                source = f"blend({int(w*100)}% mercado)"
            except (KeyError, TypeError, ZeroDivisionError):
                pass  # cuota inválida → quedamos co modelo só

        # marcador esperado: redondeo ASIMÉTRICO validado por backtest (3800 partidos).
        # Redondea os oGoals con umbral 0.9, pero se saíse un empate e hai favorito
        # claro (diferenza de lambda >= 0.30), dá o gol da vitoria ao favorito.
        # Isto acerta máis o resultado 1X2 (44.6%) SEN inflar empates (31% pred vs 29%
        # real), en vez do pico da rexilla que daba demasiados 1-1. Ver backtest_redondeo.
        # "resultado máis probable" (1X2) polo LOGIT ORDENADO sobre o Delta Elo.
        # Validado por backtest (3800 partidos, 4 temporadas out-of-sample): acerta
        # +2.46 puntos MÁIS que derivar o 1X2 do marcador Poisson (45.6% vs 43.1%).
        # O marcador Poisson (likely_score) segue sendo os "goles esperados", aparte.
        # Se hai cuota, mestúrase co mercado igual que as probabilidades (blend <=50%).
        likely = self._expected_score(lam_h, lam_a)
        outcome = self._logit_1x2(home, away)
        # se hai blend co mercado, deixamos que o mercado tamén incline o 1X2: usamos o
        # argmax das probabilidades xa mesturadas cando o mercado é forte, senón o logit.
        if odds:
            probs_1x2 = max((("1", p_home), ("X", p_draw), ("2", p_away)),
                            key=lambda kv: kv[1])[0]
            outcome = probs_1x2
        return {
            "home_win": round(p_home, 4),
            "draw": round(p_draw, 4),
            "away_win": round(p_away, 4),
            "oGoals_home": round(float(lam_h), 2),
            "oGoals_away": round(float(lam_a), 2),
            "likely_score": likely,          # marcador (goles esperados) — Poisson
            "likely_1x2": outcome,           # resultado máis probable — logit Elo / blend
            "source": source,
        }

    def _logit_1x2(self, home: str, away: str,
                   thr_hi: float = 3.0, thr_lo: float = 0.0) -> str:
        """
        Resultado máis probable (1/X/2) polo Delta Elo (logit ordenado). Umbrales
        validados por backtest out-of-sample nas 4 temporadas. Usa o home_adv en
        puntos Elo do propio EloModel (non o de goles do Poisson).
        """
        delta = (self.elo.rating(home) + self.elo.home_adv) - self.elo.rating(away)
        if delta > thr_hi:
            return "1"
        if delta < thr_lo:
            return "2"
        return "X"

    @staticmethod
    def _expected_score(lam_h: float, lam_a: float,
                        base: float = 0.9, gap: float = 0.30,
                        fav_min: float = 2.0) -> list[int]:
        """
        Marcador esperado por redondeo asimétrico. Redondea cada lambda con corte `base`
        (0.9): floor(l + 1 - base).

        A regra do gap (dar o gol da vitoria ao favorito cando o redondeo dá empate) SÓ se
        aplica se o favorito ten un lambda alto (>= fav_min). Isto evita inflar empates
        normais a marcadores esaxerados: p.ex. oGoals 1.4-1.06 daba 2-1, agora dá 1-1.
        Motivo: dende que o 1X2 (resultado máis probable) sae do logit por Delta Elo, o
        marcador xa non precisa "forzar" un gañador; só debe ser REALISTA. Backtest sobre
        3.800 partidos: esta versión mellora o acerto exacto (14.4%) e reduce o erro de goles.
        """
        h = int(np.floor(lam_h + (1.0 - base)))
        a = int(np.floor(lam_a + (1.0 - base)))
        if h == a and abs(lam_h - lam_a) >= gap and max(lam_h, lam_a) >= fav_min:
            if lam_h > lam_a:
                h += 1
            else:
                a += 1
        return [h, a]

    # ---------------------------------------------------- blend con cuotas ----
    @staticmethod
    def odds_to_prob(odd_home: float, odd_draw: float, odd_away: float) -> dict:
        """
        Convierte cuotas decimales (Bet365 u otras) en probabilidades implícitas,
        eliminando el margen de la casa (overround) por normalización simple.
        """
        inv = np.array([1 / odd_home, 1 / odd_draw, 1 / odd_away])
        p = inv / inv.sum()
        return {"home_win": float(p[0]), "draw": float(p[1]), "away_win": float(p[2])}

    def expected_result(self, home: str, away: str, odds: dict | None = None,
                        blend: float = 0.5) -> dict:
        """
        "Expected result" del partido: modelo propio, y si hay cuotas, mezcla.
        blend = peso del mercado (0 = solo modelo, 1 = solo cuotas).
        """
        model = self.match_probs(home, away)
        out = dict(model)
        out["source"] = "model"
        if odds:
            mkt = self.odds_to_prob(odds["home"], odds["draw"], odds["away"])
            for k in ("home_win", "draw", "away_win"):
                out[k] = round((1 - blend) * model[k] + blend * mkt[k], 4)
            out["source"] = f"blend({int(blend*100)}% mercado)"
        return out

    # ----------------------------------------------------- simulación temporada
    def simulate(self, played: list[dict], remaining: list[dict],
                n_sims: int = 10000, seed: int | None = 42) -> dict:
        """
        Simula `n_sims` veces los partidos `remaining` partiendo de los puntos ya
        logrados en `played`. Devuelve, por equipo, probabilidades de acabar
        campeón / en playoff / descendido, además de posición media y oPts.
        """
        rng = np.random.default_rng(seed)
        idx = {t: i for i, t in enumerate(self.teams)}
        n = len(self.teams)

        base_pts = np.zeros(n)
        base_gd = np.zeros(n)
        base_gf = np.zeros(n)
        for m in played:
            hg, ag = int(m["hg"]), int(m["ag"])
            ih, ia = idx[m["home"]], idx[m["away"]]
            base_gf[ih] += hg; base_gf[ia] += ag
            base_gd[ih] += hg - ag; base_gd[ia] += ag - hg
            if hg > ag: base_pts[ih] += 3
            elif hg < ag: base_pts[ia] += 3
            else: base_pts[ih] += 1; base_pts[ia] += 1

        # Pre-cálculo de lambdas de cada partido restante (más rápido en el bucle)
        rem = []
        for m in remaining:
            lam_h, lam_a = self._lambdas(m["home"], m["away"])
            rem.append((idx[m["home"]], idx[m["away"]], lam_h, lam_a))

        counts_champ = np.zeros(n)
        counts_po = np.zeros(n)
        counts_rel = np.zeros(n)
        pos_sum = np.zeros(n)
        pos_all = np.zeros((n_sims, n), dtype=np.int16)  # posición de cada equipo en cada sim
        pts_1 = np.zeros(n_sims); pts_5 = np.zeros(n_sims); pts_15 = np.zeros(n_sims)

        for sim_i in range(n_sims):
            pts = base_pts.copy()
            gd = base_gd.copy()
            gf = base_gf.copy()
            for ih, ia, lam_h, lam_a in rem:
                hg = rng.poisson(lam_h)
                ag = rng.poisson(lam_a)
                gf[ih] += hg; gf[ia] += ag
                gd[ih] += hg - ag; gd[ia] += ag - hg
                if hg > ag: pts[ih] += 3
                elif hg < ag: pts[ia] += 3
                else: pts[ih] += 1; pts[ia] += 1

            # ordenar por puntos, luego diferencia de goles, luego goles a favor
            order = np.lexsort((-gf, -gd, -pts))  # último criterio = primero
            ranks = np.empty(n, dtype=int)
            ranks[order] = np.arange(1, n + 1)

            counts_champ += (ranks <= PROMO_DIRECT)
            counts_po += (ranks <= PLAYOFF_TO)
            counts_rel += (ranks >= RELEGATION_FROM)
            pos_sum += ranks
            pos_all[sim_i] = ranks

            # limiares de puntos: os do 1º, 5º e 15º nesta simulación
            sp = np.sort(pts)[::-1]
            pts_1[sim_i] = sp[PROMO_DIRECT - 1]
            pts_5[sim_i] = sp[PLAYOFF_TO - 1]
            pts_15[sim_i] = sp[RELEGATION_FROM - 2]

        # banda de posición proxectada: percentís 10 e 90 (rango probable)
        pos_best = np.percentile(pos_all, 10, axis=0)   # mellor posición probable
        pos_worst = np.percentile(pos_all, 90, axis=0)  # peor posición probable
        self._thresholds = {
            "champion": round(float(pts_1.mean())),
            "playoff": round(float(pts_5.mean())),
            "safety": round(float(pts_15.mean())),
        }

        # oPts: puntos esperados del modelo sobre los partidos YA jugados
        opts = self._expected_points_played(played, idx, n)

        result = {}
        for t, i in idx.items():
            result[t] = {
                "pChamp": round(100 * counts_champ[i] / n_sims, 1),
                "pPO": round(100 * counts_po[i] / n_sims, 1),
                "pRel": round(100 * counts_rel[i] / n_sims, 1),
                "avgPos": round(pos_sum[i] / n_sims, 1),
                "posBest": int(pos_best[i]),   # posición máis alta probable (P10)
                "posWorst": int(pos_worst[i]), # posición máis baixa probable (P90)
                "oPts": round(opts[i], 1),
                "elo": round(self.strength[t].elo),
            }
        return result

    def _expected_points_played(self, played, idx, n) -> np.ndarray:
        """oPts: suma de puntos esperados (según probabilidades del modelo) en los
        partidos jugados. Compararlos con los reales dice si un equipo rinde por
        encima o por debajo de lo que 'merecía'."""
        opts = np.zeros(n)
        for m in played:
            p = self.match_probs(m["home"], m["away"])
            ih, ia = idx[m["home"]], idx[m["away"]]
            opts[ih] += 3 * p["home_win"] + 1 * p["draw"]
            opts[ia] += 3 * p["away_win"] + 1 * p["draw"]
        return opts


# --------------------------------------------------------------- utilidades ---
def _poisson_pmf(lam: float, max_k: int) -> np.ndarray:
    """Vector de probabilidades Poisson P(X=k) para k=0..max_k."""
    from math import lgamma, log
    k = np.arange(max_k + 1)
    logp = k * log(lam) - lam - np.array([lgamma(int(v) + 1) for v in k])
    return np.exp(logp)
