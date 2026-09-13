# Arquitectura de firmware — la decisión

## El problema

Adoptar Matter significa **renunciar a WLED**. No es un módulo que se le agrega:
son dos firmwares distintos y solo uno puede correr en el chip.

Lo que WLED da hoy, gratis y configurado en 15 minutos:

- Interfaz web completa, personalizable con CSS propio
- 100+ efectos, entre ellos `Candle` (parpadeo orgánico) y `Breathe`
- Presets y playlists → el parpadeo de ojos cada 8 s
- Segmentos → cada ojo con color y velocidad independientes
- Manejo de botón con 3 gestos (corto / doble / mantener)
- Respaldo y restauración de configuración → clonar unidades en 30 segundos
- Actualización OTA
- Alexa nativo por emulación Hue

Un proyecto esp-matter desde cero **no trae nada de eso**. Empieza con un LED que
enciende y apaga. Todo lo demás hay que escribirlo.

Esa es la magnitud real de la decisión. No es "agregar Google", es reconstruir el
producto sobre otra base.

> **Actualizado:** el análisis del código de WLED cambió el panorama. WLED es
> software libre y se puede bifurcar, lo que abre una cuarta opción que no estaba
> contemplada aquí. Ver [`06-wled-fork.md`](06-wled-fork.md) antes de decidir.

## Las opciones

### A · esp-matter puro

SDK oficial de Espressif sobre ESP-IDF.

| | |
|---|---|
| ✅ | Control total, Matter nativo y certificable, sin dependencias ajenas |
| ✅ | Los colores de estado en los ojos (configuración / conectado / error) salen naturales |
| ❌ | Hay que escribir: motor de efectos, sistema de presets, interfaz web, gestión de botón, persistencia, OTA |
| ❌ | Requiere C++ y toolchain ESP-IDF |
| ⏱ | Semanas a meses |

### B · Tasmota con soporte Matter

Tasmota (ESP32) incorporó rol de dispositivo Matter. Ya trae interfaz web,
control de WS2812, manejo de botones, OTA y scripting Berry para lógica propia.

| | |
|---|---|
| ✅ | Entre el 70% y el 90% del trabajo ya está hecho |
| ✅ | Berry permite efectos y colores de estado sin compilar C++ |
| ✅ | Se instala y configura, no se programa desde cero |
| ⚠️ | **POR VERIFICAR:** si el rol Matter expone color RGB completo o solo encendido/brillo |
| ⚠️ | **POR VERIFICAR:** soporte Matter en el build para ESP32-**C3** específicamente |
| ❌ | Interfaz web con estética de ingeniería, menos personalizable que WLED |
| ⏱ | Días |

### D · Fork de WLED con Matter integrado

Bifurcar WLED y añadirle Matter. Conserva todo lo que WLED ya resuelve.

| | |
|---|---|
| ✅ | No se pierde nada: efectos, presets, interfaz, botón, OTA |
| ✅ | ESP32-C3 ya está soportado; el sistema de usermods es maduro |
| ❌ | WLED usa framework Arduino y esp-matter usa ESP-IDF puro: hay que compilar Arduino como componente de IDF |
| ❌ | **Requiere 8 MB de flash como mínimo** — en 4 MB no cabe |
| ❌ | Obligación de publicar el fork: licencia EUPL v1.2, copyleft |
| ⏱ | Semanas, con riesgo real de que el paso de integración no salga |

Análisis completo con datos en [`06-wled-fork.md`](06-wled-fork.md).

### C · WLED + puente externo

Mantener WLED y exponerlo a Google mediante Home Assistant o similar.

| | |
|---|---|
| ✅ | Cero trabajo de firmware |
| ❌ | Traslada al cliente el costo de montar un servidor. Inaceptable en producto de consumo |

**Descartada.**

## Recomendación

Ver la sección final de [`06-wled-fork.md`](06-wled-fork.md): enviar la Serie
Cero con WLED de fábrica y trabajar Matter en paralelo, sin bloquear el envío.

Si se descarta el fork, el siguiente candidato es Tasmota:

### Spike de Tasmota

Un día de trabajo, en este orden:

1. Confirmar que existe build de Tasmota con Matter para ESP32-C3
2. Instalarlo en una placa y emparejarlo con Google Home
3. Verificar si el dispositivo Matter expone **color RGB**, no solo on/off y brillo
4. Probar 2 píxeles WS2812B en GPIO4 y el botón en GPIO3
5. Escribir un script Berry mínimo que cambie el color según el estado de WiFi

**Si los 5 pasos pasan → Tasmota.** Se gana Matter conservando casi todo lo que
daba WLED, por una fracción del esfuerzo.

**Si falla el paso 3** (Matter solo expone on/off y brillo, sin color) → la
pregunta se vuelve: ¿el cambio de color por voz es requisito, o basta con voz
para encender/apagar y color desde la app? Si basta, Tasmota sigue ganando.

**Si falla el paso 1 o 2** → esp-matter, asumiendo el proyecto completo.

## Riesgo a nombrar antes de empezar

La ESP32-C3 SuperMini trae típicamente **4 MB de flash**. Una aplicación Matter
ocupa del orden de 1,5-1,8 MB. Con dos particiones de aplicación para OTA
(necesarias para actualizar el firmware de forma remota) el espacio no alcanza
con holgura.

**Consecuencia posible:** Matter sí, OTA no. En un producto que se vende y se
envía, no poder actualizar el firmware remotamente es una limitación seria.

**Verificar primero que nada:**
```bash
esptool.py --port <PUERTO> flash_id
```

Si el resultado es 4 MB, evaluar módulos ESP32-C3 con 8 MB antes de comprar las
siguientes 20 placas. Ver [`03-matter.md`](03-matter.md).

## Camino sugerido

No son excluyentes en el tiempo:

```
Ahora        → Armar y probar el hardware con WLED.
               Valida soldadura, difusión de ojos, canal de cables,
               botón y mecánica. Nada de eso depende del firmware.

En paralelo  → Spike de Tasmota (1 día) y verificación de flash.

Después      → Migrar el firmware a la opción ganadora.
               El hardware no cambia.
```

El hardware es idéntico en los tres caminos. Probarlo con WLED primero no es
trabajo perdido: es aislar las variables mecánicas antes de meter una variable
de software mucho más grande.
