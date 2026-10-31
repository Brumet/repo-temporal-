# Contexto del proyecto: Maniquí de medidas para armadura impresa en 3D

> Pega este texto al principio de tu chat local para que el asistente sepa en qué estábamos.

## Objetivo
Necesito medir a una persona que está lejos para escalar una armadura impresa en 3D
(archivo de Etsy: https://www.etsy.com/es/listing/1749173747/archivo-de-impresion-3d-armadura-din
— se asumió que es la armadura de Din Djarin / el Mandaloriano; no se pudo abrir el anuncio).
Quería un "maniquí" que le diga qué medirse (muñeca, antebrazo, hombro, pecho…) para ajustar la armadura a la perfección.

## Qué se hizo
Una página web de un solo archivo: `index.html` (HTML + CSS + JS, sin dependencias; funciona en móvil y sin internet).
Tiene 3 pestañas:

1. **Medir**: maniquí SVG que resalta en naranja dónde va la cinta + instrucciones paso a paso.
   26 medidas (todas en cm; también se pueden escribir en pulgadas):
   - General: estatura
   - Casco: contorno, alto (barbilla→coronilla), ancho y fondo de cabeza
   - Hombreras/espalda: ancho de hombros, largo del hombro (deltoides), ancho y largo de espalda
   - Pecho: contorno, ancho axila→axila, largo clavícula→fin del esternón
   - Abdomen: alto (esternón→ombligo), contorno de cintura, ancho
   - Bíceps: contorno, largo hombro→codo
   - Brazales: contorno de antebrazo, muñeca, mano cerrada, largo codo→muñeca
   - Piernas: contorno de muslo, largo de muslo, contorno de rodilla, gemelo, largo de espinilla
   Botón "Saltar (no aplica)". Las medidas se guardan en localStorage.

2. **Enviar / recibir**: resumen de texto + botón de WhatsApp. Incluye un código `ARM1:<base64 url-safe de {n:nombre, m:{id:valor}}>`.
   Quien imprime pega el mensaje y se cargan las medidas. (El enlace `#d=...` solo sirve si la página está publicada en internet.)

3. **Escalar**: por cada pieza se mide en el slicer al 100 % (en mm) y calcula el %:
   - Fórmula longitud: `% = (medida_cuerpo_cm × factor + holgura_cm) × 10 / medida_modelo_mm × 100`
   - Fórmula tubos (diámetro interior): `% = ((contorno_cm + holgura) × 10 / π) / diámetro_modelo_mm × 100`
   - Da escala uniforme (la mayor, para que quepa) y no uniforme X/Y/Z; avisa si los ejes difieren > 8 %.
   - Comprueba si el brazal (tubo cerrado) pasa por la mano.
   - Atajo: escala general = estatura persona / estatura de diseño (180 cm por defecto).

   Holguras por defecto (editables):
   | Pieza | Medidas usadas | Holgura |
   |---|---|---|
   | Casco | ancho X, fondo Y, alto Z | +2, +2, +1,5 cm |
   | Hombreras | largo deltoides | 0 |
   | Pecho | ancho X, alto Z | 0, −1 |
   | Abdomen | ancho X, alto Z | −2, −1 |
   | Espalda | ancho X, alto Z | 0, −4 |
   | Brazales | Ø codo, Ø muñeca, largo Z | +2, +1,5, −1,5 |
   | Bíceps | Ø, largo (60 % del brazo) | +2, 0 |
   | Muslos | alto Z, ancho (1/3 del contorno) | −2, 0 |
   | Rodilleras | ancho (1/3 del contorno) | +1 |
   | Espinilleras | Ø gemelo, largo Z | +2, −1 |

## Estado
- Probado en navegador: recorrido completo medir → enviar → importar → escalar sin errores.
- Archivos: `index.html`, `README.md`, `captura-medir.png`, este archivo.
- También está en GitHub: repo `brumet/repo-temporal-`, rama `claude/armor-measurement-mannequin-ioqe5s`, carpeta `maniqui-armadura/`.

## Ideas pendientes (opcionales)
- Publicarlo en GitHub Pages para que funcione el enlace con medidas.
- Ajustar holguras tras imprimir una pieza de prueba (p. ej. un brazal).
- Añadir piezas que traiga el archivo y no estén (guanteletes, cinturón, collar…).
