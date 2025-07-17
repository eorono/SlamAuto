from flask import Flask, request, jsonify
import os
from datetime import datetime

# --- Inicialización de la Aplicación ---
app = Flask(__name__)

# --- Almacenamiento en Memoria ---
# Usamos un diccionario para guardar el estado. Es mucho más rápido
# que leer y escribir archivos en cada petición, lo que evita los timeouts.
# Nota: Los datos se reiniciarán si el servidor se reinicia.
current_status = {}

# --- Endpoint Principal para el ESP32 ---
@app.route('/api/data', methods=['POST'])
def receive_data():
    """
    Este endpoint está optimizado para ser muy rápido.
    Recibe los datos, los guarda en memoria y responde inmediatamente.
    """
    try:
        # 1. Obtener los datos JSON de la petición del ESP32
        data = request.get_json()
        
        # Imprime en los logs de Railway para que veas que llegó
        print(f"--- DATO RECIBIDO --- : {data}")

        # 2. Validar que los datos necesarios están presentes
        if not (data and 'tag' in data and 'distance' in data):
            return jsonify({"error": "Petición inválida, faltan 'tag' o 'distance'."}), 400
        
        tag = str(data['tag'])
        distance = int(data['distance'])
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 3. Actualizar el estado en el diccionario de memoria
        current_status[tag] = {
            "distance": distance,
            "last_update": timestamp
        }
        
        # 4. Enviar una respuesta de éxito de inmediato.
        return jsonify({"message": "Datos recibidos con éxito"}), 200

    except Exception as e:
        # Si algo falla, imprime el error y envía una respuesta de error
        print(f"!!! ERROR EN /api/data: {e}")
        return jsonify({"message": "Error interno en el servidor", "error": str(e)}), 500

# --- Endpoint Secundario para Ver el Estado ---
@app.route('/api/status', methods=['GET'])
def get_status():
    """
    Esta ruta te permite ver el último estado de todos los tags
    abriendo la URL en un navegador.
    """
    return jsonify(current_status)

# --- Punto de Entrada para Railway ---
if __name__ == '__main__':
    # Railway usa la variable de entorno PORT para asignar el puerto.
    # El host '0.0.0.0' es necesario para que sea accesible desde el exterior.
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
