"""Entrena el predictor desde `logs_tiempo_real.csv` usando funciones del script de entrenamiento.

Este wrapper construye un DataFrame compatible con `train_predictor.build_samples` a
partir del CSV de logs, marca eventos de interés como fallos y entrena un modelo.
"""
from pathlib import Path
import logging
import json
import pandas as pd
import numpy as np
import sys

# helper to locate resources when running as a PyInstaller single-file exe
def get_resource_path(rel_path: str) -> Path:
    if getattr(sys, '_MEIPASS', None):
        return Path(sys._MEIPASS) / rel_path
    return Path(__file__).resolve().parents[1] / rel_path

ROOT = Path(__file__).resolve().parents[1]
# default resource paths (when running unpacked)
CSV_PATH = ROOT / 'logs_tiempo_real.csv'
MODEL_OUT = ROOT / 'models' / 'predictor_from_csv.joblib'

# import local training utilities
import train_predictor as tp


def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')


def load_csv_as_events(csv_path: Path) -> pd.DataFrame:
    encodings = ['utf-8', 'utf-8-sig', 'cp1252', 'latin-1']
    df = None
    for enc in encodings:
        try:
            df = pd.read_csv(csv_path, encoding=enc)
            logging.info('Leído CSV %s con %s', csv_path, enc)
            break
        except Exception as e:
            logging.debug('encoding %s falló: %s', enc, e)
    if df is None:
        raise FileNotFoundError(f'No se pudo leer CSV {csv_path}')

    # Build event-like dataframe expected by build_samples
    ev = pd.DataFrame()
    ev['id'] = range(len(df))
    ev['source'] = 'logs'
    ev['timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce') if 'Timestamp' in df.columns else pd.NaT

    def make_parsed(row):
        d = {}
        # include machine id so extract_machine_id can find it
        if 'Linea' in row and not pd.isna(row['Linea']):
            try:
                d['machine_id'] = int(row['Linea'])
            except Exception:
                d['machine_id'] = str(row['Linea'])
        # telemetry fields
        if 'Salud' in row:
            try:
                d['salud'] = float(row['Salud'])
            except Exception:
                d['salud'] = row['Salud']
        if 'Tiempo_Ciclo' in row:
            try:
                d['tiempo_ciclo'] = float(row['Tiempo_Ciclo'])
            except Exception:
                d['tiempo_ciclo'] = row['Tiempo_Ciclo']
        # event label
        if 'Evento' in row:
            evt = str(row['Evento'])
            d['evento'] = evt
            # treat some values as failures
            if evt.strip().upper() in ('MANTENIMIENTO','STUCK','SPIKE','ERROR'):
                d['event'] = 'fail'
        return d

    ev['data_parsed'] = [make_parsed(r) for _, r in df.iterrows()]
    # keep an original JSON string column for compatibility if needed
    ev['data'] = ev['data_parsed'].apply(lambda x: json.dumps(x, ensure_ascii=False))
    return ev


def main():
    setup_logging()
    # resolve resource path when running from an exe
    csv = get_resource_path('logs_tiempo_real.csv') if get_resource_path('logs_tiempo_real.csv').exists() else CSV_PATH
    if not csv.exists():
        logging.error('CSV no encontrado: %s', csv)
        return

    ev = load_csv_as_events(csv)
    logging.info('Eventos construidos: %d', len(ev))

    # use a 1-day window for shorter log datasets to ensure samples are generated
    samp = tp.build_samples(ev, window_days=1, step_days=1)
    logging.info('Muestras generadas: %d', len(samp))
    if samp.empty:
        logging.error('No se generaron muestras; revisar el CSV y la lógica de etiquetas')
        return

    if samp['label'].sum() < 3:
        logging.warning('Pocas etiquetas positivas: %d', int(samp['label'].sum()))

    features = [c for c in samp.columns if c not in ('anchor_time','label')]
    X = samp[features].drop(columns=[c for c in features if c == 'anchor_time' and c in features], errors='ignore')
    y = samp['label']

    model_choice = 'lgb' if tp._HAS_LIGHTGBM else 'rf'
    if model_choice == 'lgb':
        logging.info('LightGBM disponible; usándolo para entrenar')
    else:
        logging.info('LightGBM no disponible; usando RandomForest')

    model = tp.train_model(X, y, model_choice=model_choice, test_size=0.2, random_state=42)

    # write trained model to a writable location (current working dir by default)
    out_path = Path.cwd() / MODEL_OUT.name
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tp.save_model(out_path, model, list(X.columns), {'source':'csv','csv':str(csv), 'model_choice':model_choice})
    logging.info('Modelo guardado en %s', out_path)


if __name__ == '__main__':
    main()
