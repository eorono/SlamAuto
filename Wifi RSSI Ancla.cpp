/*
 * Título: Ancla BLE RSSI con reporte a API (Sin UWB)
 * Autor: Asistente de IA
 * Fecha: 2024-07-12
 * Descripción:
 * Este ESP32 actúa como un Ancla. Utiliza Bluetooth (BLE) para escanear
 * y encontrar un "Repetidor". Mide la intensidad de la señal (RSSI) para
 * estimar la distancia. Luego, usa su conexión WiFi para enviar
 * el resultado a una API web.
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEScan.h>
#include <BLEAdvertisedDevice.h>

// --- Configuración de Usuario ---
const char* ssid_wifi = "iPhone (6)";       // << TU RED WIFI PARA INTERNET
const char* password_wifi = "12345678"; // << TU CONTRASEÑA WIFI
const char* apiUrl = "https://app2-production-187a.up.railway.app/api/data"; // << TU URL DE LA API
const char* targetDeviceName = "REPETIDOR_BLE"; // << Nombre del dispositivo BLE a buscar

BLEScan* pBLEScan;
bool deviceFound = false;

// Prototipo de la función
void sendToAPI(const char* tag, int distance);

// Clase para manejar los resultados del escaneo
class MyAdvertisedDeviceCallbacks: public BLEAdvertisedDeviceCallbacks {
    void onResult(BLEAdvertisedDevice advertisedDevice) {
        // Comprobar si el dispositivo encontrado es nuestro objetivo
        if (advertisedDevice.haveName() && advertisedDevice.getName() == targetDeviceName) {
            int rssi = advertisedDevice.getRSSI();
            Serial.print("¡Repetidor encontrado! Nombre: ");
            Serial.print(advertisedDevice.getName().c_str());
            Serial.print(", RSSI: ");
            Serial.println(rssi);

            // --- Estimación de Distancia desde RSSI de BLE ---
            // A = Potencia de la señal de referencia en dBm a 1 metro. (-59 a -69 es típico para BLE)
            // n = Exponente de pérdida de ruta (2.0 a 4.0)
            double A = -65;
            double n = 2.5;
            double distance_m = pow(10, (A - rssi) / (10 * n));
            int distance_cm = distance_m * 100;

            Serial.print("Distancia estimada: ");
            Serial.print(distance_m);
            Serial.println(" m");

            // Enviar la distancia a la API
            sendToAPI(targetDeviceName, distance_cm);
            
            deviceFound = true; // Marcar que lo encontramos
            pBLEScan->stop(); // Detener el escaneo actual una vez que encontramos el dispositivo
        }
    }
};

void setup() {
  Serial.begin(115200);
  Serial.println("\n--- Iniciando Ancla BLE con Reporte a API ---");

  // 1. Conectar a WiFi para tener acceso a internet
  Serial.print("Conectando a WiFi: ");
  Serial.println(ssid_wifi);
  WiFi.begin(ssid_wifi, password_wifi);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConexión WiFi exitosa!");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());

  // 2. Iniciar el escáner BLE
  Serial.println("Iniciando escáner BLE...");
  BLEDevice::init("");
  pBLEScan = BLEDevice::getScan(); // Crear el objeto de escaneo
  pBLEScan->setAdvertisedDeviceCallbacks(new MyAdvertisedDeviceCallbacks());
  pBLEScan->setActiveScan(true); // Escaneo activo para obtener más datos
  pBLEScan->setInterval(100);
  pBLEScan->setWindow(99);  // Escanear casi continuamente
}

void loop() {
  Serial.println("Iniciando nuevo escaneo BLE...");
  deviceFound = false;
  // El escaneo se detendrá por el callback o después de 5 segundos
  pBLEScan->start(5, false); 

  if (!deviceFound) {
    Serial.println("No se encontró el repetidor en este ciclo.");
  }
  
  Serial.println("Ciclo de escaneo terminado. Esperando 5 segundos para el siguiente.");
  delay(5000); // Esperar 5 segundos antes de volver a escanear
}

// Función para enviar los datos a la API
void sendToAPI(const char* tag, int distance) {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(apiUrl);
    http.addHeader("Content-Type", "application/json");

    String jsonData = "{\"tag\":\"" + String(tag) + "\", \"distance\":" + String(distance) + "}";

    Serial.println("Enviando a API: " + jsonData);
    int httpCode = http.POST(jsonData);

    if (httpCode > 0) {
      String payload = http.getString();
      Serial.println("Código de respuesta API: " + String(httpCode));
      Serial.println("Cuerpo de respuesta API: " + payload);
    } else {
      Serial.println("Error al enviar a la API. Código: " + String(httpCode));
    }
    http.end();
  } else {
    Serial.println("No se puede enviar a la API, WiFi desconectado.");
  }
}
