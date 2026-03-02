import simpy
import random
import time
import sys
import csv  # <--- NUEVO: Para generar Excel

# --- CONFIGURACIÓN INTERACTIVA ---
print("\n" + "="*80)
print("   PANEL DE CONTROL - GEMELO DIGITAL PRO (TOP + FINANZAS)")
print("="*80)

try:
    input_dias = input(" [1] Días a simular (Ej. 7): ")
    DIAS_SIMULACION = int(input_dias)
    input_lineas = input(" [2] Líneas activas (Ej. 12): ")
    CANTIDAD_LINEAS = int(input_lineas)
except:
    DIAS_SIMULACION = 7
    CANTIDAD_LINEAS = 12

print(f" > CONFIGURACIÓN: {CANTIDAD_LINEAS} Líneas | {DIAS_SIMULACION} Días.")
print(f" > MÓDULO FINANCIERO: ACTIVADO")
print(f" > EXPORTACIÓN CSV:   ACTIVADO")
time.sleep(1)

# --- PARÁMETROS ECONÓMICOS (ESTIMADOS) ---
# Estos valores son hipotéticos para la simulación
VALOR_CAMARA_OK = 150.00   # USD: Precio de venta de una cámara
COSTO_SCRAP = 45.00        # USD: Lo que cuesta tirar una pieza a la basura
COSTO_HORA_PARO = 500.00   # USD: Costo operativo de tener la línea parada 1 hora

# --- PARÁMETROS TÉCNICOS ---
CAPACIDAD_LINEA_WIP = 12
TIEMPO_SIMULACION = DIAS_SIMULACION * 24 * 3600
DELAY_VISUAL = 60 / (DIAS_SIMULACION * 24)

PIEZAS_POR_PALLET = 12
TIEMPO_LLEGADA = 138 

# Tiempos de Ciclo
TC_HOUSING_LOAD = 30     
TC_WEIGH_1 = 2           
TC_TIM_APPLY = 4         
TC_TIM_LASER = 3         
TC_WEIGH_2 = 2           
TC_PCB_INSTALL = 40      
TC_FASTENING = 138       
TC_PCB_LASER = 4         
TC_UNLOAD = 25           

TIEMPO_CORRECCION_ATASCO = 60
TIEMPO_REINTENTO_TORNILLO = 15

