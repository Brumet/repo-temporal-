# Patch 001 · Eliminar la puerta de reset de fábrica

**Archivo:** `wled00/button.cpp`
**Motivo:** un cliente que mantiene el botón pulsado no puede tener forma de
borrar la configuración de la pieza.

## Problema

En WLED de fábrica, mantener el botón 0 dispara dos acciones según la duración:

```cpp
#define WLED_LONG_AP             5000  // 5 s  → modo configuración
#define WLED_LONG_FACTORY_RESET 10000  // 10 s → formatea
```

Cinco segundos separan *recuperar la red* de *borrar todo*. Un reset de fábrica
ejecuta `WLED_FS.format()`, que elimina los presets (ámbar, vela, parpadeo), el
CSS con la marca y toda la configuración de la unidad.

Para un comprador que no sabe qué está haciendo, ese margen es inaceptable.

## Decisión

**Eliminar la puerta, no alargarla.** Subir el umbral a 30 s solo hace el
accidente más raro — y por tanto más difícil de diagnosticar cuando ocurra.

La recuperación destructiva sigue disponible para el taller por USB-C, que queda
accesible en la base. No tiene por qué estar al alcance del cliente.

## Cambio

Localizar en `wled00/button.cpp`, dentro del manejo de botón soltado:

```cpp
      if (b == 0 && dur > WLED_LONG_AP) { // long press on button 0 (when released)
        if (dur > WLED_LONG_FACTORY_RESET) { // factory reset if pressed > 10 seconds
          WLED_FS.format();
          doReboot = true;
        } else {
          WLED::instance().initAP(true);
        }
      } else if (!buttons[b].longPressed) { //short press
```

Sustituir por:

```cpp
      if (b == 0 && dur > WLED_LONG_AP) { // long press on button 0 (when released)
        // Cuervo Guardián: sin puerta de reset de fábrica. Mantener pulsado
        // solo devuelve a modo configuración; nunca borra presets ni CSS.
        // La reinstalación destructiva se hace por USB-C en el taller.
        WLED::instance().initAP(true);
      } else if (!buttons[b].longPressed) { //short press
```

## Resultado

Mantener el botón, el tiempo que sea:
- Menos de 5 s → nada
- Más de 5 s → modo configuración

No existe ninguna secuencia de botón que destruya la configuración.

## Verificación en hardware

- [ ] Mantener 6 s → levanta la red de configuración
- [ ] Mantener 15 s → levanta la red de configuración, **los presets siguen ahí**
- [ ] Mantener 30 s → igual, sin pérdida
- [ ] Reflashear por USB-C sigue funcionando
