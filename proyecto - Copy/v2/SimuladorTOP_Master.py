import simpy
import random
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import sys

# --- CONFIGURACIÓN DE INGENIERÍA ---
COSTO_SCRAP = 45.00        # USD por pieza
COSTO_HORA_PARO = 500.00   # USD por hora línea detenida
META_OEE = 85.0            # % Meta Corporativa

def tiempo_gauss(media, desv):
    return max(0.1, np.random.normal(media, desv))

class LineaProduccion:
    def __init__(self, env, id_linea):
        self.env = env
        self.id = id_linea
        self.piezas_ok = 0
        self.piezas_ng = 0
        self.tiempo_paros = 0
        self.ciclos_log = []
        
        # Recurso Limitado (Máquina Cuello de Botella - Fastening)
        self.maquina = simpy.Resource(env, capacity=1)
        
        # Perfil de la línea (Variabilidad única)
        self.sigma = random.uniform(0.5, 3.0) 
        self.yield_rate = random.uniform(0.95, 0.99)

    def procesar(self):
        while True:
            t_inicio = self.env.now
            with self.maquina.request() as req:
                yield req
                
                # Simular Tiempo de Ciclo (Gaussiano)
                tc = tiempo_gauss(138, self.sigma)
                
                # Simular Micro-Fallas Aleatorias
                if random.random() < 0.02: # 2% prob de paro
                    t_paro = random.randint(30, 180)
                    self.tiempo_paros += t_paro
                    yield self.env.timeout(t_paro)
                
                yield self.env.timeout(tc)
                
                # Calidad (Scrap)
                es_scrap = random.random() > self.yield_rate
                if es_scrap:
                    self.piezas_ng += 1
                else:
                    self.piezas_ok += 1
                
                # Guardar datos para análisis Sigma
                self.ciclos_log.append(tc)

def correr_simulacion():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("="*80)
    print("   GEMELO DIGITAL: SIMULADOR TOP & FINANCIERO")
    print("="*80)
    
    dias = int(input(" > Días a simular: "))
    tiempo_total = dias * 24 * 3600
    
    env = simpy.Environment()
    lineas = [LineaProduccion(env, i+1) for i in range(12)]
    
    for l in lineas:
        env.process(l.procesar())
        
    print(f" [RUN] Simulando {dias} días de operación continua...")
    env.run(until=tiempo_total)
    
    # --- REPORTING ---
    datos = []
    print("\n" + "-"*80)
    print(f"{'Línea':<6} | {'Prod OK':<10} | {'Scrap':<8} | {'OEE %':<8} | {'Pérdida ($)':<15}")
    print("-" * 80)
    
    total_perdida_planta = 0
    
    for l in lineas:
        total_pzs = l.piezas_ok + l.piezas_ng
        disponibilidad = (tiempo_total - l.tiempo_paros) / tiempo_total
        calidad = l.piezas_ok / total_pzs if total_pzs > 0 else 0
        rendimiento = 1.0 # Asumido para simplificar
        oee = disponibilidad * calidad * rendimiento * 100
        
        costo = (l.piezas_ng * COSTO_SCRAP) + ((l.tiempo_paros/3600)*COSTO_HORA_PARO)
        total_perdida_planta += costo
        
        datos.append({
            "Linea": l.id, "OEE": oee, "Perdida": costo, 
            "Sigma": np.std(l.ciclos_log), "Scrap": l.piezas_ng
        })
        
        print(f" #{l.id:<4} | {l.piezas_ok:<10} | {l.piezas_ng:<8} | {oee:6.2f}%  | ${costo:,.2f}")

    print("="*80)
    print(f" TOTAL PÉRDIDA PLANTA: ${total_perdida_planta:,.2f} USD")
    
    # Generar Gráfica Rápida
    df = pd.DataFrame(datos)
    plt.style.use('ggplot')
    plt.bar(df['Linea'], df['Perdida'], color='maroon')
    plt.title(f'Pérdidas Financieras por Línea ({dias} Días)')
    plt.ylabel('USD ($)')
    plt.xlabel('Línea de Producción')
    plt.savefig('Reporte_Financiero.png')
    print(" [EXPORT] Gráfica guardada como 'Reporte_Financiero.png'")

if __name__ == "__main__":
    correr_simulacion()