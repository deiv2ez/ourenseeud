"""
elo.py — Ratings Elo por equipo, específico para fútbol.

El Elo mide la FUERZA GENERAL de cada equipo en un único número que sube o baja
según los resultados y contra quién se consiguen. Se usa como modulador global:
un equipo con Elo alto verá reforzadas sus fuerzas de ataque/defensa en el modelo
Poisson (ver montecarlo.py).

Particularidades futbolísticas frente al Elo de ajedrez:
  - Ventaja de campo (HOME_ADV) sumada al local antes de calcular la expectativa.
  - Margen de victoria (goal difference) que amplifica el cambio de rating:
    ganar 4-0 mueve más el rating que ganar 1-0.
  - K ajustable (velocidad de aprendizaje del sistema).

Este módulo NO conoce nada de la web ni de pandas; solo números. Así es testeable
y reutilizable desde el pipeline de ingesta.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from math import log


# --- Parámetros por defecto (calibrables con backtesting sobre datos reales) ---
DEFAULT_RATING = 1500.0   # rating de arranque para un equipo sin histórico
HOME_ADV = 60.0           # puntos Elo de ventaja para el equipo local
K_BASE = 24.0             # velocidad de ajuste; más alto = reacciona más rápido


@dataclass
class EloModel:
    ratings: dict[str, float] = field(default_factory=dict)
    home_adv: float = HOME_ADV
    k_base: float = K_BASE

    def rating(self, team: str) -> float:
        """Rating actual del equipo (lo crea con el valor por defecto si es nuevo)."""
        return self.ratings.setdefault(team, DEFAULT_RATING)

    def expected(self, home: str, away: str) -> float:
        """
        Probabilidad esperada de que gane el LOCAL (entre 0 y 1), incluyendo empate
        repartido. Fórmula logística estándar de Elo con ventaja de campo.
        """
        diff = (self.rating(home) + self.home_adv) - self.rating(away)
        return 1.0 / (1.0 + 10 ** (-diff / 400.0))

    def _mov_multiplier(self, goal_diff: int, elo_diff: float) -> float:
        """
        Multiplicador por margen de victoria (Margin of Victory), estilo
        clubelo/FiveThirtyEight. Amplía el cambio en goleadas y lo corrige para
        que a un favorito no se le premie de más al ganar como se esperaba.
        """
        gd = max(1, abs(goal_diff))
        return log(gd + 1) * (2.2 / ((elo_diff * 0.001) + 2.2))

    def update(self, home: str, away: str, hg: int, ag: int) -> None:
        """
        Actualiza los ratings de ambos equipos tras un partido con resultado hg-ag.
        Resultado real desde la óptica del local: 1 gana, 0.5 empata, 0 pierde.
        """
        exp_home = self.expected(home, away)
        if hg > ag:
            score_home = 1.0
        elif hg < ag:
            score_home = 0.0
        else:
            score_home = 0.5

        elo_diff = (self.rating(home) + self.home_adv) - self.rating(away)
        mult = self._mov_multiplier(hg - ag, elo_diff if score_home == 1.0 else -elo_diff)
        change = self.k_base * mult * (score_home - exp_home)

        self.ratings[home] = self.rating(home) + change
        self.ratings[away] = self.rating(away) - change

    def run(self, matches: list[dict]) -> "EloModel":
        """
        Procesa una lista de partidos JUGADOS en orden cronológico.
        Cada match: {"home","away","hg","ag"}. Devuelve self para encadenar.
        """
        for m in matches:
            self.update(m["home"], m["away"], int(m["hg"]), int(m["ag"]))
        return self

    def table(self) -> list[tuple[str, float]]:
        """Ranking de equipos por rating, de mayor a menor."""
        return sorted(self.ratings.items(), key=lambda kv: kv[1], reverse=True)
