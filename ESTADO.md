# Estado del proyecto — punto de retoma

> **Empieza por aquí.** Resume dónde está todo, qué sigue y qué ya está
> decidido, para que una sesión nueva no tenga que reconstruir el contexto.
>
> Última actualización: **10 de octubre de 2026**

## Qué es esto

Escultura de cuervo impresa en 3D (FDM, ~500 g de filamento), pintada a mano,
con dos LEDs direccionables en las cuencas de los ojos. Se controla por botón
físico, por página web desde el celular y por voz. Alimentación USB-C.

**Ya se vendieron 5 unidades a ~170.000 COP** en versión estática. La versión
con ojos inteligentes apunta a 320.000-380.000 COP, con ~14.500 COP de
electrónica por pieza.

## Dónde estamos hoy

### Material recibido ✅
- 5× ESP32-C3 SuperMini (USB-C integrado)
- 100× módulos WS2812B BTF-LIGHTING (PCB redondo negro, 5V, con R1 y C1)
- Cable de silicona 30AWG, 5 colores
- Multímetro Truper MUT-33
- Switches mecánicos MX (stock propio, de los clickers)

### Lo último que pasó
Se flasheó **WLED 16.0.1 (build "Plain")** en la primera placa desde
`install.wled.me`. La instalación terminó correctamente.

Al pulsar *Reset Device* desde la consola del instalador, el log mostró:

```
rst:0x15 (USB_UART_CHIP_RESET), boot:0x5 (DOWNLOAD(USB/UART0/1))
waiting for download
```

Es decir, la placa quedó en **modo descarga**, no arrancó WLED. La indicación
fue desconectar y reconectar el USB sin tocar BOOT, para forzar un arranque
limpio.

### ✅ WLED arranca (confirmado el 10/10/2026, sesión local)
- Firmware verificado leyendo el flash: bootloader y app con checksum y hash válidos.
- WLED responde por **Improv serial** en COM3: `WLED 16.0.1/2606300`, `esp32-c3`,
  nombre `wled-fcfa34`.
- **No aparece `WLED-AP` porque no hace falta:** el instalador web le pasó la
  WiFi de casa al terminar. WLED solo abre el AP si no tiene red configurada.
- En la red de casa: `192.168.40.26` (IP por DHCP, **provisional**), señal 100 %
  (RSSI −40 dBm, canal 8). `/json/info` responde.
- La configuración sigue de fábrica: 30 LEDs, 850 mA. Se cambia en el paso 4.

### ✅ Personalización aplicada a la placa 1
- Nombre `Cuervo 01`, mDNS **`cuervo-01.local`** (verificado: responde),
  red de configuración `Cuervo-01` en vez de `WLED-AP` (contraseña aún `wled1234`).
- Piel [`firmware/config/skin.css`](firmware/config/skin.css) subida: negro con
  reflejo violeta y acentos ámbar. WLED la carga sola en cualquier navegador.
- Copia de la configuración de fábrica guardada fuera del repo (contiene la WiFi).

### ✅ Interfaz propia Brumet (placa 1)
[`firmware/ui/index.htm`](firmware/ui/index.htm): un solo archivo de 32 KB, sin
librerías ni internet. Estilo app de Apple, logo BM (del repo `Cortador`),
**español por defecto con inglés en Ajustes**. WLED la sirve en `/` sin recompilar.

- Ojos que brillan con el color y el brillo reales, encendido, brillo,
  escenas (tocar = aplicar, mantener = borrar, «Guardar» = nueva),
  rueda de color, 12 efectos útiles con dos LEDs, temporizador de apagado.
- Sincronización en vivo por WebSocket: si alguien pulsa el botón físico,
  la página se actualiza sola.
- La interfaz clásica sigue en `/wled.htm` (Ajustes → Avanzado).
- Escenas de catálogo creadas: 1 Ámbar, 2 Vela, 3 Sangre, 4 Espectro.
  **Falta la 5 (Parpadeo)**, que es una secuencia y depende de cómo cicla el botón.
- Probado en tamaño de celular y de computador: aplicar escena, cambio de
  idioma y hoja de Ajustes, sin errores en la consola.
