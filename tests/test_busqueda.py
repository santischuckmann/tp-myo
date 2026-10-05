import pytest

from tp_modelado import busqueda_tau
from tp_modelado.busqueda import candidatos_refinamiento, generar_grilla


@pytest.mark.solver
def test_busqueda_exhaustiva_encuentra_optimo_global(path_manual):
    resultado = busqueda_tau(str(path_manual), 5)
    assert resultado.mejor is not None
    assert resultado.mejor.tau == 2
    assert resultado.mejor.x == (0, 2, 0)
    assert resultado.mejor.beneficio_neto == 12
    assert resultado.taus_evaluados == 13
    assert resultado.taus_certificados == 13
    assert resultado.garantia_global


def test_presupuesto_cero_no_lee_instancia():
    resultado = busqueda_tau("no_existe.txt", 0)
    assert resultado.estado == "presupuesto_agotado"
    assert resultado.dimensiones is None


def test_grilla_es_reproducible_y_acotada():
    grilla = generar_grilla(10**12)
    assert grilla[:3] == (0, 10**12, 5 * 10**11)
    assert len(grilla) == 17 == len(set(grilla))


def test_refinamiento_sin_evaluaciones_propone_extremo():
    assert candidatos_refinamiento({}, 100) == (0,)
