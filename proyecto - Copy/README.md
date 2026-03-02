# Proyecto - migración rápida y API health

Archivos añadidos:
- `scripts/migrate_csv_to_sqlite.py`: script para migrar CSVs conocidos a `data/data.db` (tabla `events`).
- `api/main.py`: FastAPI con endpoints `/health` y `/db-status`.
- `requirements.txt`: dependencias mínimas.

Uso rápido:

1. Instalar dependencias:

```powershell
pip install -r requirements.txt
```

2. Ejecutar migración (crea `data/data.db`):

```powershell
python scripts/migrate_csv_to_sqlite.py
```

3. Levantar API:

```powershell
uvicorn api.main:app --reload
```

Siguientes pasos recomendados: revisar y adaptar el esquema DB, exponer endpoints de máquinas, y conectar productores (MQTT/WebSocket) para streaming.