- **Escena fija detrás de los paneles:** render del modelo `forma preliminar.stl`
  completo (cabeza a base) con fondo transparente, sobre el fondo de plumas
  generado. Los paneles son translúcidos: al bajar se sigue viendo el cuervo.
  Ojos de este modelo: (−11.4, −64, 268) y (16.9, −64, 268) mm.
  Script: [`firmware/ui/render/hero.py`](firmware/ui/render/hero.py).
- `cuervo.png` es **WebP con extensión .png**: WLED sirve `.webp` como
  `text/plain` y `.png` como imagen; el navegador detecta el formato real.
- Marca: **logo oficial Brumet completo** (de `brumet-contabilidad/icons/brumet-blanco.svg`,
  "no hay isotipo ni variantes"), rojo `#e3262f` como único color, enlace a **brumet.co**.

> ⚠️ **iPhone: `cuervo-01.local` no abre, `http://192.168.40.26` sí** (Safari y Chrome).
> La placa anuncia bien su nombre (solo IPv4, verificado), pero desde el PC la
> primera resolución tardó 2,7 s y una vez falló. Sospecha: el router filtra o
> retrasa multicast por WiFi. **Resolver antes de vender** — el NFC depende de
> ese nombre. Mientras tanto: reservar la IP en el router (DHCP fijo).

> El log de arranque **no sale por serie** en el build de lanzamiento: para
> saber si WLED está vivo, preguntar por Improv o pedir `/json/info`.

### ✅ Primer módulo de ojos funcionando (7/11/2026)
Placa 3 (cuervo-03): dos WS2812B encadenados, ojo derecho primero. Ambos encienden
en ámbar al arrancar. Soldado sin multímetro, con revisión visual por foto.

⚠️ **WLED trae los datos en el pin 2 de fábrica** (pin de arranque, prohibido).
Cada placa necesita: `POST /json/cfg {"hw":{"led":{"maxpwr":250,"ins":[{...,"pin":[4],"len":2,"maxpwr":250}]}}}`
+ reinicio. Hecho en la placa 3; **pendiente en 1, 2 y 4**.

## Lo siguiente, en orden

### 1. ✅ Confirmar que WLED arranca
Hecho. Ver arriba.

### 2. ✅ Flash medido: 4 MB, integrado en el chip
Medido el 10/10/2026 con `esptool flash-id` (placa 1, COM3, MAC `84:fc:e6:fc:fa:34`):

```
ESP32-C3 (QFN32) rev v0.4 — Embedded Flash 4MB (XMC)
```

El flash está **dentro del chip**: no se puede ampliar. Consecuencia:
- **Estas 5 placas sirven para la Serie Cero con WLED de fábrica.**
- **La ruta Matter queda descartada en ellas.** Para la I+D de Matter hay que
  comprar ESP32-S3 de **16 MB**. Ver [`docs/06-wled-fork.md`](docs/06-wled-fork.md).

Partición grabada por el instalador (WLED estándar de 4 MB): `app0` y `app1`
de 1,5 MB (OTA), `spiffs` de 960 KB en `0x310000`.

### 3. Primer módulo de ojos
Soldar 2 WS2812B encadenados con cable de 30AWG y probarlos en la mesa, **antes**
de meterlos en ninguna cabeza impresa. Proceso en
[`docs/04-ensamblaje.md`](docs/04-ensamblaje.md).

### 4. Configurar WLED
```
LED count ............. 2
GPIO .................. 4
Maximum Current ....... 250 mA
Apply preset at boot .. 1
Botón 0 ............... GPIO 3
Botón 1 ............... GPIO 5
```

### 5. Presets de catálogo
Ver [`docs/05-produccion.md`](docs/05-produccion.md). Ámbar es `RGB 255,100,0`
con brillo ~50/255.

## Decisiones ya tomadas — no reabrir

