import simpy
import random

# --- CONFIGURACIÓN DE ESCENARIO (12 HORAS) ---

PIEZAS_POR_PALLET = 12
TIEMPO_SIMULACION = 12 * 3600  

# Ritmo de llegada (Takt Time calibrado)
TIEMPO_LLEGADA = 138 

# --- TIEMPOS DE CICLO ---
TC_HOUSING = 30
TC_WEIGH = 2        
TC_TIM = 45
TC_PCB = 40
TC_FASTENING = 138  
TC_LASER = 5        
TC_UNLOAD = 25

# --- PROBABILIDADES ---
PROB_ATASCO_PCB = 0.05       # 5%
PROB_FALLO_TORNILLO = 0.08   # 8%
PROB_NG_CALIDAD = 0.005      # 0.5%

# Penalizaciones
TIEMPO_CORRECCION_ATASCO = 60 
TIEMPO_REINTENTO_TORNILLO = 15 

def obtener_hora_str(segundos_totales):
    segundos_totales = int(segundos_totales)
    horas = segundos_totales // 3600
    minutos = (segundos_totales % 3600) // 60
    segundos = segundos_totales % 60
    return f"{horas:02d}:{minutos:02d}:{segundos:02d}"

class LineaProduccion:
    def __init__(self, env):
        self.env = env
        self.piezas_procesadas = 0
        self.piezas_ng = 0
        self.pallets_finalizados = 0
        
        # Listas para guardar el historial detallado
        self.log_atascos = []
        self.log_tornillos = []
        self.log_ng = []
        
        # Recursos
        self.housing_load = simpy.Resource(env, capacity=1)
        self.weight_station = simpy.Resource(env, capacity=1)
        self.tim_station = simpy.Resource(env, capacity=1)
        self.pcb_install = simpy.Resource(env, capacity=1)
        self.fastening = simpy.Resource(env, capacity=1)
        self.laser_inspect = simpy.Resource(env, capacity=1)
        self.unload = simpy.Resource(env, capacity=1)

    def procesar_pallet(self, id_pallet):
        # 1. Housing Load
        with self.housing_load.request() as req:
            yield req
            yield self.env.timeout(TC_HOUSING)
        
        # 2. Pesaje Inicial
        with self.weight_station.request() as req:
            yield req
            for _ in range(PIEZAS_POR_PALLET):
                yield self.env.timeout(TC_WEIGH)

        # 3. Aplicación TIM
        with self.tim_station.request() as req:
            yield req
            yield self.env.timeout(TC_TIM)

        # 4. Pesaje TIM
        with self.weight_station.request() as req:
            yield req
            for _ in range(PIEZAS_POR_PALLET):
                yield self.env.timeout(TC_WEIGH)

        # 5. Install PCB (Incidencia: Atasco)
        with self.pcb_install.request() as req:
            yield req
            if random.random() < PROB_ATASCO_PCB:
                hora = obtener_hora_str(self.env.now)
                self.log_atascos.append(f"[{hora}] Pallet {id_pallet}: Máquina detenida {TIEMPO_CORRECCION_ATASCO}s")
                yield self.env.timeout(TIEMPO_CORRECCION_ATASCO)
            yield self.env.timeout(TC_PCB)

        # 6. Fastening (Incidencia: Tornillo)
        with self.fastening.request() as req:
            yield req
            tiempo_actual = TC_FASTENING
            if random.random() < PROB_FALLO_TORNILLO:
                hora = obtener_hora_str(self.env.now)
                self.log_tornillos.append(f"[{hora}] Pallet {id_pallet}: Reintento (+{TIEMPO_REINTENTO_TORNILLO}s)")
                tiempo_actual += TIEMPO_REINTENTO_TORNILLO
            yield self.env.timeout(tiempo_actual)

        # 7. Laser Inspect (Incidencia: NG/Scrap)
        with self.laser_inspect.request() as req:
            yield req
            piezas_ng_en_este_pallet = 0
            for i in range(PIEZAS_POR_PALLET):
                yield self.env.timeout(TC_LASER)
                if random.random() < PROB_NG_CALIDAD: 
                    self.piezas_ng += 1
                    piezas_ng_en_este_pallet += 1
                    hora = obtener_hora_str(self.env.now)
                    self.log_ng.append(f"[{hora}] Pallet {id_pallet}: Pieza #{i+1} DESECHADA (Scrap)")
            
            # Si hubo scrap, la producción neta baja
            # Nota: Las piezas procesadas cuentan las buenas y malas, pero el scrap se resta al final para calidad

        # 8. Unload
        with self.unload.request() as req:
            yield req
            yield self.env.timeout(TC_UNLOAD)

        self.pallets_finalizados += 1 
        self.piezas_procesadas += PIEZAS_POR_PALLET
        
        # Mostrar progreso cada 20 pallets
        if self.pallets_finalizados % 20 == 0:
            print(f"[{obtener_hora_str(self.env.now)}] ... Progreso: {self.pallets_finalizados} Pallets")

def generador_de_flujo(env, linea):
    id_p = 1
    while True:
        env.process(linea.procesar_pallet(id_p))
        id_p += 1
        yield env.timeout(TIEMPO_LLEGADA)

# --- EJECUCIÓN ---
print(f"--- INICIANDO SIMULACIÓN DETALLADA (12 HORAS) ---")
env = simpy.Environment()
linea_top = LineaProduccion(env)
env.process(generador_de_flujo(env, linea_top))
env.run(until=TIEMPO_SIMULACION)

# --- REPORTE DETALLADO (LOG) ---
piezas_ok = linea_top.piezas_procesadas - linea_top.piezas_ng
produccion_planta = piezas_ok * 2 # Proyección 2 líneas

print("\n" + "="*60)
print("       BITÁCORA DE INCIDENCIAS (TOP)")
print("="*60)

print(f"\n--- [!] ATASCOS DE PCB (Paros de Línea) ---")
if linea_top.log_atascos:
    for evento in linea_top.log_atascos:
        print(evento)
else:
    print("Sin incidencias registradas.")

print(f"\n--- [!] FALLOS DE TORNILLO (Micro-paros) ---")
if linea_top.log_tornillos:
    for evento in linea_top.log_tornillos:
        print(evento)
else:
    print("Sin incidencias registradas.")

print(f"\n--- [X] REPORTE DE SCRAP (PIEZAS NG) ---")
if linea_top.log_ng:
    for evento in linea_top.log_ng:
        print(evento)
    print(f"TOTAL NG: {linea_top.piezas_ng} piezas perdidas.")
else:
    print("Calidad Perfecta (0 Scrap).")

print("\n" + "="*60)
print("       RESUMEN EJECUTIVO")
print("="*60)
print(f" Duración:              {obtener_hora_str(env.now)}")
print(f" Piezas PRODUCIDAS (OK): {piezas_ok} (por línea)")
print(f" Proyección PLANTA:     {produccion_planta} piezas totales")

if 7200 <= produccion_planta <= 7600:
    print(f" ESTADO DE META:        CUMPLIDA (Dentro de rango)")
elif produccion_planta < 7200:
    print(f" ESTADO DE META:        NO CUMPLIDA (Afectada por paros/scrap)")
else:
    print(f" ESTADO DE META:        SOBREPRODUCCIÓN")
print("="*60)