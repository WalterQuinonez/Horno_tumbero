#include "max6675.h"

int thermoDO = 4;
int thermoCS = 5;
int thermoCLK = 6;
MAX6675 thermocouple(thermoCLK, thermoCS, thermoDO);

const int pinSalida = 10;

const int VENTANA = 20;
const int UMBRAL_INVALIDOS = 10;

bool historial[VENTANA];
int indiceHistorial = 0;
bool bufferLleno = false;

bool falloArduino = false;

void setup() {
  Serial.begin(9600);
  delay(500);

  pinMode(pinSalida, OUTPUT);
  digitalWrite(pinSalida, HIGH);
}

int contarInvalidos() {
  int total = bufferLleno ? VENTANA : indiceHistorial;
  int cont = 0;

  for (int i = 0; i < total; i++) {
    if (!historial[i]) cont++;
  }
  return cont;
}

void loop() {
  if (Serial.available()) {
    String comando = Serial.readStringUntil('\n');
    comando.trim();

    if (comando == "GET") {

      if (falloArduino) {
        Serial.println("ARDUINO FALLANDO");
        return;
      }

      double c = thermocouple.readCelsius();

      bool valido = !isnan(c);

      // Guardar resultado en buffer circular
      historial[indiceHistorial] = valido;
      indiceHistorial++;

      if (indiceHistorial >= VENTANA) {
        indiceHistorial = 0;
        bufferLleno = true;
      }

      // Contar inválidos en ventana
      int invalidos = contarInvalidos();

      if (valido) {
        Serial.println(c);
      } else {
        Serial.println("DATO INVALIDO");
      }

      // Evaluar fallo
      if ((bufferLleno || indiceHistorial >= UMBRAL_INVALIDOS) && invalidos >= UMBRAL_INVALIDOS) {
        falloArduino = true;
        digitalWrite(pinSalida, LOW);
        Serial.println("ARDUINO FALLANDO");
      }
    }

    else if (comando == "AbrirRele") {
      digitalWrite(pinSalida, LOW);
      Serial.println("RELE ABIERTO");
    }

    else if (comando == "CerrarRele") {
      if (!falloArduino) {
        digitalWrite(pinSalida, HIGH);
        Serial.println("RELE CERRADO");
      } else {
        Serial.println("RELE BLOQUEADO POR FALLO");
      }
    }
  }
}
