# Firmware

> **Estado: no iniciado.** La base sobre la que se construye está pendiente de
> decisión. Ver [`../docs/02-arquitectura-firmware.md`](../docs/02-arquitectura-firmware.md).

## Estructura prevista

```
firmware/
├── config/          Respaldos de configuración para clonar unidades
│                    (presets.json, cfg.json, style.css)
├── main/            Código fuente, si el camino es esp-matter
└── berry/           Scripts Berry, si el camino es Tasmota
```

## Antes de escribir una sola línea

Ejecutar el spike descrito en `docs/02-arquitectura-firmware.md`:

1. ¿Existe build de Tasmota con Matter para ESP32-C3?
2. ¿Empareja con Google Home?
3. ¿El dispositivo Matter expone **color RGB**, o solo encendido y brillo?
4. ¿Funcionan 2 píxeles WS2812B en GPIO4 y el botón en GPIO3?
5. ¿Se puede leer el estado de red desde Berry para los colores de estado?

Y en paralelo, con las placas en mano:

```bash
esptool.py --port /dev/ttyACM0 flash_id
```

Si el flash es de 4 MB, decidir sobre OTA **antes** del próximo pedido de placas.

## Si el camino es esp-matter

```bash
# ESP-IDF
git clone -b v5.2 --recursive https://github.com/espressif/esp-idf.git
cd esp-idf && ./install.sh esp32c3 && . ./export.sh

# esp-matter
git clone --recursive https://github.com/espressif/esp-matter.git
cd esp-matter && ./install.sh && . ./export.sh
```

Punto de partida: `esp-matter/examples/light`. Implementa un *Extended Color
Light*, que es exactamente la clase de dispositivo que corresponde a esta pieza.

Trabajo propio sobre esa base:
- Motor de efectos (Candle, Breathe, parpadeo periódico)
- Sistema de presets con persistencia en NVS
- Manejo del botón: toque corto / doble / mantener
- Colores de estado según la fase de comisionamiento
- Interfaz web de configuración, si se conserva

> **Verificar las versiones vigentes de ESP-IDF y esp-matter en la
> documentación oficial antes de clonar.** Las ramas cambian y la compatibilidad
> entre ambos SDK es estricta.

## Mapa de pines

```
GPIO 4  → WS2812B DIN
GPIO 3  → botón a GND
3V3     → alimentación LEDs (no 5V — ver docs/01-hardware.md)
```

**Prohibidos:** GPIO 2, 8, 9 (pines de arranque).
