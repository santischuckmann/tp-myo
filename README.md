# Control de tiempos y optimización paramétrica

Trabajo práctico de Modelado y Optimización. La aplicación resuelve planes de producción enteros con PySCIPOpt y busca una capacidad eléctrica `tau` que maximiza el beneficio neto.

Fecha de entrega docente: **7 de octubre de 2026**.

## Modelo

Para una capacidad fija `tau`, las variables enteras `x[j]` cumplen `0 <= x[j] <= u[j]`. El modelo maximiza la ganancia operativa:

```text
max sum(c[j] * x[j])
sum(a[i][j] * x[j]) <= b[i]       para cada recurso i
sum(w[j] * x[j]) <= tau
```

El beneficio neto usado para comparar capacidades es:

```text
ganancia_operativa - beta * tau**2
```

Una solución obtenida por timeout es válida si SCIP dejó un incumbent, pero no se denomina `Pi(tau)` ni se marca como óptima. El archivo `instancia_sin_solucion.txt` tiene un nombre engañoso: `x=0` siempre es factible para datos válidos. Puede ocurrir que SCIP no encuentre un incumbent dentro de un límite corto, lo cual no prueba infactibilidad.

## Entorno verificado

La implementación fue verificada en Windows 11 de 64 bits con Python 3.13.16, PySCIPOpt 6.2.1, SCIP 10.0.2, pytest 9.1.1 y openpyxl 3.1.5. `requirements.txt` fija el entorno completo utilizado.

Desde PowerShell, en la raíz del proyecto:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: -r requirements.txt
.\.venv\Scripts\python.exe scripts\verificar_entorno.py
```

No hace falta activar el entorno. Si el launcher `py` no detecta Python, se puede crear `.venv` con la ruta completa de `python.exe` y luego usar siempre `.\.venv\Scripts\python.exe`.

## Instancias

El formato UTF-8 admite líneas vacías y comentarios cuya línea comienza con `#`:

```text
N <diseños>
M <recursos>
BETA <factor>
B <recurso> <disponibilidad>
DISENO <diseño> <beneficio> <potencia> <cota>
A <recurso> <diseño> <coeficiente>
```

Los índices del archivo empiezan en 1. Internamente `a[i][j]` representa el consumo del recurso `i` por el diseño `j`. Los coeficientes `A` pueden ser negativos. El lector detecta índices inválidos, duplicados, registros faltantes, tipos incorrectos y dimensiones incoherentes.

Para regenerar las tres instancias aleatorias sin modificar el generador docente:

```powershell
.\.venv\Scripts\python.exe -m scripts.generar_instancias
```

Semillas: chica 42 (N=3, M=2), pesada 777 (N=80, M=25) y restrictiva 999 (N=120, M=40).

## Uso

Etapa 1, capacidad fija:

```powershell
.\.venv\Scripts\python.exe -m tp_modelado etapa1 instancias\instancia_manual.txt --segundos 1 --tau 2 --salida resultados\manual_e1
```

Etapa 2, búsqueda de capacidad:

```powershell
.\.venv\Scripts\python.exe -m tp_modelado etapa2 instancias\instancia_manual.txt --segundos 5 --salida resultados\manual_e2
```

La salida se muestra en la terminal y se guarda en `<salida>.json` y `<salida>.xlsx`. La CLI se niega a reemplazar archivos existentes; para hacerlo deliberadamente se debe agregar `--sobrescribir`.

Para ejecutar el protocolo breve de ocho casos:

```powershell
.\.venv\Scripts\python.exe -m tp_modelado experimentos --config experimentos\rapidos.json --salida resultados\entrega
```

Para repetir una entrada diez veces, agregar `"repeticiones": 10` a esa entrada del protocolo. Cada resultado recibe un sufijo `-r1` a `-r10` y una fila propia. También se puede regenerar un Excel sin ejecutar SCIP:

```powershell
.\.venv\Scripts\python.exe -m tp_modelado exportar --json resultados\entrega.json --excel resultados\entrega_regenerada.xlsx
```

## Búsqueda y tiempos

Si `U=sum(w[j]*u[j])` es como máximo 200, se recorren todas las capacidades de 0 a U. La garantía global sólo es verdadera cuando todas fueron resueltas a optimalidad.

Para U mayor, se evalúa una grilla reproducible de 17 puntos que contiene 0 y U. Luego se refinan hasta tres de los mejores centros durante un máximo de ocho rondas, sin repetir capacidades. Esta estrategia es heurística; no supone unimodalidad y, normalmente, informa «mejor solución encontrada, sin garantía global».

La etapa 1 aplica `segundos` a una única resolución de SCIP; su tiempo total incluye además lectura y construcción. La etapa 2 inicia un reloj monotónico al entrar, usa un deadline global y recalcula el restante antes de cada resolución. Lectura, construcción, cambios de RHS y extracción cuentan dentro del límite global. SCIP y Python pueden exceder ligeramente el deadline antes de devolver control; el exceso real queda registrado.

Entre iteraciones se copian los valores de la solución a objetos Python, se ejecuta `freeTransform()` cuando corresponde y se cambia únicamente el RHS de potencia con `chgRhs()`. El modelo no se reconstruye. La configuración `misc/resetstat=True` fue comprobada con capacidades no monótonas: el contador de resolución vuelve a cero al liberar la transformación.

## Reportes

El JSON conserva parámetros, entorno, hash de entradas, solución y traza completa de capacidades. El Excel contiene las hojas `Etapa 1` y `Etapa 2`, siempre con exactamente cinco columnas:

1. Instancia y ejecución.
2. Mejor solución factible, ganancia y beneficio neto.
3. Tau de esa solución.
4. Garantía de optimalidad para tau fijo o global.
5. Tiempos solicitado, total, solver y exceso.

Si un vector supera el límite de una celda Excel, la hoja referencia el vector completo conservado en JSON. Ausencia de incumbent se escribe como `sin solución encontrada`; no se reemplaza por ceros ficticios.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Los tests cubren lectura, argumentos inválidos, comparación contra enumeración exhaustiva, actualización de RHS, reinicio del contador SCIP, búsqueda global pequeña, JSON, Excel y protección contra sobrescritura. La instancia manual tiene óptimo global `tau=2`, `x=(0,2,0)` y beneficio neto 12.

El protocolo `experimentos/completos.json` incluye presupuestos de 3, 10 y 60 segundos para las instancias grandes. Es opcional y no se ejecuta por defecto porque suma varios minutos de cuotas.

## Ejecución realizada

El 4 de octubre de 2026 se ejecutó `experimentos/rapidos.json`. Los resultados completos están en `resultados/entrega.json` y `resultados/entrega.xlsx`. La instancia manual y la chica fueron certificadas globalmente en la etapa 2. Las búsquedas de tres segundos sobre las instancias grandes devolvieron la mejor solución encontrada sin garantía global. La etapa 1 restrictiva terminó por `timelimit` con un incumbent válido; esto confirma que el nombre del archivo no describe infactibilidad matemática.

En la ejecución final guardada, las búsquedas grandes consumieron el presupuesto global y la pesada registró un pequeño exceso mientras SCIP devolvía el control. El reporte conserva el valor medido en lugar de truncarlo. Los resultados dependen de la carga y del equipo, por lo que deben regenerarse si se cambia el entorno fijado.
