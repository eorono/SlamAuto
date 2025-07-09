from flask import Flask, request, jsonify, render_template_string, send_file
import os
import json
from datetime import datetime

# --- Inicialización de la Aplicación ---
app = Flask(__name__)

# --- Configuración ---
DATA_LOG_FILE = 'sensor_data_OperarioHist.txt'
JSON_STATUS_FILE = 'sensor_status.json'
OPERARIOS_INFO = {
    "1001": {"nombre": "Operario Principal"}
}

# --- Variables Globales de Estado ---
current_car_status = {}
active_connection = {}

# --- Funciones de Utilidad (Helpers) ---
def format_seconds_to_hms(seconds_total: float) -> str:
    """Convierte un total de segundos a un formato de string HH:MM:SS."""
    if not isinstance(seconds_total, (int, float)) or seconds_total < 0:
        return "00:00:00"
    
    seconds_total = round(seconds_total)
    hours, remainder = divmod(seconds_total, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"

# --- Funciones de Lectura y Escritura ---
def load_status_from_file():
    """Carga el último estado conocido desde el archivo JSON al iniciar."""
    global current_car_status
    if os.path.exists(JSON_STATUS_FILE):
        try:
            with open(JSON_STATUS_FILE, 'r') as f:
                current_car_status = json.load(f)
                print(f"Estado cargado correctamente desde '{JSON_STATUS_FILE}'.")
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error al leer el archivo de estado: {e}. Se iniciará con un estado vacío.")
            current_car_status = {}
    else:
        print(f"Archivo de estado no encontrado. Se iniciará con un estado vacío.")
        current_car_status = {}

def save_status_to_file():
    """Guarda el diccionario de estado actual en el archivo JSON."""
    try:
        with open(JSON_STATUS_FILE, 'w') as f:
            json.dump(current_car_status, f, indent=4)
    except IOError as e:
        print(f"Error al guardar el estado en '{JSON_STATUS_FILE}': {e}")

def append_to_log(log_entry: str):
    """Añade una nueva línea al archivo de historial de texto."""
    try:
        with open(DATA_LOG_FILE, 'a') as f:
            f.write(log_entry + '\n')
    except IOError as e:
        print(f"Error al escribir en el log '{DATA_LOG_FILE}': {e}")

# --- Endpoints de la API ---
@app.route('/api/data', methods=['POST'])
def receive_sensor_data():
    """Endpoint principal para recibir datos de los sensores."""
    global current_car_status, active_connection

    data = request.get_json()
    print(f"--- DATO RECIBIDO --- : {data}")

    if not (data and 'tag' in data and 'distance' in data):
        return jsonify({"message": "Petición inválida, faltan 'tag' o 'distance'."}), 400
    
    try:
        tag = str(data['tag'])
        distance = int(data['distance'])
    except (ValueError, TypeError):
        return jsonify({"message": "El formato de 'tag' o 'distance' es incorrecto."}), 400

    timestamp = datetime.now()
    timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")

    if tag not in current_car_status:
        current_car_status[tag] = {
            "tag": tag,
            "operario_historial": {
                "1001": {"tiempo_total_segundos": 0.0}
            }
        }
    current_car_status[tag]['distance'] = distance
    current_car_status[tag]['timestamp'] = timestamp_str

    closest_car_tag = None
    min_distance = float('inf')
    for car_tag, car_data in current_car_status.items():
        car_dist = car_data.get('distance', -1)
        if car_dist != -1 and car_dist < min_distance:
            min_distance = car_dist
            closest_car_tag = car_tag

    current_active_car = active_connection.get('coche')
    
    if closest_car_tag and closest_car_tag != current_active_car:
        if current_active_car and current_active_car in current_car_status:
            start_time = active_connection['start_time']
            duration_seconds = (timestamp - start_time).total_seconds()
            historial = current_car_status[current_active_car]['operario_historial']['1001']
            historial['tiempo_total_segundos'] += duration_seconds
            log_msg = (f"{timestamp_str} - OPERARIO DESCONECTADO de {current_active_car}. "
                       f"Sesión: {format_seconds_to_hms(duration_seconds)}. "
                       f"Total en coche: {format_seconds_to_hms(historial['tiempo_total_segundos'])}")
            append_to_log(log_msg)

        active_connection = {'coche': closest_car_tag, 'start_time': timestamp}
        log_msg = (f"{timestamp_str} - OPERARIO CONECTADO a {closest_car_tag} "
                   f"(Distancia: {min_distance} cm)")
        append_to_log(log_msg)

    elif not closest_car_tag and current_active_car:
        start_time = active_connection['start_time']
        duration_seconds = (timestamp - start_time).total_seconds()
        historial = current_car_status[current_active_car]['operario_historial']['1001']
        historial['tiempo_total_segundos'] += duration_seconds
        log_msg = (f"{timestamp_str} - OPERARIO DESCONECTADO (sin coches cerca). "
                   f"Sesión: {format_seconds_to_hms(duration_seconds)}. "
                   f"Total en coche: {format_seconds_to_hms(historial['tiempo_total_segundos'])}")
        append_to_log(log_msg)
        active_connection = {}

    save_status_to_file()
    return jsonify({"message": "Datos recibidos"}), 200

@app.route('/api/status', methods=['GET'])
def get_current_status_json():
    # --- LÍNEA AÑADIDA ---
    print(f"--- PÁGINA WEB SOLICITADA STATUS --- {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    # ----------------------
    """Devuelve el estado actual completo en formato JSON."""
    return jsonify(current_car_status)

@app.route('/download/log')
def download_log_file():
    """Permite descargar el archivo de historial de texto."""
    if os.path.exists(DATA_LOG_FILE):
        return send_file(DATA_LOG_FILE, as_attachment=True)
    return "Archivo de log no encontrado.", 404

# --- Interfaz Web (UI) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Estado de Operario</title>
    <meta http-equiv="refresh" content="5">
    <style>
        body { font-family: sans-serif; background-color: #f4f4f9; color: #333; }
        h1, h2 { text-align: center; color: #444; }
        table { border-collapse: collapse; width: 90%; margin: 20px auto; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: center; }
        th { background-color: #007bff; color: white; }
        tr:nth-child(even) { background-color: #f2f2f2; }
        .timestamp { font-size: 0.8em; color: grey; text-align: center; margin-top: 10px; }
        .links { text-align:center; margin: 20px; }
        .links a { margin: 0 15px; text-decoration: none; color: #007bff; font-weight: bold; }
    </style>
</head>
<body>
    <h1>Estado de Coches y Operario</h1>
    
    <h2>Operario: {{ operario['nombre'] }}</h2>
    <table>
        <tr>
            <th>Coche Actual</th>
            <th>Distancia (cm)</th>
            <th>Tiempo Sesión Actual</th>
            <th>Tiempo Total en este Coche</th>
        </tr>
        <tr>
            <td>{{ operario['coche_tag'] or 'Ninguno' }}</td>
            <td>{{ operario['distancia'] if operario['distancia'] is not none else 'N/A' }}</td>
            <td>{{ format_time(operario['tiempo_sesion_actual']) }}</td>
            <td>{{ format_time(operario['tiempo_total_acumulado']) }}</td>
        </tr>
    </table>

    <p class="timestamp">Última actualización: {{ now }}</p>
    <div class="links">
        <a href="/api/status" target="_blank">Ver JSON Actual</a> | 
        <a href="/download/log">Descargar Historial TXT</a>
    </div>
</body>
</html>
"""

@app.route('/')
def show_data_ui():
    """Muestra la página web con el estado actual del operario."""
    # --- LÍNEA AÑADIDA ---
    print(f"--- PÁGINA WEB SOLICITADA --- {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    # ----------------------
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    operario_data = {
        "nombre": OPERARIOS_INFO['1001']['nombre'],
        "coche_tag": None,
        "distancia": None,
        "tiempo_sesion_actual": 0.0,
        "tiempo_total_acumulado": 0.0,
    }

    if 'coche' in active_connection:
        coche_actual_tag = active_connection['coche']
        operario_data['coche_tag'] = coche_actual_tag
        
        duracion_sesion = datetime.now() - active_connection['start_time']
        operario_data['tiempo_sesion_actual'] = duracion_sesion.total_seconds()
        
        if coche_actual_tag in current_car_status:
            coche_info = current_car_status[coche_actual_tag]
            operario_data['distancia'] = coche_info.get('distance')
            
            historial_coche = coche_info.get('operario_historial', {}).get('1001', {})
            operario_data['tiempo_total_acumulado'] = historial_coche.get('tiempo_total_segundos', 0.0)

    return render_template_string(
        HTML_TEMPLATE, 
        operario=operario_data,
        now=now_str,
        format_time=format_seconds_to_hms
    )

# --- Arranque de la Aplicación ---
if __name__ == '__main__':
    try:
        print("Iniciando aplicación y cargando estado...")
        load_status_from_file()
        print("Carga inicial finalizada. La aplicación está lista.")
    except Exception as e:
        print(f"!!!!!!!! ERROR CRÍTICO DURANTE LA CARGA INICIAL !!!!!!!!")
        print(f"Error: {e}")
        print("La aplicación continuará, pero podría no funcionar como se espera.")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")