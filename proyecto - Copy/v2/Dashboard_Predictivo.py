import matplotlib.pyplot as plt
import matplotlib.animation as animation
import pandas as pd
import numpy as np
import os

# CONFIGURACIÓN VISUAL
plt.style.use('dark_background')
fig = plt.figure(figsize=(12, 7))
ax1 = fig.add_subplot(2, 1, 1) 
ax2 = fig.add_subplot(2, 1, 2) 

ARCHIVO_LOGS = "logs_tiempo_real.csv"
ARCHIVO_MTO = "bitacora_mantenimiento.csv"

def predecir_falla(tiempos, salud_actual):
    if len(tiempos) < 10: return None, None, None
    
    x = np.arange(len(salud_actual))
    y = np.array(salud_actual)
    
    if np.all(y == y[0]): return None, None, None
    
    z = np.polyfit(x, y, 1) 
    p = np.poly1d(z)
    
    futuro_x = np.arange(len(salud_actual), len(salud_actual) + 60)
    futuro_y = p(futuro_x)
    
    slope = z[0]
    intercept = z[1]
    
    if slope >= 0: 
        ttf = "Infinito (Estable)"
    else:
        pasos_para_morir = -intercept / slope
        pasos_restantes = pasos_para_morir - len(salud_actual)
        ttf = f"{int(pasos_restantes)} seg" if pasos_restantes > 0 else "YA!"

    return futuro_x, futuro_y, ttf

def animar(i):
    if not os.path.exists(ARCHIVO_LOGS): return
    
    try:
        # Leer últimos 60 registros
        data = pd.read_csv(ARCHIVO_LOGS)
        if data.empty: return
        
        # Filtramos Línea 1
        l1 = data[data['Linea'] == 1].tail(60)
        if l1.empty: return

        timestamps = l1['Timestamp'].values
        salud = l1['Salud'].values
        
        # --- CORRECCIÓN AQUÍ: Usamos 'Tiempo_Ciclo' igual que en el generador ---
        ciclos = l1['Tiempo_Ciclo'].values 

        # --- GRÁFICA 1: TIEMPOS DE CICLO ---
        ax1.clear()
        ax1.plot(timestamps, ciclos, color='cyan', label='Ciclo Real')
        ax1.axhline(y=138, color='white', linestyle=':', alpha=0.5, label='Target (138s)')
        ax1.set_title("MONITOREO DE TIEMPO CICLO - LÍNEA 1")
        ax1.set_ylabel("Segundos")
        ax1.legend(loc='upper left')
        ax1.set_xticks([]) 

        # --- GRÁFICA 2: PREDICCIÓN DE SALUD ---
        ax2.clear()
        x_axis = np.arange(len(salud))
        ax2.plot(x_axis, salud, color='#00ff00', linewidth=2, label='Salud Actual')
        ax2.axhline(y=20, color='red', linestyle='--', label='Falla Inminente')

        # PREDICCIÓN
        fx, fy, ttf = predecir_falla(timestamps, salud)
        
        if fx is not None:
            ax2.plot(fx, fy, color='yellow', linestyle='--', alpha=0.7, label='Tendencia Predictiva (AI)')
            ax2.text(0.02, 0.5, f"TIEMPO PARA FALLA:\n{ttf}", transform=ax2.transAxes, 
                     color='yellow', fontsize=12, fontweight='bold', bbox=dict(facecolor='black', alpha=0.7))

        # DETECTAR MANTENIMIENTO VISUALMENTE
        if os.path.exists(ARCHIVO_MTO):
            try:
                mto = pd.read_csv(ARCHIVO_MTO)
                # Si hay saltos bruscos positivos en salud, dibujamos línea
                diffs = np.diff(salud)
                indices_mto = np.where(diffs > 20)[0] # Si subió mas de 20% de golpe
                for idx in indices_mto:
                    ax2.axvline(x=idx, color='white', linewidth=2)
                    ax2.text(idx, 50, " MTO", color='white', rotation=90)
            except: pass

        ax2.set_title("PREDICCIÓN DE DEGRADACIÓN (DIGITAL TWIN)")
        ax2.set_ylabel("% Salud")
        ax2.set_ylim(0, 110)
        ax2.legend(loc='upper right')
        
        if len(timestamps) > 0:
            etiquetas = [timestamps[i] if i % 10 == 0 else "" for i in range(len(timestamps))]
            ax2.set_xticks(x_axis)
            ax2.set_xticklabels(etiquetas, rotation=45, ha='right')

        plt.tight_layout()

    except Exception as e:
        # Imprimir error solo si no es el de "Time_Ciclo" (que ya arreglamos)
        print(f"Error animacion: {e}")

print("--- DASHBOARD PREDICTIVO INICIADO ---")
# cache_frame_data=False evita el warning que te salía antes
ani = animation.FuncAnimation(fig, animar, interval=1000, cache_frame_data=False)
plt.show()