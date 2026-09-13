# Hardware

## Lista de materiales (por unidad)

| Componente | Modelo | Costo COP | Fuente |
|---|---|---:|---|
| Microcontrolador | ESP32-C3 SuperMini (USB-C integrado) | 12.354 | Amazon, pack de 5 = 61.769 |
| LEDs de ojos | 2× módulo WS2812B redondo, PCB negro, 5V | 927 | Amazon, 100 uds = 46.319 |
| Cable | 30AWG silicona, ~1,7 m | ~1.200 | Amazon, kit 5 colores = 37.049 |
| Botón | Switch mecánico MX | 0 | Stock propio (de los clickers) |
| **Total electrónica** | | **~14.500** | |

Sobre un precio de venta objetivo de 320.000, la electrónica es el **4,5%**.

### Alcance de la compra inicial
- 5 placas ESP32-C3 → **5 unidades** (cuello de botella)
- 100 módulos LED → 50 unidades
- Kit de cable → ~30 unidades

### No se necesita
- **Resistencia en línea de datos**: los módulos BTF-LIGHTING ya traen R1 (75Ω)
  y C1 (capacitor de desacople) integrados en el PCB.
- **Fuente externa ni batería**: todo va por USB-C a 5V.

## Mapa de pines

```
ESP32-C3 SuperMini
├── GPIO 4  → DIN del primer LED (ojo derecho)
├── GPIO 3  → Switch mecánico → GND
├── 3V3     → alimentación de los dos LEDs
└── GND     → común
```

### Pines prohibidos
`GPIO 2`, `GPIO 8` y `GPIO 9` son pines de arranque (strapping) de la ESP32-C3.
Conectar algo ahí puede dejar la placa en modo programación al encender, con los
ojos apagados y sin explicación aparente.

### Por qué 3V3 y no 5V para los LEDs

La ESP32-C3 emite datos a 3,3 V. Un WS2812B alimentado a 5 V exige un nivel alto
de al menos 3,5 V (0,7 × VDD) para reconocer un "1" — el margen queda negativo y
el comportamiento es errático: parpadeos, colores equivocados, primer píxel
correcto y segundo no.

Alimentando los LEDs desde 3V3 los niveles coinciden y el enlace es estable.
Efecto secundario deseable: brillo más bajo, que es exactamente lo que se busca
para unos ojos.

## Conexionado

Los dos ojos van **encadenados**, no en paralelo. Cada WS2812B tiene su propio
controlador: consume el primer paquete de datos y retransmite el resto. Un solo
cable de datos, control individual de ambos ojos.

```
ESP32 (en la base)
  GPIO4 ─────────────────────> DIN   ┐
  3V3   ─────────────────────> 5V+   ├── LED 1 · ojo derecho
  GND   ─────────────────────> GND   ┘
                                      
                   LED 1 · Dout ────> DIN   ┐
                   LED 1 · 5V+  ────> 5V+   ├── LED 2 · ojo izquierdo
                   LED 1 · GND  ────> GND   ┘
```

Solo **3 conductores** suben por la pata y el cuello. Del ojo derecho salen
3 cables cortos que cruzan la cabeza hasta el izquierdo.

### Código de color obligatorio
```
ROJO     → 3V3 / 5V+
NEGRO    → GND
AMARILLO → datos (DIN/Dout)
```
Verde y azul quedan de repuesto. Mantener el código idéntico en todas las
unidades: en la pieza número 12, a medianoche, es lo único que evita conectar
alimentación donde iba señal.

## Consumo

| Elemento | Corriente |
|---|---|
| 2× WS2812B a brillo máximo | ~120 mA |
| ESP32-C3 con WiFi activo (picos) | ~150 mA |
| **Total** | **< 300 mA** |

Cualquier puerto USB o cargador de celular sirve. Sin batería de litio, lo que
además elimina las restricciones de envío que aplican al transporte aéreo de
baterías.

> **Nota para Matter:** el consumo sube al usar Thread o al mantener sesiones
> Matter activas. Medir antes de fijar la especificación final.

## Diseño mecánico

### Un LED por ojo, retirado del lente
Cada módulo va en su propia cámara, **3-5 mm detrás** de su lente. Pegado al
lente se ve un punto brillante duro; separado, la luz se abre y el ojo enciende
parejo. Interior de la cámara pintado de negro mate para evitar filtración hacia
las plumas.

Nunca un LED central compartido: la estructura del cráneo y el pico lo bloquean,
los ojos quedan desiguales y se pierde el control independiente.

### Refuerzo estructural
Las patas son el punto de falla en transporte. Canal de 2,5-3 mm por dentro de
cada tarso:
- **Una pata** lleva los 3 conductores
- **La otra** lleva varilla roscada o de latón con epóxico

Con eso la pata deja de ser plástico impreso y pasa a ser metal forrado.

### División de impresión
```
1. CABEZA        hueca, tapa trasera o inferior para insertar
                 el módulo de ojos ya armado y probado
2. CUERPO        canal interno de 3 mm desde el cuello
3. PATAS+CRÁNEO  canal de 3 mm por una pata, varilla en la otra
4. BASE          bahía para la ESP32 + tapa inferior atornillada
                 + recorte USB-C de 22,5 × 18 mm al ras del borde
```

### Junta desmontable (opcional)
Si se separa, el corte va entre **la roca y el cráneo**, nunca entre el ave y el
cráneo — las garras son demasiado delicadas para ser también junta mecánica.

Conexión: 3 pogo pins en la roca + pads de latón en la base del cráneo + imanes
de neodimio.

> ⚠️ **Riesgo de polaridad invertida.** Si los imanes permiten girar la pieza
> 180°, el cliente puede invertir la conexión y quemar ambos LEDs al instante.
> Obligatorio: una guía mecánica asimétrica que haga físicamente imposible
> montarla al revés. No confiar en instrucciones.

## Herramientas

| Herramienta | Costo aprox. | Prioridad |
|---|---:|---|
| Cautín de temperatura regulable 60W | 100-150.000 | Imprescindible |
| Pelacables con muesca de 30AWG | 30-50.000 | Los comunes cortan el cable |
| Tercera mano con pinzas | 25-40.000 | Cuatro manos necesarias, hay dos |
| Multímetro con zumbador | ~64.000 | Truper MUT-33 |

### Uso real del multímetro
1. **Buscar cortos antes de energizar** — puntas entre 5V y GND del módulo ya
   soldado. Si pita, hay puente de estaño.
2. **Verificar el cable tras pasarlo por el cuello** — ¿se partió al jalarlo?
3. **Confirmar que el switch cierra.**

> Continuidad **siempre** con el USB desconectado. En circuito energizado las
> lecturas son falsas y puede dañarse el instrumento.
