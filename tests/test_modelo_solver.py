import pytest

from tp_modelado import resolver_modelo

from conftest import enumerar


@pytest.mark.solver
@pytest.mark.parametrize("tau", range(13))
def test_solver_coincide_con_enumeracion(path_manual, manual, tau):
    resultado = resolver_modelo(str(path_manual), 1, tau)
    esperado, _ = enumerar(manual, tau)
    assert resultado.estado == "optimal"
    assert resultado.garantia_tau
    assert resultado.solucion is not None
    assert resultado.solucion.ganancia_operativa == esperado
    assert sum(manual.w[j] * resultado.solucion.x[j] for j in range(manual.n)) <= tau


def test_presupuesto_cero_no_optimiza(path_manual):
    resultado = resolver_modelo(str(path_manual), 0, 2)
    assert resultado.estado == "presupuesto_agotado"
    assert resultado.evaluacion is None
    assert resultado.solucion is None


@pytest.mark.parametrize("segundos", [-1, float("nan"), float("inf")])
def test_presupuesto_invalido(path_manual, segundos):
    with pytest.raises(ValueError):
        resolver_modelo(str(path_manual), segundos, 2)


@pytest.mark.parametrize("tau", [-1, 13, 2.0, True])
def test_tau_invalido(path_manual, tau):
    with pytest.raises((ValueError, TypeError)):
        resolver_modelo(str(path_manual), 0, tau)
