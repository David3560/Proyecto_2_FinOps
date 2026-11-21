"""Banco de pruebas local para balanceador, clúster web, base de datos y caché."""
from dataclasses import dataclass, replace
from math import floor

from .modelo import HORAS_MES, FalloActuador, Percepcion, Recursos, Tarifas


@dataclass(frozen=True)
class Carga:
    rps: int
    tarifa: Tarifas = Tarifas()
    peso_bd: float = 1.0
    cacheabilidad: float = 0.47
    latencia_externa: float = 0.0
    cpu_ausente: bool = False
    antiguedad_s: int = 0
    fallo_actuador: bool = False


@dataclass(frozen=True)
class Observacion:
    cpu_pct: float
    ram_pct: float
    bd_pct: float
    latencia_ms: float
    ofrecidas: int
    exitosas: int

    @property
    def disponibilidad(self) -> float:
        return self.exitosas / self.ofrecidas if self.ofrecidas else 1.0


class EntornoSimulado:
    def __init__(self, recursos: Recursos, presupuesto: float, consumido: float = 0,
                 horas_restantes: float = HORAS_MES):
        self.recursos = recursos
        self.presupuesto = presupuesto
        self.consumido = consumido
        self.horas_restantes = horas_restantes
        self.minuto = 0
        self.alertas: list[tuple[int, str]] = []
        self.carga = Carga(0)

    def medir(self) -> Observacion:
        """Observación sintética a partir de la demanda oculta y la capacidad efectiva."""
        r, c = self.recursos, self.carga
        web = c.rps / (96 * r.web)
        factor_bd = c.peso_bd * (1 - c.cacheabilidad if r.cache else 1)
        bd = c.rps * factor_bd / (202 * r.bd)
        ocupacion = max(web, bd)
        ofrecidas = c.rps * 60
        exitosas = floor(ofrecidas / max(1.0, ocupacion))
        latencia = 50 + 90 * ocupacion ** 2 + 110 * max(0, ocupacion - 0.85) + c.latencia_externa
        return Observacion(min(100, 100 * web), min(100, 22 + 72 * web),
                           min(100, 100 * bd), latencia, ofrecidas, exitosas)

    def percibir(self, id_evento: str, carga: Carga) -> Percepcion:
        self.carga = carga
        obs = self.medir()
        p = Percepcion(id_evento, self.minuto, obs.cpu_pct, obs.ram_pct, obs.latencia_ms,
                      carga.rps, obs.bd_pct, obs.disponibilidad, self.consumido,
                      self.horas_restantes, self.presupuesto, carga.tarifa, carga.antiguedad_s)
        return replace(p, cpu_pct=None) if carga.cpu_ausente else p

    def aplicar(self, recursos: Recursos):
        if self.carga.fallo_actuador:
            raise FalloActuador("Rechazo simulado antes de aplicar")
        self.recursos = recursos

    def notificar(self, minuto: int, alerta: str):
        self.alertas.append((minuto, alerta))

    def facturar(self) -> float:
        intervalo = min(self.horas_restantes, 1 / 60)
        costo = intervalo * self.carga.tarifa.costo_hora(self.recursos)
        self.consumido += costo
        self.horas_restantes -= intervalo
        self.minuto += 1
        return costo
