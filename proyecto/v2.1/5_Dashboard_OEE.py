import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os
import matplotlib.animation as animation
import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# CONFIGURACIÓN
ARCHIVO_LOGS = "logs_tiempo_real.csv"
CYCLE_TIME_IDEAL = 138.0  # Segundos

# Colores Corporativos
COLOR_FONDO = '#1e1e1e' # Gris oscuro elegante
COLOR_TEXTO = 'white'
COLOR_OEE_BAJO = '#e74c3c'  # Rojo
COLOR_OEE_MEDIO = '#f1c40f' # Amarillo
COLOR_OEE_ALTO = '#2ecc71'  # Verde

plt.rcParams['text.color'] = COLOR_TEXTO
plt.rcParams['axes.labelcolor'] = COLOR_TEXTO
plt.rcParams['xtick.color'] = COLOR_TEXTO
plt.rcParams['ytick.color'] = COLOR_TEXTO

fig = plt.figure(figsize=(14, 8), facecolor=COLOR_FONDO)
grid = plt.GridSpec(2, 3, height_ratios=[1, 2], hspace=0.4)

# Subplots
ax_global = fig.add_subplot(grid[0, :], facecolor=COLOR_FONDO) # Barra OEE Global arriba
ax_l1 = fig.add_subplot(grid[1, 0], facecolor=COLOR_FONDO)     # Línea 1
ax_l2 = fig.add_subplot(grid[1, 1], facecolor=COLOR_FONDO)     # Línea 2
ax_empty = fig.add_subplot(grid[1, 2], facecolor=COLOR_FONDO)

axes_lineas = {1: ax_l1, 2: ax_l2}

# GUI state (se configura en la app)
APP = None
DEFAULT_LINE = 1

def calcular_oee(df_linea):
    if df_linea.empty: return 0, 0, 0, 0
    
    total_registros = len(df_linea)
    
    # 1. DISPONIBILIDAD
    # (Tiempo que NO estuvo en Mantenimiento / Tiempo Total)
    tiempo_paro = len(df_linea[df_linea['Evento'] == 'MANTENIMIENTO'])
    disponibilidad = (total_registros - tiempo_paro) / total_registros if total_registros > 0 else 0
    
    # Filtrar solo tiempo operativo para los siguientes cálculos
    df_op = df_linea[df_linea['Evento'] != 'MANTENIMIENTO']
    if df_op.empty: return disponibilidad * 100, 0, 0, 0

    # 2. CALIDAD
    # (Piezas que NO fueron Scrap / Total Piezas Producidas)
    # Buscamos eventos que contengan "SCRAP"
    scrap_count = len(df_op[df_op['Evento'].str.contains('SCRAP', na=False)])
    calidad = (len(df_op) - scrap_count) / len(df_op)
    
    # 3. RENDIMIENTO (Performance)
    # (Tiempo Ciclo Ideal / Tiempo Ciclo Real Promedio)
    tc_promedio = df_op['Tiempo_Ciclo'].mean()
    if tc_promedio < CYCLE_TIME_IDEAL: tc_promedio = CYCLE_TIME_IDEAL # No puede ser > 100%
    rendimiento = CYCLE_TIME_IDEAL / tc_promedio if tc_promedio > 0 else 0

    # 4. OEE
    oee = disponibilidad * calidad * rendimiento
    
    return disponibilidad*100, calidad*100, rendimiento*100, oee*100

def dibujar_medidor(ax, nombre, disp, cal, rend, oee):
    ax.clear()
    
    # Definir color según el OEE
    color_barra = COLOR_OEE_ALTO if oee >= 85 else COLOR_OEE_MEDIO if oee >= 65 else COLOR_OEE_BAJO
    
    # Barras Horizontales
    metricas = ['OEE', 'Rendimiento', 'Calidad', 'Disponibilidad']
    valores = [oee, rend, cal, disp]
    colores = [color_barra, '#3498db', '#9b59b6', '#e67e22']
    
    y_pos = np.arange(len(metricas))
    
    rects = ax.barh(y_pos, valores, align='center', color=colores, height=0.6)
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(metricas, fontsize=10)
    ax.set_xlim(0, 110) # Escala 0 a 110%
    ax.set_title(f"{nombre}\n{oee:.1f}%", fontsize=16, fontweight='bold', color=color_barra)
    
    # Quitar bordes feos
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_color('gray')
    ax.spines['left'].set_visible(False)
    
    # Poner el valor numérico al final de la barra
    for i, rect in enumerate(rects):
        width = rect.get_width()
        ax.text(width + 2, rect.get_y() + rect.get_height()/2, 
                f'{valores[i]:.1f}%', ha='left', va='center', color='white', fontweight='bold')

