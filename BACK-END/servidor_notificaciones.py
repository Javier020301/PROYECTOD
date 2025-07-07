from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from geopy.distance import distance

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
# Diccionario para almacenar usuarios conectados con su ubicación y sesión
usuarios = {}
# Variables globales para guardar el último estado y detalle recibido desde la cámara
ultimo_status = None
ultimo_detalle_camara = None
# Función para calcular la distancia en metros entre dos coordenadas geográficas
def distancia_km(lat1, lon1, lat2, lon2):
    punto1 = (lat1, lon1)
    punto2 = (lat2, lon2)
    distancia = distance(punto1, punto2).meters
    return distancia

@app.route("/")
def index():
    # Ruta principal que devuelve la página HTML al usuario
    return render_template("index.html")

@app.route("/api/evento", methods=["POST"])
def recibir_evento():
    global ultimo_status
    data = request.json
    # Validaciones para asegurarnos que el campo 'status' está presente en el JSON recibido
    if not data:
        return {"error": "Falta el campo 'status'"}
    if "status" not in data:
        return {"error": "Falta el campo 'status'"}
    # Guardamos el último estado recibido para poder compartirlo luego con usuarios nuevos
    ultimo_status = data["status"]
    print("Status guardado:", ultimo_status)
    respuesta = {"status": "ok"}
    return respuesta

@app.route("/api/detalle_camara", methods=["POST"])
def recibir_detalle_camara():
    global ultimo_detalle_camara, ultimo_status
    # Validamos que todos los campos necesarios estén presentes en el JSON
    data = request.json
    if not data:
        return {"error": "Faltan campos"}
    if "nombre_camara" not in data:
        return {"error": "Faltan campos"}
    if "ubicacion" not in data:
        return {"error": "Faltan campos"}
    if "fecha" not in data:
        return {"error": "Faltan campos"}
    if "alerta" not in data:
        return {"error": "Faltan campos"}
    if "informacion_extra" not in data:
        return {"error": "Faltan campos"}
    # Guardamos el detalle completo para compartir con usuarios nuevos
    ultimo_detalle_camara = data
    print("Detalle de cámara recibido:", data)
    # Si tenemos un estado guardado, enviamos notificaciones a usuarios cercanos
    if ultimo_status is not None:
        lat_evento = data["ubicacion"]["lat"]
        lon_evento = data["ubicacion"]["lon"]
        # Recorremos todos los usuarios conectados para verificar su distancia a la cámara
        for user_id in usuarios:
            info = usuarios[user_id]
            lat_user = info["lat"]
            lon_user = info["lon"]
            d = distancia_km(lat_user, lon_user, lat_evento, lon_evento)
            if d <= 500:
                cercano = True
            else:
                cercano = False
            if cercano == True:
                estado = ultimo_status
                detalle = data
            else:
                estado = None
                detalle = None
            # Enviamos el mensaje solo a ese usuario (usando su ID de sesión)
            socketio.emit("evento", {
                "cercano": cercano,
                "status": estado,
                "detalle": detalle
            }, room=info["sid"])
    # También enviamos el detalle actualizado de la cámara a todos los usuarios conectados
    socketio.emit("actualizar_camara", data)
    respuesta = {"status": "ok"}
    return respuesta

@socketio.on("registrar")
def registrar_usuario(data):
    user_id = request.sid
    lat = data.get("lat")
    lon = data.get("lon")
    # Comprobamos que el usuario envió su ubicación
    if lat is None:
        return
    if lon is None:
        return
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
    print("Usuario registrado:", lat_redondeado, ",", lon_redondeado)
    # Si ya hay detalles y estado guardados, enviamos la info al usuario nuevo si está cerca
    if ultimo_detalle_camara is not None:
        if ultimo_status is not None:
            lat_cam = ultimo_detalle_camara["ubicacion"]["lat"]
            lon_cam = ultimo_detalle_camara["ubicacion"]["lon"]
            d = distancia_km(lat_redondeado, lon_redondeado, lat_cam, lon_cam)
            if d <= 500:
                cercano = True
            else:
                cercano = False
            if cercano == True:
                estado = ultimo_status
                detalle = ultimo_detalle_camara
            else:
                estado = None
                detalle = None
            # Enviamos los datos al usuario que se acaba de conectar
            emit("evento", {
                "cercano": cercano,
                "status": estado,
                "detalle": detalle
            })
            # También enviamos el detalle actualizado para refrescar info de la cámara
            emit("actualizar_camara", ultimo_detalle_camara)

@socketio.on("disconnect")
def desconectar():
    user_id = request.sid
    # Al desconectarse, removemos al usuario del diccionario para no enviarle eventos futuros
    if user_id in usuarios:
        usuarios.pop(user_id)
    print("Usuario desconectado:", user_id)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=8000)
