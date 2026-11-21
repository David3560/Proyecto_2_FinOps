"""Ciclo percepción, estado interno, proyección, decisión y actuación."""
from dataclasses import replace
from itertools import product

from .plantilla import AgenteBasadoEnUtilidad
from .modelo import (
    BASE_RAM, ESPERA_REDUCCION, MAX_BD, MAX_WEB, MIN_WEB, MUESTRAS_BAJAS,
    OBJ_DISP, OBJ_LAT_MS, PESOS, Decision, EstadoProyectado, FalloActuador,
    Percepcion, Recursos,
)


def nombre_accion(actual: Recursos, nuevo: Recursos) -> str:
    """Traduce la diferencia entre dos configuraciones a un nombre de acción legible."""
    cambios = []
    if nuevo.web > actual.web:
        cambios.append(f"ENCENDER_WEB_{nuevo.web - actual.web}")
    if nuevo.web < actual.web:
        cambios.append("APAGAR_WEB_1")
    if nuevo.bd > actual.bd:
        cambios.append("ESCALAR_BD")
    if nuevo.cache and not actual.cache:
        cambios.append("ACTIVAR_CACHE")
    if actual.cache and not nuevo.cache:
        cambios.append("DESACTIVAR_CACHE")
    return "+".join(cambios) or "MANTENER"


