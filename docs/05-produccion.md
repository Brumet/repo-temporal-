# Producción y entrega

## Clonar la configuración

No repetir la configuración manual en cada unidad. Configurar **una** placa
perfecta, exportar, y restaurar en las demás.

Archivos a versionar en `firmware/config/`:

| Archivo | Contenido |
|---|---|
| `presets.json` | Presets y playlists |
| `cfg.json` | GPIO, cantidad de LEDs, botón, nombres |
| `skin.css` | Colores de marca para la interfaz WLED clásica (WLED lo carga solo; el nombre tiene que ser exactamente este) |

Además, la interfaz propia (`firmware/ui/`):

| Archivo en la placa | Origen | Contenido |
|---|---|---|
| `index.htm` | `firmware/ui/index.htm` | Interfaz Brumet. WLED la sirve en `/` en lugar de la suya |
| `wled.htm` | La página `/` de WLED, guardada **antes** de subir `index.htm` | Interfaz clásica, enlazada desde Ajustes → Avanzado |
| `cuervo.png` | `firmware/ui/cuervo.png` | Render del modelo, transparente (WebP con nombre .png) |
| `fondo.jpg` | `firmware/ui/fondo.jpg` | Fondo de plumas |
| `luz.png` | `firmware/ui/luz.png` | Luz de los ojos; la página la tiñe con el color real |
| `icon.png` | `firmware/ui/icon.png` | Ícono para "Agregar a pantalla de inicio" |

Borrar un archivo: `curl "http://cuervo-01.local/edit?func=delete&path=/archivo"`

Subir siempre sin barra inicial en el nombre:
`curl -F "data=@index.htm;filename=index.htm" http://cuervo-01.local/upload`

Placa nueva: instalar firmware → guardar `wled.htm` → subir los archivos → **1 minuto**.

> ⚠️ **Antes de empacar cada unidad, borrar el SSID y la contraseña de WiFi.**
> De lo contrario se está enviando la clave de la casa dentro de la escultura.
> Además, al borrarlas la pieza arranca en modo de configuración, que es
> justamente lo que se necesita.

## Clonado por USB (probado el 7/11/2026)

Más rápido que subir archivos: copiar la memoria completa de una placa terminada.

```bash
# 1. Leer la placa modelo (una sola vez). Contiene la WiFi: NO versionar.
python -m esptool --port COM3 -b 921600 read-flash 0 ALL cuervo01_full.bin
# 2. Grabar cada placa nueva (verifica el hash al final)
python -m esptool --port COM7 -b 921600 write-flash 0 cuervo01_full.bin
# 3. Arrancarla. El reinicio normal por RTS la deja en modo descarga;
#    el de watchdog sí arranca WLED (el error de pySerial es normal: el puerto se cae al reiniciar)
python -m esptool --port COM7 --before no-reset --after watchdog-reset read-mac
```

4. Preguntarle la IP por Improv y renombrarla: `POST /json/cfg`
   `{"id":{"mdns":"cuervo-0N","name":"Cuervo 0N"},"ap":{"ssid":"Cuervo-0N"}}`
   y reiniciar con `{"rb":true}`.

| Placa | MAC | Nombre |
|---|---|---|
| 1 | `84:fc:e6:fc:fa:34` | cuervo-01 |
| 2 | `cc:8d:a2:c0:5a:38` | cuervo-02 |
| 3 | `cc:8d:a2:c1:66:24` | cuervo-03 |
| 4 | `f0:f5:bd:a2:a9:a8` | cuervo-04 |

> La imagen de la placa 1 tiene WiFi sleep **apagado** y los LEDs en el **pin 2 con 30 LEDs**
> (valores de fábrica de WLED). Al clonar, en el paso 4: `"wifi":{"sleep":true}` y
> `"hw":{"led":{"maxpwr":250,"ins":[{"pin":[4],"len":2,"maxpwr":250,...}]}}`.

## Presets de catálogo

