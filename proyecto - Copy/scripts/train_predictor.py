"""Train a baseline predictor for 'failure within N days'.

This enhanced script adds:
- CLI via `argparse` to control DB/model paths and training options.
- Structured `logging` instead of prints.
- Robust JSON parsing and schema validation for `events.data`.
- Expanded feature engineering (counts, telemetry aggregates, time deltas).
- An sklearn `Pipeline` with `SimpleImputer` and `StandardScaler`.
- Optional LightGBM support and model metadata saving.

Adapt features and heuristics to your telemetry schema for best results.
"""

from pathlib import Path
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import argparse
import logging

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
import joblib

try:
    import lightgbm as lgb
    _HAS_LIGHTGBM = True
except Exception:
    _HAS_LIGHTGBM = False


ROOT = Path(__file__).resolve().parents[1]


def setup_logging(level=logging.INFO):
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")


def load_events(db_path: Path) -> pd.DataFrame:
    if not db_path.exists():
        raise FileNotFoundError(f"DB not found at {db_path}. Run migration first.")
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT id, source, timestamp, data FROM events", conn)
    conn.close()
    # parse timestamps
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    def safe_parse(x):
        if x is None:
            return {}
        if isinstance(x, dict):
            return x
        try:
            return json.loads(x)
        except Exception:
            try:
                # try eval as fallback (not ideal but sometimes valid)
                return json.loads(str(x))
            except Exception:
                return {}

    df["data_parsed"] = df["data"].apply(safe_parse)
    return df


def extract_machine_id(d: Dict[str, Any]) -> Optional[str]:
    if not isinstance(d, dict):
        return None
    for k in ("machine_id", "maquina", "id_maquina", "id", "machine"):
        if k in d and d[k] is not None:
            return str(d[k])
    return None


def is_failure_record(d: Dict[str, Any]) -> bool:
    if not isinstance(d, dict):
        return False
    txt = json.dumps(d).lower()
    for kw in ("fail", "fault", "error", "shutdown", "fallen", "breakdown"):
        if kw in txt:
            return True
    # also support explicit field flags
    for k in ("status", "state", "event"):
        v = d.get(k)
        if isinstance(v, str) and any(sub in v.lower() for sub in ("fail", "error", "fault", "down")):
            return True
    return False


def infer_numeric_keys(df: pd.DataFrame, sample_frac: float = 0.2) -> List[str]:
    # find numeric keys present in data_parsed across a sample of events
    keys = set()
    sample = df.sample(frac=min(1.0, sample_frac), random_state=0) if len(df) > 0 else df
    for d in sample["data_parsed"]:
        if isinstance(d, dict):
            for k, v in d.items():
                if isinstance(v, (int, float)):
                    keys.add(k)
                else:
                    # try castable to float
                    try:
                        float(v)
                        keys.add(k)
                    except Exception:
                        pass
    return sorted(keys)


def build_samples(df: pd.DataFrame, window_days=7, step_days=1) -> pd.DataFrame:
    df = df.copy()
    df["machine_id"] = df["data_parsed"].apply(extract_machine_id)
    df["is_failure"] = df["data_parsed"].apply(is_failure_record).astype(int)
    df["is_maintenance"] = df["source"].str.contains("mantenimiento|bitacora|maintenance", case=False, na=False).astype(int)

    numeric_keys = infer_numeric_keys(df)
    logging.info("Inferred numeric telemetry keys: %s", numeric_keys)

    samples = []
    machines = df["machine_id"].dropna().unique()
    if len(machines) == 0:
        machines = [None]

    for m in machines:
        sub = df[df["machine_id"] == m] if m is not None else df
        if sub.empty:
            continue
        start = sub["timestamp"].min().floor("D")
        end = sub["timestamp"].max().ceil("D") - pd.Timedelta(days=window_days)
        if start >= end:
            continue
        t = start
        while t <= end:
            window_start = t
            window_end = t + pd.Timedelta(days=window_days)
            past = sub[(sub["timestamp"] >= window_start) & (sub["timestamp"] < window_end)]
            future_start = window_end
            future_end = window_end + pd.Timedelta(days=window_days)
            future = sub[(sub["timestamp"] >= future_start) & (sub["timestamp"] < future_end)]

            features: Dict[str, Any] = {
                "machine_id": m,
                "anchor_time": window_start,
                "events_count": len(past),
                "failures_count": int(past["is_failure"].sum()),
                "maint_count": int(past["is_maintenance"].sum()),
            }

            maint_before = sub[sub["timestamp"] < window_end]
            if not maint_before.empty:
                last_maint = maint_before["timestamp"].max()
                features["days_since_last_maint"] = (window_end - last_maint).days
            else:
                features["days_since_last_maint"] = np.nan

            last_event = past["timestamp"].max() if not past.empty else sub["timestamp"].min()
            features["hours_since_last_event"] = (window_end - last_event).total_seconds() / 3600.0

            # aggregate telemetry numeric keys over the past window
            for k in numeric_keys:
                vals = []
                for d in past["data_parsed"]:
                    if isinstance(d, dict) and k in d:
                        try:
                            vals.append(float(d[k]))
                        except Exception:
                            pass
                if len(vals) == 0:
                    features[f"{k}_mean"] = np.nan
                    features[f"{k}_std"] = np.nan
                else:
                    arr = np.array(vals, dtype=float)
                    features[f"{k}_mean"] = float(np.nanmean(arr))
                    features[f"{k}_std"] = float(np.nanstd(arr))

            label = int(future["is_failure"].sum() > 0)
            features["label"] = label
            samples.append(features)

            t = t + pd.Timedelta(days=step_days)

    samp_df = pd.DataFrame(samples)
    return samp_df


