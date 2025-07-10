import datetime
import cv2
import numpy as np
import requests
from ultralytics import YOLO
import os
import time
from datetime import datetime

class SecuritySystem:
    def __init__(self):
        self.load_models()
        self.cap = self.setup_camera()
        self.status = "Todo en orden"
        self.status_color = (0, 255, 0)
        self.ultimo_frame = None
        self.running = True
        self.camara_name = "Camara 1 BELLAVISTA"

    def load_models(self):
        self.classNames = []
        classFile = 'coco.names'
        if os.path.exists(classFile):
            with open(classFile, 'rt') as f:
                self.classNames = f.read().rstrip('\n').split('\n')
        else:
            print(f"Advertencia: No se encontró el archivo {classFile}")
            self.classNames = [f"Class_{i}" for i in range(90)]

        configPath = 'ssd_mobilenet_v3_large_coco_2020_01_14.pbtxt'
        weightsPath = 'frozen_inference_graph.pb'

        if os.path.exists(configPath) and os.path.exists(weightsPath):
            self.net = cv2.dnn_DetectionModel(weightsPath, configPath)
            self.net.setInputSize(320, 320)
            self.net.setInputScale(1.0 / 127.5)
            self.net.setInputMean((127.5, 127.5, 127.5))
            self.net.setInputSwapRB(True)
        else:
            print("Advertencia: No se encontraron los archivos del modelo MobileNet-SSD")
            self.net = None

        try:
            self.yolo_model = YOLO('yolov8m.pt')
        except Exception as e:
            print(f"Error al cargar YOLOv8: {e}")
            self.yolo_model = None

    def setup_camera(self):
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            print("Error: No se pudo abrir la cámara")
            exit()
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        return cap

    def detect_events(self, frame):
        if self.yolo_model is None:
            return None

        results = self.yolo_model(frame, verbose=False)[0]
        personas = []
        armas = []

        for box in results.boxes:
            cls_id = int(box.cls)
            label = self.yolo_model.names[cls_id]
            x1, y1, x2, y2 = map(int, box.xyxy[0])

            if label == "person":
                personas.append((x1, y1, x2, y2))
            elif label in ["knife", "sports ball", "scissors", "gun"]:
                armas.append((x1, y1, x2, y2))

        for px1, py1, px2, py2 in personas:
            for ax1, ay1, ax2, ay2 in armas:
                persona_center = ((px1 + px2) // 2, (py1 + py2) // 2)
                arma_center = ((ax1 + ax2) // 2, (ay1 + ay2) // 2)
                distancia = np.linalg.norm(np.array(persona_center) - np.array(arma_center))
                if distancia < 150:
                    return "robo"

        return None

    def run_detection(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.1)
                continue

            # Detección rápida MobileNet-SSD
            if self.net is not None:
                classIds, confs, bbox = self.net.detect(frame, confThreshold=0.5)
                if len(classIds) != 0:
                    for classId, confidence, box in zip(classIds.flatten(), confs.flatten(), bbox):
                        cv2.rectangle(frame, box, color=(0, 255, 0), thickness=2)
                        label = self.classNames[classId - 1] if classId - 1 < len(self.classNames) else "Desconocido"
                        cv2.putText(frame, f"{label} {int(confidence * 100)}%",
                                    (box[0] + 10, box[1] + 25),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            # Detección de eventos importantes con YOLO
            evento = self.detect_events(frame)

            self.status = "Todo en orden"
            self.status_color = (0, 255, 0)

            if evento == "robo":
                self.status = "¡Alerta de robo!"
                self.status_color = (0, 0, 255)

            cv2.putText(frame, self.status, (30, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, self.status_color, 2)

            self.ultimo_frame = frame

    def stream(self):
        # Método para generar el video en formato MJPEG para streaming
        while True:
            # Si no hay frame capturado aún, esperamos un poco y seguimos esperando
            if self.ultimo_frame is None:
                time.sleep(0.01)
                continue
            # Codificamos el frame actual a formato JPEG
            resultado, buffer = cv2.imencode('.jpg', self.ultimo_frame)
            # Convertimos el buffer a bytes para poder enviarlo
            frame_bytes = buffer.tobytes()
            # Enviamos los bytes en el formato necesario para multipart streaming
            yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    def verify_report(self):
        while self.running:
            # Verificamos si la cámara está activa
            if self.cap.isOpened():
                # Creamos un diccionario con la información del estado actual
                alerta_info = {
                    "nombre_camara": self.camara_name,
                    "ubicacion": {"lat": -0.0626, "lon": -78.452},
                    "fecha": datetime.now().isoformat(),
                    "alerta": self.status,
                    "informacion_extra": {"mensaje": "tener cuidado."}
                    }
                # Enviamos un evento básico al servidor indicando que la cámara está operativa
                response = requests.post("http://localhost:8000/api/estado", json={"status": "Cámara operativa"})
                if response.status_code != 200:
                    print(f"Error al enviar evento: {response.text}")
                # Enviamos la información detallada
                response = requests.post("http://localhost:8000/api/detalle", json=alerta_info)
                if response.status_code == 200:
                    print(f"Información de cámara: {self.camara_name} enviada.")
                else:
                    print(f"Error al enviar detalles de la camara: {response.text}")
            else:
                print("La cámara está apagada.")
            time.sleep(0.00001)