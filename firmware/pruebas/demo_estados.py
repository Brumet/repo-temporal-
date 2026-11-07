"""
Demostración de los avisos de los ojos durante la configuración, imitados con
efectos de WLED (el firmware propio los hará solo, con estos mismos colores).

Uso:  python demo_estados.py 192.168.40.35 [--espera 60] [--vueltas 3]
Sirve también para grabar o fotografiar cada estado para el instructivo.
"""
import argparse, json, time, urllib.request
from datetime import datetime

ap = argparse.ArgumentParser()
ap.add_argument("ip"); ap.add_argument("--espera", type=int, default=0); ap.add_argument("--vueltas", type=int, default=3)
a = ap.parse_args()
H = f"http://{a.ip}/json/state"
AZUL, BLANCO, VERDE, ROJO = [0, 70, 255], [255, 255, 255], [0, 255, 40], [255, 0, 0]


def post(o):
    r = urllib.request.Request(H, data=json.dumps(o).encode(), headers={"Content-Type": "application/json"})
    urllib.request.urlopen(r, timeout=6).read()


def say(m):
    print(f"{datetime.now():%H:%M:%S}  {m}", flush=True)


def fijo(col, bri=120):
    post({"on": True, "bri": bri, "transition": 0, "seg": [{"fx": 0, "col": [col]}]})


def parpadeos(col, n=3):
    for _ in range(n):
        fijo(col, 160); time.sleep(0.35)
        post({"on": False, "transition": 0}); time.sleep(0.35)


if a.espera:
    say(f"Empieza en {a.espera} s"); time.sleep(a.espera)
for v in range(1, a.vueltas + 1):
    say(f"— Vuelta {v} de {a.vueltas} —")
    say("1. Esperando configuración: AZUL RESPIRANDO (12 s)")
    post({"on": True, "bri": 140, "transition": 0, "seg": [{"fx": 2, "sx": 40, "col": [AZUL]}]}); time.sleep(12)
    say("2. Celular conectado a la red del cuervo: AZUL FIJO (6 s)")
    fijo(AZUL); time.sleep(6)
    say("3. Conectándose a la WiFi de la casa: DESTELLOS BLANCOS (6 s)")
    post({"on": True, "bri": 120, "transition": 0, "seg": [{"fx": 1, "sx": 230, "ix": 60, "col": [BLANCO, [0, 0, 0]]}]}); time.sleep(6)
    say("4a. Clave equivocada: 3 PARPADEOS ROJOS y vuelve a azul")
    parpadeos(ROJO)
    post({"on": True, "bri": 140, "transition": 0, "seg": [{"fx": 2, "sx": 40, "col": [AZUL]}]}); time.sleep(5)
    say("3. Reintento: DESTELLOS BLANCOS (4 s)")
    post({"on": True, "bri": 120, "transition": 0, "seg": [{"fx": 1, "sx": 230, "ix": 60, "col": [BLANCO, [0, 0, 0]]}]}); time.sleep(4)
    say("4b. ¡Conectado!: 3 PARPADEOS VERDES y pasa a ÁMBAR")
    parpadeos(VERDE)
    post({"on": True, "ps": 1}); time.sleep(8)
say("Fin: Ámbar.")