def build_pipeline(feature_columns: List[str], categorical_cols: List[str]) -> Pipeline:
    numeric_cols = [c for c in feature_columns if c not in categorical_cols]
    numeric_transformer = Pipeline(steps=[("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())])
    categorical_transformer = Pipeline(steps=[("imputer", SimpleImputer(strategy="constant", fill_value="-")), ("onehot", OneHotEncoder(handle_unknown="ignore"))])
    preproc = ColumnTransformer(transformers=[("num", numeric_transformer, numeric_cols), ("cat", categorical_transformer, categorical_cols)])
    model = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
    pipe = Pipeline(steps=[("preproc", preproc), ("clf", model)])
    return pipe


def train_model(X: pd.DataFrame, y: pd.Series, model_choice: str = "rf", test_size: float = 0.2, random_state: int = 42):
    X = X.copy()
    X = X.fillna(np.nan)
    categorical_cols = [c for c in X.columns if c == "machine_id"]
    feature_columns = list(X.columns)
    pipe = build_pipeline(feature_columns, categorical_cols)

    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=test_size, stratify=y, random_state=random_state)

    if model_choice == "lgb" and _HAS_LIGHTGBM:
        # replace classifier with lightgbm
        lgbm = lgb.LGBMClassifier(n_estimators=200, random_state=random_state, n_jobs=-1)
        pipe.steps[-1] = ("clf", lgbm)
    elif model_choice == "lgb" and not _HAS_LIGHTGBM:
        logging.warning("LightGBM requested but not installed; falling back to RandomForest")

    logging.info("Training with %d samples (%d pos, %d neg)", len(X_train), int(y_train.sum()), int(len(y_train) - y_train.sum()))
    pipe.fit(X_train, y_train)
    y_pred = pipe.predict(X_val)
    logging.info("Validation results:\n%s", classification_report(y_val, y_pred))
    return pipe


def save_model(path: Path, model_obj: Any, features: List[str], params: Dict[str, Any]):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"model": model_obj, "features": features, "metadata": {"params": params, "saved_at": datetime.utcnow().isoformat()}}
    joblib.dump(payload, path)


def parse_args():
    p = argparse.ArgumentParser(description="Train failure predictor from events DB")
    p.add_argument("--db", default=str(ROOT / "data" / "data.db"))
    p.add_argument("--model-path", default=str(ROOT / "models" / "predictor.joblib"))
    p.add_argument("--window", type=int, default=7)
    p.add_argument("--step", type=int, default=1)
    p.add_argument("--model", choices=("rf", "lgb"), default="rf")
    p.add_argument("--min-positives", type=int, default=5)
    p.add_argument("--test-size", type=float, default=0.2)
    p.add_argument("--random-state", type=int, default=42)
    p.add_argument("--log-level", default="INFO")
    return p.parse_args()


def main():
    args = parse_args()
    setup_logging(getattr(logging, args.log_level.upper(), logging.INFO))
    db_path = Path(args.db)
    model_path = Path(args.model_path)

    logging.info("Loading events from %s", db_path)
    df = load_events(db_path)
    logging.info("Total events: %d", len(df))

    logging.info("Building samples (window=%dd step=%d)", args.window, args.step)
    samp = build_samples(df, window_days=args.window, step_days=args.step)
    logging.info("Total samples: %d", len(samp))
    if samp.empty:
        logging.error("No samples generated — aborting.")
        return

    if samp["label"].sum() < args.min_positives:
        logging.error("Too few positive labels (%d) — need at least %d", int(samp["label"].sum()), args.min_positives)
        logging.info("Label distribution:\n%s", samp["label"].value_counts())
        return

    features = [c for c in samp.columns if c not in ("anchor_time", "label")]
    X = samp[features].drop(columns=[c for c in features if c == "anchor_time" and c in features], errors="ignore")
    y = samp["label"]

    logging.info("Training model (%s)...", args.model)
    model = train_model(X, y, model_choice=args.model, test_size=args.test_size, random_state=args.random_state)

    params = {"window": args.window, "step": args.step, "model_choice": args.model}
    logging.info("Saving model to %s", model_path)
    save_model(model_path, model, list(X.columns), params)
    logging.info("Done")


if __name__ == "__main__":
    main()
