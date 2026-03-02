from pathlib import Path
import sqlite3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import joblib
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "data.db"
MODEL_PATH = ROOT / "models" / "predictor.joblib"

app = FastAPI(title="Simulador TOP - API")


def db_exists():
    return DB_PATH.exists()


def query_one(sql: str):
    if not db_exists():
        return None
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(sql)
    res = cur.fetchone()
    conn.close()
    return res


@app.get("/health")
def health():
    ok = True
    db_ok = db_exists()
    recent = 0
    if db_ok:
        try:
            r = query_one("SELECT COUNT(1) FROM events")
            recent = int(r[0]) if r else 0
        except Exception:
            db_ok = False
            ok = False
    return {"status": "ok" if ok else "error", "db_exists": db_ok, "events_count": recent}


@app.get("/db-status")
def db_status():
    if not db_exists():
        return {"db_exists": False}
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    counts = {}
    for t in tables:
        try:
            cur.execute(f"SELECT COUNT(1) FROM {t}")
            counts[t] = cur.fetchone()[0]
        except Exception:
            counts[t] = None
    conn.close()
    return {"db_exists": True, "tables": tables, "counts": counts}


class PredictRequest(BaseModel):
    machine_id: str | None = None


@app.post("/predict")
def predict(req: PredictRequest):
    # load model
    if not MODEL_PATH.exists():
        raise HTTPException(status_code=404, detail="Model not found. Train it with scripts/train_predictor.py")
    meta = joblib.load(MODEL_PATH)
    model = meta.get("model")
    features = meta.get("features", [])

    # build a simple feature vector from recent DB info
    if not DB_PATH.exists():
        raise HTTPException(status_code=404, detail="DB not found")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # fetch last 7 days for the machine
    params = []
    if req.machine_id:
        cur.execute("SELECT timestamp, data FROM events WHERE data LIKE ? ORDER BY timestamp DESC LIMIT 1000", (f"%{req.machine_id}%",))
        rows = cur.fetchall()
    else:
        cur.execute("SELECT timestamp, data FROM events ORDER BY timestamp DESC LIMIT 1000")
        rows = cur.fetchall()
    conn.close()

    # crude feature extraction mirroring train script
    now = pd.Timestamp.now()
    past_7d = now - pd.Timedelta(days=7)
    events_count_7d = 0
    failures_count_7d = 0
    maint_count_7d = 0
    last_event_ts = None
    for ts_s, data_s in rows:
        try:
            ts = pd.to_datetime(ts_s)
        except Exception:
            continue
        if ts >= past_7d:
            events_count_7d += 1
            txt = str(data_s).lower()
            if any(k in txt for k in ("fail", "fault", "error", "shutdown", "fallen")):
                failures_count_7d += 1
            if "manten" in str(data_s).lower() or "bitacora" in str(data_s).lower():
                maint_count_7d += 1
            if last_event_ts is None:
                last_event_ts = ts

    hours_since_last_event = (now - last_event_ts).total_seconds() / 3600.0 if last_event_ts is not None else 9999.0
    days_since_last_maint = 9999.0

    feat_vec = []
    for f in features:
        if f == "events_count_7d":
            feat_vec.append(events_count_7d)
        elif f == "failures_count_7d":
            feat_vec.append(failures_count_7d)
        elif f == "maint_count_7d":
            feat_vec.append(maint_count_7d)
        elif f == "days_since_last_maint":
            feat_vec.append(days_since_last_maint)
        elif f == "hours_since_last_event":
            feat_vec.append(hours_since_last_event)
        else:
            feat_vec.append(0)

    X = np.array([feat_vec], dtype=float)
    try:
        proba = model.predict_proba(X)[0, 1] if hasattr(model, "predict_proba") else float(model.predict(X)[0])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model prediction failed: {e}")

    return {"machine_id": req.machine_id, "failure_probability_7d": float(proba)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
