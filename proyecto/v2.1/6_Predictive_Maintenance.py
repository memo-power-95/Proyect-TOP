"""Predictive maintenance tool (single-file, robust)

Features:
- Loads `bitacora_mantenimiento.csv` (searches upward for project root)
- Normalizes columns, computes MTBF/MTTR, downtime per shift
- Simple predictor training (RandomForest) if scikit-learn is available
- Saves/loads model to `predictive_model.pkl`
- GUI: line selector, date/time picker (tkcalendar optional), plot risk trend
"""
from pathlib import Path
import logging
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import pandas as pd
import json
import pickle
import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

BASE = Path(__file__).parent
import sys

def get_resource_path(rel_path: str) -> Path:
    """Return a Path to a resource whether running unpacked or inside a PyInstaller exe.

    When packed with PyInstaller --onefile, resources added with --add-data are
    available under `sys._MEIPASS` at runtime.
    """
    if getattr(sys, '_MEIPASS', None):
        return Path(sys._MEIPASS) / rel_path
    # search upwards for development mode files
    p = BASE
    for _ in range(5):
        candidate = p / rel_path
        if candidate.exists():
            return candidate
        p = p.parent
    return BASE / rel_path

MAINT_FILE = get_resource_path('bitacora_mantenimiento.csv')
LOGS_FILE = get_resource_path('logs_tiempo_real.csv')
LOGS_POR_LINEA = {
    1: BASE / 'logs_tiempo_real_linea_1.csv',
    2: BASE / 'logs_tiempo_real_linea_2.csv',
}
MODEL_PATH = get_resource_path('predictive_model.pkl')
MODEL = None

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    SKLEARN_AVAILABLE = True
except Exception:
    SKLEARN_AVAILABLE = False

try:
    from tkcalendar import Calendar
    TKCAL_AVAILABLE = True
except Exception:
    TKCAL_AVAILABLE = False


def load_maintenance(path=MAINT_FILE):
    if not Path(path).exists():
        logging.warning('Maintenance CSV not found: %s', path)
        return pd.DataFrame()
    # Try several encodings to avoid UnicodeDecodeError on Windows/Latin1 files
    encodings = ['utf-8', 'utf-8-sig', 'cp1252', 'latin-1']
    last_exc = None
    df = None
    for enc in encodings:
        try:
            df = pd.read_csv(path, encoding=enc)
            logging.info('Read CSV %s with encoding %s', path, enc)
            break
        except Exception as e:
            last_exc = e
    if df is None:
        logging.exception('Failed to read CSV with tried encodings')
        raise last_exc
    # normalize column names
    cols_map = {}
    for c in df.columns:
        lc = c.strip().lower()
        if 'line' in lc:
            cols_map[c] = 'Linea'
        elif 'time' in lc or 'fecha' in lc or 'timestamp' in lc or 'date' in lc:
            cols_map[c] = 'Timestamp'
        elif 'dur' in lc and 'ciclo' not in lc:
            cols_map[c] = 'Duracion'
        elif 'ciclo' in lc:
            cols_map[c] = 'Tiempo_Ciclo'
        elif 'event' in lc or 'accion' in lc or 'evento' in lc:
            cols_map[c] = 'Accion'
        else:
            cols_map[c] = c.strip()
    df = df.rename(columns=cols_map)
    if 'Timestamp' in df.columns:
        df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
    if 'Linea' in df.columns:
        df['Linea'] = pd.to_numeric(df['Linea'], errors='coerce')
    if 'Duracion' in df.columns:
        df['Duracion'] = pd.to_numeric(df['Duracion'], errors='coerce').fillna(0)
    else:
        if 'Tiempo_Ciclo' in df.columns:
            df['Duracion'] = pd.to_numeric(df['Tiempo_Ciclo'], errors='coerce').fillna(0)
        else:
            df['Duracion'] = 0
    return df


def compute_mtbf_mttr(df, line: int):
    d = df[df['Linea'] == line].sort_values('Timestamp')
    if d.empty:
        return None, None, None
    times = d['Timestamp'].dropna()
    if len(times) < 2:
        return None, float(d['Duracion'].mean() or 0), times.max()
    diffs = times.diff().dt.total_seconds().dropna()
    mtbf = diffs.mean()
    mttr = float(d['Duracion'].mean() or 0)
    return mtbf, mttr, times.max()


def predict_time_to_failure(mtbf_seconds, last_ts):
    if mtbf_seconds is None or pd.isna(last_ts):
        return None, None
    now = pd.Timestamp.now()
    elapsed = (now - last_ts).total_seconds()
    remaining = mtbf_seconds - elapsed
    risk = min(100.0, max(0.0, (elapsed / mtbf_seconds) * 100.0)) if mtbf_seconds > 0 else 100.0
    return remaining, risk


