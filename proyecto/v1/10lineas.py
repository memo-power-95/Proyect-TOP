import simpy
import random

# --- CONFIGURACIÓN DE LA NAVE (10 LÍNEAS - 12 HORAS) ---
CANTIDAD_LINEAS = 10
PIEZAS_POR_PALLET = 12
TIEMPO_SIMULACION = 12 * 3600  # 43,200 segundos

# Ritmo (Takt Time)
TIEMPO_LLEGADA = 138 

# --- TIEMPOS DE CICLO ---
TC_HOUSING = 30
TC_WEIGH = 2        
TC_TIM = 45
TC_PCB = 40
TC_FASTENING = 138
TC_LASER = 5        
TC_UNLOAD = 25

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
    def __init__(self, env, id_linea):
        self.env = env
        self.id_linea = id_linea
        self.piezas_procesadas = 0
        self.piezas_ng = 0
        self.pallets_finalizados = 0
        
        
        self.bitacora_atascos = []
        self.bitacora_tornillos = []
        self.bitacora_scrap = []
     
        self.prob_scrap_local = random.uniform(0.01, 0.07)
        self.prob_atasco_local = random.uniform(0.03, 0.06) 
        self.prob_tornillo_local = random.uniform(0.05, 0.10) 

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

        # 3. TIM Apply
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
            if random.random() < self.prob_atasco_local:
                hora = obtener_hora_str(self.env.now)
                msg = f"[{hora}] LÍNEA {self.id_linea:02d} | Pallet {id_pallet}: [PARO] Atasco PCB ({TIEMPO_CORRECCION_ATASCO}s)"
                self.bitacora_atascos.append((self.env.now, msg))
                yield self.env.timeout(TIEMPO_CORRECCION_ATASCO)
            yield self.env.timeout(TC_PCB)

        # 6. Fastening (Incidencia: Tornillo)
        with self.fastening.request() as req:
            yield req
            tiempo_actual = TC_FASTENING
            if random.random() < self.prob_tornillo_local:
                hora = obtener_hora_str(self.env.now)
                msg = f"[{hora}] LÍNEA {self.id_linea:02d} | Pallet {id_pallet}: [WARN] Fallo Tornillo (+{TIEMPO_REINTENTO_TORNILLO}s)"
                self.bitacora_tornillos.append((self.env.now, msg))
                tiempo_actual += TIEMPO_REINTENTO_TORNILLO
            yield self.env.timeout(tiempo_actual)

        # 7. Laser Inspect (Incidencia: Scrap)
        with self.laser_inspect.request() as req:
            yield req
            for i in range(PIEZAS_POR_PALLET):
                yield self.env.timeout(TC_LASER)
                if random.random() < self.prob_scrap_local: 
                    self.piezas_ng += 1
                    hora = obtener_hora_str(self.env.now)
                    msg = f"[{hora}] LÍNEA {self.id_linea:02d} | Pallet {id_pallet}: [SCRAP] Pieza #{i+1} NG"
                    self.bitacora_scrap.append((self.env.now, msg))

        # 8. Unload
        with self.unload.request() as req:
            yield req
            yield self.env.timeout(TC_UNLOAD)

        self.pallets_finalizados += 1 
        self.piezas_procesadas += PIEZAS_POR_PALLET

def generador_de_flujo(env, linea):
    id_p = 1
    while True:
        env.process(linea.procesar_pallet(id_p))
        id_p += 1
        yield env.timeout(TIEMPO_LLEGADA + random.randint(-2, 2))

# --- EJECUCIÓN ---
print(f"--- INICIANDO GEMELO DIGITAL NAVE INDUSTRIAL ({CANTIDAD_LINEAS} LÍNEAS) ---")
env = simpy.Environment()

lineas_top = []
for i in range(CANTIDAD_LINEAS):
    nueva_linea = LineaProduccion(env, id_linea=i+1)
    lineas_top.append(nueva_linea)
    env.process(generador_de_flujo(env, nueva_linea))

env.run(until=TIEMPO_SIMULACION)

# --- RECOPILACIÓN Y ORDENAMIENTO DE DATOS ---
total_planta_ok = 0
total_planta_scrap = 0

# Juntamos todos los reportes de las 10 líneas en listas maestras
todos_atascos = []
todos_tornillos = []
todos_scrap = []

for l in lineas_top:
    todos_atascos.extend(l.bitacora_atascos)
    todos_tornillos.extend(l.bitacora_tornillos)
    todos_scrap.extend(l.bitacora_scrap)
    
    total_planta_ok += (l.piezas_procesadas - l.piezas_ng)
    total_planta_scrap += l.piezas_ng

# Ordenamos cronológicamente (por el tiempo en segundos, que es el primer elemento de la tupla)
todos_atascos.sort(key=lambda x: x[0])
todos_tornillos.sort(key=lambda x: x[0])
todos_scrap.sort(key=lambda x: x[0])

# --- REPORTES DESGLOSADOS ---

print("\n" + "="*80)
print(f"       BITÁCORA DE PAROS MAYORES (ATASCOS PCB)")
print(f"       Total Eventos: {len(todos_atascos)}")
print("="*80)
# Mostramos todos (o podrías limitar con [:50] si son demasiados)
for _, msg in todos_atascos:
    print(msg)

print("\n" + "="*80)
print(f"       BITÁCORA DE MICRO-PAROS (FALLOS TORNILLO)")
print(f"       Total Eventos: {len(todos_tornillos)}")
print("="*80)
for _, msg in todos_tornillos:
    print(msg)

print("\n" + "="*80)
print(f"       BITÁCORA DE CALIDAD (PIEZAS NG/SCRAP)")
print(f"       Total Piezas Desechadas: {len(todos_scrap)}")
print("="*80)
for _, msg in todos_scrap:
    print(msg)

# --- RESUMEN FINAL ---
print("\n" + "#"*90)
print(f"       RESUMEN EJECUTIVO FINAL (12 HORAS)")
print("#"*90)
print(f" {'Línea':<8} | {'Prod. Total':<12} | {'Piezas OK':<10} | {'Scrap (NG)':<10} | {'Eficiencia':<12} | {'Estado':<10}")
print("-" * 90)

# Ordenar reporte final por eficiencia
lineas_ordenadas = sorted(lineas_top, key=lambda x: (x.piezas_procesadas - x.piezas_ng)/x.piezas_procesadas if x.piezas_procesadas > 0 else 0, reverse=True)

for linea in lineas_ordenadas:
    total = linea.piezas_procesadas
    scrap = linea.piezas_ng
    ok = total - scrap
    eff = (ok / total) * 100 if total > 0 else 0
    
    if eff >= 98: status = "EXCELENTE"
    elif eff >= 95: status = "NORMAL"
    elif eff >= 93: status = "ALERTA"
    else: status = "CRÍTICO"

    print(f" #{linea.id_linea:<7} | {total:<12} | {ok:<10} | {scrap:<10} | {eff:.2f}%       | {status:<10}")

print("-" * 90)
eff_global = (total_planta_ok / (total_planta_ok + total_planta_scrap)) * 100
print(f" TOTAL PLANTA: {total_planta_ok} piezas OK | SCRAP TOTAL: {total_planta_scrap} | EFICIENCIA: {eff_global:.2f}%")
print("#"*90)