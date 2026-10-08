# Control de tiempos y optimización paramétrica

El enunciado plantea dos decisiones para una fábrica de paneles acústicos: cuántas unidades producir de cada diseño y qué potencia eléctrica contratar. Contratar más potencia puede permitir una mayor producción, pero también aumenta el costo de infraestructura. El objetivo es encontrar el mejor beneficio neto dentro del tiempo disponible.

Resolvimos el problema en Python con PySCIPOpt, siguiendo las dos etapas de la consigna.

## Cómo representamos el problema

Cada variable `x[j]` indica cuántos paneles fabricar del diseño `j`. Las cantidades son enteras, no negativas y tienen un máximo `u[j]`. Cada unidad aporta un beneficio `c[j]`, utiliza recursos internos según `a[i][j]` y requiere una potencia `w[j]`.

Un plan de producción debe respetar tanto la disponibilidad `b[i]` de cada recurso como la potencia contratada `tau`. Para comparar distintas capacidades, descontamos de la ganancia de producción el costo de infraestructura del enunciado:

```text
beneficio neto = ganancia de producción - beta * tau²
```

El costo depende de la potencia contratada, aunque el plan elegido utilice menos.

## Etapa 1: producir con una capacidad fija

En `resolver_modelo(path_instancia, segundos, tau)` fijamos la potencia contratada y buscamos el plan de producción que dé la mayor ganancia sin superar los recursos disponibles. Como el costo de infraestructura es fijo para ese `tau`, maximizar la ganancia también maximiza el beneficio neto.

El tiempo solicitado limita la resolución del modelo. Medimos además el tiempo total de la función, que incluye leer los datos y preparar el problema.

Si se encuentra una solución, informamos las cantidades a producir, su ganancia, el beneficio neto y si se pudo demostrar que es óptima para esa capacidad.

## Etapa 2: elegir la capacidad

En `busqueda_tau(path_instancia, segundos)` probamos distintas potencias y conservamos el plan con mayor beneficio neto. La búsqueda abarca valores enteros entre cero y `U`, la potencia necesaria para fabricar el máximo permitido de todos los diseños.

Cuando el rango es pequeño, recorremos todas las capacidades mientras alcance el tiempo. Para rangos grandes, primero probamos valores repartidos a lo largo del intervalo y luego exploramos alrededor de los que dieron mejores resultados. Esta segunda estrategia permite buscar con un tiempo acotado, aunque puede dejar capacidades mejores sin evaluar.

Como pide la consigna, construimos el modelo una sola vez y, entre evaluaciones, cambiamos únicamente la capacidad eléctrica. El tiempo es global para toda la búsqueda: incluye lectura, preparación y resoluciones. Antes de cada evaluación calculamos cuánto queda y detenemos la búsqueda si resulta insuficiente. Registramos el tiempo real utilizado, incluido cualquier pequeño exceso al finalizar una resolución.

## Cómo interpretar los resultados

Una solución **factible** cumple las restricciones. Una solución **óptima** tiene además la garantía de que no existe otra mejor dentro del problema evaluado.

En la etapa 1, esa garantía corresponde a la potencia fijada. En la etapa 2, sólo declaramos un óptimo global si evaluamos todas las capacidades y demostramos el óptimo de cada una. En los demás casos informamos la mejor solución encontrada, sin garantía global. El valor `Pi(tau)` del enunciado representa la ganancia óptima para esa capacidad; una solución obtenida al agotarse el tiempo puede tener una ganancia menor.

Si el tiempo termina antes de encontrar una solución factible, lo indicamos expresamente. Eso por sí solo no demuestra que el problema sea imposible. En particular, la instancia docente llamada `instancia_sin_solucion.txt` tiene restricciones más ajustadas, pero producir cero unidades sigue siendo factible.

## Instancias y comprobaciones

Los datos se cargan desde archivos externos mediante `leer_instancia(path_instancia: str)`, respetando el formato del generador docente y detectando archivos inexistentes o mal formados.

Incluimos una instancia manual de 3 diseños y 2 recursos, una chica del generador y las dos instancias grandes provistas por este. Las pruebas revisan la lectura, las restricciones, el control del tiempo y el manejo de los estados del solver, incluidos los casos en que no llega a encontrar una solución.

En la instancia manual comparamos la respuesta con todas las combinaciones posibles. La mejor decisión es contratar `tau=2` y producir dos unidades del segundo diseño: la ganancia es 14, el costo de infraestructura es 2 y el beneficio neto es **12**.

## Reporte de la entrega

El archivo [entrega.xlsx](resultados/entrega.xlsx) reúne las ejecuciones en dos hojas, una por etapa. Cada fila tiene las cinco columnas solicitadas:

1. Instancia y ejecución.
2. Mejor solución factible encontrada y su valor.
3. Potencia contratada correspondiente.
4. Garantía de optimalidad.
5. Tiempo solicitado y efectivamente utilizado.

El archivo [entrega.json](resultados/entrega.json) conserva también el detalle de las capacidades evaluadas. En las ejecuciones guardadas, la etapa 2 encontró y certificó el óptimo global de las instancias manual y chica. Para las grandes, las búsquedas de tres segundos terminaron sin garantía global. En la etapa 1, la instancia restrictiva devolvió una solución factible al alcanzar el límite de tiempo, sin demostrar optimalidad.

## Cómo ejecutarlo

Desde PowerShell, en la carpeta del proyecto, con Python 3.13:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: -r requirements.txt
.\.venv\Scripts\python.exe scripts\verificar_entorno.py
```

Para probar las dos etapas con la instancia manual:

```powershell
.\.venv\Scripts\python.exe -m tp_modelado etapa1 instancias\instancia_manual.txt --segundos 1 --tau 2 --salida resultados\manual_e1
.\.venv\Scripts\python.exe -m tp_modelado etapa2 instancias\instancia_manual.txt --segundos 5 --salida resultados\manual_e2
```

Los resultados se muestran en la terminal y se guardan en JSON y Excel. Para reemplazar una salida existente, agregar `--sobrescribir`.

Para repetir las ocho ejecuciones de la entrega con un nuevo nombre de salida:

```powershell
.\.venv\Scripts\python.exe -m tp_modelado experimentos --config experimentos\rapidos.json --salida resultados\nueva_entrega
```

Para ejecutar las pruebas:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```