def downtime_by_shift(df, line: int, start=None, end=None):
    d = df[df['Linea'] == line].copy()
    if d.empty:
        return {'Morning':0,'Afternoon':0,'Night':0}
    d['Timestamp'] = pd.to_datetime(d['Timestamp'], errors='coerce') if 'Timestamp' in d.columns else pd.NaT
    if start:
        d = d[d['Timestamp'] >= pd.to_datetime(start)]
    if end:
        d = d[d['Timestamp'] <= pd.to_datetime(end)]
    def shift_of(ts):
        if pd.isna(ts):
            return 'Night'
        h = ts.hour
        if 6 <= h < 14: return 'Morning'
        if 14 <= h < 22: return 'Afternoon'
        return 'Night'
    d['Shift'] = d['Timestamp'].apply(shift_of)
    d['Duracion'] = pd.to_numeric(d['Duracion'], errors='coerce').fillna(0)
    g = d.groupby('Shift')['Duracion'].sum().to_dict()
    return {k: float(g.get(k,0.0)) for k in ('Morning','Afternoon','Night')}


def save_model(model):
    try:
        with open(MODEL_PATH, 'wb') as f:
            pickle.dump(model, f)
        logging.info('Modelo guardado en %s', MODEL_PATH)
    except Exception:
        logging.exception('No se pudo guardar el modelo')


def _read_logs_both_lines():
    """Lee logs de ambas líneas y retorna dataframe combinado."""
    dfs = []
    for lid, path in LOGS_POR_LINEA.items():
        if path.exists():
            try:
                df = pd.read_csv(path)
                dfs.append(df)
            except Exception:
                pass
    if not dfs:
        return pd.DataFrame(columns=['Timestamp', 'Linea', 'Maquina', 'Salud', 'Tiempo_Ciclo', 'Evento'])
    df = pd.concat(dfs, ignore_index=True)
    for col in ['Linea', 'Salud', 'Tiempo_Ciclo']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    if 'Timestamp' in df.columns:
        df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
    return df


def build_training_data_from_logs(logs_path=None, window_hours=1):
    """Construye datos de entrenamiento desde logs de ambas líneas."""
    df = _read_logs_both_lines()
    if df.empty:
        return None
    df = df.sort_values('Timestamp')
    df['t'] = df['Timestamp'].dt.floor(f'{window_hours}h')
    df['linea'] = df['Linea']
    grouped = df.groupby(['t', 'linea']).agg(
        avg_tc=('Tiempo_Ciclo', 'mean'),
        total=('Evento', 'count'),
        scrap=('Evento', lambda x: (x.astype(str).str.contains('SCRAP', na=False)).sum()),
        error=('Evento', lambda x: (x.isin(['CRITICAL', 'SENSOR_FAIL', 'STUCK'])).sum()),
    ).reset_index()
    return grouped


def generate_report(df_maint, line, start=None, end=None):
    """Genera reporte predictivo combinando bitácora + logs reales."""
    mtbf, mttr, last_ts = compute_mtbf_mttr(df_maint, line)
    remaining, risk = predict_time_to_failure(mtbf, last_ts)
    shifts = downtime_by_shift(df_maint, line, start, end)

    now = pd.Timestamp.now()
    rpt = {
        'line': line,
        'mtbf_seconds': mtbf,
        'mttr_seconds': mttr,
        'mtbf_hours': (mtbf / 3600) if mtbf is not None else None,
        'mttr_minutes': (mttr / 60) if mttr is not None else None,
        'last_maintenance': str(last_ts) if last_ts is not None else None,
        'predicted_seconds_to_failure': remaining,
        'risk_percent': min(100.0, max(0.0, risk)) if risk is not None else None,
        'downtime_by_shift': shifts,
        'generated_at': str(now),
    }
    return rpt