| Decisión | Razón |
|---|---|
| LEDs alimentados desde **3V3**, no 5V | Nivel lógico: la C3 emite 3,3 V y a 5 V el umbral del WS2812B es 3,5 V |
| **Nunca** GPIO 2, 8 ni 9 | Pines de arranque; la placa queda en modo programación |
| **Dos** switches, no uno | El regulador de brillo continuo solo existe en botones de índice > 0 |
| Lente **ahumado neutro**, no ámbar | Un lente teñido contamina todos los colores y mata el cambio de color |
| Un LED **por ojo**, separado 3-5 mm del lente | Un LED central no alcanza ambos ojos; pegado al lente se ve un punto duro |
| Se envía **armado**, no por partes | Se vende "listo para usar"; un conector es punto de falla permanente |
| Refuerzo de **varilla metálica** en una pata | Es el punto de rotura en transporte |
| Acceso por **nombre mDNS**, nunca por IP | La IP la asigna DHCP y cambia; el nombre viaja con la pieza |
| **Un nombre por unidad** (`cuervo-01.local`) | Dos piezas en la misma casa chocarían |
| **Eliminar** el reset de fábrica del botón | 10 s de pulsación formatea y borra todos los presets |
| Serie Cero sale con **WLED de fábrica** | Matter es I+D en paralelo; no puede bloquear 5 entregas |
| Serie Cero = **4 cuervos** (cuervo-01 a 04) | Decisión del 7/11/2026 |
| **WiFi sleep activo** en todas | Se calienta claramente menos; +90 ms de respuesta, imperceptible |

## Preguntas abiertas

- [x] Tamaño de flash real de las placas compradas → **4 MB integrado**
- [ ] ¿Compila WLED como componente de ESP-IDF? ← **el filtro de viabilidad de Matter**
- [ ] ¿Existe build de Tasmota con Matter para ESP32-C3, y expone color RGB?
- [ ] Costos vigentes de membresía CSA (consultar en csa-iot.org)
- [ ] ¿Puede una macro de WLED expresar "siguiente preset"?

## Qué puede hacer una sesión local que esta no pudo

Esta sesión corrió en un contenedor en la nube: **sin bus USB, sin puerto serie,
sin acceso a la red de casa**. Todo el trabajo con hardware fue a ciegas,
interpretando lo que se pegaba en el chat.

Una sesión local sí puede:

- Ejecutar `esptool` directamente contra la placa
- Leer el puerto serie y ver el arranque en vivo
- Diagnosticar errores de WLED con el log delante
- Compilar WLED (`pio run -e esp32c3dev`) y medir el binario real
- Entrar a `cuervo.local` y a la interfaz de WLED

> **Nota sobre la compilación:** se intentó compilar WLED en el contenedor
> remoto. El toolchain de Espressif se instaló completo, pero el registro de
> paquetes de PlatformIO está bloqueado por la política de red de ese entorno.
> En una máquina normal el build corre sin intervención.

## Mapa de la documentación

| Documento | Contenido |
|---|---|
| [`docs/01-hardware.md`](docs/01-hardware.md) | BOM, mapa de pines, conexionado, mecánica, herramientas |
| [`docs/02-arquitectura-firmware.md`](docs/02-arquitectura-firmware.md) | esp-matter vs Tasmota vs fork de WLED |
| [`docs/03-matter.md`](docs/03-matter.md) | Certificación, flash, emparejamiento por QR |
| [`docs/04-ensamblaje.md`](docs/04-ensamblaje.md) | Proceso por unidad y tabla de fallas |
| [`docs/05-produccion.md`](docs/05-produccion.md) | Presets, clonado, empaque, envío, precios |
| [`docs/06-wled-fork.md`](docs/06-wled-fork.md) | Licencia EUPL, restricción de flash, viabilidad |
| [`docs/07-botones-y-red.md`](docs/07-botones-y-red.md) | Botones verificados en el código, acceso a la web |
| [`firmware/patches/0001-...`](firmware/patches/0001-eliminar-reset-de-fabrica.md) | Quitar el reset de fábrica |

## Paralelo: contenido

Se está grabando el proceso para YouTube, TikTok, Reels y Shorts. Ya está
grabado el desempaque. **Pendientes y no repetibles: la primera soldadura y el
primer encendido de los ojos.** Montar la cámara antes de hacerlos.

Ajustes acordados: 4K horizontal con aire para recortar a vertical, exposición y
enfoque bloqueados, balance de blancos manual (app Blackmagic Camera), luz
lateral rasante para las plumas y casi oscuridad para los ojos encendidos.
