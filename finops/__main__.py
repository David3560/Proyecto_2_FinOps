"""Ejecuta el laboratorio y guarda evidencia auditable por escenario."""
import argparse
import csv
import json
from dataclasses import asdict
from pathlib import Path

from .agente import AgenteFinOps
from .escenarios import CASOS, Escenario
from .modelo import OBJ_DISP, OBJ_LAT_MS
from .simulador import EntornoSimulado


def simular(caso: Escenario, usar_agente: bool = True) -> list[dict]:
    entorno = EntornoSimulado(caso.recursos, caso.presupuesto,
                              caso.consumido, caso.horas_restantes)
    agente = AgenteFinOps() if usar_agente else None
    filas = []
    for i, carga in enumerate(caso.cargas, 1):
        p = entorno.percibir(f"{caso.id}-{i:02d}", carga)
        antes = entorno.recursos
        medida_antes = entorno.medir()
        decision = agente.procesar_evento(p, entorno) if agente else None
        medida = entorno.medir()
        candidatos = [asdict(e) for e in decision.candidatos] if decision else []
        aplicada = next((e for e in candidatos if e["accion"] == decision.accion), None)
        cierre = entorno.consumido + entorno.horas_restantes * p.tarifas.costo_hora(entorno.recursos)
        costo = entorno.facturar()
        filas.append({
            "caso": caso.id, "evento": p.id_evento, "minuto": p.minuto,
            "modo": "agente" if usar_agente else "fijo",
            "diagnostico": decision.diagnostico if decision else "CAPACIDAD_FIJA",
            "accion": decision.accion if decision else "MANTENER",
            "antes": asdict(antes), "despues": asdict(entorno.recursos),
            "alertas": list(decision.alertas) if decision else [],
            "accion_fallida": decision.accion_fallida if decision else None,
            "utilidad_aplicada": aplicada["utilidad"] if aplicada else None,
            "costo_intervalo_usd": costo, "cierre_proyectado_usd": cierre,
            "telemetria": asdict(p), "observacion_previa": asdict(medida_antes),
            "observacion": asdict(medida), "candidatos": candidatos,
        })
    return filas


def metricas(filas: list[dict]) -> dict:
    total = sum(f["observacion"]["ofrecidas"] for f in filas)
    exitosas = sum(f["observacion"]["exitosas"] for f in filas)
    latencia = sum(f["observacion"]["latencia_ms"] * f["observacion"]["exitosas"] for f in filas)
    costo = sum(f["costo_intervalo_usd"] for f in filas)
    return {
        "peticiones": total, "exitosas": exitosas,
        "disponibilidad_pct": 100 * exitosas / total if total else None,
        "latencia_media_ms": latencia / exitosas if exitosas else None,
        "intervalos_latencia_objetivo": sum(f["observacion"]["latencia_ms"] < OBJ_LAT_MS for f in filas),
        "intervalos": len(filas), "costo_intervalos_usd": costo,
        "cierre_final_proyectado_usd": filas[-1]["cierre_proyectado_usd"],
        "cambios": sum(f["antes"] != f["despues"] for f in filas),
        "alertas": sum(len(f["alertas"]) for f in filas),
        "objetivo_disponibilidad": exitosas / total >= OBJ_DISP if total else None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--caso", choices=[c.id for c in CASOS])
    parser.add_argument("--salida", type=Path, default=Path("evidencia"))
    args = parser.parse_args()
    args.salida.mkdir(parents=True, exist_ok=True)
    resumen, traza = [], []
    for caso in CASOS:
        if args.caso and caso.id != args.caso:
            continue
        agente, fijo = simular(caso), simular(caso, False)
        traza.extend(agente + fijo)
        kpi_agente, kpi_fijo = metricas(agente), metricas(fijo)
        resumen.append({"caso": caso.id, "categoria": caso.categoria, "nombre": caso.nombre,
                        "agente": kpi_agente, "fijo": kpi_fijo})
        print(f"{caso.id} {caso.nombre}: {kpi_agente['disponibilidad_pct']:.3f}% | "
              f"{kpi_agente['latencia_media_ms']:.1f} ms | "
              f"cierre USD {kpi_agente['cierre_final_proyectado_usd']:.2f} | "
              + ", ".join(f["accion"] for f in agente))
    (args.salida / "resumen.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (args.salida / "traza.jsonl").open("w", encoding="utf-8", newline="\n") as archivo:
        for fila in traza:
            archivo.write(json.dumps(fila, ensure_ascii=False) + "\n")
    with (args.salida / "metricas.csv").open("w", encoding="utf-8-sig", newline="") as archivo:
        columnas = ["caso", "categoria", "nombre", "modo", *resumen[0]["agente"].keys()]
        tabla = csv.DictWriter(archivo, fieldnames=columnas, lineterminator="\n")
        tabla.writeheader()
        for caso in resumen:
            for modo in ("agente", "fijo"):
                datos = {k: caso[k] for k in ("caso", "categoria", "nombre")}
                tabla.writerow({**datos, "modo": modo, **caso[modo]})
    print(f"Archivos de evidencia: {args.salida.resolve()}")


if __name__ == "__main__":
    main()
