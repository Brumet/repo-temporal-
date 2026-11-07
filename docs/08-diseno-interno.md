# Diseño interno del cuervo

> Análisis del modelo `forma preliminar.stl` (7/11/2026) y propuesta para imprimirlo
> en resina: hueco, cabeza desmontable, cables por dentro, electrónica y lastre en una
> tapa inferior. Scripts en [`../hardware/analisis/`](../hardware/analisis/).

## Lo que dice el modelo

| Dato | Valor |
|---|---|
| Tamaño total | 181 × 212 × 300 mm (ancho × fondo × alto) |
| Malla | 2,7 M caras, una sola pieza; 8 bordes abiertos y 82 aristas defectuosas (reparable) |
| Volumen macizo | **2.367 cm³** de resina |
| Volumen hueco, paredes de 3 mm | **504 cm³** → **79 % menos resina** |

### Alturas de cada parte

| Parte | Altura (z) | Sección |
|---|---|---|
| Roca (base) | 0 – 38 mm | hasta 159 mm de ancho útil |
| Calavera | 40 – 137 mm | hasta 98 mm de ancho |
| Patas (tarsos) | 140 – 170 mm | **dos patas en x ≈ ±21 mm** |
| Cuerpo | 170 – 285 mm | hasta 88 mm |
| Cabeza | sobre el collar, z ≈ 245 (garganta) a 287 (nuca) | ~50 mm de ancho |
| Cola | cuelga libre detrás de la calavera hasta z ≈ 70 | **no toca la roca** |

### Las patas: ¿caben los cables?

- Grosor mínimo de cada pata: **10 – 12 mm** de diámetro (más delgada hacia z ≈ 157).
- Mazo de 3 cables de 30 AWG con silicona: ~2,2 mm → **canal de Ø 3 mm**.
- Queda pared de **3,5 – 4,5 mm** a cada lado.
- Efecto en la resistencia de esa pata: el área baja ~8 % y la rigidez a flexión
  **menos del 1 %** (un agujero en el centro casi no trabaja). **Es viable.**
- El canal tiene que salir **modelado** desde la impresión (curvo: muslo → tarso →
  pie → calavera); no se puede taladrar después. Se enhebra con un alambre guía.
- La cola no sirve de ruta: cuelga libre y no llega a la roca.

### El collar: el corte de la cabeza

El collar es una correa **inclinada**: de la garganta (z ≈ 245) a la nuca (z ≈ 285).
Cortar siguiendo esa correa esconde la costura en un detalle que ya existe. Los dos
ojos (z ≈ 268, adelante) quedan del lado de la cabeza.

## Propuesta

### Piezas

1. **Cabeza** — hueca, se quita por el collar.
   - 3 pines cónicos asimétricos (Ø 4 × 4 mm, holgura 0,2 mm): solo entra en una posición.
   - 2 imanes de 6 × 2 mm para que no se caiga y se pueda abrir en mantenimiento.
   - Bolsillo para cada LED detrás del ojo (Ø 11 × 4 mm, a 3–5 mm de la superficie),
     canal de cada ojo hacia el cuello, y espacio para la silicona que aísla la luz.
2. **Cuerpo + patas + calavera + roca** — hueco con paredes de 3 mm.
   - Canal de Ø 3 mm por **una** pata, del cuerpo a la calavera.
   - Abierto por debajo: por ahí escurre la resina al lavar y entra la tapa.
3. **Tapa inferior** — donde va todo lo demás:
   - Bahía para la ESP32 con el **USB-C hacia atrás**, por una ranura en la pared de la roca.
   - **Cámara de lastre** sellada (yeso o cemento, unos 500 g) lo más abajo posible.
   - Ranuras de ventilación por debajo, separada del piso por patitas de 3–4 mm.
4. **Botón** — interruptor MX en la pared de la roca. El keycap es **el mismo pedazo
   de roca recortado** (se extrae de la malla), con 0,4 mm de holgura: no se ve que es un botón.

### Cómo se sujeta la tapa: comparación

| Opción | A favor | En contra |
|---|---|---|
| **Bayoneta ¼ de vuelta** ("piñón") | Sin herramientas, aguanta el lastre | El botón y el USB no pueden ir en la tapa (giraría) |
| **Clips a presión** | Rápido | La resina estándar es quebradiza: los clips se parten |
| **Imanes** | Muy fácil de abrir | Con 500 g de lastre, al levantar la pieza la tapa se puede caer |
| **2 tornillos ocultos** bajo patitas de goma | El más robusto y barato | Hace falta un destornillador |

### Pendiente de decidir

- Impresora de resina y su volumen (la pieza mide 300 mm de alto).
- Cómo se ve el ojo encendido: ¿cabeza en resina transparente pintada menos los ojos?
- Sujeción de la tapa y ubicación del botón.

## Firmware: un solo botón

Si queda **un** botón, WLED solo repite el brillo al mantener en botones de índice
mayor que 0. Con el firmware propio se resuelve en `Cuervo_Estado`: toque =
encender/apagar, mantener = brillo, 5 s = red de configuración (sin reset de fábrica).
