"""Arma el instructivo de una sola hoja A4 a partir de las imágenes ya incrustadas
en instructivo.html (logo, cuervo y fichas de los ojos). Uso: python armar_hoja.py"""
import re
from pathlib import Path

aqui = Path(__file__).parent
s = (aqui / "instructivo.html").read_text(encoding="utf-8")
logo = re.search(r'<svg class="logo".*?</svg>', s, re.S).group(0)
hero = re.search(r'<img class="hero" src="([^"]+)"', s).group(1)
ojos = re.findall(r'<div class="est"><img(?: class="ojo")? src="([^"]+)" alt=""><div><b>(.*?)</b><span>(.*?)</span></div></div>', s)
assert len(ojos) == 6, len(ojos)
est = "".join(f'<div class="est"><img src="{u}" alt=""><div><b>{w}</b><span>{d}</span></div></div>' for u, w, d in ojos)

CSS = """
  @page { size: A4; margin: 0; }
  :root { --tx:#141214; --tx2:#5b565c; --line:#e7e2dc; --red:#e3262f; --paper:#fbf9f6; }
  * { box-sizing: border-box; }
  html, body { margin: 0; background: #d9d4cc; color: var(--tx);
    font-family: "Segoe UI Variable", "Segoe UI", -apple-system, "Helvetica Neue", Arial, sans-serif;
    -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .page { width: 210mm; height: 297mm; margin: 10mm auto; background: var(--paper); position: relative;
    padding: 11mm 14mm 0; overflow: hidden; box-shadow: 0 4px 30px rgba(0,0,0,.15); }
  @media print { html, body { background: none; } .page { margin: 0; box-shadow: none; } }
  .top { display: flex; justify-content: space-between; align-items: center; padding-bottom: 4mm; border-bottom: 1.2px solid var(--tx); }
  .top .logo { height: 11mm; width: auto; display: block; }
  .serie { text-align: right; font-size: 8pt; letter-spacing: .14em; text-transform: uppercase; color: var(--tx2); line-height: 1.6; }
  .serie b { color: var(--tx); letter-spacing: .1em; }
  .num { display: inline-block; min-width: 12mm; border-bottom: 1px solid var(--tx); }
  h1 { font-size: 25pt; font-weight: 700; letter-spacing: -.02em; margin: 5mm 0 1.5mm; line-height: 1; }
  h1 span { color: var(--red); }
  .lead { font-size: 9.6pt; line-height: 1.45; color: var(--tx2); max-width: 118mm; margin: 0; }
  .hero { position: absolute; right: 10mm; top: 27mm; width: 50mm; }
  h2 { font-size: 11pt; margin: 0 0 1.6mm; display: flex; align-items: center; gap: 2.4mm; }
  h2 i { font-style: normal; width: 5.8mm; height: 5.8mm; border-radius: 50%; background: var(--tx); color: #fff;
    font-size: 8.5pt; display: grid; place-items: center; flex: none; }
  section { margin-top: 3.8mm; }
  p, li { font-size: 8.9pt; line-height: 1.42; }
  p { margin: 0 0 1.2mm; }
  ol { margin: 0; padding-left: 4.5mm; }
  li { margin-bottom: .5mm; }
  .wide { width: 122mm; }
  .note { font-size: 8.2pt; color: var(--tx2); }
  .note b { color: var(--tx); }
  code { font-family: "Cascadia Mono", Consolas, monospace; font-size: 8.6pt; background: #f1ece6; padding: .2mm 1.2mm; border-radius: 1mm; }
  .estados { display: grid; grid-template-columns: repeat(3, 1fr); gap: 2mm; }
  .est { display: flex; align-items: center; gap: 2.2mm; background: #fff; border: 1px solid var(--line); border-radius: 3mm; padding: 1.6mm 2mm 1.6mm 1.6mm; }
  .est img { width: 11.5mm; height: 11.5mm; border-radius: 50%; flex: none; box-shadow: 0 1px 3px rgba(0,0,0,.25); }
  .est b { display: block; font-size: 8.6pt; }
  .est span { display: block; font-size: 7.7pt; color: var(--tx2); line-height: 1.3; }
  .cols { display: grid; grid-template-columns: 1fr 1fr; gap: 6mm; }
  .box { background: #fff; border: 1px solid var(--line); border-radius: 3mm; padding: 2.4mm 3.2mm; }
  .url { font-size: 12pt; font-weight: 700; margin: .5mm 0 1.2mm; }
  table { width: 100%; border-collapse: collapse; }
  td { font-size: 8.4pt; padding: 1.1mm 1mm; border-bottom: 1px solid var(--line); vertical-align: top; line-height: 1.35; }
  tr:last-child td { border-bottom: 0; }
  td:first-child { font-weight: 650; width: 40mm; }
  .foot { position: absolute; left: 14mm; right: 14mm; bottom: 8mm; display: flex; justify-content: space-between;
    align-items: flex-end; font-size: 7.2pt; color: var(--tx2); border-top: 1px solid var(--line); padding-top: 2.4mm; line-height: 1.45; }
  .foot b { color: var(--tx); font-size: 9pt; }
  .foot .web { color: var(--red); font-weight: 700; font-size: 11pt; letter-spacing: .06em; }
"""

