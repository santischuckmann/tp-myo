# -*- coding: utf-8 -*-
"""
Generador aleatorio de instancias de texto para ser
leídos por la función `leer_instancia` requerida en el TP.
"""

import random
import os
from typing import Optional

# ==========================================
# CONSTANTES DE CONFIGURACIÓN Y VALORES DEFAULT
# ==========================================
DIR_INSTANCIAS = "instancias"

# 1. Instancia estándar / chica
PATH_INSTANCIA_CHICA = os.path.join(DIR_INSTANCIAS, "instancia_chica.txt")
DEFAULT_N = 5
DEFAULT_M = 3
DEFAULT_SEED = 42

# 2. Instancia pesada
PATH_INSTANCIA_PESADA = os.path.join(DIR_INSTANCIAS, "instancia_pesada.txt")
PESADA_N = 80
PESADA_M = 25
PESADA_SEED = 777

# 3. Instancia infactible o sin tiempo para solución (timeout prematuro)
PATH_INSTANCIA_SIN_SOL = os.path.join(DIR_INSTANCIAS, "instancia_sin_solucion.txt")
SINSOL_N = 120
SINSOL_M = 40
SINSOL_SEED = 999

# Rangos para parámetros económicos y de infraestructura
MIN_BETA, MAX_BETA = 0.5, 3.5

# Rangos para recursos disponibles (b_i)
MIN_RECURSO_B, MAX_RECURSO_B = 50, 150

# Rangos por diseño (Beneficio c_j, Potencia w_j, Cota u_j)
MIN_BENEFICIO_C, MAX_BENEFICIO_C = 10, 100
MIN_POTENCIA_W, MAX_POTENCIA_W = 1, 5
MIN_COTA_U, MAX_COTA_U = 20, 50

# Rangos para requerimiento de recursos (a_ij)
MIN_REQ_A, MAX_REQ_A = -2, 30

# ==========================================


def generar_instancia(
    filename: str,
    N: int,
    M: int,
    seed: Optional[int] = None,
    restrictiva: bool = False
):
    """
    Genera un archivo de instancia aleatorio con control de complejidad.

    Parámetros:
    - filename: Ruta o nombre del archivo de salida.
    - N: Cantidad de diseños de paneles acústicos.
    - M: Cantidad de recursos internos limitados.
    - seed: Semilla para la reproducibilidad (opcional).
    - restrictiva: True para instancias difíciles
    """
    if seed is not None:
        random.seed(seed)

    beta = round(random.uniform(MIN_BETA, MAX_BETA), 2)

    # Si es restrictiva, bajamos los recursos b_i para asfixiar el espacio de soluciones
    divisor_b = 2 if restrictiva else 1

    # Recursos disponibles b_i (para cada i en M)
    b = [random.randint(MIN_RECURSO_B, MAX_RECURSO_B) // divisor_b for _ in range(M)]

    # Datos por diseño j en N (c_j, w_j, u_j, y consumo de recursos a_ij)
    c = []  # Beneficio unitario
    w = []  # Consumo de potencia unitario
    u = []  # Cota superior de fabricación
    a = [[0.0] * N for _ in range(M)]  # Requerimiento de recursos

    for j in range(N):
        c.append(random.randint(MIN_BENEFICIO_C, MAX_BENEFICIO_C))
        w.append(random.randint(MIN_POTENCIA_W, MAX_POTENCIA_W))
        u.append(random.randint(MIN_COTA_U, MAX_COTA_U))
        
        # Generar requerimientos de recursos a_ij asegurando que sean enteros
        for i in range(M):
            a[i][j] = random.randint(MIN_REQ_A, MAX_REQ_A)

    # Escritura del archivo de instancia
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"# Instancia generada (N={N}, M={M}, restrictiva={restrictiva})\n")
        f.write(f"N {N}\n")
        f.write(f"M {M}\n")
        f.write(f"BETA {beta}\n")
        
        f.write("\n# Recursos disponibles (b_i)\n")
        for i in range(M):
            f.write(f"B {i + 1} {b[i]}\n")
            
        f.write("\n# Datos por diseño (Beneficio c_j, Potencia w_j, Cota u_j)\n")
        for j in range(N):
            f.write(f"DISENO {j + 1} {c[j]} {w[j]} {u[j]}\n")
            
        f.write("\n# Requerimiento de recursos (a_ij por recurso i y diseño j)\n")
        for i in range(M):
            for j in range(N):
                f.write(f"A {i + 1} {j + 1} {a[i][j]}\n")

    print(f"Instancia generada: '{filename}' (N={N}, M={M}, beta={beta})")


if __name__ == "__main__":
    os.makedirs(DIR_INSTANCIAS, exist_ok=True)
    
    # 1. Instancia Pesada: Con N=80 y M=25, para un tau medio-bajo, 
    # SCIP tardará varios minutos (o no cerrará el gap) en 60 segundos.
    generar_instancia(
        filename=PATH_INSTANCIA_PESADA,
        N=PESADA_N,
        M=PESADA_M,
        seed=PESADA_SEED,
        restrictiva=False
    )
    
    # 2. Instancia Sin Solución a tiempo corto: Con N=120, M=40 y recursos muy acotados (restrictiva=True),
    # a SCIP le costará encontrar *incluso la primera solución factible*. 
    # Si le pones un límite estricto de **2 o 3 segundos** (`model.setParam('limits/time', 3)`), 
    # expirará el tiempo antes de hallar unfeasible/optimal o cualquier solución inicial.
    generar_instancia(
        filename=PATH_INSTANCIA_SIN_SOL,
        N=SINSOL_N,
        M=SINSOL_M,
        seed=SINSOL_SEED,
        restrictiva=True
    )
