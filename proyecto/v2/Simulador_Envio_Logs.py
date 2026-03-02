import time
import csv
import random
import datetime
import os

ARCHIVO_LOGS = "logs_tiempo_real.csv"
ARCHIVO_MANTENIMIENTO = "bitacora_mantenimiento.csv"

# Estado de las máquinas
# salud: 0-100%
# fin_reparacion: Timestamp cuando termina el mantenimiento actual (o None si está operando)
estado_maquinas = {
    1: {'salud': 100.0, 'fin_reparacion': None},
    2: {'salud': 100.0, 'fin_reparacion': None},
    3: {'salud': 100.0, 'fin_reparacion': None}
}

def checar_mantenimiento():
    if os.path.exists(ARCHIVO_MANTENIMIENTO):
        try:
            with open(ARCHIVO_MANTENIMIENTO, 'r') as f:
                lines = f.readlines()
                # Leemos las últimas líneas para ver si hay órdenes nuevas
                for linea_csv in reversed(lines[-5:]): # Miramos las últimas 5 por si acaso
                    datos = linea_csv.strip().split(',')
                    if len(datos) < 5: continue
                    
                    # Parsear datos
                    ts_str = datos[0] # Cuando se pidió
                    linea_id = int(datos[1])
                    duracion = int(datos[3])
                    salud_target = float(datos[4])
                    
                    try:
                        ts_orden = datetime.datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                    except: continue

                    ahora = datetime.datetime.now()
                    
                    # Si la orden es "fresca" (menos de 2 seg) Y la máquina no está ya en reparación
                    if (ahora - ts_orden).total_seconds() < 3 and estado_maquinas[linea_id]['fin_reparacion'] is None:
                        # PROGRAMAR EL PARO
                        tiempo_fin = ahora + datetime.timedelta(seconds=duracion)
                        estado_maquinas[linea_id]['fin_reparacion'] = tiempo_fin
                        estado_maquinas[linea_id]['salud_objetivo'] = salud_target # Guardamos a cuánto subirá
                        print(f" [🚨 PARO TÉCNICO] Línea {linea_id} detenida por {duracion}s...")
        except Exception as e:
            print(f"Error leer mto: {e}")

def generar_datos():
    print("--- SIMULADOR DE MÁQUINAS AVANZADO (CON PAROS) ---")
    
    with open(ARCHIVO_LOGS, 'w', newline='') as f:
        csv.writer(f).writerow(["Timestamp", "Linea", "Salud", "Tiempo_Ciclo"])

    while True:
        checar_mantenimiento()
        ahora_dt = datetime.datetime.now()
        ahora_str = ahora_dt.strftime("%H:%M:%S")
        
        with open(ARCHIVO_LOGS, 'a', newline='') as f:
            writer = csv.writer(f)
            
            for lid in [1, 2, 3]:
                maquina = estado_maquinas[lid]
                
                # VERIFICAR SI ESTÁ EN MANTENIMIENTO
                if maquina['fin_reparacion'] is not None:
                    if ahora_dt < maquina['fin_reparacion']:
                        # SIGUE EN REPARACIÓN
                        # Enviamos Salud 0 (o baja) para que se vea rojo en el dashboard
                        # Enviamos Tiempo Ciclo 0 (Línea parada)
                        writer.writerow([ahora_str, lid, 0, 0])
                        print(f"\r [L{lid}: EN REPARACIÓN] Restan {(maquina['fin_reparacion'] - ahora_dt).seconds}s...", end="")
                        continue # Saltamos al siguiente ciclo (no degrada)
                    else:
                        # YA TERMINÓ LA REPARACIÓN
                        maquina['salud'] = maquina.get('salud_objetivo', 100.0)
                        maquina['fin_reparacion'] = None
                        print(f"\n [✅ L{lid}: ONLINE] Reparación terminada. Salud: {maquina['salud']}%")

                # OPERACIÓN NORMAL
                desgaste = random.uniform(0.1, 0.6)
                maquina['salud'] -= desgaste
                if maquina['salud'] < 0: maquina['salud'] = 0
                
                # Ciclo normal
                factor = (100 - maquina['salud']) * 0.3
                tc = 138 + factor + random.gauss(0, 1)
                
                writer.writerow([ahora_str, lid, round(maquina['salud'], 2), round(tc, 2)])

        if estado_maquinas[1]['fin_reparacion'] is None:
            print(f"\r [TX] L1: {estado_maquinas[1]['salud']:.1f}% | L2: {estado_maquinas[2]['salud']:.1f}% ...", end="")
            
        time.sleep(1)

if __name__ == "__main__":
    generar_datos()