# Producción y entrega

## Clonar la configuración

No repetir la configuración manual en cada unidad. Configurar **una** placa
perfecta, exportar, y restaurar en las demás.

Archivos a versionar en `firmware/config/`:

| Archivo | Contenido |
|---|---|
| `presets.json` | Presets y playlists |
| `cfg.json` | GPIO, cantidad de LEDs, botón, nombres |
| `style.css` | Interfaz web con la marca propia |

Placa nueva: instalar firmware → subir los tres archivos → **30 segundos**.

> ⚠️ **Antes de empacar cada unidad, borrar el SSID y la contraseña de WiFi.**
> De lo contrario se está enviando la clave de la casa dentro de la escultura.
> Además, al borrarlas la pieza arranca en modo de configuración, que es
> justamente lo que se necesita.

## Presets de catálogo

| # | Nombre | Definición |
|---|---|---|
| 1 | Ámbar | RGB `255, 100, 0` · brillo ~50/255 |
| 2 | Vela | Efecto Candle, parpadeo orgánico |
| 3 | Sangre | Rojo profundo |
| 4 | Espectro | Azul frío |
| 5 | Apagado | Brillo 0 |
| 6 | Parpadeo | Playlist: preset 1 durante 8,0 s → preset 5 durante 0,2 s → repetir |

**El brillo bajo no es un error.** 50 de 255 parece poquísimo en la mesa, pero
dentro de una cabeza oscura es el brillo de un ojo vivo. A brillo alto parecen
faros de auto.

**Preset al arrancar = 1.** Garantiza que la escultura siempre encienda en ámbar,
aunque se vaya la luz.

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
