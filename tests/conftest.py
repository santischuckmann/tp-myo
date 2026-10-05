from __future__ import annotations

from itertools import product
from pathlib import Path

import pytest

from tp_modelado import leer_instancia


@pytest.fixture
def path_manual() -> Path:
    return Path("instancias/instancia_manual.txt")


@pytest.fixture
def manual(path_manual):
    return leer_instancia(str(path_manual))


def enumerar(instancia, tau):
    factibles = []
    for x in product(*(range(uj + 1) for uj in instancia.u)):
        if sum(wj * xj for wj, xj in zip(instancia.w, x)) > tau:
            continue
        if any(sum(instancia.a[i][j] * x[j] for j in range(instancia.n)) > instancia.b[i]
               for i in range(instancia.m)):
            continue
        factibles.append((sum(cj * xj for cj, xj in zip(instancia.c, x)), x))
    return max(factibles)
