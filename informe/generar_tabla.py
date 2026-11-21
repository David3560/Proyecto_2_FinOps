"""Actualiza las filas LaTeX a partir del resumen producido por el simulador."""
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def formatear(numero, decimales):
    return f"{numero:.{decimales}f}".replace(".", "{,}")


def main():
    datos = json.loads((RAIZ / "evidencia/resumen.json").read_text(encoding="utf-8"))
    filas = []
    for dato in datos:
        a, f = dato["agente"], dato["fijo"]
        celdas = [dato["caso"]]
        for clave, decimales in [("disponibilidad_pct", 2), ("latencia_media_ms", 1),
                                 ("cierre_final_proyectado_usd", 2)]:
            celdas.extend(formatear(modo[clave], decimales) for modo in (a, f))
        celdas.append(f"{a['intervalos_latencia_objetivo']}/{a['intervalos']}")
        filas.append(" & ".join(celdas) + r" \\")
    (RAIZ / "informe/resultados.tex").write_text("\n".join(filas) + "\n" + chr(92) + "bottomrule" + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
