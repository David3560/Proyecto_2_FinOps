"""Interfaz base de la sección 10 de la guía, adaptada al dominio FinOps.

La plantilla original define el ciclo de un agente basado en utilidad
(Russell y Norvig): estado interno, proyección de acciones, cálculo de U,
selección del máximo y actuación. Aquí se conservan esos pasos como métodos
abstractos; las firmas reciben también la configuración actual del entorno,
porque las acciones dependen de los recursos encendidos.
"""
from abc import ABC, abstractmethod


class AgenteBasadoEnUtilidad(ABC):
    """Ciclo percepción → estado interno → proyección → utilidad → decisión → actuación."""

    @abstractmethod
    def actualizar_estado_interno(self, percepcion) -> str:
        """Paso 1 (modelo del mundo): interpreta los sensores y devuelve un diagnóstico."""

    @abstractmethod
    def generar_estados_proyectados(self, percepcion, actual):
        """Paso 2 (modelo de transición): proyecta el efecto de cada acción posible."""

    @abstractmethod
    def calcular_utilidad(self, *args, **kwargs) -> float:
        """Paso 3 (función de utilidad): asigna un valor numérico a un estado proyectado."""

    @abstractmethod
    def seleccionar_mejor_accion(self, percepcion, actual):
        """Paso 4 (decisión): elige la acción que maximiza U entre las permitidas."""

    @abstractmethod
    def ejecutar_actuador(self, percepcion, decision, entorno):
        """Paso 5 (actuadores): aplica la decisión sobre el entorno y emite alertas."""

    def procesar_evento(self, percepcion, entorno):
        """Orquesta el ciclo completo para una lectura de sensores."""
        decision = self.seleccionar_mejor_accion(percepcion, entorno.recursos)
        return self.ejecutar_actuador(percepcion, decision, entorno)
