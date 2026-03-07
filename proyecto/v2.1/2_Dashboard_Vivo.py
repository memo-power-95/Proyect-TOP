import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.animation as animation

# Optional real-time client libs
try:
    import socketio
except Exception:
    socketio = None
try:
    import requests
except Exception:
    requests = None

ARCHIVO_LOGS = "logs_tiempo_real.csv"

TC_LINEA_OBJ = {
    1: 855.78,
    2: 855.78,
}

TC_MAQUINA_OBJ = {
    "Top cover feeding": 105.47,
    "Pre-weighing": 79.98,
    "Tim dispensing": 83.60,
    "Avl Tim": 60.69,
    "Weighing": 83.06,
    "Install PCB": 88.60,
    "Fastening 1": 80.65,
    "Fastening 2": 92.74,
    "Avl screw": 70.32,
    "Top unloader": 104.36,
}


def _rendimiento(tc_objetivo, tc_real):
    if tc_objetivo <= 0:
        return 0.0
    tc_adj = max(float(tc_real or 0), float(tc_objetivo))
    return (float(tc_objetivo) / tc_adj) * 100.0 if tc_adj > 0 else 0.0


def _rendimiento_linea(df_linea, linea):
    if df_linea is None or df_linea.empty or 'Tiempo_Ciclo' not in df_linea.columns:
        return 0.0, 0.0, TC_LINEA_OBJ.get(int(linea), 855.78)

    # Si hay varias maquinas, consolidar por timestamp para obtener TC total de linea.
    if 'Maquina' in df_linea.columns and 'Timestamp' in df_linea.columns and df_linea['Maquina'].nunique() > 1:
        tc_series = df_linea.groupby('Timestamp')['Tiempo_Ciclo'].sum(min_count=1).dropna()
        tc_real = float(tc_series.mean() or 0) if not tc_series.empty else 0.0
    else:
        tc_real = float(df_linea['Tiempo_Ciclo'].dropna().mean() or 0)

    tc_obj = float(TC_LINEA_OBJ.get(int(linea), 855.78))
    return _rendimiento(tc_obj, tc_real), tc_real, tc_obj


def _rendimiento_por_maquina(df_linea):
    out = {}
    if df_linea is None or df_linea.empty or 'Maquina' not in df_linea.columns:
        return out

    for maq, dmaq in df_linea.groupby('Maquina'):
        tc_real = float(dmaq['Tiempo_Ciclo'].dropna().mean() or 0)
        tc_obj = float(TC_MAQUINA_OBJ.get(str(maq), 138.0))
        out[str(maq)] = {
            'rend': _rendimiento(tc_obj, tc_real),
            'tc_real': tc_real,
            'tc_obj': tc_obj,
        }
    return out

