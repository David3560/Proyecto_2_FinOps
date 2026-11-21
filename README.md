# Agente de optimización y autoescalado cloud (FinOps)

Proyecto 2 del *Taller de ingeniería de agentes inteligentes*, asignatura IS0315 Technology Trends, Fundación Universitaria Los Libertadores.

**Autor:** Larry David Botia Contreras · **Docente:** Gonzalo Rodríguez

El proyecto implementa un agente basado en utilidad que, cada minuto simulado, observa la carga de una aplicación web y el gasto en la nube, proyecta el efecto de varias configuraciones y aplica la que maximiza la función de utilidad. Actúa sobre las instancias web, el nivel de la base de datos, la caché y las alertas financieras u operativas, respetando el presupuesto mensual.

## Estructura

```
finops/
  plantilla.py    Interfaz base del agente (plantilla de la guía, sección 10)
  agente.py       AgenteFinOps: estado interno, proyección, utilidad, decisión y actuación
  modelo.py       Tipos de datos, límites, tarifas y pesos de la utilidad
  simulador.py    Entorno simulado: clúster web, base de datos, caché y facturación
  escenarios.py   Once casos de prueba (rutinarios, ambiguos y críticos)
  __main__.py     Ejecución de los casos, comparación con capacidad fija y evidencia
tests/
  test_finops.py  Trece pruebas automatizadas
evidencia/        Resultados generados por la última ejecución
informe/          Informe técnico en LaTeX (XeLaTeX) y su PDF
desplegar.sh      Ejecución en macOS y Linux
desplegar.cmd     Ejecución en Windows
```

## Requisitos

Python 3.10 o posterior. El prototipo usa solo la biblioteca estándar.

## Ejecución

Desde la raíz del repositorio:

```bash
sh desplegar.sh          # macOS y Linux
desplegar.cmd            # Windows (Símbolo del sistema)
.\desplegar.cmd          # Windows (PowerShell)
```

El script ejecuta las pruebas, simula los once casos con y sin agente y actualiza `evidencia/`. Para reproducir un solo caso sin reemplazar la evidencia completa:

```bash
sh desplegar.sh --caso CP07 --salida evidencia-cp07
```

Se puede usar cualquier identificador de CP01 a CP11. Las tarifas son supuestos del laboratorio.

## Evidencia

- `evidencia/ejecucion.txt`: salida de las 13 pruebas y de los 11 casos.
- `evidencia/metricas.csv` y `evidencia/resumen.json`: indicadores por caso para el agente y para la capacidad fija.
- `evidencia/traza.jsonl`: un registro por minuto y modo con la telemetría, los candidatos con su utilidad y sus bloqueos, la acción aplicada, las alertas y la observación posterior.

Dos ejecuciones consecutivas producen archivos idénticos.

## Informe

`informe/informe.pdf` es la versión compilada. Para recompilarlo desde la carpeta `informe/`:

```bash
xelatex -halt-on-error informe.tex
xelatex -halt-on-error informe.tex
```

Si cambian las simulaciones, primero se ejecuta `desplegar.sh` y luego `python3 informe/generar_tabla.py` desde la raíz, que actualiza la Tabla 3 a partir de `evidencia/resumen.json`.

## Correspondencia con la rúbrica

| Criterio | Dónde verificarlo |
| --- | --- |
| PEAS y entorno (20 %) | Tabla 1 y formalización del entorno en el informe |
| Arquitectura y TikZ (20 %) | Figura 1, `informe/arquitectura.tex`, `finops/plantilla.py` y `finops/agente.py` |
| Utilidad, pesos y penalizaciones (25 %) | Ecuaciones 1–4, `finops/agente.py` y `finops/modelo.py` |
| Implementación en Python (25 %) | `finops/`, `tests/` y scripts de ejecución |
| Casos de prueba y métricas (10 %) | Tablas 2 y 3 y carpeta `evidencia/` |

## Resultados destacados

- **CP03:** ante un pico de tráfico, el agente agrega dos instancias y mantiene 100 % de disponibilidad, frente a 73,79 % con capacidad fija.
- **CP07:** el presupuesto bloquea las ampliaciones; el agente emite la alerta y la disponibilidad queda en 47,96 %, lo que muestra el compromiso entre servicio y costo.
- **CP10:** después de un aumento tarifario, el agente retira una instancia y deja el cierre proyectado en USD 398,60, bajo el límite de USD 400.
