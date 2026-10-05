import pytest

from tp_modelado.modelo import actualizar_tau, configurar_scip, construir_modelo


@pytest.mark.solver
def test_actualiza_rhs_y_reinicia_contador(manual):
    ctx = construir_modelo(manual, 0)
    configurar_scip(ctx)
    tiempos = []
    objetivos = []
    for tau in (0, 12, 2, 7):
        actualizar_tau(ctx, tau)
        assert ctx.model.getStageName().upper() == "PROBLEM"
        assert ctx.model.getSolvingTime() < 1e-6
        ctx.model.setParam("limits/time", 1.0)
        ctx.model.optimize()
        tiempos.append(ctx.model.getSolvingTime())
        objetivos.append(round(ctx.model.getObjVal()))
    assert objetivos == [0, 28, 14, 23]
    assert all(t >= 0 for t in tiempos)
