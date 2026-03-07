import time
import csv
import random
import datetime
import os
import numpy as np

ARCHIVO_LOGS = "logs_tiempo_real.csv"  # Para compatibilidad
ARCHIVOS_LOGS_POR_LINEA = {
    1: "logs_tiempo_real_linea_1.csv",
    2: "logs_tiempo_real_linea_2.csv"
}
ARCHIVO_MTO = "bitacora_mantenimiento.csv"

LINEAS_ACTIVAS = [1, 2]

MAQUINAS_POR_LINEA = {
    1: [
        "Top cover feeding",
        "Pre-weighing",
        "Tim dispensing",
        "Avl Tim",
        "Weighing",
        "Install PCB",
        "Fastening 1",
        "Fastening 2",
        "Avl screw",
        "Top unloader",
    ],
    2: [
        "Top cover feeding",
        "Pre-weighing",
        "Tim dispensing",
        "Avl Tim",
        "Weighing",
        "Install PCB",
        "Fastening 1",
        "Fastening 2",
        "Avl screw",
        "Top unloader",
    ],
}

TC_IDEAL_MAQUINA = {
    "Top cover feeding": 105.47,
    "Pre-weighing": 79.98,
    "Tim dispensing": 83.60,
    "Avl Tim": 60.69,
    "Weighing": 83.06,
    "Install PCB": 88.60,
    "Fastening 1": 80.65,
    "Fastening 2": 92.74,
    "Avl screw": 70.32,
    "Top unloader": 104.36,
}


def _init_maquinas():
    data = {}
    for linea in LINEAS_ACTIVAS:
        for maquina in MAQUINAS_POR_LINEA[linea]:
            data[(linea, maquina)] = {
                "salud": round(random.uniform(96.5, 99.5), 2),
                "wear": 0.0,
            }
    return data


maquinas = _init_maquinas()
mto_activos = {}  # clave: (linea, maquina) o (linea, None) para línea completa

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
    if not os.path.exists(ARCHIVO_MTO):
        return
    try:
        with open(ARCHIVO_MTO, "r", newline="", encoding="utf-8") as f:
            lines = f.readlines()
            for linea_csv in reversed(lines[-3:]):
                datos = linea_csv.strip().split(",")
                if len(datos) < 6:
                    continue
                ts_str, lid, maq_str, duracion = datos[0], int(datos[1]), datos[2], int(datos[4])
                salud_target = float(datos[5])

                if lid not in LINEAS_ACTIVAS:
                    continue

                try:
                    ts_orden = datetime.datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                except Exception:
                    continue
                
                ahora = datetime.datetime.now()
                # Si la orden es nueva (<3s) y no está ya en reparación
                clave = (lid, None) if maq_str == "Toda la línea" else (lid, maq_str)
                if (ahora - ts_orden).total_seconds() < 3 and clave not in mto_activos:
                    mto_activos[clave] = {
                        "fin_mto": ahora + datetime.timedelta(seconds=duracion),
                        "salud_objetivo": salud_target,
                    }
                    maq_desc = f"Linea {lid} - {maq_str}" if maq_str != "Toda la línea" else f"Linea {lid}"
                    print(f" [PARO TECNICO] {maq_desc} detenida por {duracion}s...")
    except Exception:
        pass

