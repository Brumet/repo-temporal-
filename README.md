# Cuervo Guardián — Escultura Matter

Escultura impresa en 3D con ojos LED direccionables, controlables por app,
botón físico y asistentes de voz mediante **Matter** (Google Home, Alexa,
Apple Home y SmartThings de forma nativa, sin nube propietaria).

## Estado del proyecto

| Área | Estado |
|---|---|
| Diseño y venta del modelo estático | ✅ 5 unidades vendidas |
| Selección de componentes | ✅ Comprados, llegada 21-22 sep |
| División del modelo para cableado | 🔨 En curso |
| Decisión de arquitectura de firmware | ⏳ Pendiente de spike |
| Firmware Matter | ⏳ No iniciado |
| Proceso de producción | 📝 Documentado |

## Documentación

| Documento | Contenido |
|---|---|
| [`docs/01-hardware.md`](docs/01-hardware.md) | Lista de materiales, mapa de pines, conexionado |
| [`docs/02-arquitectura-firmware.md`](docs/02-arquitectura-firmware.md) | La decisión: esp-matter vs Tasmota vs WLED |
| [`docs/03-matter.md`](docs/03-matter.md) | Matter en detalle: certificación, flash, emparejamiento |
| [`docs/04-ensamblaje.md`](docs/04-ensamblaje.md) | Proceso de armado de una unidad |
| [`docs/05-produccion.md`](docs/05-produccion.md) | Clonado, empaque, experiencia del cliente |
| [`docs/06-wled-fork.md`](docs/06-wled-fork.md) | Análisis del código de WLED: licencia, flash, viabilidad |

## Decisión pendiente más importante

WLED es software libre (EUPL v1.2) y **se puede bifurcar en lugar de recrear**.
El análisis del código arroja tres restricciones duras:

1. La licencia obliga a **publicar el fork** — se puede vender, no se puede cerrar
2. WLED usa framework Arduino; esp-matter usa ESP-IDF puro. Unirlos es el trabajo real
3. **WLED + Matter no cabe en 4 MB de flash.** Se necesitan 8 MB mínimo

Ver [`docs/06-wled-fork.md`](docs/06-wled-fork.md) y
[`docs/02-arquitectura-firmware.md`](docs/02-arquitectura-firmware.md).
