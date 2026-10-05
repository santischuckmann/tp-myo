from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

from .busqueda import busqueda_tau
from .reporte import cargar_json, crear_documento, exportar_excel, guardar_json, imprimir_resultado
from .solver import resolver_modelo


def _hash(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _rutas_salida(base: str | Path) -> tuple[Path, Path]:
    base = Path(base)
    if base.suffix.lower() in {".json", ".xlsx"}:
        base = base.with_suffix("")
    return base.with_suffix(".json"), base.with_suffix(".xlsx")


def _verificar_salida(rutas: tuple[Path, ...], sobrescribir: bool) -> None:
    existentes = [str(path) for path in rutas if path.exists()]
    if existentes and not sobrescribir:
        raise FileExistsError(
            "ya existe la salida " + ", ".join(existentes) + "; use --sobrescribir o elija otro nombre"
        )


def _envolver(id_: str, etapa: int, path: str, segundos: float, tau, resultado, **extra):
    instancia_path = Path(path)
    return {
        "id": id_,
        "etapa": etapa,
        "instancia": {
            "path": path,
            "sha256": _hash(path) if instancia_path.is_file() else None,
            "seed": extra.get("seed"),
            "restrictiva": extra.get("restrictiva"),
        },
        "parametros": {"segundos": segundos, "tau": tau},
        "repeticion": extra.get("repeticion", 1),
        "resultado": resultado,
    }


def _guardar(documento, salida: str, sobrescribir: bool) -> None:
    json_path, excel_path = _rutas_salida(salida)
    _verificar_salida((json_path, excel_path), sobrescribir)
    inicio = time.monotonic()
    guardar_json(documento, json_path)
    tiempo_json = time.monotonic() - inicio
    inicio = time.monotonic()
    exportar_excel(documento, excel_path, json_path)
    tiempo_excel = time.monotonic() - inicio
    print(f"JSON: {json_path} ({tiempo_json:.3f} s)")
    print(f"Excel: {excel_path} ({tiempo_excel:.3f} s)")


def _comando_etapa(args) -> int:
    if args.salida:
        _verificar_salida(_rutas_salida(args.salida), args.sobrescribir)
    if args.etapa == 1:
        resultado = resolver_modelo(args.instancia, args.segundos, args.tau)
        tau = args.tau
    else:
        resultado = busqueda_tau(args.instancia, args.segundos)
        tau = None
    imprimir_resultado(resultado)
    if args.salida:
        nombre = Path(args.instancia).stem
        id_ = args.id or f"{nombre}-e{args.etapa}-s{args.segundos:g}-r1"
        ejecucion = _envolver(id_, args.etapa, args.instancia, args.segundos, tau, resultado)
        _guardar(crear_documento([ejecucion]), args.salida, args.sobrescribir)
    return 0


def _expandir_ejecuciones(config: dict) -> list[dict]:
    expandidas = []
    for entrada in config.get("ejecuciones", []):
        repeticiones = int(entrada.get("repeticiones", 1))
        if repeticiones <= 0:
            raise ValueError("repeticiones debe ser positivo")
        for numero in range(1, repeticiones + 1):
            copia = dict(entrada)
            copia["repeticion"] = numero
            base = str(copia["id"])
            copia["id"] = base if repeticiones == 1 else f"{base}-r{numero}"
            expandidas.append(copia)
    return expandidas


def _comando_experimentos(args) -> int:
    config_path = Path(args.config)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    entradas = _expandir_ejecuciones(config)
    ids = [e["id"] for e in entradas]
    if len(ids) != len(set(ids)):
        raise ValueError("los identificadores de ejecuciones deben ser únicos")
    json_path, excel_path = _rutas_salida(args.salida)
    _verificar_salida((json_path, excel_path), args.sobrescribir)
    ejecuciones = []
    for entrada in entradas:
        etapa = int(entrada["etapa"])
        path = entrada["instancia_path"]
        segundos = float(entrada["segundos"])
        tau = entrada.get("tau")
        print(f"\n[{entrada['id']}] etapa {etapa}: {path}")
        resultado = resolver_modelo(path, segundos, tau) if etapa == 1 else busqueda_tau(path, segundos)
        imprimir_resultado(resultado)
        ejecuciones.append(
            _envolver(
                entrada["id"], etapa, path, segundos, tau, resultado,
                seed=entrada.get("seed"), restrictiva=entrada.get("restrictiva"),
                repeticion=entrada["repeticion"],
            )
        )
    documento = crear_documento(ejecuciones)
    documento["protocolo"] = {"path": str(config_path), "sha256": _hash(config_path)}
    _guardar(documento, args.salida, args.sobrescribir)
    return 0


def _comando_exportar(args) -> int:
    destino = Path(args.excel)
    _verificar_salida((destino,), args.sobrescribir)
    documento = cargar_json(args.json)
    exportar_excel(documento, destino, args.json)
    print(f"Excel: {destino}")
    return 0


def crear_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Control de tiempos y optimización paramétrica")
    sub = parser.add_subparsers(dest="comando", required=True)
    for etapa in (1, 2):
        cmd = sub.add_parser(f"etapa{etapa}", help=f"ejecutar etapa {etapa}")
        cmd.set_defaults(func=_comando_etapa, etapa=etapa)
        cmd.add_argument("instancia")
        cmd.add_argument("--segundos", type=float, required=True)
        if etapa == 1:
            cmd.add_argument("--tau", type=int, required=True)
        cmd.add_argument("--salida", help="ruta base para JSON y Excel")
        cmd.add_argument("--id", help="identificador de la ejecución")
        cmd.add_argument("--sobrescribir", action="store_true")
    batch = sub.add_parser("experimentos", help="ejecutar un protocolo JSON")
    batch.set_defaults(func=_comando_experimentos)
    batch.add_argument("--config", required=True)
    batch.add_argument("--salida", required=True)
    batch.add_argument("--sobrescribir", action="store_true")
    exportar = sub.add_parser("exportar", help="regenerar Excel desde resultados JSON")
    exportar.set_defaults(func=_comando_exportar)
    exportar.add_argument("--json", required=True)
    exportar.add_argument("--excel", required=True)
    exportar.add_argument("--sobrescribir", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = crear_parser().parse_args(argv)
        return args.func(args)
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