BODY = f"""
<div class="page">
  <div class="top">
    {logo}
    <div class="serie"><b>Cuervo · Serie Cero</b><br>Pieza <span class="num">&nbsp;</span> de 4</div>
  </div>

  <img class="hero" src="{hero}" alt="">

  <h1>Tu cuervo tiene <span>mirada</span>.</h1>
  <p class="lead">Esculpido, impreso y pintado a mano. Sus ojos se encienden con el color y el efecto que elijas:
    con el botón, desde tu celular o con la voz. Sin aplicaciones, sin cuentas y sin nube.</p>

  <section class="wide">
    <h2><i>1</i>Enciéndelo</h2>
    <p>Conecta el <b>USB-C</b> de la parte de atrás a un cargador de celular (5 V). La primera vez los ojos
      <b>respiran en azul</b>: está listo para tu WiFi. <span class="note">Sin WiFi también funciona, con el botón.</span></p>
  </section>

  <section class="wide">
    <h2><i>2</i>Conéctalo a tu WiFi</h2>
    <ol>
      <li>En tu celular: <b>Ajustes → WiFi</b> → red <code>Cuervo-<span class="num" style="min-width:6mm">&nbsp;</span></code>, clave <code>wled1234</code>. Ojos: <b>azul fijo</b>.</li>
      <li>En el navegador entra a <code>4.3.2.1</code> → <b>⚙ Ajustes → WiFi y red</b>.</li>
      <li>Escribe tu red en <b>Network name (SSID)</b> y su clave en <b>Network password</b> → <b>Save &amp; Connect</b>.</li>
      <li>Destellos blancos mientras conecta y <b>3 parpadeos verdes</b>: ¡listo! Vuelve tu celular a tu WiFi.</li>
    </ol>
    <p class="note" style="margin-top:1mm"><b>Importante:</b> usa una red de <b>2,4 GHz</b>. Si tu router tiene “Casa” y “Casa-5G”, elige la que no dice 5G.</p>
  </section>

  <section>
    <h2><i>3</i>Qué te dicen sus ojos</h2>
    <div class="estados">{est}</div>
  </section>

  <section class="cols">
    <div>
      <h2><i>4</i>Contrólalo desde el celular</h2>
      <p>En tu WiFi de siempre, abre el navegador y entra a:</p>
      <p class="url">http://cuervo-<span class="num">&nbsp;</span>.local</p>
      <p>Escenas, color, brillo, efectos (vela, fuego, latido…) y temporizador. Tócalo en <b>Compartir → Agregar a
        pantalla de inicio</b> y queda como una app.</p>
      <p class="note"><b>iPhone con Chrome:</b> si no abre, activa <b>Ajustes → Chrome → Red local</b>.</p>
    </div>
    <div>
      <h2><i>5</i>El botón de la base</h2>
      <div class="box">
        <p><b>Un toque:</b> enciende o apaga los ojos.</p>
        <p><b>Mantener:</b> sube o baja el brillo.</p>
        <p style="margin:0"><b>Mantener 5 s:</b> vuelve a abrir la red <code>Cuervo-…</code> para cambiar de WiFi.</p>
      </div>
      <p class="note" style="margin-top:2mm"><b>Cuidados:</b> pieza para interiores. No la mojes ni la dejes al sol. Límpiala con un pincel suave y seco. No tapes la base: por ahí respira la electrónica.</p>
    </div>
  </section>

  <section>
    <h2><i>6</i>Si algo no funciona</h2>
    <div class="box"><table>
      <tr><td>No enciende</td><td>Revisa el cable y prueba otro cargador de celular.</td></tr>
      <tr><td>No aparece la red Cuervo</td><td>Desconéctalo 5 segundos y vuelve a conectarlo.</td></tr>
      <tr><td>3 parpadeos rojos</td><td>El nombre o la clave de la red no coinciden. Recuerda: red de 2,4 GHz.</td></tr>
      <tr><td>Cambiaste de router</td><td>Mantén el botón 5 segundos y repite el paso 2.</td></tr>
      <tr><td>La página no abre</td><td>Tu celular debe estar en la misma WiFi que el cuervo.</td></tr>
    </table></div>
  </section>

  <div class="foot">
    <div><b>Brumet</b> · Hecho a mano en Colombia<br>Firmware abierto WLED (licencia EUPL v1.2) con módulos de Brumet · github.com/Brumet/repo-temporal-</div>
    <div class="web">brumet.co</div>
  </div>
</div>
"""

html = f'<!doctype html>\n<html lang="es">\n<head>\n<meta charset="utf-8">\n<title>Cuervo · Instructivo</title>\n<style>{CSS}</style>\n</head>\n<body>{BODY}</body>\n</html>\n'
(aqui / "instructivo.html").write_text(html, encoding="utf-8")
print("ok", len(html))