def animar(i):
    global APP
    if not os.path.exists(ARCHIVO_LOGS):
        return
    if APP is not None and APP.paused.get():
        return
    try:
        df = pd.read_csv(ARCHIVO_LOGS)
        if df.empty:
            return

        # Solo dibujar la línea seleccionada (modo single-line)
        selected = DEFAULT_LINE
        if APP is not None:
            try:
                selected = int(APP.selected_line.get())
            except Exception:
                selected = DEFAULT_LINE

        oee_global_acum = 0
        lineas_activas = 0

        # Limpiar ejes no usados
        for lid in [1, 2]:
            if lid != selected:
                axes_lineas[lid].clear()
                axes_lineas[lid].text(0.5, 0.5, f"LÍNEA {lid} (oculta)", ha='center', color='gray')

        ax_empty.clear()
        ax_empty.axis('off')
        ax_empty.text(0.5, 0.5, 'Modo 2 lineas', ha='center', color='gray')

        df_l = df[df['Linea'] == selected]
        d, c, r, o = calcular_oee(df_l)
        dibujar_medidor(axes_lineas[selected], f"LÍNEA {selected}", d, c, r, o)
        oee_global_acum += o
        if not df_l.empty:
            lineas_activas += 1

        # --- DIBUJAR GLOBAL ---
        ax_global.clear()
        # En modo single-line, el global es la misma métrica de la línea seleccionada
        oee_promedio = oee_global_acum / lineas_activas if lineas_activas > 0 else 0

        color_g = COLOR_OEE_ALTO if oee_promedio >= 85 else COLOR_OEE_MEDIO if oee_promedio >= 65 else COLOR_OEE_BAJO

        # Un gran velocímetro digital para el Global
        ax_global.text(0.5, 0.6, "EFICIENCIA GLOBAL DE PLANTA (OEE)",
                       ha='center', va='center', fontsize=18, color='gray')
        ax_global.text(0.5, 0.3, f"{oee_promedio:.1f}%",
                       ha='center', va='center', fontsize=60, fontweight='bold', color=color_g)

        # Barra de progreso inferior
        ax_global.barh([0], [oee_promedio], color=color_g, height=0.1)
        ax_global.set_xlim(0, 100)
        ax_global.axis('off')  # Ocultar ejes para que parezca letrero LED

        # Si estamos embebidos en Tk, refrescar canvas
        if APP is not None and APP.canvas is not None:
            APP.canvas.draw_idle()

    except Exception as e:
        print(f"Calculando... {e}")

class DashboardApp:
    def __init__(self, master):
        self.master = master
        self.master.title('Dashboard OEE - TOP')

        self.paused = tk.BooleanVar(value=False)
        # Selected single line (string var for Combobox)
        self.selected_line = tk.StringVar(value=str(DEFAULT_LINE))
        self.interval = tk.IntVar(value=2000)
        self.canvas = None
        self.ani = None

        self._build()

    def _build(self):
        frm = ttk.Frame(self.master, padding=6)
        frm.pack(fill='both', expand=True)

        left = ttk.Frame(frm)
        left.pack(side='left', fill='y')

        ttk.Label(left, text='Controles', font=('Segoe UI', 12, 'bold')).pack(pady=4)

        ttk.Label(left, text='Línea (single-line mode):').pack(anchor='w')
        cbo = ttk.Combobox(left, values=[1,2], textvariable=self.selected_line, state='readonly', width=6)
        cbo.pack(anchor='w', pady=2)

        self.btn_pause = ttk.Button(left, text='Pausar', command=self.toggle_pause)
        self.btn_pause.pack(fill='x', pady=8)

        ttk.Label(left, text='Intervalo (ms)').pack()
        scale = ttk.Scale(left, from_=500, to=5000, orient='horizontal', variable=self.interval, command=self.on_interval_change)
        scale.pack(fill='x', pady=4)

        # Área de gráfico
        right = ttk.Frame(frm)
        right.pack(side='right', fill='both', expand=True)

        canvas = FigureCanvasTkAgg(fig, master=right)
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.pack(fill='both', expand=True)
        self.canvas = canvas

    def toggle_pause(self):
        self.paused.set(not self.paused.get())
        self.btn_pause.config(text='Reanudar' if self.paused.get() else 'Pausar')

    def on_interval_change(self, *_):
        if self.ani is not None:
            self.ani.event_source.interval = int(self.interval.get())


def main():
    global APP
    root = tk.Tk()
    app = DashboardApp(root)
    APP = app

    # Crear animación usando el intervalo inicial
    app.ani = animation.FuncAnimation(fig, animar, interval=app.interval.get(), cache_frame_data=False)

    root.mainloop()


if __name__ == '__main__':
    main()