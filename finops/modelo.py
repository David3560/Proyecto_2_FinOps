"""Tipos y parámetros compartidos por el agente y el simulador."""
from dataclasses import dataclass
from math import isfinite

OBJ_DISP = 0.999
OBJ_LAT_MS = 200.0
MIN_WEB, MAX_WEB = 2, 8
MAX_BD = 3
HORAS_MES = 720.0
MUESTRAS_BAJAS = 3
ESPERA_REDUCCION = 3
PESOS = {"latencia": 0.30, "costo": 0.24, "riesgo": 0.38,
         "cambio": 0.032, "exceso": 0.30}
BASE_BALANCEADOR = 0.025  # USD/h
BASE_RAM = 0.22


@dataclass(frozen=True)
class Recursos:
    web: int = 2
    bd: int = 1
    cache: bool = False

    def __post_init__(self):
        if (type(self.web) is not int or type(self.bd) is not int
                or type(self.cache) is not bool
                or not MIN_WEB <= self.web <= MAX_WEB or not 1 <= self.bd <= MAX_BD):
            raise ValueError("Configuración fuera de los límites del laboratorio")


@dataclass(frozen=True)
class Tarifas:
    web: float = 0.075
    bd: float = 0.095
    cache: float = 0.020

    def __post_init__(self):
        for valor in (self.web, self.bd, self.cache):
            if not numero_en_rango(valor, 0, 1_000):
                raise ValueError("Tarifas inválidas")

    def costo_hora(self, recursos: Recursos) -> float:
        return (BASE_BALANCEADOR + recursos.web * self.web
                + recursos.bd * self.bd + recursos.cache * self.cache)


def numero_en_rango(valor, minimo, maximo) -> bool:
    return (type(valor) in (int, float) and minimo <= valor <= maximo
            and isfinite(valor))


@dataclass(frozen=True)
class Percepcion:
    id_evento: str
    minuto: int
    cpu_pct: float | None
    ram_pct: float
    latencia_ms: float
    rps: float
    bd_pct: float
    disponibilidad: float
    consumido_usd: float
    horas_restantes: float
    presupuesto_usd: float
    tarifas: Tarifas
    antiguedad_s: float = 0

    def problemas(self) -> list[str]:
        rangos = {
            "cpu_pct": (0, 100), "ram_pct": (0, 100), "bd_pct": (0, 100),
            "latencia_ms": (0, 60_000), "rps": (0, 1_000_000),
            "disponibilidad": (0, 1), "consumido_usd": (0, 1e9),
            "horas_restantes": (0, HORAS_MES), "presupuesto_usd": (0.01, 1e9),
            "antiguedad_s": (0, 90),
        }
        problemas = [campo for campo, rango in rangos.items()
                     if not numero_en_rango(getattr(self, campo), *rango)]
        if not isinstance(self.tarifas, Tarifas):
            problemas.append("tarifas")
        return problemas


@dataclass(frozen=True)
class EstadoProyectado:
    accion: str
    recursos: Recursos
    latencia_ms: float
    disponibilidad: float
    cierre_usd: float
    riesgo: float
    cambio: float
    exceso: float
    utilidad: float
    bloqueos: tuple[str, ...] = ()


@dataclass(frozen=True)
class Decision:
    diagnostico: str
    accion: str
    recursos: Recursos
    candidatos: tuple[EstadoProyectado, ...] = ()
    alertas: tuple[str, ...] = ()
    accion_fallida: str | None = None


class FalloActuador(RuntimeError):
    """El simulador rechazó el cambio antes de modificar sus recursos."""
