"""Validación de los actuadores, el modelo y las 11 simulaciones."""
import unittest
from dataclasses import replace

from finops.__main__ import metricas, simular
from finops.agente import AgenteFinOps
from finops.escenarios import CASOS
from finops.modelo import MIN_WEB, OBJ_DISP, OBJ_LAT_MS, Recursos
from finops.simulador import Carga, EntornoSimulado


def caso(numero):
    return CASOS[numero - 1]


class EscenariosFinOps(unittest.TestCase):
    def test_cp01_estable(self):
        filas = simular(caso(1))
        self.assertTrue(all(f["accion"] == "MANTENER" and not f["alertas"] for f in filas))
        self.assertTrue(metricas(filas)["objetivo_disponibilidad"])

    def test_cp02_histeresis_piso_y_ahorro(self):
        filas = simular(caso(2))
        self.assertEqual([f["minuto"] for f in filas if f["accion"] == "APAGAR_WEB_1"], [2, 5])
        self.assertEqual(filas[-1]["despues"]["web"], MIN_WEB)
        self.assertTrue(any("HISTERESIS" in e["bloqueos"] for e in filas[0]["candidatos"]))
        actual, fijo = metricas(filas), metricas(simular(caso(2), False))
        self.assertTrue(actual["objetivo_disponibilidad"])
        self.assertLess(actual["costo_intervalos_usd"], fijo["costo_intervalos_usd"])

    def test_cp03_web_recupera_pico(self):
        filas = simular(caso(3))
        self.assertEqual(filas[1]["accion"], "ENCENDER_WEB_2")
        self.assertEqual(filas[1]["despues"]["web"], 4)
        actual, fijo = metricas(filas), metricas(simular(caso(3), False))
        self.assertTrue(actual["objetivo_disponibilidad"])
        self.assertFalse(fijo["objetivo_disponibilidad"])
        self.assertLess(actual["latencia_media_ms"], OBJ_LAT_MS)

    def test_cp04_base_de_datos_y_cache_inefectiva(self):
        filas = simular(caso(4))
        self.assertEqual(filas[0]["accion"], "ACTIVAR_CACHE")
        self.assertLess(filas[0]["observacion"]["exitosas"], filas[0]["observacion"]["ofrecidas"])
        self.assertEqual(filas[1]["accion"], "ESCALAR_BD")
        self.assertEqual(filas[1]["despues"]["bd"], 2)
        self.assertEqual(filas[1]["observacion"]["exitosas"], filas[1]["observacion"]["ofrecidas"])
        self.assertFalse(metricas(filas)["objetivo_disponibilidad"])

    def test_cp05_cache_efectiva(self):
        filas = simular(caso(5))
        self.assertEqual(filas[0]["accion"], "ACTIVAR_CACHE")
        self.assertTrue(filas[0]["despues"]["cache"])
        self.assertEqual(filas[0]["despues"]["bd"], 1)
        self.assertTrue(metricas(filas)["objetivo_disponibilidad"])

    def test_cp06_telemetria_invalida(self):
        filas = simular(caso(6))
        self.assertEqual(filas[0]["alertas"], ["TELEMETRIA:cpu_pct"])
        self.assertEqual(filas[1]["alertas"], ["TELEMETRIA:antiguedad_s"])
        self.assertTrue(all(f["antes"] == f["despues"] and not f["candidatos"] for f in filas))

    def test_cp07_presupuesto_duro(self):
        filas = simular(caso(7))
        for fila in filas[1:]:
            self.assertIn("CAPACIDAD_LIMITADA_POR_PRESUPUESTO", fila["alertas"])
            self.assertTrue(any("PRESUPUESTO" in e["bloqueos"] for e in fila["candidatos"]))
            self.assertEqual(fila["antes"], fila["despues"])
        self.assertFalse(metricas(filas)["objetivo_disponibilidad"])

    def test_cp08_sin_oscilacion_de_instancias(self):
        filas = simular(caso(8))
        self.assertTrue(all(f["despues"]["web"] == 3 for f in filas))
        self.assertTrue(metricas(filas)["objetivo_disponibilidad"])

    def test_cp09_fallo_atomico_y_recuperacion(self):
        filas = simular(caso(9))
        self.assertEqual(filas[0]["antes"], filas[0]["despues"])
        self.assertEqual(filas[0]["accion_fallida"], "ENCENDER_WEB_2")
        self.assertIn("FALLO_ACTUADOR", filas[0]["alertas"])
        self.assertEqual(filas[1]["despues"]["web"], 4)
        self.assertEqual(filas[1]["observacion"]["exitosas"], filas[1]["observacion"]["ofrecidas"])

    def test_cp10_reaccion_a_tarifas_y_gasto_acumulado(self):
        filas = simular(caso(10))
        self.assertLess(filas[0]["cierre_proyectado_usd"], caso(10).presupuesto)
        self.assertIn("PRESUPUESTO_PROYECTADO_EXCEDIDO", filas[1]["alertas"])
        self.assertGreater(filas[1]["cierre_proyectado_usd"], caso(10).presupuesto)
        self.assertLess(filas[-1]["cierre_proyectado_usd"], caso(10).presupuesto)
        self.assertEqual(filas[2]["accion"], "APAGAR_WEB_1")

    def test_cp11_latencia_externa(self):
        filas = simular(caso(11))
        self.assertTrue(all("OBJETIVOS_NO_PROYECTADOS" in f["alertas"] for f in filas))
        self.assertTrue(all(f["antes"] == f["despues"] for f in filas))
        self.assertEqual(metricas(filas)["intervalos_latencia_objetivo"], 0)

    def test_seleccion_maximiza_utilidad_en_conjunto_factible(self):
        for escenario in CASOS:
            for fila in simular(escenario):
                if fila["accion_fallida"] or not fila["candidatos"]:
                    continue
                validos = [e for e in fila["candidatos"] if not e["bloqueos"]]
                conformes = [e for e in validos
                             if e["disponibilidad"] >= OBJ_DISP and e["latencia_ms"] < OBJ_LAT_MS]
                maximo = max(e["utilidad"] for e in conformes or validos)
                self.assertAlmostEqual(fila["utilidad_aplicada"], maximo)

    def test_no_presupuesto_adicional_al_fallar_sensores_o_repetir_muestra(self):
        entorno = EntornoSimulado(Recursos(), 500)
        agente = AgenteFinOps()
        p = entorno.percibir("x", Carga(130))
        agente.procesar_evento(p, entorno)
        repetida = agente.procesar_evento(p, entorno)
        invalida = agente.procesar_evento(replace(p, minuto=1, rps=float("nan")), entorno)
        self.assertEqual(repetida.alertas, ("TELEMETRIA:minuto no creciente",))
        self.assertEqual(invalida.alertas, ("TELEMETRIA:rps",))
        self.assertEqual(entorno.recursos, Recursos())


if __name__ == "__main__":
    unittest.main()
