from pathlib import Path

from generate_instance_a import generar_instancia


def main() -> None:
    destino = Path("instancias")
    destino.mkdir(exist_ok=True)
    generar_instancia(str(destino / "instancia_chica.txt"), 3, 2, seed=42)
    generar_instancia(str(destino / "instancia_pesada.txt"), 80, 25, seed=777)
    generar_instancia(str(destino / "instancia_sin_solucion.txt"), 120, 40, seed=999, restrictiva=True)


if __name__ == "__main__":
    main()