class AgenteFinOps(AgenteBasadoEnUtilidad):
    """Agente de autoescalado basado en utilidad con restricciones duras (informe, Ec. 1–4)."""

    def __init__(self):
        self.rps_suavizado = None
        self.muestras_bajas = 0
        self.ultimo_cambio = -ESPERA_REDUCCION
        self.ultimo_minuto = -1

    def actualizar_estado_interno(self, p: Percepcion) -> str:
        """Actualiza la media exponencial de RPS y el contador de muestras bajas; devuelve el diagnóstico."""
        previo = self.rps_suavizado
        self.rps_suavizado = p.rps if previo is None else 0.6 * p.rps + 0.4 * previo
        baja = (max(p.cpu_pct, p.ram_pct, p.bd_pct) < 55
                and p.latencia_ms < OBJ_LAT_MS and p.disponibilidad >= OBJ_DISP)
        self.muestras_bajas = self.muestras_bajas + 1 if baja else 0
        if p.disponibilidad < OBJ_DISP or p.latencia_ms >= OBJ_LAT_MS:
            return "DEGRADACION"
        if max(p.cpu_pct, p.ram_pct, p.bd_pct) >= 75:
            return "SATURACION"
        return "CARGA_BAJA" if baja else "ESTABLE"

    @staticmethod
    def calcular_utilidad(latencia, riesgo, cierre, presupuesto, cambio, exceso):
        """Función de utilidad U(s) de la Ec. 3."""
        return (PESOS["latencia"] * min(1.0, OBJ_LAT_MS / max(latencia, 1))
                - PESOS["costo"] * cierre / presupuesto
                - PESOS["riesgo"] * riesgo - PESOS["cambio"] * cambio
                - PESOS["exceso"] * exceso)

    def proyectar(self, p: Percepcion, actual: Recursos, nuevo: Recursos):
        """Proyecta presión (Ec. 1), latencia, pérdida, riesgo (Ec. 4) y cierre (Ec. 2) de un candidato."""
        factor = max(1.0, self.rps_suavizado / max(p.rps, 1))
        # Se conserva el exceso de latencia que el modelo no logra explicar.
        presion_actual = max(p.cpu_pct / 100, (p.ram_pct / 100 - BASE_RAM) / (1 - BASE_RAM),
                             p.bd_pct / 100, p.rps / (100 * actual.web),
                             p.rps * (0.55 if actual.cache else 1) / (210 * actual.bd))
        lat_extra = max(0, p.latencia_ms - 55 - 95 * presion_actual ** 2)

        def presion(margen):
            demanda = max(p.rps, self.rps_suavizado) * margen
            web = actual.web / nuevo.web
            cache = ((0.55 if nuevo.cache else 1) / (0.55 if actual.cache else 1))
            return max(demanda / (100 * nuevo.web),
                       p.cpu_pct / 100 * web * factor * margen,
                       max(0, p.ram_pct / 100 - BASE_RAM) / (1 - BASE_RAM) * web * factor * margen,
                       demanda * (0.55 if nuevo.cache else 1) / (210 * nuevo.bd),
                       p.bd_pct / 100 * actual.bd / nuevo.bd * cache * factor * margen)

        normal, estres = presion(1.0), presion(1.15)
        latencia = 55 + 95 * normal ** 2 + lat_extra
        def perdida(carga):
            # Tramo suave cerca de la saturación y pérdida de flujo 1 - 1/ρ en sobrecarga.
            return max(0.08 * min(1.0, max(0.0, carga - 0.85)),
                       1 - 1 / carga if carga > 1 else 0.0)

        disponibilidad = 1 - perdida(normal)
        riesgo = 0.8 * min(1.0, perdida(normal) / 0.02) + 0.2 * min(1.0, perdida(estres) / 0.02)
        cierre = p.consumido_usd + p.horas_restantes * p.tarifas.costo_hora(nuevo)
        exceso = max(0.0, cierre / p.presupuesto_usd - 1)
        cambio = (abs(nuevo.web - actual.web) + int(actual.bd != nuevo.bd)
                  + int(actual.cache != nuevo.cache)) / 4
        utilidad = self.calcular_utilidad(latencia, riesgo, cierre, p.presupuesto_usd, cambio, exceso)
        return EstadoProyectado(nombre_accion(actual, nuevo), nuevo, latencia,
                                 disponibilidad, cierre, riesgo, cambio, exceso, utilidad)

    def generar_estados_proyectados(self, p: Percepcion, actual: Recursos):
        """Enumera candidatos dentro de los límites y marca bloqueos por histéresis, servicio o presupuesto."""
        webs = range(max(MIN_WEB, actual.web - 1), min(MAX_WEB, actual.web + 2) + 1)
        bases = range(actual.bd, min(MAX_BD, actual.bd + 1) + 1)
        estados = [self.proyectar(p, actual, Recursos(web, bd, cache))
                   for web, bd, cache in product(webs, bases, (False, True))]
        mantener = next(e for e in estados if e.recursos == actual)
        salida = []
        for estado in estados:
            bloqueos = []
            nuevo = estado.recursos
            reduccion = nuevo.web < actual.web or (actual.cache and not nuevo.cache)
            if reduccion:
                if (self.muestras_bajas < MUESTRAS_BAJAS
                        or p.minuto - self.ultimo_cambio < ESPERA_REDUCCION):
                    bloqueos.append("HISTERESIS")
                if estado.disponibilidad < OBJ_DISP or estado.latencia_ms >= OBJ_LAT_MS:
                    bloqueos.append("OBJETIVOS_DE_SERVICIO")
            if (estado.cierre_usd > p.presupuesto_usd + 1e-9
                    and p.tarifas.costo_hora(nuevo) > p.tarifas.costo_hora(actual) + 1e-9):
                bloqueos.append("PRESUPUESTO")
            salida.append(replace(estado, bloqueos=tuple(bloqueos)))
        return tuple(salida), mantener

    def seleccionar_mejor_accion(self, p: Percepcion, actual: Recursos) -> Decision:
        """Valida la lectura y maximiza U entre los candidatos conformes o, si no hay, entre los permitidos."""
        problemas = p.problemas()
        if type(p.minuto) is not int or p.minuto <= self.ultimo_minuto:
            problemas.append("minuto no creciente")
        else:
            if p.minuto != self.ultimo_minuto + 1:
                self.muestras_bajas = 0
                self.rps_suavizado = None
            self.ultimo_minuto = p.minuto
        if problemas:
            self.muestras_bajas = 0
            self.rps_suavizado = None
            return Decision("TELEMETRIA_INVALIDA", "MANTENER", actual,
                            alertas=("TELEMETRIA:" + ", ".join(problemas),))
        diagnostico = self.actualizar_estado_interno(p)
        estados, mantener = self.generar_estados_proyectados(p, actual)
        permitidos = [e for e in estados if not e.bloqueos]
        conformes = [e for e in permitidos
                     if e.disponibilidad >= OBJ_DISP and e.latencia_ms < OBJ_LAT_MS]
        mejor = max(conformes or permitidos,
                    key=lambda e: (e.utilidad, -e.cambio, -e.cierre_usd))
        alertas = []
        if max(mejor.cierre_usd, mantener.cierre_usd) >= 0.90 * p.presupuesto_usd:
            alertas.append("PRESUPUESTO_90")
        if mejor.cierre_usd > p.presupuesto_usd + 1e-9:
            alertas.append("PRESUPUESTO_PROYECTADO_EXCEDIDO")
        if not conformes:
            alertas.append("OBJETIVOS_NO_PROYECTADOS")
            if any("PRESUPUESTO" in e.bloqueos for e in estados):
                alertas.append("CAPACIDAD_LIMITADA_POR_PRESUPUESTO")
        return Decision(diagnostico, mejor.accion, mejor.recursos, estados, tuple(alertas))

    def ejecutar_actuador(self, p: Percepcion, decision: Decision, entorno) -> Decision:
        """Aplica la configuración elegida de forma atómica; si el entorno la rechaza, mantiene y alerta."""
        anterior = entorno.recursos
        try:
            if decision.recursos != anterior:
                entorno.aplicar(decision.recursos)
                self.ultimo_cambio = p.minuto
                self.muestras_bajas = 0
        except FalloActuador:
            decision = replace(decision, accion="MANTENER", recursos=anterior,
                               accion_fallida=decision.accion,
                               alertas=decision.alertas + ("FALLO_ACTUADOR",))
        for alerta in decision.alertas:
            entorno.notificar(p.minuto, alerta)
        return decision
