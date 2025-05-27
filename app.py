from flask import Flask, render_template, request, redirect, url_for, jsonify
import requests
import serial
from serial.tools import list_ports
import smtplib
from email.mime.text import MIMEText

# Configuración del correo
CORREO_REMITENTE = 'vicentehego2@gmail.com'
CONTRASENA = 'gngv twex aaue hxbg'  # Usa contraseña de aplicación, no la normal
CORREO_DESTINATARIO = 'losinestables.cdmx@gmail.com'

def enviar_alerta(mensaje):
    try:
        msg = MIMEText(mensaje)
        msg['Subject'] = '🚨 Alerta de Sensor - Agrocube'
        msg['From'] = CORREO_REMITENTE
        msg['To'] = CORREO_DESTINATARIO

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(CORREO_REMITENTE, CONTRASENA)
            server.send_message(msg)
            print("Correo de alerta enviado.")
    except Exception as e:
        print(f"Error al enviar correo: {e}")

app = Flask(__name__)
arduino = None

# Estado anterior de las alertas
estado_alerta = {
    "temperatura": None,       # 'baja', 'alta', 'normal'
    "humedad_suelo": None      # 'baja', 'normal'
}

# Datos de ejemplo para login
USERS = {
    "vicente": "1234",
    
}

weather_codes = {
    0: "Cielo despejado",
    1: "Principalmente despejado",
    2: "Parcialmente nublado",
    3: "Nublado",
    45: "Niebla",
    48: "Niebla con escarcha",
    51: "Llovizna ligera",
    53: "Llovizna moderada",
    55: "Llovizna intensa",
    61: "Lluvia ligera",
    63: "Lluvia moderada",
    65: "Lluvia intensa",
    80: "Chubascos ligeros",
    81: "Chubascos moderados",
    82: "Chubascos intensos"
}

def detectar_puerto_arduino():
    puertos = list_ports.comports()
    for puerto in puertos:
        if "Arduino" in puerto.description or "CH340" in puerto.description or "USB Serial" in puerto.description:
            return puerto.device
    return None
@app.route("/", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        print(f"[DEBUG] Usuario ingresado: '{username}'")
        print(f"[DEBUG] Contraseña ingresada: '{password}'")
        print(f"[DEBUG] Contraseña esperada en USERS: '{USERS.get(username)}'")

        if USERS.get(username) == password:
            print("[DEBUG] Login exitoso ✅")
            return redirect(url_for("bienvenida"))
        else:
            print("[DEBUG] Login fallido ❌")
            error = "Nombre de usuario o contraseña incorrectos"
    return render_template("index.html", error=error)


@app.route("/bienvenida")
def bienvenida():
    return render_template("bienvenida.html")

@app.route("/monitoreo")
def monitoreo():
    return render_template("monitoreo.html")

@app.route("/datos")
def datos():
    global arduino, estado_alerta
    try:
        if arduino is None or not arduino.is_open:
            puerto = detectar_puerto_arduino()
            if not puerto:
                return jsonify({'error': 'No se detectó un Arduino conectado'})
            arduino = serial.Serial(puerto, 9600, timeout=2)

        arduino.flushInput()
        linea = arduino.readline().decode('utf-8').strip()
        temperatura, humedad_aire, humedad_suelo = map(float, linea.split(','))

        # ALERTAS INTELIGENTES
        alertas = []

        # Temperatura
        if temperatura < 15:
            if estado_alerta["temperatura"] != "baja":
                alertas.append("🚨 Temperatura muy baja (< 15°C)")
                estado_alerta["temperatura"] = "baja"
        elif temperatura > 35:
            if estado_alerta["temperatura"] != "alta":
                alertas.append("🚨 Temperatura muy alta (> 35°C)")
                estado_alerta["temperatura"] = "alta"
        else:
            if estado_alerta["temperatura"] != "normal":
                alertas.append("✅ Temperatura normalizada")
                estado_alerta["temperatura"] = "normal"

        # Humedad del suelo
        if humedad_suelo < 30:
            if estado_alerta["humedad_suelo"] != "baja":
                alertas.append("🚨 Humedad del suelo baja (< 30%)")
                estado_alerta["humedad_suelo"] = "baja"
        else:
            if estado_alerta["humedad_suelo"] != "normal":
                alertas.append("✅ Humedad del suelo normalizada")
                estado_alerta["humedad_suelo"] = "normal"

        # Enviar correo si hay alertas
        if alertas:
            mensaje = "\n".join(alertas) + f"\n\n📊 Datos actuales:\nTemperatura: {temperatura}°C\nHumedad aire: {humedad_aire}%\nHumedad suelo: {humedad_suelo}%"
            enviar_alerta(mensaje)

        return jsonify({
            'temperatura': temperatura,
            'humedad_aire': humedad_aire,
            'humedad_suelo': humedad_suelo
        })

    except Exception as e:
        return jsonify({'error': str(e)})

@app.route("/riego")
def riego():
    return render_template("riego.html")

@app.route("/zabbix")
def zabbix():
    return render_template("zabbix.html")

@app.route("/obtener_clima", methods=["POST"])
def obtener_clima():
    data = request.get_json()
    lat = data.get("latitude")
    lon = data.get("longitude")

    if lat is None or lon is None:
        return jsonify({'error': 'Latitud y longitud no proporcionadas'}), 400

    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&current_weather=true"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,cloudcover_mean,windspeed_10m_max,relative_humidity_2m_mean"
        f"&timezone=America/Mexico_City"
    )

    try:
        response = requests.get(url)
        response.raise_for_status()
        weather_data = response.json()
        return jsonify(weather_data)
    except requests.RequestException as e:
        return jsonify({"error": "Error al obtener los datos del clima", "details": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True) 