def generar():
    print("--- SIMULADOR MULTIMAQUINA (2 LINEAS CON LOGS SEPARADOS) ---")
    print("Se genera telemetria por maquina en archivos separados por linea.")

    # Inicializar archivos por línea
    for lid in LINEAS_ACTIVAS:
        archivo = ARCHIVOS_LOGS_POR_LINEA[lid]
        with open(archivo, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["Timestamp", "Linea", "Maquina", "Salud", "Tiempo_Ciclo", "Evento"])
        print(f"  Archivos de logs creados: {archivo}")

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

        # Escribir en archivos separados por línea
        for lid in LINEAS_ACTIVAS:
            archivo_linea = ARCHIVOS_LOGS_POR_LINEA[lid]
            with open(archivo_linea, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                preview = []
                for maquina in MAQUINAS_POR_LINEA[lid]:
                    maq = maquinas[(lid, maquina)]
                    evento = "OK"
                    tc = TC_IDEAL_MAQUINA.get(maquina, BASE_TC)

                    # Revisar mantenimiento: primero línea completa, luego máquina específica
                    mto_activa = None
                    clave_linea = (lid, None)
                    clave_maq = (lid, maquina)
                    
                    if clave_linea in mto_activos:
                        if ahora_dt < mto_activos[clave_linea]["fin_mto"]:
                            mto_activa = mto_activos[clave_linea]
                        else:
                            del mto_activos[clave_linea]
                    
                    if clave_maq in mto_activos:
                        if ahora_dt < mto_activos[clave_maq]["fin_mto"]:
                            mto_activa = mto_activos[clave_maq]
                        else:
                            del mto_activos[clave_maq]

                    # Si está en mantenimiento, registrar como paro técnico
                    if mto_activa is not None:
                        writer.writerow([ahora_str, lid, maquina, 0, 0, "MANTENIMIENTO"])
                        continue
                    
                    # Si acaba de terminar mantenimiento, restaurar salud
                    if clave_maq in mto_activos or clave_linea in mto_activos:
                        if clave_maq in mto_activos:
                            maq["salud"] = float(mto_activos[clave_maq].get("salud_objetivo", 100.0))
                        else:
                            maq["salud"] = float(mto_activos[clave_linea].get("salud_objetivo", 100.0))
                        maq["wear"] = max(0.0, maq["wear"] - 0.2)

                    maq["wear"] += WEAR_RATE * max(0.5, 1.0 + random.uniform(-0.3, 0.3))
                    deriva = -0.02 * maq["wear"] + random.normalvariate(0, 0.25)
                    maq["salud"] = min(100.0, max(0.0, maq["salud"] + deriva))

                    dynamic_prob = BASE_FAILURE_RATE + 0.01 * maq["wear"] + (100.0 - maq["salud"]) / 2000.0
                    if burst_timer > 0:
                        dynamic_prob *= 4

                    r = random.random()
                    if r < dynamic_prob:
                        severidad = random.random()
                        if severidad < 0.5:
                            delta = random.uniform(5, 20)
                            maq["salud"] = max(0.0, maq["salud"] - delta)
                            evento = "SENSOR_FAIL"
                            tc += abs(random.gauss(15, 8))
                        elif severidad < 0.8:
                            evento = "SCRAP_PART"
                            tc += abs(random.gauss(20, 12))
                        else:
                            evento = "STUCK"
                            mto_activos[(lid, maquina)] = {
                                "fin_mto": ahora_dt + datetime.timedelta(seconds=random.randint(10, 45)),
                                "salud_objetivo": 100.0,
                            }
                    elif r > 0.995 and maq["salud"] < 95:
                        maq["salud"] = min(100.0, maq["salud"] + random.uniform(1, 6))
                        evento = "AJUSTE_OP"

                    if evento == "OK" and maq["salud"] > 92:
                        tc += random.gauss(0, 0.6)
                    elif maq["salud"] > 75:
                        tc += random.gauss(3, 1.5)
                    elif maq["salud"] > 50:
                        tc += random.gauss(8, 4)
                    else:
                        tc += random.gauss(25, 12)
                        if random.random() < 0.25:
                            evento = "CRITICAL" if evento == "OK" else evento

                    if random.random() < 0.01:
                        tc += random.gauss(30, 20)
                        evento = "SPIKE"

                    writer.writerow([ahora_str, lid, maquina, round(maq["salud"], 2), round(tc, 2), evento])
                    if maquina == MAQUINAS_POR_LINEA[lid][0]:
                        preview.append(f"L{lid}:{maquina} {maq['salud']:.1f}% TC={tc:.1f}s")

        if preview:
            print("\r " + " | ".join(preview), end="")

        if burst_timer > 0:
            burst_timer -= 1

        time.sleep(1)


if __name__ == "__main__":
    generar()