class App:
    def __init__(self, master):
        self.master = master
        master.title('Predictive Maintenance - TOP')
        self.df = load_maintenance()
        frm = ttk.Frame(master, padding=8)
        frm.pack(fill='both', expand=True)
        ttk.Label(frm, text='Línea:').grid(column=0, row=0, sticky='w')
        lines = sorted(self.df['Linea'].dropna().unique().tolist()) if not self.df.empty else [1]
        self.line_var = tk.IntVar(value=lines[0])
        ttk.Combobox(frm, values=lines, textvariable=self.line_var, state='readonly', width=6).grid(column=1, row=0)
        ttk.Label(frm, text='Desde:').grid(column=0, row=1, sticky='w')
        self.start_e = ttk.Entry(frm, width=18, state='readonly'); self.start_e.grid(column=1,row=1)
        ttk.Button(frm, text='Seleccionar', command=lambda: self._pick(self.start_e)).grid(column=2,row=1)
        ttk.Label(frm, text='Hasta:').grid(column=0, row=2, sticky='w')
        self.end_e = ttk.Entry(frm, width=18, state='readonly'); self.end_e.grid(column=1,row=2)
        ttk.Button(frm, text='Seleccionar', command=lambda: self._pick(self.end_e)).grid(column=2,row=2)
        ttk.Button(frm, text='Calcular', command=self.on_calculate).grid(column=0,row=3,pady=6)
        ttk.Button(frm, text='Exportar reporte', command=self.on_export).grid(column=1,row=3)
        ttk.Button(frm, text='Entrenar ML (opcional)', command=self.on_train).grid(column=2,row=3)
        self.out = tk.Text(frm, width=60, height=12)
        self.out.grid(column=0,row=4,columnspan=3,pady=6)

    def _pick(self, entry):
        if TKCAL_AVAILABLE:
            dlg = tk.Toplevel(self.master); dlg.title('Seleccionar fecha')
            cal = Calendar(dlg, selectmode='day'); cal.pack()
            hour = ttk.Combobox(dlg, values=[f"{h:02d}" for h in range(24)], width=4); hour.set('00'); hour.pack(side='left')
            minute = ttk.Combobox(dlg, values=['00','15','30','45'], width=4); minute.set('00'); minute.pack(side='left')
            def ok():
                d = cal.get_date(); h = hour.get(); m = minute.get()
                try:
                    dt = pd.to_datetime(d).date(); val = f"{dt.isoformat()} {h}:{m}"
                except Exception:
                    val = f"{d} {h}:{m}"
                entry.configure(state='normal'); entry.delete(0,'end'); entry.insert(0,val); entry.configure(state='readonly'); dlg.destroy()
            ttk.Button(dlg, text='OK', command=ok).pack()
            dlg.transient(self.master); dlg.grab_set(); self.master.wait_window(dlg)
        else:
            s = simpledialog.askstring('Fecha/Hora', 'Ingrese YYYY-MM-DD HH:MM')
            if s:
                entry.configure(state='normal'); entry.delete(0,'end'); entry.insert(0,s); entry.configure(state='readonly')

    def on_calculate(self):
        line = int(self.line_var.get())
        start = self.start_e.get().strip() or None
        end = self.end_e.get().strip() or None
        mtbf, mttr, last_ts = compute_mtbf_mttr(self.df, line)
        remaining, risk = predict_time_to_failure(mtbf, last_ts)
        shifts = downtime_by_shift(self.df, line, start, end)

        # human-friendly derived fields
        now = pd.Timestamp.now()
        time_since_last = None
        overdue = None
        remaining_nonneg = None
        if last_ts is not None and not pd.isna(last_ts):
            time_since_last = (now - pd.to_datetime(last_ts)).total_seconds()
        if remaining is not None:
            if remaining < 0:
                overdue = -remaining
                remaining_nonneg = 0.0
            else:
                remaining_nonneg = remaining

        rpt = {
            'line': line,
            'mtbf_seconds': mtbf,
            'mttr_seconds': mttr,
            'mtbf_hours': (mtbf / 3600) if mtbf is not None else None,
            'mttr_minutes': (mttr / 60) if mttr is not None else None,
            'last_maintenance': str(last_ts) if last_ts is not None else None,
            'time_since_last_seconds': time_since_last,
            'predicted_seconds_to_failure': remaining,
            'predicted_seconds_to_failure_nonnegative': remaining_nonneg,
            'overdue_seconds': overdue,
            'risk_percent': min(100.0, max(0.0, risk)) if risk is not None else None,
            'downtime_by_shift': shifts,
            'generated_at': str(now)
        }
        self._show_report(rpt)

    def _show_report(self, rpt):
        self.out.delete('1.0','end')
        self.out.insert('end', json.dumps(rpt, indent=2, ensure_ascii=False))

    def on_export(self):
        line = int(self.line_var.get())
        start = self.start_e.get().strip() or None
        end = self.end_e.get().strip() or None
        mtbf, mttr, last = compute_mtbf_mttr(self.df, line)
        remaining, risk = predict_time_to_failure(mtbf, last)
        shifts = downtime_by_shift(self.df, line, start, end)
        rpt = {'line': line, 'mtbf_seconds': mtbf, 'mttr_seconds': mttr, 'last_maintenance': str(last) if last is not None else None,
               'predicted_seconds_to_failure': remaining, 'risk_percent': risk, 'downtime_by_shift': shifts, 'generated_at': str(pd.Timestamp.now())}
        p = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('JSON','*.json')])
        if p:
            with open(p, 'w', encoding='utf-8') as f:
                json.dump(rpt, f, indent=2, ensure_ascii=False)
            messagebox.showinfo('Exportado', f'Reporte guardado en {p}')

    def on_train(self):
        if not SKLEARN_AVAILABLE:
            messagebox.showwarning('ML', 'scikit-learn no está instalado')
            return
        if not Path(LOGS_FILE).exists():
            messagebox.showwarning('ML', f'Logs no encontrados: {LOGS_FILE}')
            return
        messagebox.showinfo('ML', 'Entrenamiento no implementado en esta versión simplificada')


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == '__main__':
    main()
