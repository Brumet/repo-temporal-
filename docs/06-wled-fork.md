# Análisis de WLED como base

> Análisis realizado sobre `github.com/wled/WLED` commit `18ab096` (2026-09-12).
> Verificar de nuevo si pasa tiempo antes de decidir.

## Conclusión corta

**No hay que recrear WLED — hay que bifurcarlo (fork).** Es código abierto.

Pero el análisis arroja dos hallazgos que cambian el panorama, y uno de ellos es
una obligación legal que hay que entender antes de vender la primera unidad.

## Hallazgo 1 · La licencia es EUPL v1.2, no MIT

```
Copyright (c) 2016-present Christian Schwinne and individual WLED contributors
Licensed under the EUPL v. 1.2 or later
```

La EUPL es una licencia **copyleft fuerte**, de la familia de la GPL. No es
permisiva como MIT o Apache.

### Qué permite
- ✅ Uso comercial. Se pueden vender productos con el firmware dentro
- ✅ Modificar todo lo que se quiera
- ✅ Cobrar por el producto

### Qué obliga
Vender una escultura con el firmware adentro **es distribución**. Eso activa el
copyleft:

- 📋 Hay que publicar el código fuente modificado bajo EUPL (o una licencia
  compatible de su anexo)
- 📋 Hay que conservar los avisos de copyright y licencia originales
- 📋 El comprador tiene derecho a recibir el código

**Esto incluye la personalización de la interfaz.** Un `style.css` propio y una
pantalla con la marca son obra derivada.

### ¿Es un problema?

Comercialmente, casi seguro que no: el negocio es la escultura impresa, pintada a
mano y numerada, no el firmware. Nadie va a replicar el producto por tener el
código.

Y se puede convertir en argumento de venta: *firmware abierto, sin nube, sin
cuenta, sin suscripción — la pieza sigue siendo tuya para siempre.*

Lo que **no** se puede es quedarse callado. Hay que:
1. Publicar el fork en GitHub
2. Mantener los avisos de copyright de WLED
3. Mencionar el origen y enlazar al código en la tarjeta de la caja

> ⚠️ **Verificar el texto completo de la EUPL v1.2 antes de distribuir.** Este
> resumen es orientativo, no asesoría legal. El texto oficial está en `LICENSE`
> del repositorio de WLED y en la web de la Comisión Europea.

## Hallazgo 2 · Los sistemas de compilación no coinciden

| | WLED | esp-matter |
|---|---|---|
| Framework | **Arduino** (`framework = arduino`) | **ESP-IDF puro** |
| Build | PlatformIO, 43 entornos | CMake / idf.py |
| Base | platform-espressif32 sobre IDF 4.x y 5.x | ESP-IDF 5.x |

Unir ambos exige compilar **Arduino como componente de ESP-IDF** y encajar ahí
el build de PlatformIO de WLED, fuertemente personalizado.

Es posible. No es trivial. Es el corazón real del proyecto — el trabajo no está
en WLED ni en Matter por separado, sino en hacerlos convivir.

## Hallazgo 3 · WLED no tiene nada de Matter

Búsqueda de `esp_matter`, `CHIP_DEVICE`, `chip::` y `connectedhomeip` en todo el
código: **cero resultados**.

No hay soporte, ni parcial, ni experimental, ni en usermods. Sería trabajo
pionero, sin referencia previa dentro del proyecto.

> Vale la pena buscar en los issues y forks de WLED por si existe un intento
> comunitario que no esté en la rama principal.

## Hallazgo 4 · El flash de 4 MB queda descartado, con números

Partición que WLED usa hoy en 4 MB (`tools/WLED_ESP32_4MB_1MB_FS.csv`):

```
app0    0x180000  = 1,5 MB
app1    0x180000  = 1,5 MB   (segunda copia, para OTA)
spiffs  0x0F0000  = 960 KB
                    ─────────
                    ~4 MB, lleno
```

WLED solo ya consume los 4 MB completos. Una aplicación Matter añade del orden de
1,5 MB más, lo que llevaría cada partición a ~3 MB:

```
3 MB × 2 particiones + spiffs  ≈  6,5 MB mínimo
```

**Conclusión: WLED + Matter no cabe en 4 MB.** Ni con OTA ni, con mucha
estrechez, sin él.

**Se necesitan módulos de 8 MB, y 16 MB da margen cómodo.** WLED ya trae tablas
de particiones para ambos (`WLED_ESP32_8MB.csv`, `WLED_ESP32_16MB.csv`).

Las 5 placas compradas probablemente son de 4 MB. **Confirmarlo apenas lleguen**
y no pedir las siguientes 20 hasta tener esto resuelto.

## Hallazgo 5 · Lo bueno

- ✅ **ESP32-C3 ya está soportado**: existen los entornos `esp32c3dev` y
  `esp32c3dev_qio`. No hay que portar nada
- ✅ **Sistema de usermods maduro**: 75 usermods en el repositorio. Es el
  mecanismo previsto para extender WLED sin tocar el núcleo
- ✅ **Tablas de particiones para 8 y 16 MB ya incluidas**

## Escala: por qué "recrearlo" no es una opción

```
Núcleo (wled00):   101 archivos, ~59.000 líneas de C++
Usermods:          75
Entornos de build: 43
```

Casi diez años de trabajo de decenas de colaboradores. Reescribir eso para
agregar Matter sería tirar el activo más valioso que tiene el proyecto.

**Fork, no reescritura.** Siempre.

## Ruta técnica

```
1. Fork de WLED, con los avisos de licencia intactos
2. Confirmar el flash de las placas (esptool.py flash_id)
3. Conseguir un módulo ESP32-C3 de 8 o 16 MB para desarrollar
4. Spike duro: compilar WLED con Arduino-como-componente-de-ESP-IDF
   ← aquí se decide si el proyecto es viable
5. Integrar esp-matter y exponer un Extended Color Light
6. Puentear el estado Matter con el motor de color de WLED
7. Usermod propio para los colores de estado en los ojos
8. Publicar el fork bajo EUPL
```

**El paso 4 es el filtro.** Si WLED no compila como componente de ESP-IDF con un
esfuerzo razonable, la ruta completa se cae y hay que volver a evaluar
esp-matter puro o Tasmota.

## Recomendación

Separar las dos cosas, porque tienen plazos incompatibles:

**Serie Cero, ahora:** WLED de fábrica. App, colores, brillo, presets, parpadeo,
botón físico y Alexa nativo — todo funciona hoy, sin escribir una línea. Para los
clientes de Google, un enchufe inteligente de 30.000 cubre encender y apagar por
voz.

**Matter, en paralelo:** proyecto de I+D con su propio ritmo, sobre una placa de
8 o 16 MB, sin bloquear el envío de las cinco piezas vendidas.

Cuando el fork funcione, se actualiza el firmware. **El hardware no cambia** — es
la misma ESP32-C3, los mismos LEDs, el mismo cableado.
