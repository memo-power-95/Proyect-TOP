import csv
import os
import datetime
import time

ARCHIVO = "bitacora_mantenimiento.csv"

# Catálogo de Fallas y Soluciones (Ingeniería)
# Formato: Opción: [Nombre, Tiempo_Reparacion_Segundos, Salud_Recuperada]
CATALOGO_MANTENIMIENTO = {
    1: ["Limpieza de Sensor Óptico", 5, 100.0],  # Rápido, queda nueva
    2: ["Calibración de Torque", 10, 100.0],     # Medio, queda nueva
    3: ["Cambio de Servomotor", 20, 100.0],      # Lento, queda nueva
    4: ["Reinicio de Software (Soft Reset)", 3, 80.0] # Muy rápido, pero no arregla el fondo (Salud 80%)
}

if not os.path.exists(ARCHIVO):
    with open(ARCHIVO, 'w', newline='') as f: 
        csv.writer(f).writerow(["Timestamp", "Linea", "Accion", "Duracion", "Salud_Final"])

def menu():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("="*60)
    print("   SISTEMA DE MANTENIMIENTO CORRECTIVO (TOP)")
    print("="*60)
    print(" Seleccione el tipo de intervención:")
    print("-" * 60)
    
    for key, val in CATALOGO_MANTENIMIENTO.items():
        print(f" [{key}] {val[0]:<30} | Tiempo Est: {val[1]}s | Eficiencia: {val[2]}%")
    
    print("-" * 60)

while True:
    menu()
    try:
        linea = int(input(" > ¿Línea a reparar? (1, 2 o 3): "))
        opcion = int(input(" > Seleccione opción (1-4): "))
        
        if opcion in CATALOGO_MANTENIMIENTO:
            accion_nombre = CATALOGO_MANTENIMIENTO[opcion][0]
            duracion = CATALOGO_MANTENIMIENTO[opcion][1]
            salud_final = CATALOGO_MANTENIMIENTO[opcion][2]
            
            # Opción para personalizar el tiempo real (si fue más difícil de lo planeado)
            cambiar_tiempo = input(f" > El tiempo estándar es {duracion}s. ¿Cambiar? (s/n): ")
            if cambiar_tiempo.lower() == 's':
                duracion = int(input(" > Ingrese tiempo real (seg): "))

            ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Guardamos todo en el CSV para que el Simulador lo lea
            with open(ARCHIVO, 'a', newline='') as f:
                csv.writer(f).writerow([ahora, linea, accion_nombre, duracion, salud_final])
                
            print(f"\n [OK] Orden de trabajo generada: {accion_nombre}")
            print(f" [INFO] La Línea {linea} entrará en PARO TÉCNICO por {duracion} segundos.")
            time.sleep(3)
        else:
            print(" [!] Opción inválida.")
            time.sleep(1)
            
    except ValueError:
        print(" [!] Entrada inválida.")
        time.sleep(1)