/*
 * Título: Repetidor / Baliza BLE Pasiva (Sin UWB)
 * Autor: Asistente de IA
 * Fecha: 2024-07-12
 * Descripción:
 * Este ESP32 actúa como una baliza (beacon) de Bluetooth Low Energy (BLE).
 * No se conecta a nada. Su única función es anunciar su presencia
 * constantemente para que el Ancla pueda detectar su señal y medir su RSSI.
 */

#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEServer.h>

// Nombre que el Ancla buscará
#define DEVICE_NAME "REPETIDOR_BLE"

void setup() {
  Serial.begin(115200);
  Serial.println("--- Iniciando Repetidor / Baliza BLE ---");

  // Crear el dispositivo BLE
  BLEDevice::init(DEVICE_NAME);

  // Crear el servidor BLE (aunque no ofrecerá servicios, es parte del setup)
  BLEServer *pServer = BLEDevice::createServer();
  
  // Iniciar la publicidad (advertising)
  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID("0000180f-0000-1000-8000-00805f9b34fb"); // UUID de Batería, un ejemplo común
  pAdvertising->setScanResponse(true);
  pAdvertising->setMinPreferred(0x06);  // Ayuda con la compatibilidad en iOS
  pAdvertising->setMinPreferred(0x12);
  BLEDevice::startAdvertising();
  
  Serial.println("Baliza BLE iniciada. Anunciando como 'REPETIDOR_BLE'");
  Serial.println("El Ancla ahora puede detectarme.");
}

void loop() {
  // No es necesario hacer nada en el bucle.
  // La publicidad BLE ocurre en segundo plano.
  delay(2000);
}
