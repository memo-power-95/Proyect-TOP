import matplotlib.pyplot as plt
import matplotlib.animation as animation
import pandas as pd
import os

plt.style.use('dark_background')
fig = plt.figure(figsize=(10, 6))
ax = fig.add_subplot(1,1,1)

def animar(i):
    if not os.path.exists("logs_tiempo_real.csv"): return
    try:
        data = pd.read_csv("logs_tiempo_real.csv").tail(60) # Últimos 60 seg
        l1 = data[data['Linea'] == 1] # Visualizar Línea 1
        
        ax.clear()
        ax.plot(l1['Timestamp'], l1['Salud'], color='#00ff00', label='Salud (%)')
        ax.plot(l1['Timestamp'], l1['TC'], color='cyan', label='Tiempo Ciclo (s)')
        
        # Zona crítica
        ax.axhline(y=40, color='red', linestyle='--', label='Falla Inminente')
        
        # Buscar mantenimientos
        if os.path.exists("bitacora_mantenimiento.csv"):
            mto = pd.read_csv("bitacora_mantenimiento.csv")
            for t in mto['Timestamp'].values:
                hora_mto = t.split(' ')[1] # Solo hora
                if hora_mto in l1['Timestamp'].values:
                    ax.axvline(x=hora_mto, color='yellow', linewidth=3)
                    ax.text(hora_mto, 50, " REPARACIÓN", color='yellow', rotation=90)
        
        ax.set_title("MONITOREO EN VIVO - LÍNEA 1 (TOP)")
        ax.legend(loc='upper left')
        ax.set_ylim(0, 200)
        plt.xticks(rotation=45, ha='right')
    except: pass

ani = animation.FuncAnimation(fig, animar, interval=1000)
plt.show()