import simpy
import random
import time
import sys
import pandas as pd
import matplotlib.pyplot as plt
import os

# --- CONFIGURACIÓN ---
print("\n" + "="*80)
print("   GEMELO DIGITAL: TOP ANALYTICS & VISUALIZATION SUITE")
print("="*80)

try:
    input_dias = input(" [1] Días a simular (Ej. 7): ")
    DIAS_SIMULACION = int(input_dias)
    input_lineas = input(" [2] Líneas activas (Ej. 12): ")
    CANTIDAD_LINEAS = int(input_lineas)
except:
    DIAS_SIMULACION = 7
    CANTIDAD_LINEAS = 12

print(f" > MOTOR DE DATOS: PANDAS + MATPLOTLIB ACTIVADOS")
time.sleep(1)

# --- PARÁMETROS ---
TIEMPO_SIMULACION = DIAS_SIMULACION * 24 * 3600
# Para demostración rápida, aceleramos el delay visual
DELAY_VISUAL = 30 / (DIAS_SIMULACION * 24) 

PIEZAS_POR_PALLET = 12
TIEMPO_LLEGADA_NOMINAL = 138 

# Costos
COSTO_SCRAP = 45.00
COSTO_HORA_PARO = 500.00

# Tiempos de Ciclo (Media, Desviación)
TC_HOUSING_LOAD = (30, 0.5)
TC_WEIGH_1 = (2, 0.1)
TC_TIM_APPLY = (4, 0.2)
TC_TIM_LASER = (3, 0.1)
TC_WEIGH_2 = (2, 0.1)
TC_PCB_INSTALL = (40, 1.0)
TC_FASTENING = (138, 3.0) 
TC_PCB_LASER = (4, 0.1)
TC_UNLOAD = (25, 0.5)

TIEMPO_CORRECCION_ATASCO = 60
TIEMPO_REINTENTO_TORNILLO = 15

# ALMACENAMIENTO DE DATOS EN MEMORIA (LISTA DE DICCIONARIOS)
data_log = []

def tiempo_gauss(parametros):
    media, desv = parametros
    return max(0.1, random.gauss(media, desv))

