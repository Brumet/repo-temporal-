/*
 * Cuervo_Estado — los ojos del cuervo avisan en qué paso de la configuración va la pieza.
 *
 *   Sin WiFi configurada (recién sacado de la caja) ....... azul respirando
 *   Un celular se conectó a la red del cuervo ............. azul fijo
 *   Intentando conectarse a la WiFi de la casa ............ destellos blancos
 *   No se pudo conectar (clave o red equivocada) .......... 3 parpadeos rojos, vuelve a azul
 *   ¡Conectado! ........................................... 3 parpadeos verdes, sigue la escena normal
 *
 * En uso normal (la pieza ya se conectó alguna vez) no muestra nada si la WiFi de la casa
 * se cae: solo vuelve a avisar si alguien se conecta a la red del cuervo para reconfigurarlo.
 *
 * Brumet · Serie Cero · Obra derivada de WLED, licencia EUPL v1.2.
 */
#include "wled.h"

class CuervoEstado : public Usermod {
  private:
    enum Aviso : uint8_t { NADA, AZUL_RESPIRA, AZUL_FIJO, BLANCO_DESTELLO, ROJO_X3, VERDE_X3 };

    bool listo = false;            // ya se conectó alguna vez con la WiFi actual (se guarda en cfg.json)
    bool reconfigurando = false;   // en uso normal, alguien entró a la red del cuervo
    bool estabaConectando = false;
    bool estabaConectado = false;
    Aviso aviso = NADA;
    Aviso avisoFinal = NADA;       // aviso que queda después de los 3 parpadeos
    unsigned long inicioAviso = 0;
    unsigned long ultimoCuadro = 0;

    static const char _name[];
    static const char _listo[];

    static uint8_t clientesEnRed() {
      if (!apActive) return 0;
      wifi_sta_list_t lista;
      return esp_wifi_ap_get_sta_list(&lista) == ESP_OK ? lista.num : 0;
    }

    void empezar(Aviso a, Aviso despues = NADA) {
      if (a == aviso) return;
      aviso = a; avisoFinal = despues; inicioAviso = millis();
      strip.trigger();
    }

    void guardarListo(bool v) {
      if (listo == v) return;
      listo = v;
      configNeedsWrite = true;
    }

  public:
    void setup() override {}

    void loop() override {
      const unsigned long ahora = millis();
      const bool configurada = WLED_WIFI_CONFIGURED;
      const bool conectada = Network.isConnected();
      const uint8_t clientes = clientesEnRed();

      if (!configurada) guardarListo(false);   // WiFi borrada antes de empacar: modo configuración
      const bool modoConfig = !listo || !configurada;

      // Destellos blancos solo mientras dura un intento real (WLED abre su red a los 12 s)
      const bool conectando = configurada && !conectada && lastReconnectAttempt > 0
                              && ahora - lastReconnectAttempt < 12000 && clientes == 0;

      if (conectada && !estabaConectado) {                 // recién conectada
        if (modoConfig || reconfigurando) empezar(VERDE_X3);
        guardarListo(true);
        reconfigurando = false;
      }
      estabaConectado = conectada;

      const bool parpadeando = (aviso == ROJO_X3 || aviso == VERDE_X3) && ahora - inicioAviso < 2100;
      if (!parpadeando) {
        if (aviso == ROJO_X3 || aviso == VERDE_X3) { aviso = avisoFinal; avisoFinal = NADA; }
        if (conectada) {
          aviso = NADA;
        } else if (modoConfig) {
          if (estabaConectando && !conectando && configurada) empezar(ROJO_X3, AZUL_RESPIRA);
          else if (conectando)   empezar(BLANCO_DESTELLO);
          else if (clientes > 0) empezar(AZUL_FIJO);
          else                   empezar(AZUL_RESPIRA);
        } else if (clientes > 0) {                          // reconfiguración en uso normal
          reconfigurando = true;
          empezar(AZUL_FIJO);
        } else if (!reconfigurando) {
          aviso = NADA;                                     // se cayó el internet: no molestar
        }
      }
      estabaConectando = conectando;

      if (aviso != NADA && ahora - ultimoCuadro > 25) { ultimoCuadro = ahora; strip.trigger(); }
    }

    void handleOverlayDraw() override {
      if (aviso == NADA) return;
      const unsigned long t = millis() - inicioAviso;
      uint32_t c = 0;
      switch (aviso) {
        case AZUL_RESPIRA: {                                   // ciclo de 3 s
          const uint8_t v = 25 + (uint8_t)(230.0f * (0.5f - 0.5f * cosf(t * 2.0f * PI / 3000.0f)));
          c = RGBW32(0, (70 * v) / 255, v, 0); break;
        }
        case AZUL_FIJO:       c = RGBW32(0, 70, 255, 0); break;
        case BLANCO_DESTELLO: c = (t % 320) < 110 ? RGBW32(255, 255, 255, 0) : 0; break;
        case ROJO_X3:         c = (t % 700) < 350 ? RGBW32(255, 0, 0, 0) : 0; break;
        case VERDE_X3:        c = (t % 700) < 350 ? RGBW32(0, 255, 40, 0) : 0; break;
        default: break;
      }
      strip.fill(c);
    }

    void addToJsonInfo(JsonObject& root) override {
      static const char* const nombres[] = {"normal", "esperando configuración", "celular conectado",
                                            "conectándose", "no se pudo conectar", "conectado"};
      JsonObject user = root["u"];
      if (user.isNull()) user = root.createNestedObject("u");
      JsonArray a = user.createNestedArray(F("Ojos"));
      a.add(nombres[aviso]);
    }

    void addToConfig(JsonObject& root) override {
      JsonObject top = root.createNestedObject(FPSTR(_name));
      top[FPSTR(_listo)] = listo;
    }

    bool readFromConfig(JsonObject& root) override {
      // Un cambio de ajustes por la red manda solo parte de la configuración: si no trae
      // nuestro bloque, conservar "listo" tal cual (si no, la pieza volvería a modo configuración)
      JsonObject top = root[FPSTR(_name)];
      if (top.isNull()) return false;
      return getJsonValue(top[FPSTR(_listo)], listo);
    }
};

const char CuervoEstado::_name[] PROGMEM = "CuervoEstado";
const char CuervoEstado::_listo[] PROGMEM = "listo";

static CuervoEstado cuervo_estado;
REGISTER_USERMOD(cuervo_estado);
