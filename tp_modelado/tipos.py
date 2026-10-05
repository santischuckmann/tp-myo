from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Instancia:
    n: int
    m: int
    beta: float
    c: tuple[int, ...]
    b: tuple[int, ...]
    a: tuple[tuple[int, ...], ...]
    w: tuple[int, ...]
    u: tuple[int, ...]

    @property
    def U(self) -> int:
        return sum(wj * uj for wj, uj in zip(self.w, self.u))


@dataclass(frozen=True)
class Solucion:
    x: tuple[int, ...]
    tau: int
    potencia_utilizada: int
    ganancia_operativa: int
    beneficio_neto: float
    origen: str = "solver"


@dataclass(frozen=True)
class Tiempos:
    solicitado_s: float
    total_s: float = 0.0
    lectura_s: float = 0.0
    construccion_s: float = 0.0
    preparacion_s: float = 0.0
    optimizacion_real_s: float = 0.0
    extraccion_s: float = 0.0
    cierre_s: float = 0.0
    solver_s: float = 0.0
    exceso_s: float = 0.0


@dataclass(frozen=True)
class EvaluacionTau:
    indice: int
    fase: str
    tau: int
    estado_solver: str
    solucion: Solucion | None
    optimal_tau: bool
    cota_dual_operativa: float | None
    cota_dual_neta: float | None
    gap: float | None
    presupuesto_solver_s: float
    limite_scip_s: float
    restante_antes_s: float | None
    inicio_relativo_s: float
    fin_relativo_s: float
    preparacion_s: float
    optimizacion_real_s: float
    extraccion_s: float
    contador_scip_antes_s: float
    contador_scip_despues_s: float
    solver_s: float
    observaciones: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResultadoEtapa1:
    instancia_path: str
    dimensiones: tuple[int, int]
    U: int
    tau_solicitado: int
    estado: str
    evaluacion: EvaluacionTau | None
    solucion: Solucion | None
    garantia_tau: bool
    tiempos: Tiempos
    observaciones: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResultadoBusqueda:
    instancia_path: str
    dimensiones: tuple[int, int] | None
    U: int | None
    estado: str
    motivo_parada: str
    estrategia: str
    configuracion: dict[str, Any]
    mejor: Solucion | None
    mejor_evaluacion_indice: int | None
    garantia_tau_mejor: bool
    garantia_global: bool
    taus_evaluados: int
    taus_certificados: int
    capacidades_totales: int | None
    traza: tuple[EvaluacionTau, ...]
    tiempos: Tiempos
    observaciones: tuple[str, ...] = ()


UMBRAL_EXHAUSTIVO = 200
PUNTOS_GRILLA = 17
CENTROS_REFINAMIENTO = 3
MAX_RONDAS_REFINAMIENTO = 8
MIN_SOLVER_S = 0.01
RESERVA_BASE_S = 0.02
MAX_SOLVER_POR_TAU_S = 5.0
