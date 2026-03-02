import time
import csv
import random
import datetime
import os
import numpy as np

ARCHIVO_LOGS = "logs_tiempo_real.csv"
ARCHIVO_MTO = "bitacora_mantenimiento.csv"

# Configuración de las máquinas
# salud: Nivel actual (0-100)
# fin_mto: Si está en mantenimiento, aquí se guarda la hora de fin
maquinas = {
    1: {'salud': 98.5, 'fin_mto': None, 'wear': 0.0},
    2: {'salud': 99.0, 'fin_mto': None, 'wear': 0.0},
    3: {'salud': 97.0, 'fin_mto': None, 'wear': 0.0}
}

# Parámetros de simulación
BASE_TC = 138.0
BASE_FAILURE_RATE = 0.002  # probabilidad base por iteración
WEAR_RATE = 0.0005         # cómo aumenta wear por iteración
BURST_PROB = 0.001         # probabilidad de ráfaga de fallas múltiples
SEED = None                # fijar seed para reproducibilidad (None aleatorio)

if SEED is not None:
    random.seed(SEED)
    np.random.seed(SEED)

def checar_mantenimiento():
    if not os.path.exists(ARCHIVO_MTO): return
    try:
        with open(ARCHIVO_MTO, 'r') as f:
            lines = f.readlines()
            for linea_csv in reversed(lines[-3:]):
                datos = linea_csv.strip().split(',')
                if len(datos) < 5: continue
                ts_str, lid, duracion = datos[0], int(datos[1]), int(datos[3])
                salud_target = float(datos[4])
                
                try: ts_orden = datetime.datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                except: continue
                
                ahora = datetime.datetime.now()
                # Si la orden es nueva (<3s) y no está ya en reparación
                if (ahora - ts_orden).total_seconds() < 3 and maquinas[lid]['fin_mto'] is None:
                    maquinas[lid]['fin_mto'] = ahora + datetime.timedelta(seconds=duracion)
                    maquinas[lid]['salud_objetivo'] = salud_target
                    print(f" [🚨 PARO TÉCNICO] Línea {lid} detenida por {duracion}s...")
    except: pass

def generar():
    print("--- SIMULADOR ESTABLE (CON PICOS DE FALLA) ---")
    print("Las máquinas operarán estables hasta que ocurra un evento aleatorio.")
    
    with open(ARCHIVO_LOGS, 'w', newline='') as f:
        csv.writer(f).writerow(["Timestamp", "Linea", "Salud", "Tiempo_Ciclo", "Evento"])

    # Variables para ráfagas
    burst_timer = 0

    while True:
        checar_mantenimiento()
        ahora_dt = datetime.datetime.now()
        ahora_str = ahora_dt.strftime("%Y-%m-%d %H:%M:%S")

        # Posible ráfaga de fallas (correlacionadas)
        if burst_timer <= 0 and random.random() < BURST_PROB:
            burst_timer = random.randint(3, 10)  # segundos en los que la probabilidad está alta
            print("\n[! RÁFAGA] Aumentando probabilidad de fallas por unos segundos...")

        with open(ARCHIVO_LOGS, 'a', newline='') as f:
            writer = csv.writer(f)
            for lid in [1, 2, 3]:
                maq = maquinas[lid]
                evento = "OK"
                tc = BASE_TC

                # 1. SI ESTÁ EN MANTENIMIENTO
                if maq['fin_mto'] is not None:
                    if ahora_dt < maq['fin_mto']:
                        writer.writerow([ahora_str, lid, 0, 0, "MANTENIMIENTO"])
                        continue
                    else:
                        maq['salud'] = maq.get('salud_objetivo', 100.0)
                        maq['fin_mto'] = None
                        maq['wear'] = max(0.0, maq.get('wear', 0.0) - 0.2)
                        print(f"\n [✅ L{lid}: ONLINE] Mantenimiento finalizado.")

                # --------------------------------------------------
                # Degradación y ruido natural
                # --------------------------------------------------
                # desgaste gradual
                maq['wear'] += WEAR_RATE * max(0.5, 1.0 + random.uniform(-0.3, 0.3))

                # salud sufre pequeña deriva dependiente del wear
                deriva = -0.02 * maq['wear'] + random.normalvariate(0, 0.3)
                maq['salud'] += deriva

                # Limitar rango
                maq['salud'] = min(100.0, max(0.0, maq['salud']))

                # --------------------------------------------------
                # Probabilidades de falla (aumentan con wear y baja salud)
                # --------------------------------------------------
                dynamic_prob = BASE_FAILURE_RATE + 0.01 * maq['wear'] + (100.0 - maq['salud']) / 2000.0
                if burst_timer > 0:
                    dynamic_prob *= 4

                # Eventos transitorios: sensor fail (corto), spike TC, stuck (largo)
                r = random.random()
                if r < dynamic_prob:
                    # elegir tipo de fallo según severidad
                    severidad = random.random()
                    if severidad < 0.5:
                        # sensor fail: caída de salud rápida y recuperación breve
                        delta = random.uniform(5, 20)
                        maq['salud'] = max(0.0, maq['salud'] - delta)
                        evento = 'SENSOR_FAIL'
                        tc += abs(random.gauss(15, 8))
                        print(f"\n [FALLA] L{lid} SENSOR_FAIL -{delta:.1f}%")
                    elif severidad < 0.8:
                        # scrap / quality issue: piezas malas
                        evento = 'SCRAP_PART'
                        tc += abs(random.gauss(20, 12))
                    else:
                        # stuck / bloqueo: larga degradación y posible parada
                        evento = 'STUCK'
                        maq['fin_mto'] = ahora_dt + datetime.timedelta(seconds=random.randint(10, 60))
                        print(f"\n [CRITICAL] L{lid} se detiene por STUCK")

                # Recuperaciones esporádicas (ajuste operador)
                elif r > 0.995 and maq['salud'] < 95:
                    rec = random.uniform(1, 6)
                    maq['salud'] = min(100.0, maq['salud'] + rec)
                    evento = 'AJUSTE_OP'

                # --------------------------------------------------
                # Consecuencias en el Tiempo de Ciclo
                # --------------------------------------------------
                # Basado en salud y eventos, añadimos ruido y picos
                if evento == 'OK' and maq['salud'] > 92:
                    tc += random.gauss(0, 0.6)
                elif maq['salud'] > 75:
                    tc += random.gauss(3, 1.5)
                elif maq['salud'] > 50:
                    tc += random.gauss(8, 4)
                else:
                    tc += random.gauss(25, 12)
                    if random.random() < 0.25:
                        evento = 'CRITICAL' if evento == 'OK' else evento

                # Picos aleatorios cortos (ruidos/eventos externos)
                if random.random() < 0.01:
                    tc += random.gauss(30, 20)
                    evento = 'SPIKE'

                # Registro
                writer.writerow([ahora_str, lid, round(maq['salud'], 2), round(tc, 2), evento])

        # Estado en consola para Línea 1
        salud_l1 = maquinas[1]['salud']
        tc_preview = tc if 'tc' in locals() else BASE_TC
        color = "VERDE" if salud_l1 > 90 else "ROJO" if salud_l1 < 60 else "AMARILLO"
        print(f"\r [L1] Estado: {color} ({salud_l1:05.1f}%) | TC: {tc_preview:.1f}s ", end="")

        if burst_timer > 0:
            burst_timer -= 1

        time.sleep(1)

if __name__ == "__main__": generar()