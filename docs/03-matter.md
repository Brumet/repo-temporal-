# Matter

## Qué resuelve

Matter es un estándar abierto de domótica. Un dispositivo Matter es reconocido de
forma **nativa y local** por:

- Google Home / Google Assistant
- Amazon Alexa
- Apple Home / Siri
- Samsung SmartThings

Sin nube propietaria, sin cuenta de fabricante, sin suscripción, sin acuerdo
comercial con cada plataforma.

### Por qué esto importa comercialmente

Magic Home funciona con Google porque Zengge firmó un acuerdo con Google y paga
servidores. Es una relación entre empresas, no una función técnica activable.

Si esos servidores se apagan, todos sus productos pierden el control por voz.

Matter elimina esa dependencia: el control es local y permanente. En una pieza de
colección que se vende como objeto duradero, eso es un argumento de venta real,
no un detalle técnico.

## El obstáculo: certificación

Matter tiene control de acceso por **Vendor ID (VID)** y **Product ID (PID)**,
asignados por la Connectivity Standards Alliance (CSA).

### Desarrollo
Espressif provee credenciales de prueba (VID `0xFFF1` y PIDs de test). Funcionan
para emparejar con los cuatro ecosistemas.

**Costo:** cero.
**Contrapartida:** al emparejar, la app muestra una advertencia de *dispositivo
no certificado*. El usuario puede continuar, pero ve el aviso.

### Comercial
Membresía CSA (nivel Adopter) más certificación por producto. Son miles de
dólares anuales.

> ⚠️ **Verificar los costos vigentes directamente en csa-iot.org antes de
> presupuestar.** Las cifras que circulan en foros están desactualizadas y
> los niveles de membresía cambian.

### Decisión práctica para la Serie Cero
Lanzar con credenciales de prueba. El aviso de "no certificado" es aceptable en
una serie numerada de coleccionista, y puede incluso explicarse en la tarjeta de
la caja como parte del carácter artesanal del objeto.

Evaluar certificación solo si el volumen lo justifica.

## Restricción de flash

| | ESP32-C3 4 MB | ESP32-C3 8 MB |
|---|---|---|
| Aplicación Matter (~1,5-1,8 MB) | ✅ | ✅ |
| Dos particiones OTA | ⚠️ muy justo | ✅ |
| Datos de fábrica + NVS | ✅ | ✅ |

**Comprobar el flash real de las placas compradas:**
```bash
esptool.py --port /dev/ttyACM0 flash_id
```

Si son de 4 MB, sopesar antes del próximo pedido de 20 unidades:
- ¿Es aceptable vender sin capacidad de actualización remota?
- ¿Cuánto cuesta un módulo C3 de 8 MB frente a los 12.354 COP actuales?

**Decidir esto antes de comprar en volumen**, no después.

## Emparejamiento

Un dispositivo Matter se empareja escaneando un **código QR de comisionamiento**
que codifica VID, PID, discriminador y passcode.

### Implicación de producto
Ese QR debe ir físicamente en la pieza. Dos opciones:

1. **Impreso en la base**, junto al número de serie
2. **En la tarjeta de la caja** — se puede perder

Recomendado: **ambos**. En la base para siempre, en la tarjeta para el desempaque.

### Flujo del cliente
```
1. Conecta el USB-C          → los ojos encienden en ámbar
2. Abre Google Home o Alexa  → "Agregar dispositivo"
3. Escanea el QR de la base
4. Elige en qué habitación está
5. Listo
```

Comparado con el flujo de WLED (unirse a una red WiFi temporal, abrir 4.3.2.1,
escribir credenciales) esto es **notablemente mejor**. El cliente no ve ni una
sola pantalla de configuración de red.

Ese es el argumento más fuerte a favor de Matter, por encima incluso del soporte
para Google.

## Los ojos como indicador de estado

Objetivo: que la escultura comunique su estado sin que el cliente mire el
celular.

| Estado | Ojos |
|---|---|
| Arrancando | Ámbar tenue, respirando |
| Esperando emparejamiento | Azul, respirando lento |
| Emparejando | Azul, pulso rápido |
| Conectado | Ámbar, preset guardado |
| Error de red | Rojo, doble parpadeo cada 5 s |

En esp-matter esto sale natural: hay callbacks de cambio de estado de
comisionamiento donde se dispara el color.

En Tasmota habría que lograrlo con un script Berry que consulte el estado.
**Es el paso 5 del spike** en [`02-arquitectura-firmware.md`](02-arquitectura-firmware.md).

## Referencias a consultar

- `github.com/espressif/esp-matter` — SDK y ejemplos
- `docs.espressif.com/projects/esp-matter` — documentación oficial
- `csa-iot.org` — especificación, membresía y costos vigentes
- Ejemplo base: `esp-matter/examples/light` (ya implementa un dispositivo de
  color extendido, que es exactamente la clase de dispositivo que corresponde)

## Tareas abiertas

- [ ] Verificar flash real con `esptool.py flash_id` cuando lleguen las placas
- [ ] Confirmar si existe build de Tasmota con Matter para ESP32-C3
- [ ] Verificar si Matter en Tasmota expone color RGB completo
- [ ] Consultar costos vigentes de membresía CSA en csa-iot.org
- [ ] Definir si se lanza con credenciales de prueba
- [ ] Diseñar la ubicación del QR de comisionamiento en la base
