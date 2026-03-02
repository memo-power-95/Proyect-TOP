"""
Digital Twin publisher (SocketIO server)

- Provides a `DigitalTwinPublisher` class that can replay rows from a CSV and call a callback for each emitted message.
- Provides a `run_server()` function that starts a small Flask+SocketIO server with REST controls:
    GET /start            -> start replay
    GET /stop             -> stop replay
    POST /speed           -> JSON {"speed": 2.0} set replay speed (multiplier)
    POST /inject          -> JSON payload to inject a single event immediately

Notes:
- SocketIO is optional at import time: heavy imports occur only when `run_server()` is called.
- The server uses `async_mode='threading'` to avoid requiring eventlet/uvloop.

Usage (quick):
    python digital_twin.py

Client example available in `client_consumer.py`.
"""

import os
import threading
import time
import json
from typing import Callable, Optional

try:
    import pandas as pd
except Exception:
    pd = None

ARCHIVO_LOGS = os.path.join(os.path.dirname(__file__), '..', 'logs_tiempo_real.csv')
BASE_INTERVAL = 1.0  # seconds between emits at speed=1.0

class DigitalTwinPublisher:
    """Reproduce filas desde un CSV y llama a una función callback por cada mensaje.

    Callback recibe un diccionario (serializable) con los campos del registro.
    """
    def __init__(self, csv_path: Optional[str] = None, speed: float = 1.0):
        self.csv_path = csv_path or ARCHIVO_LOGS
        self.speed = max(0.01, float(speed))
        self.df = None
        self._load_data()
        self.running = False
        self._thread = None
        self._callback: Optional[Callable[[dict], None]] = None
        self._lock = threading.Lock()

    def _load_data(self):
        if pd is None:
            self.df = None
            return
        try:
            if os.path.exists(self.csv_path):
                self.df = pd.read_csv(self.csv_path)
            else:
                self.df = None
        except Exception as e:
            print(f"DigitalTwin: error leyendo CSV: {e}")
            self.df = None

    def register_callback(self, cb: Callable[[dict], None]):
        self._callback = cb

    def start(self):
        with self._lock:
            if self.running:
                return
            self.running = True
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
            print("DigitalTwin: started")

    def stop(self):
        with self._lock:
            self.running = False
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None
        print("DigitalTwin: stopped")

    def set_speed(self, speed: float):
        with self._lock:
            self.speed = max(0.01, float(speed))
        print(f"DigitalTwin: speed set to {self.speed}")

    def inject_event(self, event: dict):
        # Emite inmediatamente un evento arbitrario vía callback
        try:
            if self._callback:
                self._callback(dict(event))
                print("DigitalTwin: injected event", event)
        except Exception as e:
            print("DigitalTwin: error injecting event:", e)

    def _emit(self, payload: dict):
        try:
            if self._callback:
                self._callback(payload)
        except Exception as e:
            print("DigitalTwin: callback error:", e)

    def _run_loop(self):
        # si no hay df cargado intentamos recargar periódicamente
        while self.running:
            if self.df is None or self.df.empty:
                self._load_data()
                time.sleep(2.0)
                continue

            # iterar sobre filas emitiendo una por una
            for _, row in self.df.iterrows():
                if not self.running:
                    break
                try:
                    payload = row.to_dict()
                except Exception:
                    payload = {}
                # añadir timestamp de emisión
                payload['emit_ts'] = time.time()
                self._emit(payload)
                # respetar velocidad
                sleep_for = max(0.01, BASE_INTERVAL / float(self.speed))
                time.sleep(sleep_for)

            # al terminar el CSV, esperamos un poco y volvemos a empezar
            time.sleep(0.5)


# --- Server runner (imports Flask+SocketIO lazily) ---
def run_server(host='0.0.0.0', port=5000, csv_path: Optional[str] = None):
    try:
        from flask import Flask, request, jsonify
        from flask_socketio import SocketIO
    except Exception as e:
        print('run_server: Missing dependencies. Install `flask` and `flask-socketio`.')
        raise

    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'top-digital-twin'
    socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading')

    publisher = DigitalTwinPublisher(csv_path=csv_path, speed=1.0)

    # conectar callback que emite por socketio
    def _on_emit(payload):
        try:
            socketio.emit('telemetry', payload, broadcast=True)
        except Exception as e:
            print('run_server: emit error', e)

    publisher.register_callback(_on_emit)

    @app.route('/start', methods=['GET'])
    def route_start():
        publisher.start()
        return jsonify({'status': 'started'})

    @app.route('/stop', methods=['GET'])
    def route_stop():
        publisher.stop()
        return jsonify({'status': 'stopped'})

    @app.route('/speed', methods=['POST'])
    def route_speed():
        data = request.get_json(force=True, silent=True) or {}
        s = data.get('speed') or request.args.get('speed') or 1.0
        try:
            publisher.set_speed(float(s))
            return jsonify({'status': 'ok', 'speed': publisher.speed})
        except Exception as e:
            return jsonify({'error': str(e)}), 400

    @app.route('/inject', methods=['POST'])
    def route_inject():
        data = request.get_json(force=True, silent=True)
        if not data:
            return jsonify({'error': 'no payload'}), 400
        publisher.inject_event(data)
        return jsonify({'status': 'injected'})

    @socketio.on('connect')
    def on_connect():
        print('Client connected')

    @socketio.on('disconnect')
    def on_disconnect():
        print('Client disconnected')

    print(f"Starting Digital Twin server on http://{host}:{port} (csv={publisher.csv_path})")
    # arrancar servidor (blocking)
    socketio.run(app, host=host, port=port)


if __name__ == '__main__':
    # modo script: ejecutar servidor local
    run_server()