| # | Nombre | Definición |
|---|---|---|
| 1 | Ámbar | RGB `255, 100, 0` · brillo ~50/255 |
| 2 | Vela | Efecto Candle, parpadeo orgánico |
| 3 | Sangre | Rojo profundo |
| 4 | Espectro | Azul frío |
| 5 | Parpadeo | Playlist: ámbar 8,0 s → oscuro 0,2 s → repetir |

**Ningún preset apagado dentro del ciclo.** El doble toque del botón recorre los
presets en orden; si uno de ellos apaga la pieza, el cliente cree que se dañó a
mitad del recorrido. El apagado lo maneja el toque corto.

Esa secuencia de cinco estados es el producto completo para quien nunca abra el
celular — se cura con el mismo cuidado que la pintura.

**El brillo bajo no es un error.** 50 de 255 parece poquísimo en la mesa, pero
dentro de una cabeza oscura es el brillo de un ojo vivo. A brillo alto parecen
faros de auto.

**Preset al arrancar = 1.** Garantiza que la escultura siempre encienda en ámbar,
aunque se vaya la luz.

## Los tres niveles de control

| Nivel | Requiere | Alcance |
|---|---|---|
| **Botón** | nada | encender, apagar, cambiar preset, brillo |
| **Celular** | WiFi de casa, 2 min una vez | color completo, efectos, brillo fino |
| **Voz** | Alexa hoy; Matter después | encender, apagar, color, brillo |

La mayoría de los compradores se queda en el primer nivel, y el producto tiene
que estar completo ahí. No hay app que instalar en ningún nivel: la interfaz de
WLED es una página web.

## Empaque

En orden de efectividad real:

1. **Caja dentro de caja**, con 5 cm de relleno entre ambas. Es la medida más
   efectiva y la que casi nadie aplica
2. **La espuma sostiene el cuerpo, no las patas.** Dentro de la caja las patas
   deben cargar **cero peso**. Si la pieza va parada sobre sus patas, se parte
3. Pico y cola protegidos por separado — son los salientes que reciben los golpes
4. Diseñar para una caída de un metro. Las etiquetas de FRÁGIL no hacen nada

## Contenido de la caja

- [ ] Escultura armada y probada
- [ ] Cable USB-C
- [ ] Tarjeta con número de serie y QR de emparejamiento
- [ ] Instrucciones en una cara: enchufar, emparejar, usar el botón
- [ ] Nota de cuidado: limpieza en seco, sin alcohol sobre la pintura

## Envío: armado, no por partes

Se envía **armado**. Razones:

1. Se vende "listo para usar". Cada paso de ensamblaje que se le pasa al cliente
   es una oportunidad de rotura, de mala conexión, o de que sienta que compró un
   kit por 320.000
2. Un conector es un punto de falla permanente. Un contacto intermitente aparece
   como "los ojos titilan raro" tres semanas después, y es irreproducible desde
   el taller
3. El volumen de la caja casi no cambia separando las piezas

La fragilidad se resuelve con **varilla de refuerzo y empaque**, no desarmando.

Si existe junta desmontable, se envía igual armada y probada. La junta sirve para
el servicio posventa: pedirle al cliente que devuelva solo la base con la
electrónica, para que la pieza pintada no vuelva a viajar.

## Trazabilidad

Registrar por unidad:

```
Serie:            01/05
Nombre mDNS:      cuervo-01.local
Nombre:           El Cuervo Guardián
Fecha de armado:
Versión firmware:
Cliente:
Incidencias:
```

Con 5 unidades parece innecesario. Con 30 y una falla de lote, es la diferencia
entre saber a quién escribirle y no saberlo.

## Estructura de precios

| Versión | Precio sugerido COP |
|---|---:|
| Estática, sin luz | 170.000 - 200.000 |
| Ojos ámbar fijos | 240.000 |
| **Smart: app + voz + colores** | **320.000 - 380.000** |

Con menos de 15.000 de componentes electrónicos.

El video de alguien diciendo *"Ok Google, enciende el cuervo"* y viendo los ojos
prenderse es el mejor contenido de venta del proyecto. Eso se comparte solo.
