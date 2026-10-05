from __future__ import annotations

import math
import time
from numbers import Real

from .lectura import leer_instancia
from .modelo import ContextoModelo, actualizar_tau, configurar_scip, construir_modelo
from .tipos import MIN_SOLVER_S, EvaluacionTau, Instancia, ResultadoEtapa1, Solucion, Tiempos


TOLERANCIA = 1e-6


def validar_segundos(segundos) -> float:
    if isinstance(segundos, bool) or not isinstance(segundos, Real):
        raise TypeError("segundos debe ser un número real")
    valor = float(segundos)
    if not math.isfinite(valor) or valor < 0:
        raise ValueError("segundos debe ser no negativo y finito")
    return valor


def validar_tau(tau, U: int) -> int:
    if isinstance(tau, bool) or not isinstance(tau, int):
        raise TypeError("tau debe ser un entero")
    if not 0 <= tau <= U:
        raise ValueError(f"tau debe estar entre 0 y {U}")
    return tau


def validar_solucion(
    instancia: Instancia,
    tau: int,
    valores: tuple[float, ...],
    objetivo_solver: float | None = None,
) -> Solucion:
    if len(valores) != instancia.n:
        raise RuntimeError("SCIP devolvió un vector con dimensión incorrecta")
    enteros: list[int] = []
    for j, valor in enumerate(valores):
        if not math.isfinite(valor) or abs(valor - round(valor)) > TOLERANCIA:
            raise RuntimeError(f"valor no entero para x[{j}]: {valor}")
        xj = int(round(valor))
        if not 0 <= xj <= instancia.u[j]:
            raise RuntimeError(f"x[{j}]={xj} viola sus cotas")
        enteros.append(xj)
    x = tuple(enteros)
    for i in range(instancia.m):
        uso = sum(instancia.a[i][j] * x[j] for j in range(instancia.n))
        if uso > instancia.b[i]:
            raise RuntimeError(f"la solución viola el recurso {i + 1}: {uso}>{instancia.b[i]}")
    potencia = sum(instancia.w[j] * x[j] for j in range(instancia.n))
    if potencia > tau:
        raise RuntimeError(f"la solución viola potencia: {potencia}>{tau}")
    ganancia = sum(instancia.c[j] * x[j] for j in range(instancia.n))
    if objetivo_solver is not None and not math.isclose(
        float(objetivo_solver), float(ganancia), rel_tol=TOLERANCIA, abs_tol=TOLERANCIA
    ):
        raise RuntimeError(f"objetivo inconsistente: SCIP={objetivo_solver}, calculado={ganancia}")
    return Solucion(
        x=x,
        tau=tau,
        potencia_utilizada=potencia,
        ganancia_operativa=ganancia,
        beneficio_neto=ganancia - instancia.beta * tau**2,
    )


def _numero_finito(model, valor) -> float | None:
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numero) or model.isInfinity(abs(numero)):
        return None
    return numero


