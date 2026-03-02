import time, csv, random, datetime, os

ARCHIVO_LOGS = "logs_tiempo_real.csv"
ARCHIVO_MTO = "bitacora_mantenimiento.csv"

salud = {i: 100 for i in range(1, 13)} # Salud inicial 100%

def checar_mantenimiento():
    if os.path.exists(ARCHIVO_MTO):
        with open(ARCHIVO_MTO, 'r') as f:
            lines = f.readlines()
            if len(lines) > 1:
                ultimo = lines[-1].strip().split(',')
                # Formato: Fecha, Linea, Accion...
                ts_str, linea = ultimo[0], int(ultimo[1])
                ahora = datetime.datetime.now()
                ts_mto = datetime.datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                # Si el mantenimiento fue hace menos de 3 seg, reparamos
                if (ahora - ts_mto).total_seconds() < 3:
                    salud[linea] = 100
                    print(f" [MANTENIMIENTO] Línea {linea} REPARADA!")

def generar():
    with open(ARCHIVO_LOGS, 'w', newline='') as f:
        csv.writer(f).writerow(["Timestamp", "Linea", "TC", "Salud"])
    
    print(" >> MÁQUINAS CORRIENDO... (No cierres esta ventana)")
    while True:
        checar_mantenimiento()
        with open(ARCHIVO_LOGS, 'a', newline='') as f:
            writer = csv.writer(f)
            ahora = datetime.datetime.now().strftime("%H:%M:%S")
            for i in range(1, 13):
                # Desgaste natural
                salud[i] -= random.uniform(0.05, 0.2)
                if salud[i] < 0: salud[i] = 0
                
                # Tiempo ciclo empeora con mala salud
                tc_base = 138 + (100 - salud[i]) * 0.5 
                tc_real = random.gauss(tc_base, 2)
                
                writer.writerow([ahora, i, round(tc_real, 2), round(salud[i], 1)])
        time.sleep(1)

if __name__ == "__main__": generar()