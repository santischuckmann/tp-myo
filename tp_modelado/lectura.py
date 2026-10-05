from __future__ import annotations

import math
from pathlib import Path

from .tipos import Instancia


def _error(path: Path, linea: int | None, mensaje: str) -> ValueError:
    ubicacion = f"{path}:{linea}" if linea is not None else str(path)
    return ValueError(f"{ubicacion}: {mensaje}")


def _entero(token: str, path: Path, linea: int, nombre: str) -> int:
    try:
        return int(token)
    except ValueError as exc:
        raise _error(path, linea, f"{nombre} debe ser un entero; recibido {token!r}") from exc


def leer_instancia(path_instancia: str):
    path = Path(path_instancia)
    try:
        contenido = path.read_bytes()
        lineas = contenido.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        numero = exc.object[:exc.start].count(b"\n") + 1
        raise _error(path, numero, "el archivo no es UTF-8 válido") from exc

    encabezados: dict[str, tuple[int, str]] = {}
    recursos: list[tuple[int, list[str]]] = []
    disenos: list[tuple[int, list[str]]] = []
    coeficientes: list[tuple[int, list[str]]] = []
    aridades = {"N": 2, "M": 2, "BETA": 2, "B": 3, "DISENO": 5, "A": 4}

    for numero, cruda in enumerate(lineas, 1):
        limpia = cruda.strip()
        if not limpia or limpia.startswith("#"):
            continue
        tokens = limpia.split()
        clave = tokens[0]
        if clave not in aridades:
            raise _error(path, numero, f"registro desconocido {clave!r}")
        if len(tokens) != aridades[clave]:
            raise _error(path, numero, f"{clave} espera {aridades[clave]} campos y recibió {len(tokens)}")
        if clave in {"N", "M", "BETA"}:
            if clave in encabezados:
                raise _error(path, numero, f"registro {clave} duplicado")
            encabezados[clave] = (numero, tokens[1])
        elif clave == "B":
            recursos.append((numero, tokens))
        elif clave == "DISENO":
            disenos.append((numero, tokens))
        else:
            coeficientes.append((numero, tokens))

    faltantes = [clave for clave in ("N", "M", "BETA") if clave not in encabezados]
    if faltantes:
        raise _error(path, None, f"faltan encabezados: {', '.join(faltantes)}")

    n_linea, n_token = encabezados["N"]
    m_linea, m_token = encabezados["M"]
    beta_linea, beta_token = encabezados["BETA"]
    n = _entero(n_token, path, n_linea, "N")
    m = _entero(m_token, path, m_linea, "M")
    if n <= 0 or m <= 0:
        raise _error(path, n_linea if n <= 0 else m_linea, "N y M deben ser positivos")
    try:
        beta = float(beta_token)
    except ValueError as exc:
        raise _error(path, beta_linea, "BETA debe ser un número real") from exc
    if not math.isfinite(beta) or beta <= 0:
        raise _error(path, beta_linea, "BETA debe ser positivo y finito")

    b: list[int | None] = [None] * m
    c: list[int | None] = [None] * n
    w: list[int | None] = [None] * n
    u: list[int | None] = [None] * n
    a: list[list[int | None]] = [[None] * n for _ in range(m)]

    for linea, tokens in recursos:
        i = _entero(tokens[1], path, linea, "índice de B")
        if not 1 <= i <= m:
            raise _error(path, linea, f"índice de recurso {i} fuera de 1..{m}")
        if b[i - 1] is not None:
            raise _error(path, linea, f"B {i} duplicado")
        valor = _entero(tokens[2], path, linea, "disponibilidad")
        if valor < 0:
            raise _error(path, linea, "la disponibilidad debe ser no negativa")
        b[i - 1] = valor

    for linea, tokens in disenos:
        j = _entero(tokens[1], path, linea, "índice de DISENO")
        if not 1 <= j <= n:
            raise _error(path, linea, f"índice de diseño {j} fuera de 1..{n}")
        if c[j - 1] is not None:
            raise _error(path, linea, f"DISENO {j} duplicado")
        cj = _entero(tokens[2], path, linea, "beneficio")
        wj = _entero(tokens[3], path, linea, "potencia")
        uj = _entero(tokens[4], path, linea, "cota superior")
        if wj < 0 or uj < 0:
            raise _error(path, linea, "potencia y cota superior deben ser no negativas")
        c[j - 1], w[j - 1], u[j - 1] = cj, wj, uj

    for linea, tokens in coeficientes:
        i = _entero(tokens[1], path, linea, "índice de recurso en A")
        j = _entero(tokens[2], path, linea, "índice de diseño en A")
        if not 1 <= i <= m or not 1 <= j <= n:
            raise _error(path, linea, f"índices A ({i}, {j}) fuera de 1..{m}, 1..{n}")
        if a[i - 1][j - 1] is not None:
            raise _error(path, linea, f"A {i} {j} duplicado")
        a[i - 1][j - 1] = _entero(tokens[3], path, linea, "coeficiente A")

    faltan_b = [str(i + 1) for i, valor in enumerate(b) if valor is None]
    faltan_d = [str(j + 1) for j, valor in enumerate(c) if valor is None]
    faltan_a = [f"({i + 1},{j + 1})" for i in range(m) for j in range(n) if a[i][j] is None]
    if faltan_b or faltan_d or faltan_a:
        partes = []
        if faltan_b:
            partes.append("B " + ", ".join(faltan_b))
        if faltan_d:
            partes.append("DISENO " + ", ".join(faltan_d))
        if faltan_a:
            partes.append("A " + ", ".join(faltan_a[:10]) + ("..." if len(faltan_a) > 10 else ""))
        raise _error(path, None, "faltan registros: " + "; ".join(partes))

    return Instancia(
        n=n,
        m=m,
        beta=beta,
        c=tuple(c),  # type: ignore[arg-type]
        b=tuple(b),  # type: ignore[arg-type]
        a=tuple(tuple(fila) for fila in a),  # type: ignore[arg-type]
        w=tuple(w),  # type: ignore[arg-type]
        u=tuple(u),  # type: ignore[arg-type]
    )