def obtener_dia_hora(segundos_totales):
    dias = int(segundos_totales // 86400)
    resto = segundos_totales % 86400
    horas = int(resto // 3600)
    minutos = int((resto % 3600) // 60)
    return f"Día {dias+1} {horas:02d}:{minutos:02d}"

class LineaProduccion:
    def __init__(self, env, id_linea):
        self.env = env
        self.id_linea = id_linea
        
        # Métricas Productivas
        self.piezas_procesadas = 0
        self.piezas_ng = 0
        self.pallets_finalizados = 0
        
        # Métricas Financieras
        self.tiempo_paros_acumulado = 0 # Segundos
        
        # Analytics
        self.tiempo_operativo_fastening = 0
        self.total_eventos_falla = 0
        
        self.espacio_fisico = simpy.Resource(env, capacity=CAPACIDAD_LINEA_WIP)
        
        self.prob_scrap = random.uniform(0.005, 0.02)
        self.prob_atasco = random.uniform(0.01, 0.04)
        self.prob_tornillo = random.uniform(0.05, 0.09)

        # Maquinaria
        self.machine_housing = simpy.Resource(env, capacity=1)
        self.machine_weigh_1 = simpy.Resource(env, capacity=1)
        self.machine_tim_apply = simpy.Resource(env, capacity=1)
        self.machine_tim_laser = simpy.Resource(env, capacity=1)
        self.machine_weigh_2 = simpy.Resource(env, capacity=1)
        self.machine_pcb_install = simpy.Resource(env, capacity=1)
        self.machine_fastening = simpy.Resource(env, capacity=1)
        self.machine_pcb_laser = simpy.Resource(env, capacity=1)
        self.machine_unload = simpy.Resource(env, capacity=1)

    def registrar_falla(self, duracion):
        self.total_eventos_falla += 1
        self.tiempo_paros_acumulado += duracion # Sumamos tiempo perdido para costo

    def procesar_pallet(self, id_pallet):
        with self.espacio_fisico.request() as req_espacio:
            yield req_espacio
            
            # 1. Housing
            with self.machine_housing.request() as req:
                yield req
                yield self.env.timeout(TC_HOUSING_LOAD)
            
            # 2. Pesaje 1
            with self.machine_weigh_1.request() as req:
                yield req
                for _ in range(PIEZAS_POR_PALLET):
                    yield self.env.timeout(TC_WEIGH_1)

            # 3. TIM Apply
            with self.machine_tim_apply.request() as req:
                yield req
                for _ in range(PIEZAS_POR_PALLET):
                    yield self.env.timeout(TC_TIM_APPLY)

            # 4. TIM Laser
            with self.machine_tim_laser.request() as req:
                yield req
                for _ in range(PIEZAS_POR_PALLET):
                    yield self.env.timeout(TC_TIM_LASER)
                    if random.random() < (self.prob_scrap / 2):
                        self.piezas_ng += 1

            # 5. Pesaje 2
            with self.machine_weigh_2.request() as req:
                yield req
                for _ in range(PIEZAS_POR_PALLET):
                    yield self.env.timeout(TC_WEIGH_2)

            # 6. PCB Install (Falla)
            with self.machine_pcb_install.request() as req:
                yield req
                if random.random() < self.prob_atasco:
                    self.registrar_falla(TIEMPO_CORRECCION_ATASCO)
                    yield self.env.timeout(TIEMPO_CORRECCION_ATASCO)
                yield self.env.timeout(TC_PCB_INSTALL)

            # 7. Fastening
            with self.machine_fastening.request() as req:
                yield req
                start = self.env.now
                tiempo = TC_FASTENING
                if random.random() < self.prob_tornillo:
                    tiempo += TIEMPO_REINTENTO_TORNILLO
                yield self.env.timeout(tiempo)
                self.tiempo_operativo_fastening += (self.env.now - start)

            # 8. PCB Laser
            with self.machine_pcb_laser.request() as req:
                yield req
                for _ in range(PIEZAS_POR_PALLET):
                    yield self.env.timeout(TC_PCB_LASER)
                    if random.random() < (self.prob_scrap / 2):
                        self.piezas_ng += 1

            # 9. Unload
            with self.machine_unload.request() as req:
                yield req
                yield self.env.timeout(TC_UNLOAD)

            self.pallets_finalizados += 1 
            self.piezas_procesadas += PIEZAS_POR_PALLET

def generador_de_flujo(env, linea):
    id_p = 1
    while True:
        env.process(linea.procesar_pallet(id_p))
        id_p += 1
        yield env.timeout(TIEMPO_LLEGADA)

def monitor_progreso(env, lineas):
    # PREPARAR ARCHIVO CSV
    nombre_archivo = "reporte_top_simulacion.csv"
    with open(nombre_archivo, mode='w', newline='') as file:
        writer = csv.writer(file)
        # Encabezados del Excel
        writer.writerow(["Dia_Hora", "Prod_Acumulada", "Scrap_Acumulado", "Eficiencia_Global_%"])
        
        while True:
            yield env.timeout(3600) # Registrar cada hora
            
            total_p = sum(l.piezas_procesadas for l in lineas)
            total_ng = sum(l.piezas_ng for l in lineas)
            if total_p > 0:
                eff = ((total_p - total_ng) / total_p) * 100
            else:
                eff = 0
            
            # Escribir fila en Excel
            writer.writerow([obtener_dia_hora(env.now), total_p, total_ng, f"{eff:.2f}"])
            
            # Barra Visual
            sys.stdout.write(f"\r >> [SIMULANDO] {obtener_dia_hora(env.now)} | Prod: {total_p:,.0f} | CSV Actualizado.")
            sys.stdout.flush()
            time.sleep(DELAY_VISUAL)

# --- EJECUCIÓN PRINCIPAL ---
env = simpy.Environment()
lineas = [LineaProduccion(env, i+1) for i in range(CANTIDAD_LINEAS)]

for linea in lineas:
    env.process(generador_de_flujo(env, linea))

env.process(monitor_progreso(env, lineas))
env.run(until=TIEMPO_SIMULACION)

# --- REPORTE FINAL ---
print("\n\n" + "="*80)
print(f"       RESULTADOS FINALES & FINANCIEROS ({DIAS_SIMULACION} DÍAS)")
print("="*80)

total_ok = 0
total_scrap = 0
total_horas_paro = 0

print(f"{'Línea':<6} | {'Prod OK':<10} | {'Scrap':<8} | {'Eficiencia':<10} | {'$ Pérdida Scrap':<15}")
print("-" * 80)

for l in lineas:
    prod_ok = l.piezas_procesadas - l.piezas_ng
    calidad = (prod_ok / l.piezas_procesadas) if l.piezas_procesadas > 0 else 0
    scrap_rate = (1 - calidad) * 100
    
    # Cálculos Financieros por Línea
    dinero_perdido_scrap = l.piezas_ng * COSTO_SCRAP
    horas_paro = l.tiempo_paros_acumulado / 3600
    
    print(f" #{l.id_linea:<4} | {prod_ok:<10,.0f} | {scrap_rate:5.2f}%  | {calidad*100:6.2f}%    | ${dinero_perdido_scrap:,.2f}")
    
    total_ok += prod_ok
    total_scrap += l.piezas_ng
    total_horas_paro += horas_paro

# --- RESUMEN DE DINERO (LO QUE IMPORTA A LOS JEFES) ---
ingresos_potenciales = total_ok * VALOR_CAMARA_OK
perdidas_scrap = total_scrap * COSTO_SCRAP
perdidas_operativas = total_horas_paro * COSTO_HORA_PARO
total_perdidas = perdidas_scrap + perdidas_operativas

print("="*80)
print(f" RESUMEN EJECUTIVO (USD):")
print(f" [V] VALOR PRODUCCIÓN (Ventas):   ${ingresos_potenciales:,.2f} USD")
print("-" * 80)
print(f" [X] PÉRDIDA POR SCRAP:           ${perdidas_scrap:,.2f} USD")
print(f" [X] PÉRDIDA POR PAROS (Downtime):${perdidas_operativas:,.2f} USD")
print("-" * 80)
print(f" [!] COSTO DE NO-CALIDAD TOTAL:   ${total_perdidas:,.2f} USD")
print("="*80)
print(f"\n [INFO] Se ha generado el archivo 'reporte_top_simulacion.csv' con el historial.")