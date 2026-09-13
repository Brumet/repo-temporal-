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

## Decisión pendiente más importante

Adoptar Matter significa **renunciar a WLED**, que hoy resuelve gratis la
interfaz web, los efectos, los presets y el manejo del botón. Antes de escribir
firmware propio hay que decidir sobre qué base se construye.

Ver [`docs/02-arquitectura-firmware.md`](docs/02-arquitectura-firmware.md).