class DashboardVivoApp:
    def __init__(self, root):
        self.root = root
        self.root.title('Dashboard Vivo - TOP')
        self.root.geometry('1100x700')

        # controles
        ctrl = tk.Frame(self.root)
        ctrl.pack(side='top', fill='x', padx=8, pady=6)

        tk.Label(ctrl, text='Linea:').pack(side='left')
        self.linea_var = tk.StringVar(value='1')
        self.combo_linea = ttk.Combobox(ctrl, textvariable=self.linea_var, values=['1', '2'], width=6, state='readonly')
        self.combo_linea.pack(side='left', padx=6)
        self.combo_linea.bind('<<ComboboxSelected>>', lambda _e: self.populate_maquinas())

        tk.Label(ctrl, text='Maquina:').pack(side='left')
        self.maquina_var = tk.StringVar(value='ALL')
        self.combo_maquina = ttk.Combobox(ctrl, textvariable=self.maquina_var, values=['ALL'], width=22, state='readonly')
        self.combo_maquina.pack(side='left', padx=6)

        tk.Label(ctrl, text='Ventana N:').pack(side='left')
        self.window_var = tk.IntVar(value=60)
        self.spin_window = tk.Spinbox(ctrl, from_=10, to=1000, textvariable=self.window_var, width=6)
        self.spin_window.pack(side='left', padx=6)

        self.btn_pause = ttk.Button(ctrl, text='Pausar', command=self.toggle_pause)
        self.btn_pause.pack(side='left', padx=6)

        ttk.Button(ctrl, text='Refresh', command=self.manual_refresh).pack(side='left', padx=6)
        ttk.Button(ctrl, text='Export CSV', command=self.export_csv).pack(side='left', padx=6)
        ttk.Button(ctrl, text='Snapshot PNG', command=self.save_snapshot).pack(side='left', padx=6)
        
        # Digital Twin controls
        tk.Label(ctrl, text='  DigitalTwin:').pack(side='left', padx=(12,2))
        self.dt_url = tk.StringVar(value='http://localhost:5000')
        self.dt_entry = ttk.Entry(ctrl, textvariable=self.dt_url, width=22)
        self.dt_entry.pack(side='left')
        self.btn_connect = ttk.Button(ctrl, text='Conectar DT', command=self.connect_to_dt)
        self.btn_connect.pack(side='left', padx=6)
        self.btn_disconnect = ttk.Button(ctrl, text='Desconectar', command=self.disconnect_from_dt)
        self.btn_disconnect.pack(side='left', padx=6)
        ttk.Button(ctrl, text='DT Start', command=self.dt_start).pack(side='left', padx=4)
        ttk.Button(ctrl, text='DT Stop', command=self.dt_stop).pack(side='left', padx=4)
        ttk.Button(ctrl, text='Inject', command=self.dt_inject_dialog).pack(side='left', padx=4)
        tk.Label(ctrl, text='Speed:').pack(side='left', padx=(8,2))
        self.speed_var = tk.DoubleVar(value=1.0)
        self.speed_spin = tk.Spinbox(ctrl, from_=0.1, to=10.0, increment=0.1, textvariable=self.speed_var, width=6)
        self.speed_spin.pack(side='left')
        ttk.Button(ctrl, text='Set', command=self.dt_set_speed).pack(side='left', padx=4)

        # panel de estadísticas a la derecha
        right = tk.Frame(self.root)
        right.pack(side='right', fill='y', padx=6, pady=6)
        tk.Label(right, text='Estadísticas (ventana)').pack(anchor='n')
        self.stats_text = tk.Text(right, width=30, height=12, state='disabled', bg='#111', fg='#ddd')
        self.stats_text.pack(pady=6)
        tk.Label(right, text='Conteo eventos').pack()
        self.events_text = tk.Text(right, width=30, height=8, state='disabled', bg='#111', fg='#ddd')
        self.events_text.pack(pady=6)

        # figura matplotlib embebida
        self.fig = Figure(figsize=(8, 7), constrained_layout=True)
        self.ax1 = self.fig.add_subplot(3, 1, 1)
        self.ax2 = self.fig.add_subplot(3, 1, 2)
        self.ax3 = self.fig.add_subplot(3, 1, 3)

        canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        canvas.get_tk_widget().pack(side='left', fill='both', expand=1)
        self.canvas = canvas

        toolbar = NavigationToolbar2Tk(canvas, self.root)
        toolbar.update()

        # animación y estado
        self.paused = False
        self.ani = animation.FuncAnimation(self.fig, self._animar, interval=1000, cache_frame_data=False)

        # real-time buffer and socket client
        self.buffer_df = pd.DataFrame(columns=['Timestamp', 'Linea', 'Maquina', 'Salud', 'Tiempo_Ciclo', 'Evento'])
        self.max_buffer = 2000
        self.sio = None
        self.connected = False
        self.auto_reconnect = True
        self._reconnect_thread = None
        self._reconnect_stop = None
        self.status_var = tk.StringVar(value='')

        # status bar
        status = tk.Frame(self.root)
        status.pack(side='bottom', fill='x')
        tk.Label(status, textvariable=self.status_var).pack(side='left', padx=6)

        # poblar combobox de líneas disponibles (desde CSV si existe)
        self.populate_lineas()

    def toggle_pause(self):
        self.paused = not self.paused
        self.btn_pause.config(text='Reanudar' if self.paused else 'Pausar')

    def manual_refresh(self):
        # forzar actualización inmediata
        try:
            self._animar(0)
            self.canvas.draw_idle()
        except Exception as e:
            print('Refresh error:', e)

    def _leer_datos(self):
        # Si estamos conectados y hay buffer, devolvemos el buffer
        if self.connected and not self.buffer_df.empty:
            return self.buffer_df.copy()
        # fallback a CSV
        if not os.path.exists(ARCHIVO_LOGS):
            return None
        try:
            df = pd.read_csv(ARCHIVO_LOGS)
            return df
        except Exception as e:
            print('Error leyendo CSV:', e)
            return None

    def populate_lineas(self):
        """Leer CSV y poblar la combobox `Linea` con valores únicos."""
        if os.path.exists(ARCHIVO_LOGS):
            try:
                df = pd.read_csv(ARCHIVO_LOGS)
                if 'Linea' in df.columns:
                    vals = sorted(pd.unique(df['Linea']).tolist())
                    # convertir a strings
                    vals_s = [str(int(v)) if (not pd.isna(v)) else '' for v in vals]
                    if vals_s:
                        self.combo_linea['values'] = vals_s
                        # si el valor actual no está, seleccionar el primero
                        if self.linea_var.get() not in vals_s:
                            self.linea_var.set(vals_s[0])
                        self.populate_maquinas()
                        return
            except Exception:
                pass
        # fallback por defecto
        self.combo_linea['values'] = ['1', '2']
        self.populate_maquinas()

    def populate_maquinas(self):
        vals = ['ALL']
        try:
            if os.path.exists(ARCHIVO_LOGS):
                df = pd.read_csv(ARCHIVO_LOGS)
                if 'Linea' in df.columns and 'Maquina' in df.columns:
                    lid = int(self.linea_var.get())
                    ds = df[df['Linea'] == lid]
                    mvals = sorted(ds['Maquina'].dropna().astype(str).unique().tolist())
                    vals += mvals
        except Exception:
            pass
        self.combo_maquina['values'] = vals
        if self.maquina_var.get() not in vals:
            self.maquina_var.set('ALL')

    # --- Digital Twin client / controls ---
    def connect_to_dt(self):
        url = self.dt_url.get().rstrip('/')
        if socketio is None:
            messagebox.showerror('Dependencia', 'Falta python-socketio. Instala python-socketio[client]')
            return
        if self.connected:
            return
        # start a background connection attempt (non-blocking)
        def _do_connect():
            try:
                self.sio = socketio.Client(reconnection=True)

                @self.sio.event
                def connect():
                    self.connected = True
                    self.status_var.set('Conectado a DT')

                @self.sio.event
                def disconnect():
                    self.connected = False
                    self.status_var.set('Desconectado de DT')
                    # if auto_reconnect is enabled, start reconnect thread
                    if self.auto_reconnect:
                        self._start_reconnect(url)

                @self.sio.on('telemetry')
                def on_telemetry(data):
                    # normalize and append
                    try:
                        row = {
                            'Timestamp': str(data.get('Timestamp', '')),
                            'Linea': int(data.get('Linea', 0)),
                            'Maquina': str(data.get('Maquina', 'GENERAL')),
                            'Salud': float(data.get('Salud', 0)),
                            'Tiempo_Ciclo': float(data.get('Tiempo_Ciclo', 0)),
                            'Evento': str(data.get('Evento', ''))
                        }
                    except Exception:
                        row = {
                            'Timestamp': str(data.get('Timestamp', '')),
                            'Linea': data.get('Linea'),
                            'Maquina': data.get('Maquina'),
                            'Salud': data.get('Salud'),
                            'Tiempo_Ciclo': data.get('Tiempo_Ciclo'),
                            'Evento': data.get('Evento')
                        }
                    try:
                        self.buffer_df = pd.concat([self.buffer_df, pd.DataFrame([row])], ignore_index=True)
                        if len(self.buffer_df) > self.max_buffer:
                            self.buffer_df = self.buffer_df.tail(self.max_buffer).reset_index(drop=True)
                    except Exception as e:
                        print('Error appending telemetry:', e)
                    # calcular latencia si viene emit_ts
                    try:
                        emit_ts = float(data.get('emit_ts', 0) or 0)
                        if emit_ts:
                            import time
                            latency_ms = int((time.time() - emit_ts) * 1000)
                            self.status_var.set(f"Último: {row.get('Evento')} L{row.get('Linea')} t={row.get('Tiempo_Ciclo')} · lat={latency_ms}ms")
                        else:
                            self.status_var.set(f"Último: {row.get('Evento')} L{row.get('Linea')} t={row.get('Tiempo_Ciclo')}")
                    except Exception:
                        self.status_var.set(f"Último: {row.get('Evento')} L{row.get('Linea')}")

                self.status_var.set('Conectando...')
                self.sio.connect(url)
            except Exception as e:
                self.status_var.set(f'Conexión fallida: {e}')
                # lanzar reconexión si está habilitado
                if self.auto_reconnect:
                    self._start_reconnect(url)

        threading.Thread(target=_do_connect, daemon=True).start()

    def disconnect_from_dt(self):
        try:
            if self.sio:
                try:
                    self.sio.disconnect()
                except Exception:
                    pass
            self.connected = False
            self.status_var.set('Desconectado')
        except Exception as e:
            print('Disconnect error', e)

    def _start_reconnect(self, url):
        # start a single reconnect thread if none active
        if self._reconnect_thread and self._reconnect_thread.is_alive():
            return
        import threading, time
        self._reconnect_stop = threading.Event()

        def _reconnect_loop():
            backoff = 1.0
            while not self._reconnect_stop.is_set():
                try:
                    self.status_var.set(f'Reintentando conexión en {int(backoff)}s')
                    time.sleep(backoff)
                    # intentar conectar de nuevo
                    if self.sio is None:
                        try:
                            self.sio = socketio.Client(reconnection=True)
                        except Exception:
                            self.sio = None
                    if self.sio:
                        try:
                            self.sio.connect(url)
                            # si conecta, salir
                            self.status_var.set('Reconectado')
                            return
                        except Exception:
                            pass
                except Exception:
                    pass
                backoff = min(30.0, backoff * 2)

        self._reconnect_thread = threading.Thread(target=_reconnect_loop, daemon=True)
        self._reconnect_thread.start()

    def _stop_reconnect(self):
        try:
            if self._reconnect_stop:
                self._reconnect_stop.set()
            self._reconnect_thread = None
        except Exception:
            pass

    def _call_rest(self, path, method='GET', json_payload=None):
        if requests is None:
            messagebox.showerror('Dependencia', 'Falta requests (opcional)')
            return None
        try:
            url = self.dt_url.get().rstrip('/') + path
            if method == 'GET':
                r = requests.get(url, timeout=3)
            else:
                r = requests.post(url, json=json_payload, timeout=3)
            try:
                return r.json()
            except Exception:
                return r.text
        except Exception as e:
            messagebox.showerror('DT REST', f'Error: {e}')
            return None

    def dt_start(self):
        self._call_rest('/start')

    def dt_stop(self):
        self._call_rest('/stop')

    def dt_set_speed(self):
        try:
            s = float(self.speed_var.get())
        except Exception:
            s = 1.0
        self._call_rest('/speed', method='POST', json_payload={'speed': s})

    def dt_inject_dialog(self):
        payload = {}
        # pedir campo Evento y Tiempo_Ciclo
        ev = simpledialog.askstring('Inject Event', 'Evento (ej: FALLA):')
        if ev is None:
            return
        payload['Evento'] = ev
        try:
            tc = simpledialog.askfloat('Inject Event', 'Tiempo_Ciclo (s):', initialvalue=150.0)
            if tc is not None:
                payload['Tiempo_Ciclo'] = float(tc)
        except Exception:
            pass
        # Linea y Salud
        try:
            ln = simpledialog.askinteger('Inject Event', 'Linea:', initialvalue=1)
            if ln is not None:
                payload['Linea'] = int(ln)
        except Exception:
            pass
        payload['Timestamp'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        payload['Salud'] = payload.get('Salud', 10)
        self._call_rest('/inject', method='POST', json_payload=payload)

    def _animar(self, i):
        if self.paused:
            return
        df = self._leer_datos()
        if df is None or df.empty:
            return

        try:
            linea = int(self.linea_var.get())
        except Exception:
            linea = 1
        N = max(10, int(self.window_var.get()))
        maq = self.maquina_var.get().strip()

        # Ventana completa de linea (base para rendimiento de linea y por maquina)
        df_linea = df[df['Linea'] == linea].tail(N)
        if df_linea.empty:
            return

        # Serie a graficar (linea completa o maquina seleccionada)
        l1 = df_linea
        if maq and maq != 'ALL' and 'Maquina' in l1.columns:
            l1 = l1[l1['Maquina'] == maq]
            if l1.empty:
                return

        timestamps = l1['Timestamp'].astype(str).values
        ciclos = l1['Tiempo_Ciclo'].values
        salud = l1['Salud'].values
        eventos = l1['Evento'].astype(str).values

        # PLOT 1
        self.ax1.clear()
        self.ax1.plot(timestamps, ciclos, color='cyan', label='Ciclo Real (s)', linewidth=1)
        if maq and maq != 'ALL':
            target = TC_MAQUINA_OBJ.get(maq, 138.0)
            label_target = f'Target maquina {target:.2f}s'
        else:
            target = TC_LINEA_OBJ.get(linea, 855.78)
            label_target = f'Target linea {target:.2f}s'
        self.ax1.axhline(y=target, color='white', linestyle=':', alpha=0.5, label=label_target)

        scrap = l1[l1['Evento'].str.contains('SCRAP', na=False)]
        if not scrap.empty:
            self.ax1.scatter(scrap['Timestamp'].astype(str), scrap['Tiempo_Ciclo'], color='red', marker='X', s=80, label='Scrap', zorder=5)
        fallas = l1[l1['Evento'].str.contains('FALLA|CRIT|WARN', regex=True, na=False)]
        if not fallas.empty:
            self.ax1.scatter(fallas['Timestamp'].astype(str), fallas['Tiempo_Ciclo'], color='yellow', marker='^', s=60, label='Falla/Pico', zorder=5)
        mto = l1[l1['Evento'] == 'MANTENIMIENTO']
        if not mto.empty:
            self.ax1.scatter(mto['Timestamp'].astype(str), mto['Tiempo_Ciclo'], color='white', marker='s', s=50, label='Mantenimiento', zorder=5)

        titulo_maquina = f" - {maq}" if maq and maq != 'ALL' else ''
        self.ax1.set_title(f'Monitor de Ciclos - Linea {linea}{titulo_maquina}')
        self.ax1.legend(loc='upper left')
        self.ax1.set_xticks([])

        # PLOT 2
        self.ax2.clear()
        x_axis = np.arange(len(salud))
        color_linea = ['#00ff00' if s > 80 else '#e74c3c' for s in salud]
        for k in range(len(salud)-1):
            self.ax2.plot(x_axis[k:k+2], salud[k:k+2], color=color_linea[k], linewidth=2)
        self.ax2.axhline(y=90, color='gray', linestyle='--', alpha=0.5, label='Zona Estable')
        self.ax2.axhline(y=40, color='red', linestyle='--', label='Zona Crítica')
        self.ax2.set_title('Estado de Salud de la Maquinaria')
        self.ax2.set_ylim(0, 110)
        if len(timestamps) > 0:
            etiquetas = [timestamps[idx] if idx % max(1, int(len(timestamps)/6)) == 0 else '' for idx in range(len(timestamps))]
            self.ax2.set_xticks(x_axis)
            self.ax2.set_xticklabels(etiquetas, rotation=45, ha='right')

        # actualizar stats con enfoque linea + maquina(s)
        self._update_stats(df_linea, l1, linea, maq)

        # PLOT 3 - Rendimiento por maquina (barra)
        rend_maqs = _rendimiento_por_maquina(df_linea)
        self.ax3.clear()
        if rend_maqs:
            nombres = list(rend_maqs.keys())
            valores = [rend_maqs[n]['rend'] for n in nombres]
            colores = ['#2ecc71' if v >= 85 else '#f1c40f' if v >= 65 else '#e74c3c' for v in valores]
            bars = self.ax3.bar(nombres, valores, color=colores)
            self.ax3.set_ylim(0, 110)
            self.ax3.set_ylabel('Rend %')
            self.ax3.set_title(f'Rendimiento por maquina - Linea {linea}')
            self.ax3.tick_params(axis='x', rotation=25)
            for bar, val in zip(bars, valores):
                self.ax3.text(bar.get_x() + bar.get_width() / 2, val + 1.5, f"{val:.1f}%", ha='center', va='bottom', fontsize=8)
        else:
            self.ax3.text(0.5, 0.5, 'Sin datos de maquinas', ha='center', va='center')
            self.ax3.set_xticks([])
            self.ax3.set_yticks([])
            self.ax3.set_title(f'Rendimiento por maquina - Linea {linea}')

        self.canvas.draw_idle()

    def _update_stats(self, df_linea_window, df_plot_window, linea, maq_sel):
        # calcular estadisticas simples
        try:
            avg = df_plot_window['Tiempo_Ciclo'].mean()
            mn = df_plot_window['Tiempo_Ciclo'].min()
            mx = df_plot_window['Tiempo_Ciclo'].max()
            std = df_plot_window['Tiempo_Ciclo'].std()
        except Exception:
            avg = mn = mx = std = None

        rend_linea, tc_real_linea, tc_obj_linea = _rendimiento_linea(df_linea_window, linea)
        rend_maqs = _rendimiento_por_maquina(df_linea_window)

        stats_lines = []
        stats_lines.append(f"Linea {linea} | Registros: {len(df_plot_window)}")
        stats_lines.append(f"Rendimiento linea: {rend_linea:.2f}%")
        stats_lines.append(f"TC linea real/obj: {tc_real_linea:.2f}s / {tc_obj_linea:.2f}s")

        if maq_sel and maq_sel != 'ALL':
            rmaq = rend_maqs.get(maq_sel)
            if rmaq:
                stats_lines.append(f"Rendimiento {maq_sel}: {rmaq['rend']:.2f}%")
                stats_lines.append(f"TC maq real/obj: {rmaq['tc_real']:.2f}s / {rmaq['tc_obj']:.2f}s")

        if avg is not None:
            stats_lines.append(f"Promedio ciclo: {avg:.2f} s")
            stats_lines.append(f"Min: {mn:.2f} s  Max: {mx:.2f} s")
            stats_lines.append(f"DesvStd: {std:.2f}")

        # eventos
        ev_counts = df_plot_window['Evento'].value_counts().to_dict()

        self.stats_text.config(state='normal')
        self.stats_text.delete('1.0', tk.END)
        self.stats_text.insert(tk.END, '\n'.join(stats_lines))
        self.stats_text.config(state='disabled')

        self.events_text.config(state='normal')
        self.events_text.delete('1.0', tk.END)
        if maq_sel == 'ALL' and rend_maqs:
            self.events_text.insert(tk.END, 'Rendimiento por maquina:\n')
            for mk in sorted(rend_maqs.keys()):
                rr = rend_maqs[mk]
                self.events_text.insert(
                    tk.END,
                    f"- {mk}: {rr['rend']:.2f}% (TC {rr['tc_real']:.2f}/{rr['tc_obj']:.2f}s)\n"
                )
            self.events_text.insert(tk.END, '\n')
        for k, v in ev_counts.items():
            self.events_text.insert(tk.END, f"{k}: {v}\n")
        self.events_text.config(state='disabled')

    def export_csv(self):
        df = self._leer_datos()
        if df is None or df.empty:
            messagebox.showwarning('Exportar', 'No hay datos para exportar')
            return
        linea = int(self.linea_var.get())
        N = max(10, int(self.window_var.get()))
        subset = df[df['Linea'] == linea].tail(N)
        maq = self.maquina_var.get().strip()
        if maq and maq != 'ALL' and 'Maquina' in subset.columns:
            subset = subset[subset['Maquina'] == maq]
        if subset.empty:
            messagebox.showwarning('Exportar', 'No hay datos para la línea/ventana seleccionada')
            return
        path = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV', '*.csv')])
        if not path:
            return
        try:
            subset.to_csv(path, index=False)
            messagebox.showinfo('Exportar', f'Datos exportados a:\n{path}')
        except Exception as e:
            messagebox.showerror('Exportar', f'Error al guardar: {e}')

    def save_snapshot(self):
        path = filedialog.asksaveasfilename(defaultextension='.png', filetypes=[('PNG', '*.png')])
        if not path:
            return
        try:
            self.fig.savefig(path)
            messagebox.showinfo('Snapshot', f'Imagen guardada en:\n{path}')
        except Exception as e:
            messagebox.showerror('Snapshot', f'Error al guardar imagen: {e}')


if __name__ == '__main__':
    root = tk.Tk()
    app = DashboardVivoApp(root)
    root.mainloop()
