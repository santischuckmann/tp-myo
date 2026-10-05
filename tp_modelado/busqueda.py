from __future__ import annotations

import math
import time

from .lectura import leer_instancia
from .modelo import configurar_scip, construir_modelo
from .solver import _cerrar_modelo, resolver_tau, validar_segundos
from .tipos import (
    CENTROS_REFINAMIENTO,
    MAX_RONDAS_REFINAMIENTO,
    MAX_SOLVER_POR_TAU_S,
    MIN_SOLVER_S,
    PUNTOS_GRILLA,
    RESERVA_BASE_S,
    UMBRAL_EXHAUSTIVO,
    EvaluacionTau,
    ResultadoBusqueda,
    Solucion,
    Tiempos,
)


def generar_grilla(U: int, puntos: int = PUNTOS_GRILLA) -> tuple[int, ...]:
    if U == 0:
        return (0,)
    valores = tuple({(k * U) // (puntos - 1) for k in range(puntos)})
    orden_indice = (0, 16, 8, 4, 12, 2, 6, 10, 14, 1, 3, 5, 7, 9, 11, 13, 15)
    nominales = [(k * U) // 16 for k in orden_indice]
    resultado = []
    vistos = set()
    for tau in nominales:
        if tau in valores and tau not in vistos:
            vistos.add(tau)
            resultado.append(tau)
    return tuple(resultado)


def candidatos_refinamiento(
    evaluaciones: dict[int, EvaluacionTau], U: int, centros: int = CENTROS_REFINAMIENTO
) -> tuple[int, ...]:
    visitados = set(evaluaciones)
    for extremo in (0, U):
        if extremo not in visitados:
            return (extremo,)
    con_solucion = [ev for ev in evaluaciones.values() if ev.solucion is not None]
    con_solucion.sort(key=lambda ev: (-ev.solucion.beneficio_neto, ev.tau))  # type: ignore[union-attr]
    elegidos = con_solucion[:centros]
    ordenados = sorted(visitados | {0, U})
    propuestas: list[int] = []
    for centro in elegidos:
        menores = [tau for tau in ordenados if tau < centro.tau]
        mayores = [tau for tau in ordenados if tau > centro.tau]
        for vecino in ((max(menores) if menores else 0), (min(mayores) if mayores else U)):
            bajo, alto = sorted((centro.tau, vecino))
            if alto - bajo >= 2:
                punto = (bajo + alto) // 2
                if punto not in visitados and punto not in propuestas:
                    propuestas.append(punto)
    if propuestas:
        return tuple(propuestas)

    bordes = sorted(visitados | {0, U})
    intervalos = [(alto - bajo, bajo, alto) for bajo, alto in zip(bordes, bordes[1:]) if alto - bajo >= 2]
    if not intervalos:
        return ()
    _, bajo, alto = max(intervalos, key=lambda dato: (dato[0], -dato[1]))
    return ((bajo + alto) // 2,)


def _es_mejor(nueva: Solucion, actual: Solucion | None) -> bool:
    if actual is None:
        return True
    if not math.isclose(nueva.beneficio_neto, actual.beneficio_neto, rel_tol=1e-9, abs_tol=1e-9):
        return nueva.beneficio_neto > actual.beneficio_neto
    return nueva.tau < actual.tau


def busqueda_tau(path_instancia, segundos):
    inicio = time.monotonic()
    limite = validar_segundos(segundos)
    configuracion = {
        "umbral_exhaustivo": UMBRAL_EXHAUSTIVO,
        "puntos_grilla": PUNTOS_GRILLA,
        "centros_refinamiento": CENTROS_REFINAMIENTO,
        "max_rondas_refinamiento": MAX_RONDAS_REFINAMIENTO,
        "min_solver_s": MIN_SOLVER_S,
        "reserva_base_s": RESERVA_BASE_S,
        "max_solver_por_tau_s": MAX_SOLVER_POR_TAU_S,
    }
    if limite == 0:
        return ResultadoBusqueda(
            instancia_path=str(path_instancia), dimensiones=None, U=None,
            estado="presupuesto_agotado", motivo_parada="presupuesto inicial cero",
            estrategia="no iniciada", configuracion=configuracion, mejor=None,
            mejor_evaluacion_indice=None, garantia_tau_mejor=False, garantia_global=False,
            taus_evaluados=0, taus_certificados=0, capacidades_totales=None, traza=(),
            tiempos=Tiempos(solicitado_s=0.0, total_s=time.monotonic() - inicio),
            observaciones=("instancia_no_leida_por_presupuesto",),
        )

    deadline = inicio + limite
    lectura_inicio = time.monotonic()
    instancia = leer_instancia(path_instancia)
    lectura_s = time.monotonic() - lectura_inicio
    if deadline - time.monotonic() < MIN_SOLVER_S + RESERVA_BASE_S:
        total = time.monotonic() - inicio
        return ResultadoBusqueda(
            instancia_path=str(path_instancia), dimensiones=(instancia.n, instancia.m), U=instancia.U,
            estado="presupuesto_agotado", motivo_parada="tiempo insuficiente después de leer",
            estrategia="no iniciada", configuracion=configuracion, mejor=None,
            mejor_evaluacion_indice=None, garantia_tau_mejor=False, garantia_global=False,
            taus_evaluados=0, taus_certificados=0, capacidades_totales=instancia.U + 1, traza=(),
            tiempos=Tiempos(limite, total_s=total, lectura_s=lectura_s, exceso_s=max(0.0, total-limite)),
        )

    estrategia = "exhaustiva" if instancia.U <= UMBRAL_EXHAUSTIVO else "grilla_refinamiento"
    ctx = None
    traza: list[EvaluacionTau] = []
    evaluaciones: dict[int, EvaluacionTau] = {}
    mejor: Solucion | None = None
    mejor_indice: int | None = None
    duraciones_overhead: list[float] = []
    motivo = ""
    estado = "completo"
    construccion_inicio = time.monotonic()
    try:
        primer_tau = 0
        ctx = construir_modelo(instancia, primer_tau)
        configurar_scip(ctx)
        construccion_s = time.monotonic() - construccion_inicio
        if deadline - time.monotonic() < MIN_SOLVER_S + RESERVA_BASE_S:
            motivo = "tiempo insuficiente después de construir"
            estado = "presupuesto_agotado"
        else:
            def evaluar_agenda(agenda: tuple[int, ...], fase: str, fin_fase: float | None = None) -> bool:
                nonlocal mejor, mejor_indice, motivo, estado
                pendientes = [tau for tau in agenda if tau not in evaluaciones]
                for posicion, tau in enumerate(pendientes):
                    reciente = max(duraciones_overhead[-3:], default=0.0)
                    reserva = max(RESERVA_BASE_S, 2 * reciente)
                    tope = min(deadline, fin_fase) if fin_fase is not None else deadline
                    disponible = tope - time.monotonic() - reserva
                    if disponible < MIN_SOLVER_S:
                        if fin_fase is not None and tope < deadline:
                            return True
                        estado = "presupuesto_agotado"
                        motivo = "restante insuficiente para una nueva iteración"
                        return False
                    denominador = len(pendientes) - posicion
                    if fase == "refinamiento":
                        denominador += 1
                    cuota = min(MAX_SOLVER_POR_TAU_S, max(MIN_SOLVER_S, disponible / denominador))
                    ev = resolver_tau(
                        ctx, instancia, tau, cuota, indice=len(traza), fase=fase,
                        inicio_global=inicio, deadline=deadline, reserva_s=reserva,
                    )
                    if ev is None:
                        estado = "presupuesto_agotado"
                        motivo = "presupuesto consumido durante la preparación"
                        return False
                    traza.append(ev)
                    evaluaciones[tau] = ev
                    duraciones_overhead.append(ev.preparacion_s + ev.extraccion_s)
                    if ev.solucion is not None and _es_mejor(ev.solucion, mejor):
                        mejor, mejor_indice = ev.solucion, ev.indice
                    if ev.estado_solver in {"userinterrupt", "infeasible", "unbounded", "inforunbd"}:
                        estado = "estado_solver_no_continuable"
                        motivo = f"estado SCIP {ev.estado_solver}"
                        return False
                return True

            if estrategia == "exhaustiva":
                completa = evaluar_agenda(tuple(range(instancia.U + 1)), "exhaustiva")
                if completa:
                    motivo = "recorrido exhaustivo finalizado"
            else:
                restante_inicial = max(0.0, deadline - time.monotonic() - RESERVA_BASE_S)
                fin_grilla = time.monotonic() + 0.40 * restante_inicial
                continuar = evaluar_agenda(generar_grilla(instancia.U), "grilla", fin_grilla)
                if continuar:
                    for _ in range(MAX_RONDAS_REFINAMIENTO):
                        candidatos = candidatos_refinamiento(evaluaciones, instancia.U)
                        if not candidatos:
                            estado = "candidatos_agotados"
                            motivo = "el refinamiento no produjo candidatos nuevos"
                            break
                        if not evaluar_agenda(candidatos, "refinamiento"):
                            break
                    else:
                        estado = "candidatos_agotados"
                        motivo = "se alcanzó el máximo de rondas de refinamiento"
    finally:
        cierre_inicio = time.monotonic()
        _cerrar_modelo(ctx)
        cierre_s = time.monotonic() - cierre_inicio

    total = time.monotonic() - inicio
    certificados = sum(ev.optimal_tau for ev in traza)
    garantia_global = len(evaluaciones) == instancia.U + 1 and certificados == instancia.U + 1
    mejor_ev = None if mejor_indice is None else traza[mejor_indice]
    if not motivo:
        motivo = "búsqueda finalizada"
    tiempos = Tiempos(
        solicitado_s=limite,
        total_s=total,
        lectura_s=lectura_s,
        construccion_s=construccion_s,
        preparacion_s=sum(ev.preparacion_s for ev in traza),
        optimizacion_real_s=sum(ev.optimizacion_real_s for ev in traza),
        extraccion_s=sum(ev.extraccion_s for ev in traza),
        cierre_s=cierre_s,
        solver_s=sum(ev.solver_s for ev in traza),
        exceso_s=max(0.0, total - limite),
    )
    return ResultadoBusqueda(
        instancia_path=str(path_instancia), dimensiones=(instancia.n, instancia.m), U=instancia.U,
        estado=estado, motivo_parada=motivo, estrategia=estrategia, configuracion=configuracion,
        mejor=mejor, mejor_evaluacion_indice=mejor_indice,
        garantia_tau_mejor=False if mejor_ev is None else mejor_ev.optimal_tau,
        garantia_global=garantia_global, taus_evaluados=len(evaluaciones),
        taus_certificados=certificados, capacidades_totales=instancia.U + 1,
        traza=tuple(traza), tiempos=tiempos,
    )
