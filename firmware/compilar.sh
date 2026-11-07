#!/bin/sh
# Compila el firmware del cuervo sobre WLED v16.0.1 sin modificar el código de WLED.
# Uso: sh firmware/compilar.sh [carpeta-de-wled]   (por defecto ../wled-cuervo junto al repo)
set -e
AQUI=$(cd "$(dirname "$0")" && pwd)
WLED=${1:-"$AQUI/../../wled-cuervo"}
[ -d "$WLED/.git" ] || git clone --depth 1 -b v16.0.1 https://github.com/wled/WLED.git "$WLED"
rm -rf "$WLED/usermods/Cuervo_Estado"
cp -r "$AQUI/usermods/Cuervo_Estado" "$WLED/usermods/"
cp "$AQUI/platformio_override.ini" "$WLED/"
cd "$WLED" && python -m platformio run -e cuervo
echo "Binario: $WLED/.pio/build/cuervo/firmware.bin"
