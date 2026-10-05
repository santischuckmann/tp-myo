from __future__ import annotations

from dataclasses import dataclass

from pyscipopt import Model, quicksum

from .tipos import Instancia


@dataclass
class ContextoModelo:
    model: Model
    x: tuple
    restriccion_potencia: object
    tau_actual: int


def construir_modelo(instancia: Instancia, tau: int) -> ContextoModelo:
    model = Model("control_capacidad")
    x = tuple(
        model.addVar(name=f"x_{j + 1}", vtype="INTEGER", lb=0, ub=instancia.u[j])
        for j in range(instancia.n)
    )
    model.setObjective(quicksum(instancia.c[j] * x[j] for j in range(instancia.n)), "maximize")
    for i in range(instancia.m):
        model.addCons(
            quicksum(instancia.a[i][j] * x[j] for j in range(instancia.n)) <= instancia.b[i],
            name=f"recurso_{i + 1}",
        )
    potencia = model.addCons(
        quicksum(instancia.w[j] * x[j] for j in range(instancia.n)) <= tau,
        name="potencia",
    )
    return ContextoModelo(model=model, x=x, restriccion_potencia=potencia, tau_actual=tau)


def configurar_scip(ctx: ContextoModelo) -> None:
    model = ctx.model
    model.hideOutput()
    model.setParam("timing/clocktype", 2)
    model.setParam("misc/resetstat", True)
    model.setParam("timing/rareclockcheck", False)
    model.setParam("limits/gap", 0.0)
    model.setParam("limits/absgap", 0.0)
    model.setParam("randomization/randomseedshift", 0)


def actualizar_tau(ctx: ContextoModelo, tau: int) -> None:
    etapa = ctx.model.getStageName().upper()
    if etapa != "PROBLEM":
        permitidas = {
            "TRANSFORMED",
            "PRESOLVING",
            "PRESOLVED",
            "SOLVING",
            "SOLVED",
        }
        if etapa not in permitidas:
            raise RuntimeError(f"no se puede actualizar tau desde la etapa SCIP {etapa}")
        ctx.model.freeTransform()
        if ctx.model.getStageName().upper() != "PROBLEM":
            raise RuntimeError("SCIP no regresó a la etapa PROBLEM tras freeTransform")
    ctx.model.chgRhs(ctx.restriccion_potencia, tau)
    ctx.tau_actual = tau
