import math
from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
# Inicializa SocketIO la aplicación Flask, asi permite conexiones desde cualquier dominio.
socketio = SocketIO(app, cors_allowed_origins="*")
# Diccionario para almacenar usuarios conectados con su ubicación y sesión
usuarios = {}
# Variables globales para guardar el último estado y detalle recibido desde la cámara
ultimo_status = None
ultimo_detalle_camara = None
# Función para calcular distancia en km entre dos puntos (Haversine)
def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371  # Radio Tierra en km
    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    lon1_r = math.radians(lon1)
    lon2_r = math.radians(lon2)
    term1 = (math.sin((lat2_r-lat1_r)/2))**2
    term2 = (math.cos(lat1_r)*math.cos(lat2_r))*(math.sin((lon2_r-lon1_r)/2))**2
    Haver = math.asin(math.sqrt(term1+term2))*2*R
    return Haver

def notificar_usuario():
    if ultimo_detalle_camara is None or ultimo_status is None:
        return  # No hay datos aún, así que no se notifica nada
    LATITUD_CAMARA = ultimo_detalle_camara["ubicacion"]["lat"]
    LONGITUD_CAMARA = ultimo_detalle_camara["ubicacion"]["lon"]

    for usuarioid in usuarios:
        info = usuarios[usuarioid]
        lat_usu = info["lat"]
        lon_usu = info["lon"]

        distancia = calcular_distancia(lat_usu, lon_usu, LATITUD_CAMARA, LONGITUD_CAMARA)
        if distancia <= 1:
            estado = ultimo_status
            detalle = ultimo_detalle_camara
        else:
            estado = None
            detalle = None
        socketio.emit("evento", {
            "cercano": True,
            "status": estado,
            "detalle": detalle
        }, room=info["sid"])
    
@app.route("/")
def index():
    # Ruta principal que devuelve la página HTML al usuario
    return render_template("index.html")

@app.route("/api/estado", methods=["POST"])
def recibir_evento():
    global ultimo_status
    data = request.json
    # Validaciones para asegurarnos que el campo 'status' está presente en el JSON recibido
    if "status" not in data:
        return {"error": "Falta el campo 'status'"}
    # Guardamos el último estado recibido para poder compartirlo luego con usuarios nuevos
    ultimo_status = data["status"]
    print("Status guardado:", ultimo_status)
    return jsonify({"status": True, "message": "Solicitud recibida"})

@app.route("/api/detalle", methods=["POST"])
def recibir_detalle_camara():
    global ultimo_detalle_camara, ultimo_status
    # Validamos que todos los campos necesarios estén presentes en el JSON
    data = request.json
    if not data or "nombre_camara" not in data or "ubicacion" not in data or "fecha" not in data or "alerta" not in data or "informacion_extra" not in data:
        return {"error": "Faltan campos"}
    # Guardamos el detalle completo para compartir con usuarios nuevos
    ultimo_detalle_camara = data
    print("Detalle de cámara recibido:", data)
    # Si tenemos un estado guardado, enviamos notificaciones a usuarios cercanos
    notificar_usuario()
    # También enviamos el detalle actualizado de la cámara a todos los usuarios conectados
    socketio.emit("actualizar_camara", data)
    return jsonify({"mensaje": "Detalle recibido correctamente"})

@socketio.on("registrar")
def registrar_usuario(data):
    user_id = request.sid
    lat = data.get("lat")
    lon = data.get("lon")
    # Comprobamos que el usuario envió su ubicación
    if lat is None or lon is None:
        return None
    lat_float = float(lat)
    lon_float = float(lon)
    lat_redondeado = round(lat_float, 4)
    lon_redondeado = round(lon_float, 4)
    # Guardamos al usuario con su ubicación y su ID de sesión
    usuarios[user_id] = {
        "lat": lat_redondeado,
        "lon": lon_redondeado,
        "sid": user_id
    }
    print(f"Usuario registrado: \nLatitud: {lat_redondeado},  Longitud: {lon_redondeado}")
    # Si ya hay detalles y estado guardados, enviamos la info al usuario nuevo si está cerca
    notificar_usuario()
    # También enviamos el detalle actualizado para refrescar info de la cámara
    emit("actualizar_camara", ultimo_detalle_camara)

@socketio.on("disconnect")
def usuario_deconectado():
    userid = request.sid
    # Al desconectarse, removemos al usuario del diccionario para no enviarle eventos futuros
    if userid in usuarios:
        usuarios.pop(userid)
    print(f"El usuario {userid} se ha desconectado.\n\n\n\n\n\n\n\n\n\n")

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=8000)
