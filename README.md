# Agente de optimización y autoescalado cloud (FinOps)

Proyecto 2 de la guía *Taller de ingeniería de agentes inteligentes*. El prototipo ejecuta un laboratorio FinOps en el PC y genera evidencia reproducible. Cada minuto simulado, compara acciones mediante una función de utilidad y aplica una configuración al clúster, la base de datos y la caché del simulador.

## Ejecutar

1. Extrae el ZIP completo. Se requiere **Python 3.10 o posterior**. El laboratorio usa la biblioteca estándar. Si el PC aún no tiene Python, puedes descargarlo desde [python.org](https://www.python.org/downloads/).
2. Abre una terminal en la carpeta extraída. Ejecuta `desplegar.cmd` en Windows con Símbolo del sistema, `.\desplegar.cmd` en PowerShell o `sh desplegar.sh` en macOS/Linux.
3. El script ejecuta las pruebas y las once simulaciones, compara los resultados con capacidad fija y actualiza `evidencia/`.

Para reproducir solo el conflicto presupuestario sin reemplazar la evidencia completa, usa `desplegar.cmd --caso CP07 --salida evidencia-cp07` en Símbolo del sistema o `sh desplegar.sh --caso CP07 --salida evidencia-cp07` en macOS/Linux. Puedes seleccionar cualquier identificador de CP01 a CP11. El simulador corre localmente con tarifas sintéticas.

## Entregar

1. Completa los cinco datos de portada en `informe/datos.tex`. Puedes abrir la carpeta `informe/` como proyecto de LaTeX y elegir XeLaTeX. Si compilas en tu PC con TeX Live o MiKTeX, desde esa carpeta corre `xelatex -halt-on-error informe.tex` dos veces.
2. Entrega el PDF compilado, las fuentes LaTeX y el repositorio. El ZIP incluye la estructura completa lista para usar como repositorio. Si tu aula exige un enlace, sube la carpeta a tu repositorio de clase y comparte el enlace desde allí.
3. Si cambias las simulaciones, corre primero el script y luego `python informe/generar_tabla.py` desde la raíz. Actualiza el análisis del informe si cambiaron los resultados y recompila.

## Archivos y criterios de la rúbrica

| Criterio de la guía | Dónde verificarlo |
| --- | --- |
| PEAS y entorno (20 %) | Tabla 1 y formalización en el informe |
| Arquitectura y TikZ (20 %) | Figura 1, `informe/arquitectura.tex` y ciclo en `finops/agente.py` |
| Utilidad, pesos y penalizaciones (25 %) | Ecuaciones 1–4 y `finops/agente.py`, `finops/modelo.py` |
| Implementación en Python (25 %) | `finops/`, `tests/` y scripts de ejecución |
| Casos de prueba y métricas (10 %) | Tablas 2 y 3 y carpeta `evidencia/` |

- `evidencia/ejecucion.txt` conserva la salida de las 13 pruebas y 11 casos.
- `evidencia/metricas.csv` y `evidencia/resumen.json` comparan resultados por caso.
- `evidencia/traza.jsonl` guarda un objeto por minuto y modo. Incluye métricas previas y posteriores, candidatos y sus puntajes, bloqueos, configuración aplicada y alertas.
- `informe/informe.pdf` es la versión compilada con campos de portada editables desde LaTeX.
- `Prompt_Claude.txt` contiene un prompt opcional para revisar la entrega en Claude Web.

## Cómo explicar la demostración

En CP03, el agente agrega dos instancias y alcanza 100 % de disponibilidad simulada, frente a 73,79 % con capacidad fija. En CP07, el presupuesto bloquea las ampliaciones y se emite una alerta, con 47,96 % de disponibilidad. En CP10, después de un aumento tarifario, el agente reduce una instancia y devuelve el cierre proyectado bajo el límite de USD 400. Esta comparación muestra por qué el agente necesita valorar conjuntamente la calidad del servicio y el costo.
