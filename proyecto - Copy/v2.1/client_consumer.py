"""
Cliente de ejemplo que se conecta al servidor SocketIO del Digital Twin

Requiere `python-socketio`:
    pip install "python-socketio[client]"

Ejecutar:
    python client_consumer.py

El cliente muestra por consola los mensajes recibidos.
"""

import time

def main():
    try:
        import socketio
    except Exception:
        print('Este cliente requiere python-socketio. Instala con: pip install "python-socketio[client]"')
        return

    sio = socketio.Client()

    @sio.event
    def connect():
        print('Conectado al servidor')

    @sio.event
    def disconnect():
        print('Desconectado')

    @sio.on('telemetry')
    def on_telemetry(data):
        print('telemetry:', data)

    try:
        sio.connect('http://localhost:5000')
        print('Conectado, esperando mensajes... (CTRL+C para salir)')
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('Saliendo...')
    except Exception as e:
        print('Error conectando:', e)
    finally:
        try:
            sio.disconnect()
        except Exception:
            pass

if __name__ == '__main__':
    main()
