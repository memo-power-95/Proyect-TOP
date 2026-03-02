from pathlib import Path
import sqlite3
import pandas as pd
import json
from datetime import datetime


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "data.db"


def ensure_db():
    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            timestamp TEXT,
            data TEXT
        )
        """
    )
    conn.commit()
    return conn


def detect_timestamp(row):
    # try common timestamp column names
    for key in row.keys():
        k = key.lower()
        if k in ("timestamp", "time", "fecha", "ts", "date", "datetime"):
            return row.get(key)
    return None


def ingest_csv(csv_path: Path, source: str, conn: sqlite3.Connection):
    df = pd.read_csv(csv_path, dtype=str, encoding_errors='replace')
    inserted = 0
    cur = conn.cursor()
    for _, r in df.iterrows():
        row = r.dropna().to_dict()
        ts = detect_timestamp(row)
        if ts is None:
            ts = datetime.utcnow().isoformat()
        cur.execute(
            "INSERT INTO events (source, timestamp, data) VALUES (?, ?, ?)",
            (source, str(ts), json.dumps(row, ensure_ascii=False)),
        )
        inserted += 1
    conn.commit()
    return inserted


def find_and_ingest(conn: sqlite3.Connection):
    # possible CSV locations in the project
    candidates = [
        ROOT / "bitacora_mantenimiento.csv",
        ROOT / "logs_tiempo_real.csv",
        ROOT / "v1" / "bitacora_mantenimiento.csv",
        ROOT / "v1" / "logs_tiempo_real.csv",
        ROOT / "v2" / "logs_tiempo_real.csv",
        ROOT / "v2.1" / "logs_tiempo_real.csv",
    ]
    total = 0
    for p in candidates:
        if p.exists():
            src = p.name
            print(f"Ingesting {p} as {src} ...")
            try:
                n = ingest_csv(p, src, conn)
                print(f"  inserted {n} rows")
                total += n
            except Exception as e:
                print(f"  failed to ingest {p}: {e}")
    return total


def main():
    conn = ensure_db()
    total = find_and_ingest(conn)
    print(f"Migration finished. Total inserted: {total}")


if __name__ == "__main__":
    main()
