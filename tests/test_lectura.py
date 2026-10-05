from pathlib import Path

import pytest

from generate_instance_a import generar_instancia
from tp_modelado import leer_instancia


def test_lee_manual_y_preserva_coeficiente_negativo(path_manual):
    instancia = leer_instancia(str(path_manual))
    assert (instancia.n, instancia.m, instancia.U) == (3, 2, 12)
    assert instancia.beta == 0.5
    assert instancia.a[0][2] == -1


def test_lee_archivo_generado(tmp_path):
    path = tmp_path / "generada.txt"
    generar_instancia(str(path), 3, 2, seed=42)
    instancia = leer_instancia(str(path))
    assert (instancia.n, instancia.m) == (3, 2)
    assert len(instancia.a) == 2 and all(len(fila) == 3 for fila in instancia.a)


@pytest.mark.parametrize(
    "contenido, patron",
    [
        ("N 0\nM 1\nBETA 1\n", "positivos"),
        ("N 1\nM 1\nBETA nan\n", "positivo y finito"),
        ("N 1\nM 1\nBETA 1\nB 1 1\nDISENO 1 1 1 1\n", "faltan registros"),
        ("N 1\nN 1\nM 1\nBETA 1\n", "duplicado"),
        ("N 1\nM 1\nBETA 1\nDESCONOCIDO 1\n", "desconocido"),
        ("N 1.0\nM 1\nBETA 1\n", "entero"),
    ],
)
def test_rechaza_formatos_invalidos(tmp_path, contenido, patron):
    path = tmp_path / "invalida.txt"
    path.write_text(contenido, encoding="utf-8")
    with pytest.raises(ValueError, match=patron):
        leer_instancia(str(path))


def test_archivo_inexistente():
    with pytest.raises(FileNotFoundError):
        leer_instancia("no_existe.txt")


def test_acepta_registros_reordenados(tmp_path):
    lineas = Path("instancias/instancia_manual.txt").read_text(encoding="utf-8").splitlines()
    path = tmp_path / "reordenada.txt"
    path.write_text("\n".join(reversed(lineas)), encoding="utf-8")
    assert leer_instancia(str(path)).U == 12
