# Botones y acceso a la red

> Verificado leyendo `wled00/button.cpp` de WLED, commit `18ab096`.
> No son suposiciones: son las constantes y el flujo real del código.

## Comportamiento real de los botones

Por defecto, sin macros asignadas:

| | **Botón 0** | **Botón 1** |
|---|---|---|
| Toque corto | Encender / apagar | Siguiente efecto |
| Doble toque | **nada** (comentado en el fuente) | Siguiente paleta |
| Mantener | Color aleatorio, **una sola vez** | **Brillo ↑↓, repitiendo** |

### El brillo solo funciona en el botón 1

```cpp
} else if (b) {   // repeatable action on button > 0
  longPressAction(b);
```

La repetición mientras se mantiene pulsado está condicionada a que el índice del
botón sea mayor que 0. En el botón 0 la pulsación larga dispara una sola vez.

**Consecuencia de diseño: hacen falta dos botones.**

### Dirección del brillo

```cpp
buttonBriDirection = !buttonBriDirection; // toggle brightness direction
```

Cada nueva pulsación larga invierte el sentido. Mantener → sube. Soltar y
mantener de nuevo → baja. Y así alternando.

## Constantes

```cpp
#define WLED_DOUBLE_PRESS          350  // ventana para el doble toque (ms)
#define WLED_LONG_REPEATED_ACTION  400  // cada cuánto repite al mantener (ms)
#define WLED_LONG_AP              5000  // 5 s → vuelve a modo configuración
#define WLED_LONG_FACTORY_RESET  10000  // 10 s → FORMATEA y reinicia
#define WLED_LONG_BRI_STEPS         16  // paso de brillo, sobre 255
```

### ⚠️ Riesgo: 5 segundos separan recuperar de destruir

Mantener el botón 0:
- **5 segundos** → levanta la red de configuración. Es el rescate cuando el
  cliente cambia de router. Debe ir en la tarjeta de la caja.
- **10 segundos** → `WLED_FS.format()` y reinicio. **Borra todos los presets**:
  ámbar, vela, parpadeo, el CSS con la marca. Todo.

Cinco segundos de margen es poco para alguien que no sabe qué está haciendo.
Evaluar subir `WLED_LONG_FACTORY_RESET` en el fork, o no mencionar el gesto de
5 s en las instrucciones y resolver esos casos por soporte.

## Asignación de pines propuesta

```
GPIO 4  → WS2812B DIN
GPIO 3  → Botón 0   toque: encender / apagar
GPIO 5  → Botón 1   mantener: brillo
```

Dos actuadores esculpidos distintos en la base — un hueso y una runa, por
ejemplo — para que se lean como elementos de la escultura y no como dos botones.

## Pendiente de verificar en hardware

Hacer que un toque recorra **los cinco presets propios** en vez de los 100+
efectos de fábrica requiere asignar una macro (`macroButton`,
`macroDoublePress`, `macroLongPress`). En el código, una macro aplica **un
preset concreto**, no "el siguiente".

- [ ] ¿Se puede expresar "siguiente preset" en una macro?
- [ ] Si no: ¿basta con dejar el botón 1 en efecto y paleta de fábrica?
- [ ] ¿Cuánto sube el consumo con dos botones? (irrelevante, pero medir)

## Acceso a la interfaz web

### Fase 1 · Sin configurar
La escultura levanta su propia red. **Es la única puerta de entrada.** El celular
tiene que unirse a ella para abrir la página.

Mientras está conectado a esa red, el celular se queda sin internet. Los
teléfonos modernos lo detectan y a veces vuelven solos a la red de datos. Es
molesto, y por eso conviene que el cliente haga la configuración.

### Fase 2 · Configurada
La escultura se une al WiFi de la casa y **deja de emitir su propia red**. La
página queda accesible desde cualquier dispositivo de esa casa, con internet
funcionando con normalidad.

### Autorreparación
Si el WiFi de la casa desaparece, WLED vuelve a levantar su red por su cuenta.
La pieza nunca queda inaccesible.

### Límite honesto
El control es **solo dentro de la casa**. Desde fuera no es posible sin montar
infraestructura adicional.

En la ficha de producto se declara como lo que es:

> Control local. Sin nube, sin cuenta, sin suscripción.

Para mucha gente es una ventaja de privacidad. Quien espere controlarlo desde la
oficina merece saberlo **antes** de comprar.
