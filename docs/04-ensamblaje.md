# Ensamblaje de una unidad

## Regla de oro

**Armar y probar el módulo de ojos en la mesa, conectado a una ESP32, ANTES de
meterlo en la cabeza.**

Una vez ese módulo está dentro de una cabeza pegada y pintada, cualquier falla
cuesta la pieza completa — incluidas las horas de pintura. Ninguna medición vale
tanto como no instalar un módulo sin probar.

## 1 · Módulo de ojos (en lote)

Armar los 5 de una sentada mientras se imprime. Es trabajo repetitivo y baja
mucho el tiempo por pieza.

Por módulo:

1. Cortar 3 cables largos (~30 cm) y 3 cortos (~8 cm) según código de color
2. Estañar los pads **antes** de acercar el cable — nunca soldar cable y pad
   simultáneamente, levanta el cobre
3. Soldar los 3 largos a los pads de entrada del LED 1 (`DIN`, `5V+`, `GND`)
4. Soldar los 3 cortos de los pads de salida del LED 1 (`Dout`, `5V+`, `GND`)
   a los de entrada del LED 2
5. **Multímetro en continuidad, USB desconectado:** puntas entre `5V+` y `GND`.
   Si pita, hay un puente de estaño. Corregir antes de seguir
6. Conectar a una ESP32 con firmware y confirmar que **ambos** ojos encienden y
   responden por separado
7. Etiquetar el módulo probado y apartarlo

## 2 · Preparación de la impresión

- Interior de las cámaras de ojos: **negro mate**
- Lentes: lijado progresivo hasta grano 1000, sellado con resina UV o barniz
  brillante. Tono **ahumado o gris neutro**, nunca ámbar
- Varilla de refuerzo en una pata, con epóxico
- Verificar que el canal de 3 mm esté despejado de punta a punta

> **Por qué el lente no va ámbar:** un lente teñido contamina todos los colores
> — el azul se ve verdoso, el blanco amarillo. Se pierde la función de cambio de
> color. Con lente neutro, apagado se ve como una cuenca oscura y encendido
> reproduce el color real del LED. El ámbar es un preset, no una pintura.

## 3 · Cableado

1. Pasar los 3 cables largos por el canal: cabeza → cuello → cuerpo → pata →
   cráneo → base
2. **Verificar continuidad de los 3 cables después de jalarlos.** Es el momento
   de detectar una rotura, no después de cerrar
3. Asentar el módulo de ojos en su cámara, alineando cada LED con su lente
4. Cerrar la cabeza

## 4 · Base

1. Montar el switch mecánico en su alojamiento (~25 mm de profundidad; si la
   roca es delgada, montarlo acostado sacando el vástago por la parte trasera)
2. Soldar 2 cables del switch: `GPIO3` y `GND`. Sin polaridad
3. Alojar la ESP32 en su bahía, con el USB-C al ras del borde trasero
4. Conectar los 3 cables del cuerpo: `GPIO4`, `3V3`, `GND`
5. Tapa inferior atornillada

## 5 · Prueba final

- [ ] Enchufar USB-C → ambos ojos encienden en ámbar sin intervención
- [ ] Toque corto en el botón → apaga y enciende
- [ ] Doble toque → cambia de preset
- [ ] Mantener pulsado el botón 1 → varía el brillo (alterna sentido)
- [ ] Emparejar con un asistente de voz y confirmar respuesta
- [ ] Dejar encendida 2 horas y verificar que no hay parpadeo ni calentamiento
- [ ] Desconectar y reconectar → vuelve sola al preset guardado

## Errores frecuentes

| Síntoma | Causa probable |
|---|---|
| Ningún LED enciende | Datos conectados al pad de salida en vez del de entrada. Las flechas del módulo mandan |
| Solo enciende el primer ojo | Cable `Dout`→`DIN` entre ojos suelto o mal soldado |
| Colores erráticos, parpadeo | LEDs alimentados a 5V en vez de 3V3 |
| Los ojos no encienden al arrancar | Algo conectado a GPIO 2, 8 o 9 — la placa quedó en modo programación |
| Un toque cuenta como dos | Rebote del switch mecánico. Capacitor de 0,1 µF entre sus dos pines |
| El cable se cortó al pelarlo | Pelacables sin muesca de 30AWG |
