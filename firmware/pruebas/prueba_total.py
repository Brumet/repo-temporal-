"""
Prueba total de una unidad: placa ESP32-C3 + módulo de ojos.

Uso:
    python prueba_total.py 192.168.40.35 [--espera 45] [--calor 5] [--resistencia 20]

Fases:
  0. Ficha y configuración (pin 4, 2 LEDs, 250 mA, WiFi sleep, preset al arrancar)
  1. Funcional: encendido, brillo, colores puros (detecta orden de color cambiado),
     escenas, efectos y temporizador. Cada paso dura 3 s para mirarlo en los ojos.
  2. Estrés: cientos de órdenes seguidas; cuenta fallos y comprueba que no reinicia.
  3. Peor caso de calor: blanco al 100 % durante N minutos (el límite de 250 mA actúa).
  4. Resistencia: N minutos con efecto Vela vigilando reinicios, memoria y WiFi.
Al final deja la pieza en la escena 1 (Ámbar) y escribe un reporte en reportes/.

El chip no publica su temperatura en este firmware: el calor se valida al tacto
al terminar la fase 3, con las instrucciones del reporte.
"""
import argparse, json, statistics, sys, time, urllib.request
from datetime import datetime
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("ip")
ap.add_argument("--espera", type=int, default=0, help="segundos antes de empezar")
ap.add_argument("--calor", type=float, default=5, help="minutos de blanco al 100 %%")
ap.add_argument("--resistencia", type=float, default=20, help="minutos de vigilancia")
a = ap.parse_args()
H = f"http://{a.ip}"
log, fallas, avisos = [], [], []


def say(m):
    line = f"{datetime.now():%H:%M:%S}  {m}"
    print(line, flush=True)
    log.append(line)


def get(p, t=6):
    return json.loads(urllib.request.urlopen(H + p, timeout=t).read().decode("utf-8"))


def post(o, t=6):
    r = urllib.request.Request(H + "/json/state", data=json.dumps({**o, "v": True}).encode(),
                               headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=t).read().decode("utf-8"))


def info():
    return get("/json/info")


def temp(x):  # °C del chip; solo con el firmware propio (módulo Internal_Temperature)
    return (x.get("u") or {}).get("Internal Temperature", [None])[0]


def check(nombre, cond, detalle=""):
    say(f"{'OK   ' if cond else 'FALLA'} {nombre} {detalle}")
    if not cond:
        fallas.append(f"{nombre} {detalle}")


def paso(nombre, orden, verif=None, ver=""):
    try:
        s = post(orden)
        if "ps" in orden:  # WLED aplica las escenas en su siguiente ciclo, no en la respuesta
            time.sleep(1.2); s = get("/json/state")
        ok = verif(s) if verif else True
        check(nombre, ok, f"— mirar: {ver}" if ver else "")
    except Exception as e:
        check(nombre, False, f"(sin respuesta: {type(e).__name__})")
    time.sleep(3)


if a.espera:
    say(f"Empieza en {a.espera} s")
    time.sleep(a.espera)

# ——— 0. Ficha ———
say("=== 0. Ficha y configuración ===")
i0 = info(); c = get("/json/cfg")
led = c["hw"]["led"]; ins = led["ins"][0]
say(f"{i0['name']} · WLED {i0['ver']} · MAC {i0['mac']} · IP {i0['ip']}")
say(f"memoria libre {i0['freeheap']} B · WiFi {i0['wifi']['signal']} % ({i0['wifi']['rssi']} dBm) · "
    f"encendida hace {i0['uptime']} s · consumo estimado {i0['leds']['pwr']} mA · chip {temp(i0)} °C")
check("Pin de datos = 4", ins["pin"] == [4], f"(es {ins['pin']})")
check("Cantidad de LEDs = 2", ins["len"] == 2, f"(es {ins['len']})")
check("Límite de corriente ≤ 250 mA", 0 < led["maxpwr"] <= 250, f"(es {led['maxpwr']})")
check("WiFi sleep activo", c["wifi"]["sleep"] is True)
bootps = c.get("def", {}).get("ps", 0)
if bootps != 1:
    avisos.append(f"Preset al arrancar = {bootps}, el proyecto pide 1 (Ámbar)")
    say(f"AVISO preset al arrancar = {bootps} (se espera 1)")
up0, t0 = i0["uptime"], time.time()

# ——— 1. Funcional ———
say("=== 1. Funcional (mirar los ojos) ===")
paso("Apagar", {"on": False}, lambda s: s["on"] is False, "ojos apagados")
paso("Encender", {"on": True, "bri": 50, "seg": [{"fx": 0, "col": [[255, 100, 0]]}]},
     lambda s: s["on"] is True, "ámbar suave")
for b in (5, 50, 128, 255, 50):
    paso(f"Brillo {round(b / 2.55)} %", {"bri": b}, lambda s, b=b: s["bri"] == b,
         f"brillo {round(b / 2.55)} %")
for n, col in (("ROJO", [255, 0, 0]), ("VERDE", [0, 255, 0]), ("AZUL", [0, 0, 255]),
               ("BLANCO", [255, 255, 255]), ("ÁMBAR", [255, 100, 0])):
    paso(f"Color {n}", {"bri": 128, "seg": [{"fx": 0, "col": [col]}]},
         lambda s, col=col: s["seg"][0]["col"][0][:3] == col, f"los DOS ojos en {n}")
pres = get("/presets.json")
for pid in sorted(int(k) for k, v in pres.items() if int(k) > 0 and v):
    paso(f"Escena {pid} {pres[str(pid)].get('n', '')}", {"ps": pid},
         lambda s, pid=pid: s["ps"] == pid, pres[str(pid)].get("n", ""))
