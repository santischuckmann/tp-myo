import json
import platform
import sys

from pyscipopt import Model


def main() -> None:
    model = Model("smoke_test")
    model.hideOutput()
    x = model.addVar("x", vtype="INTEGER", lb=0, ub=2)
    model.addCons(2 * x <= 3)
    model.setObjective(x, "maximize")
    model.setParam("limits/time", 1.0)
    model.optimize()
    sol = model.getBestSol()
    if str(model.getStatus()) != "optimal" or sol is None or round(model.getSolVal(sol, x)) != 1:
        raise RuntimeError("el modelo entero mínimo no produjo el resultado esperado")
    datos = {
        "python": platform.python_version(),
        "implementacion": platform.python_implementation(),
        "arquitectura_bits": 64 if sys.maxsize > 2**32 else 32,
        "sistema": platform.platform(),
        "scip": f"{model.getMajorVersion()}.{model.getMinorVersion()}.{model.getTechVersion()}",
        "estado_smoke_test": str(model.getStatus()),
        "solucion_smoke_test": 1,
        "parametros": {
            "timing/clocktype": model.getParam("timing/clocktype"),
            "misc/resetstat": model.getParam("misc/resetstat"),
        },
    }
    print(json.dumps(datos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
