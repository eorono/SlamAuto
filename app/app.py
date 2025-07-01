from flask import Flask, request, jsonify, render_template_string, send_file
import os
import json
from datetime import datetime, timedelta

app = Flask(__name__)

# Archivos
# ADVERTENCIA: Estos archivos son locales para cada contenedor y no se comparten.
# Se recomienda usar una base de datos o un volumen persistente en Railway para producción.
data_log_file = 'sensor_data_OperarioHist.txt'
json_current_file = 'sensor_status.json'

# Estado actual de los coches
current_car_status = {}

# Información fija del operario
OPERARIOS_INFO = {
    "1001": {"nombre": "Operario Principal"}
}

# Conexiones activas de operarios
conexion_activa_principal = {}

# --- Helper Function para formatear tiempo ---
def format_seconds_to_hms(seconds_total):
    """Convierte segundos a un string HH:MM:SS."""
    if not isinstance(seconds_total, (int, float)) or seconds_total < 0:
        return "00:00:00"
    seconds_total = round(seconds_total)
    hours, remainder = divmod(seconds_total, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"

# HTML para mostrar datos en una sola tabla
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Estado de Coches y Operario</title>
    <meta http-equiv="refresh" content="5">
    <style>
        table { border-collapse: collapse; width: 90%; margin: 20px auto; }
        th, td { border: 1px solid black; padding: 8px; text-align: center; }
        th { background-color: #f2f2f2; }
        body { font-family: sans-serif; }
        h1 { text-align: center; }
        .timestamp { font-size: 0.8em; color: grey; text-align: center; margin-top: 10px;}
    </style>
</head>
<body>
    <h1>Estado de Coches y Operario</h1>
    <table>
        <tr>
            <th>Operario</th>
            <th>Tiempo Actual en Coche</th>
            <th>Distancia (cm)</th>
            <th>Tiempo Total Acumulado (Coche)</th>
        </tr>
        <tr>
            <td>{{ operario['nombre'] }}</td>
            <td>{{ format_time(operario['tiempo_actual_en_coche_segundos']) }}</td>
            <td>
                {% if operario['distancia'] != 'N/A' %}
                    {{ operario['distancia'] }} ({{ operario['coche_tag'] }})
                {% else %}
                    N/A
                {% endif %}
            </td>
            <td>{{ format_time(operario['tiempo_total_acumulado_segundos']) }}</td>
        </tr>
    </table>
    <p class="timestamp">Última actualización de la página: {{ now }}</p>
    <p style="text-align:center;">
        <a href="/api/status">Ver JSON Actual</a> | <a href="/download/log">Descargar Historial TXT</a>
    </p>
</body>
</html>
"""

# Cargar y guardar funciones
def load_current_status():
    global current_car_status, conexion_activa_principal
    if os.path.exists(json_current_file):
        try:
            with open(json_current_file, 'r') as f:
                loaded_data = json.load(f)
                for car_data in loaded_data.values():
                    car_data.setdefault('operario_historial', {})
                    if '1001' not in car_data['operario_historial']:
                        car_data['operario_historial']['1001'] = {"tiempo_total_segundos": 0.0}
                current_car_status = loaded_data
                print("Estado actual cargado desde", json_current_file)
        except (json.JSONDecodeError, IOError, TypeError) as e:
            print(f"Error al cargar el estado actual: {e}. Empezando con estado vacío.")
            current_car_status = {}
    else:
        print(f"Archivo de estado '{json_current_file}' no encontrado. Empezando con estado vacío.")
        current_car_status = {}
    
    # Reiniciar la conexión activa al arrancar
    conexion_activa_principal = {}

def save_current_status():
    try:
        with open(json_current_file, 'w') as f:
            json.dump(current_car_status, f, indent=4)
    except IOError as e:
        print(f"Error al guardar el estado actual en {json_current_file}: {e}")

def append_to_log(log_entry):
    try:
        with open(data_log_file, 'a') as f:
            f.write(log_entry + '\n')
    except IOError as e:
        print(f"Error al escribir en el log {data_log_file}: {e}")

@app.route('/api/data', methods=['POST'])
def receive_sensor_data():
    global current_car_status, conexion_activa_principal
    data = request.get_json()
    if not (data and 'tag' in data and 'distance' in data):
        return jsonify({"message": "Datos inválidos o incompletos"}), 400

    tag = data['tag']
    try:
        distance = int(data['distance'])
    except (ValueError, TypeError):
        return jsonify({"message": "Distancia inválida"}), 400

    timestamp = datetime.now()
    timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
    
    log_entry_distance = f"{timestamp_str} - Data Received: Tag: {tag}, Distance: {distance} cm"
    append_to_log(log_entry_distance)

    if tag not in current_car_status:
        current_car_status[tag] = {
            "tag": tag, "distance": distance, "timestamp": timestamp_str,
            "operario_historial": {"1001": {"tiempo_total_segundos": 0.0}}
        }
    else:
        current_car_status[tag].update({"distance": distance, "timestamp": timestamp_str})
        current_car_status[tag].setdefault('operario_historial', {}).setdefault('1001', {"tiempo_total_segundos": 0.0})

    min_distance = float('inf')
    closest_car_tag = None
    for car_tag, car_data in current_car_status.items():
        current_car_status[car_tag]['is_closest_car'] = False
        if car_data['distance'] != -1 and car_data['distance'] < min_distance:
            min_distance = car_data['distance']
            closest_car_tag = car_tag

    current_active_car = conexion_activa_principal.get('operario_principal', {}).get('coche')

    if closest_car_tag and closest_car_tag != current_active_car:
        if current_active_car:
            start_time_prev = conexion_activa_principal['operario_principal']['start_time']
            duracion_prev = timestamp - start_time_prev
            tiempo_segundos_sesion_prev = duracion_prev.total_seconds()
            
            if current_active_car in current_car_status:
                prev_hist = current_car_status[current_active_car]['operario_historial']['1001']
                prev_hist['tiempo_total_segundos'] += tiempo_segundos_sesion_prev
                
                log_entry = f"{timestamp_str} - OPERARIO DESCONECTADO: {OPERARIOS_INFO['1001']['nombre']} de {current_active_car}. Sesión: {format_seconds_to_hms(tiempo_segundos_sesion_prev)}. Total: {format_seconds_to_hms(prev_hist['tiempo_total_segundos'])}"
                append_to_log(log_entry)

        conexion_activa_principal['operario_principal'] = {'coche': closest_car_tag, 'start_time': timestamp}
        log_entry_connect = f"{timestamp_str} - OPERARIO CONECTADO: {OPERARIOS_INFO['1001']['nombre']} a {closest_car_tag} (Distancia: {min_distance} cm)"
        append_to_log(log_entry_connect)

    elif not closest_car_tag and current_active_car:
        start_time_prev = conexion_activa_principal['operario_principal']['start_time']
        duracion_prev = timestamp - start_time_prev
        tiempo_segundos_sesion_prev = duracion_prev.total_seconds()
        
        if current_active_car in current_car_status:
            prev_hist = current_car_status[current_active_car]['operario_historial']['1001']
            prev_hist['tiempo_total_segundos'] += tiempo_segundos_sesion_prev
            
            log_entry = f"{timestamp_str} - OPERARIO DESCONECTADO (sin coches): {OPERARIOS_INFO['1001']['nombre']} de {current_active_car}. Sesión: {format_seconds_to_hms(tiempo_segundos_sesion_prev)}. Total: {format_seconds_to_hms(prev_hist['tiempo_total_segundos'])}"
            append_to_log(log_entry)
        
        del conexion_activa_principal['operario_principal']

    save_current_status()
    return jsonify({"message": "Datos recibidos"}), 200

@app.route('/api/status', methods=['GET'])
def get_current_status_json():
    return jsonify(current_car_status)

@app.route('/')
def show_data():
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    operario_data = {
        "nombre": OPERARIOS_INFO['1001']['nombre'],
        "tiempo_actual_en_coche_segundos": 0.0,
        "distancia": "N/A",
        "coche_tag": "N/A",
        "tiempo_total_acumulado_segundos": 0.0
    }
    
    if 'operario_principal' in conexion_activa_principal:
        info_conn = conexion_activa_principal['operario_principal']
        coche_actual = info_conn['coche']
        
        if coche_actual in current_car_status:
            ahora = datetime.now()
            duracion = ahora - info_conn['start_time']
            operario_data["tiempo_actual_en_coche_segundos"] = duracion.total_seconds()
            
            active_car_data = current_car_status[coche_actual]
            operario_data["distancia"] = active_car_data.get('distance', 'N/A')
            operario_data["coche_tag"] = coche_actual
            operario_data["tiempo_total_acumulado_segundos"] = active_car_data.get('operario_historial', {}).get('1001', {}).get('tiempo_total_segundos', 0.0)

    return render_template_string(HTML_TEMPLATE, 
                                  operario=operario_data,
                                  now=now_str,
                                  format_time=format_seconds_to_hms)

@app.route('/download/log')
def download_log_file():
    if os.path.exists(data_log_file):
        return send_file(data_log_file, as_attachment=True, download_name="sensor_data_OperarioHist.txt")
    return "Archivo de log no encontrado", 404

# Cargar el estado al iniciar la aplicación.
# Se envuelve en un try-except para evitar que un error aquí detenga toda la aplicación.
try:
    print("Intentando cargar el estado inicial...")
    load_current_status()
    print("El proceso de carga inicial ha finalizado.")
except Exception as e:
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    print(f"ERROR CRÍTICO DURANTE LA CARGA INICIAL: {e}")
    print("La aplicación continuará, pero podría no funcionar como se espera.")
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
