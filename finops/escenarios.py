"""Escenarios reproducibles. Las tarifas representan supuestos de laboratorio."""
from dataclasses import dataclass

from .modelo import HORAS_MES, Recursos, Tarifas
from .simulador import Carga


@dataclass(frozen=True)
class Escenario:
    id: str
    categoria: str
    nombre: str
    recursos: Recursos
    presupuesto: float
    cargas: tuple[Carga, ...]
    consumido: float = 0
    horas_restantes: float = HORAS_MES


def rps(*valores: int) -> tuple[Carga, ...]:
    return tuple(Carga(v) for v in valores)


CASOS = (
    Escenario("CP01", "Rutinario", "Carga estable", Recursos(), 420, rps(85, 92, 90)),
    Escenario("CP02", "Rutinario", "Descenso sostenido", Recursos(4), 560, rps(62, 60, 63, 60, 61, 60, 61)),
    Escenario("CP03", "Crítico", "Pico en el clúster web", Recursos(2, 2), 570, rps(125, 290, 300, 235)),
    Escenario("CP04", "Crítico", "Saturación de BD y tráfico no cacheable", Recursos(4), 540,
              (Carga(165, peso_bd=1.35, cacheabilidad=0),) * 3),
    Escenario("CP05", "Crítico", "Saturación de BD con tráfico cacheable", Recursos(4), 490,
              (Carga(230),) * 3),
    Escenario("CP06", "Ambiguo", "CPU ausente o lectura desactualizada", Recursos(3), 500,
              (Carga(270, cpu_ausente=True), Carga(270, antiguedad_s=120))),
    Escenario("CP07", "Crítico", "Pico sin margen financiero", Recursos(), 210, rps(110, 460, 460)),
    Escenario("CP08", "Ambiguo", "Tráfico oscilante", Recursos(3), 500, rps(70, 174, 62, 180, 64, 172)),
    Escenario("CP09", "Crítico", "Fallo y recuperación del actuador", Recursos(2, 2), 570,
              (Carga(290, fallo_actuador=True), Carga(290))),
    Escenario("CP10", "Crítico", "Tarifa alta cerca del cierre", Recursos(4), 400,
              (Carga(60),) + (Carga(60, tarifa=Tarifas(0.19, 0.12, 0.025)),) * 3, 370, 40),
    Escenario("CP11", "Ambiguo", "Latencia externa con baja utilización", Recursos(), 440,
              (Carga(80, latencia_externa=300),) * 3),
)
