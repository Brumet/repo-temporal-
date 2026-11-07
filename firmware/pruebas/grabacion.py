"""
Secuencia para grabar en video: los ojos recorren todo lo que saben hacer, con pausas
pensadas para cámara. Imprime cada escena con su hora para ubicarla al editar.

Uso:  python grabacion.py 192.168.40.35
Duración: unos 2 min 30 s. Termina en Ámbar.
"""
import json, sys, time, urllib.request
from datetime import datetime

H = f"http://{sys.argv[1]}/json/state"
inicio = time.time()


def post(o):
    r = urllib.request.Request(H, data=json.dumps(o).encode(), headers={"Content-Type": "application/json"})
    urllib.request.urlopen(r, timeout=6).read()


def escena(nombre, orden, seg):
    print(f"{time.time() - inicio:6.1f} s  {nombre}", flush=True)
    post(orden); time.sleep(seg)


def parpadeos(col, n=3):
    for _ in range(n):
        post({"on": True, "bri": 160, "transition": 0, "seg": [{"fx": 0, "col": [col]}]}); time.sleep(0.35)
        post({"on": False, "transition": 0}); time.sleep(0.35)


fx = lambda n, col, sx=128, ix=128, bri=90: {"on": True, "bri": bri, "transition": 7,
                                              "seg": [{"fx": n, "sx": sx, "ix": ix, "col": [col, [0, 0, 0]]}]}
print(f"Grabación iniciada {datetime.now():%H:%M:%S}", flush=True)

escena("Oscuridad", {"on": False, "transition": 0}, 4)
escena("Despierta: Ámbar", {"on": True, "bri": 50, "transition": 30, "seg": [{"fx": 0, "col": [[255, 100, 0]]}]}, 6)
escena("Brillo sube", {"bri": 200, "transition": 25}, 4)
escena("Brillo baja", {"bri": 50, "transition": 25}, 4)
for n, c in (("Rojo", [255, 0, 0]), ("Verde", [0, 255, 0]), ("Azul", [0, 0, 255]), ("Blanco", [255, 255, 255])):
    escena(f"Color {n}", {"bri": 120, "transition": 7, "seg": [{"fx": 0, "col": [c]}]}, 4)
escena("Escena Vela", {"ps": 2}, 6)
escena("Escena Sangre", {"ps": 3}, 5)
escena("Escena Espectro", {"ps": 4}, 5)
escena("Efecto Respirar", fx(2, [140, 40, 255], sx=90), 6)
escena("Efecto Fuego", fx(45, [255, 60, 0], sx=140, ix=180), 6)
escena("Efecto Latido", fx(100, [200, 0, 0], sx=120), 6)
escena("Efecto Arcoíris", fx(9, [255, 0, 0], sx=60), 6)

print(f"{time.time() - inicio:6.1f} s  — Avisos de configuración —", flush=True)
escena("Esperando configuración: azul respirando", fx(2, [0, 70, 255], sx=40, bri=140), 9)
escena("Celular conectado: azul fijo", {"on": True, "bri": 120, "transition": 0, "seg": [{"fx": 0, "col": [[0, 70, 255]]}]}, 5)
escena("Conectándose: destellos blancos", fx(1, [255, 255, 255], sx=230, ix=60, bri=120), 5)
print(f"{time.time() - inicio:6.1f} s  Clave equivocada: 3 parpadeos rojos", flush=True); parpadeos([255, 0, 0])
escena("Vuelve a esperar: azul respirando", fx(2, [0, 70, 255], sx=40, bri=140), 5)
escena("Reintento: destellos blancos", fx(1, [255, 255, 255], sx=230, ix=60, bri=120), 4)
print(f"{time.time() - inicio:6.1f} s  ¡Conectado!: 3 parpadeos verdes", flush=True); parpadeos([0, 255, 40])
escena("Su mirada de siempre: Ámbar", {"on": True, "ps": 1}, 6)
print(f"{time.time() - inicio:6.1f} s  Fin", flush=True)
