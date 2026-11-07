# Firmware

> **Estado (7/11/2026): en uso.** WLED 16.0.1 oficial para ESP32-C3 + dos módulos
> (usermods). Instalado y probado en la placa 3. La ruta Matter sigue siendo I+D
> aparte: ver [`../docs/02-arquitectura-firmware.md`](../docs/02-arquitectura-firmware.md).

## Qué hay aquí

```
firmware/
├── usermods/Cuervo_Estado/   Módulo propio: los ojos avisan el paso de la configuración
├── platformio_override.ini   Entorno "cuervo": WLED esp32c3dev + los módulos
├── compilar.sh               Compila sobre una copia limpia de WLED v16.0.1
├── binarios/                 Firmware compilado, listo para instalar
├── ui/                       Interfaz web Brumet (index.htm, render, fondo, ícono)
├── config/skin.css           Colores de marca para la interfaz clásica de WLED
├── pruebas/                  Prueba total, demo de avisos y secuencia para grabar
└── patches/                  Cambios previstos al núcleo de WLED (aún no aplicados)
```

## Los avisos de los ojos (Cuervo_Estado)

| Momento | Ojos |
|---|---|
| Sin WiFi configurada (recién sacado de la caja) | Azul respirando (ciclo de 3 s) |
| Un celular se conectó a la red `Cuervo-0N` | Azul fijo |
| Intentando conectarse a la WiFi de la casa | Destellos blancos |
| No se pudo conectar (clave o red equivocada) | 3 parpadeos rojos y vuelve a azul |
| ¡Conectado! | 3 parpadeos verdes y sigue la escena normal |
| Uso normal, se cae el internet de la casa | Nada |

- Guarda `"um":{"CuervoEstado":{"listo":true}}` en `cfg.json` la primera vez que se conecta.
- Si la WiFi se borra (antes de empacar), vuelve solo a modo configuración.
- En uso normal solo avisa si alguien se conecta a la red del cuervo para reconfigurarlo.
- Publica su estado en `/json/info` → `u.Ojos`.

## Temperatura del chip (Internal_Temperature_v2, oficial de WLED)

Se activa una vez por placa: `POST /json/cfg {"um":{"Internal Temperature":{"Enabled":true}}}`.
Publica los grados en `/json/info` → `u["Internal Temperature"]`. Placa 3 en uso
normal con WiFi sleep: **45,5 °C** (el chip aguanta 105 °C).

## Compilar

```bash
sh firmware/compilar.sh      # clona WLED v16.0.1 en ../wled-cuervo si no existe
```

Requiere Python y `pip install platformio`. La primera vez descarga el toolchain
(unos minutos). Resultado: `wled-cuervo/.pio/build/cuervo/firmware.bin`
(1,27 MB, 81 % de la partición de 1,5 MB).

## Instalar

**Por WiFi (OTA)**, conserva interfaz, escenas y configuración:
```bash
curl -F "update=@firmware/binarios/cuervo-wled16.0.1-estado1.bin" http://192.168.40.35/update
```

**Por USB**, en una placa nueva: clonar la imagen completa (ver
[`../docs/05-produccion.md`](../docs/05-produccion.md)) y luego actualizar por OTA.

## Licencia

WLED se distribuye bajo **EUPL v1.2**. Vender piezas con este firmware es
distribución: el código de los módulos propios y la configuración de compilación
se publican aquí, junto con el aviso en el instructivo de la caja. El código de
WLED es el de la etiqueta `v16.0.1` de https://github.com/wled/WLED, sin cambios.

## Mapa de pines

```
GPIO 4  → WS2812B DIN (primer LED = ojo derecho)
GPIO 3  → botón 0 a GND (encender/apagar)          — pendiente de soldar
GPIO 5  → botón 1 a GND (brillo)                   — pendiente de soldar
3V3     → alimentación LEDs (no 5V — ver docs/01-hardware.md)
```

**Prohibidos:** GPIO 2, 8, 9 (pines de arranque). WLED trae de fábrica el pin 2:
cambiarlo a 4 en cada placa.