eff = get("/json/eff")
for n in ("Breathe", "Candle", "Fire Flicker", "Heartbeat", "Blink", "Rainbow"):
    if n in eff:
        fx = eff.index(n)
        paso(f"Efecto {n}", {"bri": 80, "seg": [{"fx": fx, "col": [[255, 100, 0]]}]},
             lambda s, fx=fx: s["seg"][0]["fx"] == fx, n)
paso("Temporizador activar", {"nl": {"on": True, "dur": 30, "mode": 1, "tbri": 0}},
     lambda s: s["nl"]["on"] is True)
paso("Temporizador cancelar", {"nl": {"on": False}}, lambda s: s["nl"]["on"] is False)

# ——— 2. Estrés ———
say("=== 2. Estrés: 400 órdenes seguidas ===")
lat, err = [], 0
for k in range(400):
    o = {"bri": 20 + (k * 37) % 200, "seg": [{"fx": 0, "col": [[(k * 53) % 256, (k * 97) % 256, (k * 29) % 256]]}]}
    t = time.time()
    try:
        post(o, t=4); lat.append((time.time() - t) * 1000)
    except Exception:
        err += 1
lat.sort()
say(f"respuesta mediana {statistics.median(lat):.0f} ms · p95 {lat[int(len(lat) * .95)]:.0f} ms · "
    f"peor {lat[-1]:.0f} ms · fallos {err}/400")
check("Estrés sin fallos (≤1 %)", err <= 4, f"({err} fallos)")
time.sleep(2)
i2 = info()
check("No se reinició durante el estrés", i2["uptime"] >= up0 + int(time.time() - t0) - 5,
      f"(encendida hace {i2['uptime']} s)")

# ——— 3. Peor caso de calor ———
say(f"=== 3. Peor caso: blanco al 100 % durante {a.calor:g} min ===")
post({"on": True, "bri": 255, "seg": [{"fx": 0, "col": [[255, 255, 255]]}]})
pw, tc, fin = [], [], time.time() + a.calor * 60
while time.time() < fin:
    try:
        x = info(); pw.append(x["leds"]["pwr"])
        if temp(x) is not None: tc.append(temp(x))
    except Exception:
        pass
    time.sleep(15)
say(f"consumo estimado con blanco 100 %: {max(pw) if pw else '?'} mA (límite {led['maxpwr']} mA)")
if tc:
    say(f"temperatura del chip: {tc[0]} → {tc[-1]} °C (máx {max(tc)} °C)")
    check("Chip por debajo de 70 °C", max(tc) < 70, f"({max(tc)} °C)")
check("El límite de corriente actúa", bool(pw) and max(pw) <= led["maxpwr"] + 10, f"({max(pw) if pw else '?'} mA)")
say("TOCAR AHORA: chip de la placa y los dos LEDs (5 s cada uno)")

# ——— 4. Resistencia ———
say(f"=== 4. Resistencia: {a.resistencia:g} min con efecto Vela ===")
post({"bri": 80, "seg": [{"fx": eff.index("Candle") if "Candle" in eff else 0, "col": [[255, 100, 0]]}]})
heap, rssi, lat4, err4, reinicios = [], [], [], 0, 0
prev_up, prev_t = None, None
fin = time.time() + a.resistencia * 60
while time.time() < fin:
    t = time.time()
    try:
        x = info(); lat4.append((time.time() - t) * 1000)
        heap.append(x["freeheap"]); rssi.append(x["wifi"]["rssi"])
        if temp(x) is not None: tc.append(temp(x))
        if prev_up is not None and x["uptime"] < prev_up + (t - prev_t) - 10:
            reinicios += 1; say(f"FALLA reinicio detectado (encendida hace {x['uptime']} s)")
        prev_up, prev_t = x["uptime"], t
    except Exception:
        err4 += 1; say("sin respuesta")
    time.sleep(15)
say(f"memoria libre mín {min(heap)} B · máx {max(heap)} B · WiFi {min(rssi)}..{max(rssi)} dBm · "
    f"respuesta mediana {statistics.median(lat4):.0f} ms · sin respuesta {err4}/{len(heap) + err4}")
if tc: say(f"temperatura del chip máx {max(tc)} °C")
check("Sin reinicios", reinicios == 0, f"({reinicios})")
check("Responde siempre (≤5 % sin respuesta)", err4 <= max(1, (len(heap) + err4) * .05), f"({err4})")
check("Sin fuga de memoria (caída < 10 KB)", heap[0] - heap[-1] < 10240, f"({heap[0]} → {heap[-1]} B)")

post({"ps": 1})
say("Fin. Pieza en la escena 1 (Ámbar).")

# ——— Reporte ———
d = Path(__file__).parent / "reportes"; d.mkdir(exist_ok=True)
f = d / f"prueba_{i0['name'].replace(' ', '-').lower()}_{datetime.now():%Y%m%d-%H%M}.md"
f.write_text(
    f"# Prueba total · {i0['name']}\n\n"
    f"**Resultado: {'✅ APROBADA' if not fallas else '❌ CON FALLAS'}** · "
    f"{len(fallas)} fallas · {len(avisos)} avisos\n\n"
    + ("## Fallas\n" + "\n".join(f"- {x}" for x in fallas) + "\n\n" if fallas else "")
    + ("## Avisos\n" + "\n".join(f"- {x}" for x in avisos) + "\n\n" if avisos else "")
    + "## Registro\n```\n" + "\n".join(log) + "\n```\n", encoding="utf-8")
say(f"Reporte: {f}")
sys.exit(1 if fallas else 0)