class LineaProduccion:
    def __init__(self, env, id_linea):
        self.env = env
        self.id_linea = id_linea
        self.piezas_procesadas = 0
        self.piezas_ng = 0
        self.tiempo_paros = 0
        
        self.espacio_fisico = simpy.Resource(env, capacity=12)
        
        # Perfil de riesgo único por línea
        self.prob_scrap = random.uniform(0.005, 0.025)
        self.prob_atasco = random.uniform(0.01, 0.04)
        self.prob_tornillo = random.uniform(0.05, 0.10)

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

    def registrar_falla(self, duracion, tipo):
        self.tiempo_paros += duracion
        # Loguear evento específico para análisis detallado
        data_log.append({
            "Tiempo_Seg": self.env.now,
            "Dia": int(self.env.now // 86400) + 1,
            "Linea": self.id_linea,
            "Evento": "Falla",
            "Tipo": tipo,
            "Costo": (duracion/3600)*COSTO_HORA_PARO
        })

    def procesar_pallet(self, id_pallet):
        with self.espacio_fisico.request() as req:
            yield req
            
            # --- FLUJO DE PROCESO (Resumido para enfoque en datos) ---
            with self.machine_housing.request() as req_m:
                yield req_m
                yield self.env.timeout(tiempo_gauss(TC_HOUSING_LOAD))

            with self.machine_weigh_1.request() as req_m:
                yield req_m
                for _ in range(PIEZAS_POR_PALLET): yield self.env.timeout(tiempo_gauss(TC_WEIGH_1))
            
            with self.machine_tim_apply.request() as req_m:
                yield req_m
                for _ in range(PIEZAS_POR_PALLET): yield self.env.timeout(tiempo_gauss(TC_TIM_APPLY))

            with self.machine_tim_laser.request() as req_m:
                yield req_m
                for _ in range(PIEZAS_POR_PALLET): 
                    yield self.env.timeout(tiempo_gauss(TC_TIM_LASER))
                    if random.random() < (self.prob_scrap/2):
                        self.piezas_ng += 1
                        data_log.append({"Tiempo_Seg": self.env.now, "Dia": int(self.env.now//86400)+1, "Linea": self.id_linea, "Evento": "Scrap", "Tipo": "TIM Defect", "Costo": COSTO_SCRAP})

            with self.machine_weigh_2.request() as req_m:
                yield req_m
                for _ in range(PIEZAS_POR_PALLET): yield self.env.timeout(tiempo_gauss(TC_WEIGH_2))

            # PCB Install (Posible Atasco)
            with self.machine_pcb_install.request() as req_m:
                yield req_m
                if random.random() < self.prob_atasco:
                    self.registrar_falla(TIEMPO_CORRECCION_ATASCO, "Atasco PCB")
                    yield self.env.timeout(TIEMPO_CORRECCION_ATASCO)
                yield self.env.timeout(tiempo_gauss(TC_PCB_INSTALL))

            # Fastening (Cuello botella)
            with self.machine_fastening.request() as req_m:
                yield req_m
                t = tiempo_gauss(TC_FASTENING)
                if random.random() < self.prob_tornillo:
                    t += TIEMPO_REINTENTO_TORNILLO
                yield self.env.timeout(t)

            with self.machine_pcb_laser.request() as req_m:
                yield req_m
                for _ in range(PIEZAS_POR_PALLET): 
                    yield self.env.timeout(tiempo_gauss(TC_PCB_LASER))
                    if random.random() < (self.prob_scrap/2):
                        self.piezas_ng += 1
                        data_log.append({"Tiempo_Seg": self.env.now, "Dia": int(self.env.now//86400)+1, "Linea": self.id_linea, "Evento": "Scrap", "Tipo": "PCB Defect", "Costo": COSTO_SCRAP})

            with self.machine_unload.request() as req_m:
                yield req_m
                yield self.env.timeout(tiempo_gauss(TC_UNLOAD))

            self.piezas_procesadas += PIEZAS_POR_PALLET
            
            # Log de Producción (Cada pallet cuenta)
            data_log.append({
                "Tiempo_Seg": self.env.now,
                "Dia": int(self.env.now // 86400) + 1,
                "Linea": self.id_linea,
                "Evento": "Produccion",
                "Tipo": "Pallet OK",
                "Costo": 0 # Ganancia no se registra aquí como costo
            })

def generador_de_flujo(env, linea):
    id_p = 1
    while True:
        env.process(linea.procesar_pallet(id_p))
        id_p += 1
        yield env.timeout(TIEMPO_LLEGADA_NOMINAL)

def monitor_progreso(env):
    while True:
        yield env.timeout(3600 * 4) # Actualizar consola cada 4 horas simuladas
        dia = int(env.now // 86400) + 1
        sys.stdout.write(f"\r >> [SIMULANDO] Día {dia} | Procesando datos en tiempo real...")
        sys.stdout.flush()
        time.sleep(DELAY_VISUAL)

# --- EJECUCIÓN ---
env = simpy.Environment()
lineas = [LineaProduccion(env, i+1) for i in range(CANTIDAD_LINEAS)]

for l in lineas:
    env.process(generador_de_flujo(env, l))

env.process(monitor_progreso(env))
env.run(until=TIEMPO_SIMULACION)

print("\n\n" + "="*80)
print("   GENERANDO ANÁLISIS DE DATOS Y GRÁFICAS (ESPERE...)")
print("="*80)

# --- ANÁLISIS CON PANDAS ---
df = pd.DataFrame(data_log)

# 1. Resumen por Línea
df_scrap = df[df["Evento"] == "Scrap"]
df_prod = df[df["Evento"] == "Produccion"]
df_fallas = df[df["Evento"] == "Falla"]

resumen = df.groupby("Linea").agg(
    Produccion_Pallets=('Evento', lambda x: (x=='Produccion').sum()),
    Total_Scrap_Piezas=('Evento', lambda x: (x=='Scrap').sum()),
    Costo_Total=('Costo', 'sum')
).reset_index()

resumen['Piezas_OK'] = (resumen['Produccion_Pallets'] * 12) - resumen['Total_Scrap_Piezas']
resumen['Eficiencia_%'] = (resumen['Piezas_OK'] / (resumen['Produccion_Pallets'] * 12)) * 100

print(resumen.to_string(index=False))

# --- GENERACIÓN DE GRÁFICAS ---

# Configuración de estilo
plt.style.use('ggplot')
fig, axs = plt.subplots(2, 2, figsize=(15, 10))
fig.suptitle(f'REPORTE DE SIMULACIÓN TOP - {DIAS_SIMULACION} DÍAS', fontsize=16)

# GRÁFICA 1: Producción vs Scrap por Línea (Barras Apiladas)
lineas_id = resumen['Linea']
pzas_ok = resumen['Piezas_OK']
pzas_ng = resumen['Total_Scrap_Piezas']

axs[0, 0].bar(lineas_id, pzas_ok, label='Piezas OK', color='#2ecc71')
axs[0, 0].bar(lineas_id, pzas_ng, bottom=pzas_ok, label='Scrap (NG)', color='#e74c3c')
axs[0, 0].set_title('Volumen de Producción y Calidad por Línea')
axs[0, 0].set_xlabel('Línea de Producción')
axs[0, 0].set_ylabel('Cantidad de Piezas')
axs[0, 0].legend()

# GRÁFICA 2: Costo Financiero Acumulado (Línea de Tiempo)
df['Costo_Acumulado'] = df['Costo'].cumsum()
# Muestrear cada 100 eventos para no saturar la gráfica
df_sample = df.iloc[::100, :]
axs[0, 1].plot(df_sample['Tiempo_Seg']/3600, df_sample['Costo_Acumulado'], color='#c0392b', linewidth=2)
axs[0, 1].set_title('Acumulación de Pérdidas Financieras (USD)')
axs[0, 1].set_xlabel('Horas de Operación')
axs[0, 1].set_ylabel('Dólares Perdidos (Scrap + Paros)')
axs[0, 1].grid(True)

# GRÁFICA 3: Distribución de Tipos de Fallas (Pastel)
fallas_counts = df_fallas['Tipo'].value_counts()
if len(fallas_counts) > 0:
    axs[1, 0].pie(fallas_counts, labels=fallas_counts.index, autopct='%1.1f%%', startangle=90, colors=['#f1c40f', '#e67e22', '#95a5a6'])
    axs[1, 0].set_title('Distribución de Causas de Paro')
else:
    axs[1, 0].text(0.5, 0.5, 'Sin Fallas Mayores', ha='center')

# GRÁFICA 4: Eficiencia OEE por Línea (Scatter Plot)
colors = ['green' if x >= 98 else 'orange' if x >= 95 else 'red' for x in resumen['Eficiencia_%']]
axs[1, 1].scatter(resumen['Linea'], resumen['Eficiencia_%'], c=colors, s=100)
axs[1, 1].set_ylim(90, 100)
axs[1, 1].axhline(y=95, color='blue', linestyle='--', label='Meta (95%)')
axs[1, 1].set_title('Eficiencia Global por Línea')
axs[1, 1].set_xlabel('Línea')
axs[1, 1].set_ylabel('Eficiencia (%)')
axs[1, 1].legend()

# Guardar imagen
plt.tight_layout()
plt.savefig('analisis_top_graficas.png')
print(f"\n [OK] Gráficas generadas exitosamente: 'analisis_top_graficas.png'")

# --- ANÁLISIS EXTENSO DE TEXTO ---
print("\n" + "="*80)
print("   ANÁLISIS EXTENSO DE ANOMALÍAS")
print("="*80)

peor_linea = resumen.loc[resumen['Costo_Total'].idxmax()]
mejor_linea = resumen.loc[resumen['Costo_Total'].idxmin()]

print(f"1. DESEMPEÑO FINANCIERO:")
print(f"   - La LÍNEA CRÍTICA es la #{int(peor_linea['Linea'])}.")
print(f"   - Esta línea generó pérdidas por ${peor_linea['Costo_Total']:,.2f} USD.")
print(f"   - Causa probable: Revisar calibración de máquina 'PCB Install' (Alta tasa de atascos simulada).")

print(f"\n2. ANÁLISIS DE CALIDAD:")
print(f"   - El Scrap total de la planta fue de {resumen['Total_Scrap_Piezas'].sum()} piezas.")
print(f"   - La eficiencia promedio de la planta es {resumen['Eficiencia_%'].mean():.2f}%.")
if resumen['Eficiencia_%'].mean() < 96:
    print("   - [ALERTA] El promedio está por debajo del estándar mundial (96%). Se sugiere auditoría de proceso.")

print(f"\n3. MODELO DE TENDENCIA:")
print(f"   - La LÍNEA MODELO es la #{int(mejor_linea['Linea'])}, con solo ${mejor_linea['Costo_Total']:,.2f} USD de pérdida.")
print(f"   - Se recomienda replicar los parámetros de mantenimiento de la Línea #{int(mejor_linea['Linea'])} en las demás.")

print("="*80)