def resolver_tau(
    ctx: ContextoModelo,
    instancia: Instancia,
    tau: int,
    presupuesto_s: float,
    *,
    indice: int,
    fase: str,
    inicio_global: float,
    deadline: float | None = None,
    reserva_s: float = 0.0,
    reloj=time.monotonic,
) -> EvaluacionTau | None:
    inicio_preparacion = reloj()
    if ctx.tau_actual != tau or ctx.model.getStageName().upper() != "PROBLEM":
        actualizar_tau(ctx, tau)
    ahora = reloj()
    restante = None if deadline is None else deadline - ahora
    limite = presupuesto_s
    if restante is not None:
        limite = min(limite, restante - reserva_s)
    if limite <= 0:
        return None
    ctx.model.setParam("limits/time", float(limite))
    antes_opt = reloj()
    if deadline is not None:
        limite = min(limite, deadline - antes_opt - reserva_s)
        if limite < MIN_SOLVER_S:
            return None
        ctx.model.setParam("limits/time", float(limite))
    contador_antes = float(ctx.model.getSolvingTime())
    inicio_opt = reloj()
    ctx.model.optimize()
    fin_opt = reloj()

    inicio_extraccion = reloj()
    estado = str(ctx.model.getStatus()).lower()
    solucion = None
    if ctx.model.getNSols() > 0:
        mejor = ctx.model.getBestSol()
        if mejor is not None:
            valores = tuple(float(ctx.model.getSolVal(mejor, var)) for var in ctx.x)
            objetivo = float(ctx.model.getSolObjVal(mejor))
            solucion = validar_solucion(instancia, tau, valores, objetivo)
    if estado == "optimal" and solucion is None:
        raise RuntimeError("SCIP informó optimal pero no devolvió solución")
    dual = _numero_finito(ctx.model, ctx.model.getDualbound())
    gap = _numero_finito(ctx.model, ctx.model.getGap()) if solucion is not None else None
    contador_despues = float(ctx.model.getSolvingTime())
    fin_extraccion = reloj()
    return EvaluacionTau(
        indice=indice,
        fase=fase,
        tau=tau,
        estado_solver=estado,
        solucion=solucion,
        optimal_tau=estado == "optimal" and solucion is not None,
        cota_dual_operativa=dual,
        cota_dual_neta=None if dual is None else dual - instancia.beta * tau**2,
        gap=gap,
        presupuesto_solver_s=presupuesto_s,
        limite_scip_s=float(limite),
        restante_antes_s=restante,
        inicio_relativo_s=inicio_preparacion - inicio_global,
        fin_relativo_s=fin_extraccion - inicio_global,
        preparacion_s=inicio_opt - inicio_preparacion,
        optimizacion_real_s=fin_opt - inicio_opt,
        extraccion_s=fin_extraccion - inicio_extraccion,
        contador_scip_antes_s=contador_antes,
        contador_scip_despues_s=contador_despues,
        solver_s=max(0.0, contador_despues - contador_antes),
    )


def _cerrar_modelo(ctx: ContextoModelo | None) -> None:
    if ctx is None:
        return
    liberar = getattr(ctx.model, "free", None)
    if callable(liberar):
        liberar()


def resolver_modelo(path_instancia, segundos, tau):
    inicio = time.monotonic()
    limite = validar_segundos(segundos)
    lectura_inicio = time.monotonic()
    instancia = leer_instancia(path_instancia)
    lectura_s = time.monotonic() - lectura_inicio
    tau = validar_tau(tau, instancia.U)
    if limite == 0:
        total = time.monotonic() - inicio
        return ResultadoEtapa1(
            instancia_path=str(path_instancia), dimensiones=(instancia.n, instancia.m), U=instancia.U,
            tau_solicitado=tau, estado="presupuesto_agotado", evaluacion=None, solucion=None,
            garantia_tau=False, tiempos=Tiempos(limite, total_s=total, lectura_s=lectura_s),
            observaciones=("no se construyó ni optimizó el modelo",),
        )

    ctx = None
    construccion_inicio = time.monotonic()
    try:
        ctx = construir_modelo(instancia, tau)
        configurar_scip(ctx)
        construccion_s = time.monotonic() - construccion_inicio
        evaluacion = resolver_tau(
            ctx, instancia, tau, limite, indice=0, fase="fija", inicio_global=inicio
        )
        if evaluacion is None:
            raise RuntimeError("no se pudo iniciar la optimización con un presupuesto positivo")
        antes_cierre = time.monotonic()
        _cerrar_modelo(ctx)
        ctx = None
        cierre_s = time.monotonic() - antes_cierre
    finally:
        _cerrar_modelo(ctx)
    total = time.monotonic() - inicio
    tiempos = Tiempos(
        solicitado_s=limite,
        total_s=total,
        lectura_s=lectura_s,
        construccion_s=construccion_s,
        preparacion_s=evaluacion.preparacion_s,
        optimizacion_real_s=evaluacion.optimizacion_real_s,
        extraccion_s=evaluacion.extraccion_s,
        cierre_s=cierre_s,
        solver_s=evaluacion.solver_s,
        exceso_s=max(0.0, evaluacion.optimizacion_real_s - limite),
    )
    return ResultadoEtapa1(
        instancia_path=str(path_instancia), dimensiones=(instancia.n, instancia.m), U=instancia.U,
        tau_solicitado=tau, estado=evaluacion.estado_solver, evaluacion=evaluacion,
        solucion=evaluacion.solucion, garantia_tau=evaluacion.optimal_tau, tiempos=tiempos,
    )
