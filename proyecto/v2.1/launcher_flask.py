"""TOP SYSTEM unified web launcher and dashboards (Flask)."""

from __future__ import annotations

import csv
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import psutil
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

DIRECTORIO_BASE = Path(__file__).resolve().parent
ARCHIVO_LOGS = DIRECTORIO_BASE / "logs_tiempo_real.csv"  # Para compatibilidad
ARCHIVOS_LOGS_POR_LINEA = {
    1: DIRECTORIO_BASE / "logs_tiempo_real_linea_1.csv",
    2: DIRECTORIO_BASE / "logs_tiempo_real_linea_2.csv"
}
ARCHIVO_MTO = DIRECTORIO_BASE / "bitacora_mantenimiento.csv"
CYCLE_TIME_IDEAL = 138.0
LINEAS_ACTIVAS = [1, 2]

# Tiempo ideal por linea (segundos). Linea 1 usa el desglose compartido por usuario.
CYCLE_TIME_IDEAL_BY_LINE: dict[int, float] = {
    1: 855.78,
    2: 855.78,
}

MAQUINAS_POR_LINEA: dict[int, list[str]] = {
    1: [
        "Top cover feeding",
        "Pre-weighing",
        "Tim dispensing",
        "Avl Tim",
        "Weighing",
        "Install PCB",
        "Fastening 1",
        "Fastening 2",
        "Avl screw",
        "Top unloader",
    ],
    2: [
        "Top cover feeding",
        "Pre-weighing",
        "Tim dispensing",
        "Avl Tim",
        "Weighing",
        "Install PCB",
        "Fastening 1",
        "Fastening 2",
        "Avl screw",
        "Top unloader",
    ],
}

MACHINE_CYCLE_TIME_IDEAL: dict[int, dict[str, float]] = {
    1: {
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
    },
    2: {
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
    },
}


def _tc_objetivo_maquina(linea: int, maquina: str) -> float:
    line_cfg = MACHINE_CYCLE_TIME_IDEAL.get(linea, {})
    if maquina in line_cfg:
        return float(line_cfg[maquina])
    # fallback a configuracion de linea 1 para simulacion homogénea entre lineas
    if maquina in MACHINE_CYCLE_TIME_IDEAL.get(1, {}):
        return float(MACHINE_CYCLE_TIME_IDEAL[1][maquina])
    return float(CYCLE_TIME_IDEAL)


def _tc_promedio_linea(df_op: pd.DataFrame) -> float:
    """TC promedio de linea (total): suma de TC por timestamp, luego promedio."""
    if df_op.empty:
        return 0.0

    if "Maquina" in df_op.columns and "Timestamp" in df_op.columns and df_op["Maquina"].nunique() > 1:
        serie = df_op.groupby("Timestamp")["Tiempo_Ciclo"].sum(min_count=1).dropna()
        return float(serie.mean() or 0)

    return float(df_op["Tiempo_Ciclo"].dropna().mean() or 0)

procesos_activos: dict[str, dict[str, Any]] = {}

CATALOGO_MTO: dict[int, tuple[str, int, float]] = {
    1: ("Limpieza Sensor", 5, 100.0),
    2: ("Calibracion Torque", 10, 100.0),
    3: ("Cambio Servomotor", 20, 100.0),
    4: ("Soft Reset", 3, 75.0),
}

MODULOS = [
    {
        "id": 1,
        "nombre": "MOTOR IOT (Backend)",
        "script": "1_Generador_Maquinas.py",
        "descripcion": "Motor de generacion de datos IoT en tiempo real",
        "icon": "▶",
        "color": "success",
        "categoria": "Backend",
    },
    {
        "id": 2,
        "nombre": "DASHBOARD VIVO",
        "script": "2_Dashboard_Vivo.py",
        "descripcion": "Monitoreo operativo en tiempo real",
        "icon": "📈",
        "color": "primary",
        "categoria": "Operativo",
    },
    {
        "id": 3,
        "nombre": "DASHBOARD LOGS",
        "script": "3_Dashboard_Logs.py",
        "descripcion": "Analisis historico de logs del sistema",
        "icon": "🗂",
        "color": "info",
        "categoria": "Operativo",
    },
    {
        "id": 4,
        "nombre": "APP MANTENIMIENTO",
        "script": "4_App_Mantenimiento.py",
        "descripcion": "Gestion y registro de tareas de mantenimiento",
        "icon": "🛠",
        "color": "warning",
        "categoria": "Tecnico",
    },
    {
        "id": 5,
        "nombre": "DASHBOARD OEE",
        "script": "5_Dashboard_OEE.py",
        "descripcion": "Indicadores gerenciales de eficiencia (OEE)",
        "icon": "📊",
        "color": "purple",
        "categoria": "Gerencial",
    },
    {
        "id": 6,
        "nombre": "MANTENIMIENTO PREDICTIVO",
        "script": "6_Predictive_Maintenance.py",
        "descripcion": "Sistema de prediccion de fallos",
        "icon": "🤖",
        "color": "dark",
        "categoria": "Analitico",
    },
]


def _read_logs() -> pd.DataFrame:
    """Lee logs de ambas líneas y retorna dataframe combinado."""
    dfs = []
    for lid in LINEAS_ACTIVAS:
        archivo = ARCHIVOS_LOGS_POR_LINEA[lid]
        if archivo.exists():
            try:
                df = pd.read_csv(archivo)
                dfs.append(df)
            except Exception:
                pass
    
    if not dfs:
        return pd.DataFrame(columns=["Timestamp", "Linea", "Maquina", "Salud", "Tiempo_Ciclo", "Evento"])
    
    df = pd.concat(dfs, ignore_index=True)
    
    for col in ["Linea", "Salud", "Tiempo_Ciclo"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "Timestamp" in df.columns:
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
    if "Maquina" not in df.columns:
        df["Maquina"] = "GENERAL"
    else:
        df["Maquina"] = df["Maquina"].fillna("GENERAL").astype(str)
    if "Evento" not in df.columns:
        df["Evento"] = ""
    return df


def _read_logs_linea(linea: int) -> pd.DataFrame:
    """Lee logs de una línea específica."""
    archivo = ARCHIVOS_LOGS_POR_LINEA.get(linea)
    if not archivo or not archivo.exists():
        return pd.DataFrame(columns=["Timestamp", "Linea", "Maquina", "Salud", "Tiempo_Ciclo", "Evento"])
    try:
        df = pd.read_csv(archivo)
    except Exception:
        return pd.DataFrame(columns=["Timestamp", "Linea", "Maquina", "Salud", "Tiempo_Ciclo", "Evento"])

    for col in ["Linea", "Salud", "Tiempo_Ciclo"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "Timestamp" in df.columns:
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
    if "Maquina" not in df.columns:
        df["Maquina"] = "GENERAL"
    else:
        df["Maquina"] = df["Maquina"].fillna("GENERAL").astype(str)
    if "Evento" not in df.columns:
        df["Evento"] = ""
    return df


def _ensure_mto_file() -> None:
    if ARCHIVO_MTO.exists():
        return
    with ARCHIVO_MTO.open("w", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerow(["Timestamp", "Linea", "Maquina", "Accion", "Duracion", "Salud_Final"])


def _read_mantenimiento() -> pd.DataFrame:
    _ensure_mto_file()
    try:
        df = pd.read_csv(ARCHIVO_MTO)
    except Exception:
        return pd.DataFrame(columns=["Timestamp", "Linea", "Maquina", "Accion", "Duracion", "Salud_Final"])

    if "Timestamp" in df.columns:
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
    for col in ["Linea", "Duracion", "Salud_Final"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _calcular_oee(df_linea: pd.DataFrame, cycle_time_ideal: float) -> dict[str, float]:
    if df_linea.empty:
        return {"disponibilidad": 0.0, "calidad": 0.0, "rendimiento": 0.0, "oee": 0.0}

    total_registros = len(df_linea)
    tiempo_paro = len(df_linea[df_linea["Evento"] == "MANTENIMIENTO"])
    disponibilidad = ((total_registros - tiempo_paro) / total_registros) if total_registros > 0 else 0.0

    df_op = df_linea[df_linea["Evento"] != "MANTENIMIENTO"]
    if df_op.empty:
        return {
            "disponibilidad": round(disponibilidad * 100, 2),
            "calidad": 0.0,
            "rendimiento": 0.0,
            "oee": 0.0,
        }

    scrap_count = len(df_op[df_op["Evento"].astype(str).str.contains("SCRAP", na=False)])
    calidad = (len(df_op) - scrap_count) / len(df_op) if len(df_op) > 0 else 0.0

    tc_promedio_real = _tc_promedio_linea(df_op)
    tc_ajustado = max(tc_promedio_real, cycle_time_ideal)
    rendimiento = cycle_time_ideal / tc_ajustado if tc_ajustado > 0 else 0.0

    oee = disponibilidad * calidad * rendimiento
    return {
        "disponibilidad": round(disponibilidad * 100, 2),
        "calidad": round(calidad * 100, 2),
        "rendimiento": round(rendimiento * 100, 2),
        "oee": round(oee * 100, 2),
        "tc_promedio": round(tc_promedio_real, 2),
        "tc_objetivo": round(cycle_time_ideal, 2),
    }


def _compute_mtbf_mttr(df_mto: pd.DataFrame, line: int) -> tuple[float | None, float | None, Any]:
    d = df_mto[df_mto["Linea"] == line].sort_values("Timestamp")
    if d.empty:
        return None, None, None

    times = d["Timestamp"].dropna()
    mttr = float(d["Duracion"].dropna().mean() or 0)
    if len(times) < 2:
        return None, mttr, times.max() if not times.empty else None

    diffs = times.diff().dt.total_seconds().dropna()
    mtbf = float(diffs.mean()) if not diffs.empty else None
    return mtbf, mttr, times.max()


def _predict_time_to_failure(mtbf_seconds: float | None, last_ts: Any) -> tuple[float | None, float | None]:
    if mtbf_seconds is None or pd.isna(last_ts):
        return None, None
    now = pd.Timestamp.now()
    elapsed = (now - pd.to_datetime(last_ts)).total_seconds()
    remaining = mtbf_seconds - elapsed
    risk = min(100.0, max(0.0, (elapsed / mtbf_seconds) * 100.0)) if mtbf_seconds > 0 else 100.0
    return remaining, risk


def _downtime_by_shift(df_mto: pd.DataFrame, line: int, start: str | None, end: str | None) -> dict[str, float]:
    d = df_mto[df_mto["Linea"] == line].copy()
    if d.empty:
        return {"Morning": 0.0, "Afternoon": 0.0, "Night": 0.0}

    d["Timestamp"] = pd.to_datetime(d["Timestamp"], errors="coerce")
    if start:
        d = d[d["Timestamp"] >= pd.to_datetime(start, errors="coerce")]
    if end:
        d = d[d["Timestamp"] <= pd.to_datetime(end, errors="coerce")]

    def shift_of(ts: Any) -> str:
        if pd.isna(ts):
            return "Night"
        h = ts.hour
        if 6 <= h < 14:
            return "Morning"
        if 14 <= h < 22:
            return "Afternoon"
        return "Night"

    d["Shift"] = d["Timestamp"].apply(shift_of)
    d["Duracion"] = pd.to_numeric(d["Duracion"], errors="coerce").fillna(0)
    g = d.groupby("Shift")["Duracion"].sum().to_dict()
    return {k: float(g.get(k, 0.0)) for k in ("Morning", "Afternoon", "Night")}


@app.route("/")
def index():
    return render_template("launcher.html", modulos=MODULOS, catalogo=CATALOGO_MTO)


@app.route("/api/modulos")
def get_modulos():
    modulos_con_estado = []
    for modulo in MODULOS:
        script = modulo["script"]
        estado = get_estado_proceso(script)
        modulos_con_estado.append({**modulo, "estado": estado})
    return jsonify(modulos_con_estado)


@app.route("/api/lanzar/<int:modulo_id>", methods=["POST"])
def lanzar_modulo(modulo_id: int):
    modulo = next((m for m in MODULOS if m["id"] == modulo_id), None)
    if not modulo:
        return jsonify({"success": False, "error": "Modulo no encontrado"}), 404

    script = modulo["script"]
    ruta_completa = DIRECTORIO_BASE / script
    if not ruta_completa.exists():
        return jsonify({"success": False, "error": f"Script no encontrado: {script}"}), 404

    if script in procesos_activos and procesos_activos[script]["proceso"].poll() is None:
        return jsonify({"success": False, "error": "El modulo ya esta en ejecucion"}), 400

    try:
        if os.name == "nt":
            creationflags = subprocess.CREATE_NEW_CONSOLE
            proceso = subprocess.Popen([sys.executable, str(ruta_completa)], creationflags=creationflags)
        else:
            proceso = subprocess.Popen([sys.executable, str(ruta_completa)])

        procesos_activos[script] = {
            "proceso": proceso,
            "modulo_id": modulo_id,
            "nombre": modulo["nombre"],
            "inicio": datetime.now().isoformat(),
            "pid": proceso.pid,
        }
        return jsonify({"success": True, "mensaje": f"Modulo {modulo['nombre']} iniciado", "pid": proceso.pid})
    except Exception as exc:
        return jsonify({"success": False, "error": f"Error al lanzar el modulo: {exc}"}), 500


@app.route("/api/detener/<int:modulo_id>", methods=["POST"])
def detener_modulo(modulo_id: int):
    modulo = next((m for m in MODULOS if m["id"] == modulo_id), None)
    if not modulo:
        return jsonify({"success": False, "error": "Modulo no encontrado"}), 404

    script = modulo["script"]
    if script not in procesos_activos:
        return jsonify({"success": False, "error": "El modulo no esta en ejecucion"}), 400

    try:
        proceso = procesos_activos[script]["proceso"]
        if proceso.poll() is None:
            proceso.terminate()
            try:
                proceso.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proceso.kill()
        del procesos_activos[script]
        return jsonify({"success": True, "mensaje": f"Modulo {modulo['nombre']} detenido"})
    except Exception as exc:
        return jsonify({"success": False, "error": f"Error al detener el modulo: {exc}"}), 500


@app.route("/api/detener_todos", methods=["POST"])
def detener_todos():
    detenidos: list[str] = []
    errores: list[str] = []
    for script, info in list(procesos_activos.items()):
        try:
            proceso = info["proceso"]
            if proceso.poll() is None:
                proceso.terminate()
                try:
                    proceso.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proceso.kill()
            detenidos.append(info["nombre"])
        except Exception as exc:
            errores.append(f"{info['nombre']}: {exc}")
        finally:
            if script in procesos_activos:
                del procesos_activos[script]

    return jsonify({"success": len(errores) == 0, "detenidos": detenidos, "errores": errores})


@app.route("/api/estado")
def get_estado_sistema():
    procesos = []
    for script, info in list(procesos_activos.items()):
        proceso = info["proceso"]
        estado = "running" if proceso.poll() is None else "stopped"

        cpu = None
        memoria = None
        try:
            p = psutil.Process(proceso.pid)
            cpu = p.cpu_percent(interval=0.05)
            memoria = p.memory_info().rss / 1024 / 1024
        except Exception:
            pass

        procesos.append(
            {
                "script": script,
                "nombre": info["nombre"],
                "pid": info["pid"],
                "estado": estado,
                "inicio": info["inicio"],
                "cpu": cpu,
                "memoria": memoria,
            }
        )

    return jsonify({"total_procesos": len(procesos), "procesos": procesos, "directorio": str(DIRECTORIO_BASE)})


@app.route("/api/dashboard/vivo")
def api_dashboard_vivo():
    df = _read_logs()
    line = int(request.args.get("linea", "1"))
    maquina = str(request.args.get("maquina", "ALL")).strip()
    window = int(request.args.get("window", "60"))

    if "Linea" in df.columns:
        df = df[df["Linea"] == line]
    else:
        df = pd.DataFrame(columns=df.columns)

    # Ventana por timestamps para no cortar parcialmente la linea cuando hay varias maquinas.
    if not df.empty and "Timestamp" in df.columns:
        df = df.sort_values("Timestamp")
        ts_unicos = df["Timestamp"].dropna().drop_duplicates().tail(max(10, window))
        if not ts_unicos.empty:
            df = df[df["Timestamp"].isin(ts_unicos)]

    df_raw_for_machine = df.copy()

    if maquina and maquina != "ALL" and "Maquina" in df.columns:
        df = df[df["Maquina"] == maquina]

    # Vista general de linea: consolidar por timestamp para mostrar TC total de linea.
    if maquina == "ALL" and not df.empty and "Maquina" in df.columns and df["Maquina"].nunique() > 1:
        df_grouped = (
            df.groupby("Timestamp", as_index=False)
            .agg(
                Salud=("Salud", "mean"),
                Tiempo_Ciclo=("Tiempo_Ciclo", "sum"),
                Evento=("Evento", lambda s: "|".join(sorted(set(s.astype(str)))))
            )
            .sort_values("Timestamp")
            .tail(max(10, window))
        )
        df = df_grouped

    health_values = [float(v) for v in df.get("Salud", pd.Series(dtype=float)).fillna(0).tolist()]
    cycle_values = [float(v) for v in df.get("Tiempo_Ciclo", pd.Series(dtype=float)).fillna(0).tolist()]
    labels = [str(ts) for ts in df.get("Timestamp", pd.Series(dtype=object)).dt.strftime("%H:%M:%S").fillna("-").tolist()]

    eventos = (
        df.get("Evento", pd.Series(dtype=str)).fillna("").astype(str).value_counts().head(8).to_dict()
        if not df.empty
        else {}
    )

    # Rendimiento general de linea (TC total de linea por timestamp vs objetivo de linea).
    dline_op = (
        df_raw_for_machine[df_raw_for_machine["Evento"] != "MANTENIMIENTO"]
        if "Evento" in df_raw_for_machine.columns
        else df_raw_for_machine
    )
    tc_linea_real = _tc_promedio_linea(dline_op)
    tc_linea_obj = float(CYCLE_TIME_IDEAL_BY_LINE.get(line, CYCLE_TIME_IDEAL))
    tc_linea_adj = max(tc_linea_real, tc_linea_obj)
    rendimiento_linea = round((tc_linea_obj / tc_linea_adj) * 100.0 if tc_linea_adj > 0 else 0.0, 2)

    stats = {
        "linea": line,
        "maquina": maquina,
        "muestras": int(len(df)),
        "salud_promedio": round(float(pd.Series(health_values).mean() or 0), 2),
        "salud_min": round(float(pd.Series(health_values).min() if health_values else 0), 2),
        "tc_promedio": round(float(pd.Series(cycle_values).mean() or 0), 2),
        "tc_max": round(float(pd.Series(cycle_values).max() if cycle_values else 0), 2),
        "rendimiento_linea": rendimiento_linea,
        "tc_linea_real": round(tc_linea_real, 2),
        "tc_linea_objetivo": round(tc_linea_obj, 2),
    }

    rendimiento_por_maquina: dict[str, float] = {}
    if not df_raw_for_machine.empty and "Maquina" in df_raw_for_machine.columns:
        for maq, dmaq in df_raw_for_machine.groupby("Maquina"):
            tc_obj = _tc_objetivo_maquina(line, str(maq))
            tc_real = float(dmaq["Tiempo_Ciclo"].dropna().mean() or 0)
            tc_adj = max(tc_real, tc_obj)
            rend = (tc_obj / tc_adj * 100.0) if tc_adj > 0 else 0.0
            rendimiento_por_maquina[str(maq)] = round(rend, 2)

    return jsonify({
        "labels": labels,
        "salud": health_values,
        "tiempo_ciclo": cycle_values,
        "eventos": eventos,
        "stats": stats,
        "rendimiento_por_maquina": rendimiento_por_maquina,
    })


@app.route("/api/dashboard/logs")
def api_dashboard_logs():
    df = _read_logs()
    if df.empty:
        return jsonify({
            "kpis": {},
            "pareto": {},
            "calidad": {"OK": 0, "SCRAP": 0, "MICRO": 0},
            "rendimiento_por_linea": {},
            "rendimiento_por_maquina": {},
        })

    df_prod = df[df["Evento"] != "MANTENIMIENTO"].copy()
    total_ciclos = len(df_prod)
    ok_count = len(df_prod[df_prod["Evento"] == "OK"])
    scrap_count = len(df_prod[df_prod["Evento"].astype(str).str.contains("SCRAP", na=False)])
    micro_count = len(df_prod[df_prod["Evento"].astype(str).str.contains("MICRO", na=False)])

    pareto = df_prod[df_prod["Evento"] != "OK"]["Evento"].value_counts().head(10).to_dict()
    rendimiento = (ok_count / total_ciclos * 100) if total_ciclos > 0 else 0

    kpis = {
        "total_ciclos": total_ciclos,
        "ok": ok_count,
        "scrap": scrap_count,
        "micro": micro_count,
        "rendimiento": round(rendimiento, 2),
    }

    rendimiento_por_linea: dict[str, float] = {}
    rendimiento_por_maquina: dict[str, dict[str, float]] = {}
    if "Linea" in df_prod.columns:
        for lid in LINEAS_ACTIVAS:
            dline = df_prod[df_prod["Linea"] == lid]
            if dline.empty:
                rendimiento_por_linea[str(lid)] = 0.0
                rendimiento_por_maquina[str(lid)] = {}
                continue

            tc_obj_linea = CYCLE_TIME_IDEAL_BY_LINE.get(lid, CYCLE_TIME_IDEAL)
            tc_real_linea = _tc_promedio_linea(dline)
            tc_adj_linea = max(tc_real_linea, tc_obj_linea)
            rendimiento_por_linea[str(lid)] = round((tc_obj_linea / tc_adj_linea) * 100.0 if tc_adj_linea > 0 else 0.0, 2)

            por_maquina: dict[str, float] = {}
            if "Maquina" in dline.columns:
                for maq, dmaq in dline.groupby("Maquina"):
                    tc_obj_maq = _tc_objetivo_maquina(lid, str(maq))
                    tc_real_maq = float(dmaq["Tiempo_Ciclo"].dropna().mean() or 0)
                    tc_adj_maq = max(tc_real_maq, tc_obj_maq)
                    por_maquina[str(maq)] = round((tc_obj_maq / tc_adj_maq) * 100.0 if tc_adj_maq > 0 else 0.0, 2)
            rendimiento_por_maquina[str(lid)] = por_maquina

    return jsonify({
        "kpis": kpis,
        "pareto": pareto,
        "calidad": {"OK": ok_count, "SCRAP": scrap_count, "MICRO": micro_count},
        "rendimiento_por_linea": rendimiento_por_linea,
        "rendimiento_por_maquina": rendimiento_por_maquina,
    })


@app.route("/api/dashboard/oee")
def api_dashboard_oee():
    df = _read_logs()
    results: dict[str, Any] = {
        "lineas": {},
        "global": 0.0,
        "rendimiento_por_linea": {},
        "rendimiento_general": 0.0,
    }
    valores_oee = []
    valores_rend = []

    for lid in LINEAS_ACTIVAS:
        if "Linea" in df.columns:
            df_linea = df[df["Linea"] == lid]
        else:
            df_linea = pd.DataFrame(columns=df.columns)

        tc_objetivo = CYCLE_TIME_IDEAL_BY_LINE.get(lid, CYCLE_TIME_IDEAL)
        metricas = _calcular_oee(df_linea, tc_objetivo)
        metricas_maquinas: dict[str, dict[str, float]] = {}
        if not df_linea.empty and "Maquina" in df_linea.columns:
            for maq in sorted(df_linea["Maquina"].dropna().astype(str).unique().tolist()):
                dmaq = df_linea[df_linea["Maquina"] == maq]
                metricas_maquinas[maq] = _calcular_oee(dmaq, _tc_objetivo_maquina(lid, maq))

        metricas["maquinas"] = metricas_maquinas
        results["lineas"][str(lid)] = metricas
        results["rendimiento_por_linea"][str(lid)] = metricas["rendimiento"]

        if not df_linea.empty:
            valores_oee.append(metricas["oee"])
            valores_rend.append(metricas["rendimiento"])

    results["global"] = round(float(sum(valores_oee) / len(valores_oee)), 2) if valores_oee else 0.0
    results["rendimiento_general"] = (
        round(float(sum(valores_rend) / len(valores_rend)), 2) if valores_rend else 0.0
    )
    return jsonify(results)


@app.route("/api/maquinas")
def api_maquinas():
    line = int(request.args.get("linea", "1"))
    catalogo = MAQUINAS_POR_LINEA.get(line, [])

    # Si hay data real en logs, priorizar lo observado para reflejar planta real.
    df = _read_logs()
    if not df.empty and "Linea" in df.columns and "Maquina" in df.columns:
        d = df[df["Linea"] == line]
        observadas = sorted(d["Maquina"].dropna().astype(str).unique().tolist())
        if observadas:
            catalogo = observadas

    return jsonify({"linea": line, "maquinas": catalogo})


@app.route("/api/linea/<int:linea_id>")
def api_linea(linea_id):
    """Retorna rendimiento, máquinas y mantenimiento para una línea específica."""
    if linea_id not in LINEAS_ACTIVAS:
        return jsonify({"error": "Línea no válida"}), 404
    
    df = _read_logs_linea(linea_id)
    df_prod = df[df["Evento"] != "MANTENIMIENTO"].copy() if not df.empty else df
    
    # KPI de línea
    total_ciclos = len(df_prod)
    ok_count = len(df_prod[df_prod["Evento"] == "OK"]) if not df_prod.empty else 0
    
    # Rendimiento linea
    tc_obj_linea = CYCLE_TIME_IDEAL_BY_LINE.get(linea_id, CYCLE_TIME_IDEAL)
    tc_real_linea = _tc_promedio_linea(df_prod) if not df_prod.empty else 0
    tc_adj_linea = max(tc_real_linea, tc_obj_linea)
    rendimiento_linea = round((tc_obj_linea / tc_adj_linea) * 100.0 if tc_adj_linea > 0 else 0.0, 2)
    
    # Máquinas en mantenimiento
    maquinas_mantenimiento = []
    if not df.empty:
        mto_now = df[df["Evento"] == "MANTENIMIENTO"]
        if not mto_now.empty:
            maquinas_mantenimiento = mto_now["Maquina"].unique().tolist()
    
    # Rendimiento por máquina
    rendimiento_por_maquina = {}
    if not df_prod.empty and "Maquina" in df_prod.columns:
        for maq, dmaq in df_prod.groupby("Maquina"):
            tc_obj_maq = _tc_objetivo_maquina(linea_id, str(maq))
            tc_real_maq = float(dmaq["Tiempo_Ciclo"].dropna().mean() or 0)
            tc_adj_maq = max(tc_real_maq, tc_obj_maq)
            rendimiento_por_maquina[str(maq)] = round((tc_obj_maq / tc_adj_maq) * 100.0 if tc_adj_maq > 0 else 0.0, 2)
    
    # Últimos registros de mantenimiento para esta línea
    df_mto = _read_mantenimiento()
    ultimos_mto = []
    if not df_mto.empty:
        mto_linea = df_mto[df_mto["Linea"] == linea_id].tail(10)
        for _, row in mto_linea.iterrows():
            ultimos_mto.append({
                "timestamp": str(row.get("Timestamp", ""))[:19],
                "maquina": str(row.get("Maquina", "Toda la línea")),
                "accion": str(row.get("Accion", "")),
                "duracion": float(row.get("Duracion", 0) or 0),
                "salud_final": float(row.get("Salud_Final", 0) or 0)
            })
    
    return jsonify({
        "linea": linea_id,
        "kpi": {
            "total_ciclos": total_ciclos,
            "ok": ok_count,
            "rendimiento": rendimiento_linea,
            "tc_real": round(tc_real_linea, 2),
            "tc_objetivo": tc_obj_linea
        },
        "rendimiento_por_maquina": rendimiento_por_maquina,
        "maquinas_en_mantenimiento": maquinas_mantenimiento,
        "ultimos_mantenimientos": ultimos_mto
    })


@app.route("/api/mantenimiento", methods=["GET", "POST"])
def api_mantenimiento():
    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
        linea = int(payload.get("linea", 1))
        maquina = str(payload.get("maquina", "Toda la línea"))
        accion_id = int(payload.get("accion_id", 1))
        if accion_id not in CATALOGO_MTO:
            return jsonify({"success": False, "error": "Accion invalida"}), 400

        accion, duracion, salud = CATALOGO_MTO[accion_id]
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _ensure_mto_file()
        with ARCHIVO_MTO.open("a", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerow([ts, linea, maquina, accion, duracion, salud])
        return jsonify({"success": True, "mensaje": "Mantenimiento registrado"})

    df = _read_mantenimiento().tail(50)
    if df.empty:
        return jsonify({"rows": []})

    rows = []
    for _, row in df.sort_values("Timestamp", ascending=False).iterrows():
        rows.append(
            {
                "Timestamp": str(row.get("Timestamp", ""))[:19],
                "Linea": int(row.get("Linea", 0)) if pd.notna(row.get("Linea")) else 0,
                "Maquina": str(row.get("Maquina", "Toda la línea")),
                "Accion": str(row.get("Accion", "")),
                "Duracion": float(row.get("Duracion", 0) or 0),
                "Salud_Final": float(row.get("Salud_Final", 0) or 0),
            }
        )
    return jsonify({"rows": rows})


@app.route("/api/predictivo")
def api_predictivo():
    """Predictive endpoint mejorado: usa logs de ambas líneas + bitácora de MTO."""
    df_mto = _read_mantenimiento()
    line = int(request.args.get("linea", "0"))  # 0 = ambas
    start = request.args.get("start")
    end = request.args.get("end")

    lineas_analizar = [line] if line in LINEAS_ACTIVAS else LINEAS_ACTIVAS

    resumen_lineas: dict[str, Any] = {}

    for lid in lineas_analizar:
        df_logs = _read_logs_linea(lid)
        if not df_logs.empty and start:
            df_logs = df_logs[df_logs["Timestamp"] >= pd.to_datetime(start, errors="coerce")]
        if not df_logs.empty and end:
            df_logs = df_logs[df_logs["Timestamp"] <= pd.to_datetime(end, errors="coerce")]

        # --- MTBF / MTTR desde bitácora ---
        mtbf, mttr, last_ts = _compute_mtbf_mttr(df_mto, lid)
        remaining, risk_mtbf = _predict_time_to_failure(mtbf, last_ts)

        # --- Métricas por máquina desde logs ---
        maquinas_detalle: list[dict[str, Any]] = []
        if not df_logs.empty and "Maquina" in df_logs.columns:
            for maq, dmaq in df_logs.groupby("Maquina"):
                salud_vals = dmaq["Salud"].dropna()
                tc_vals = dmaq["Tiempo_Ciclo"].dropna()
                eventos = dmaq["Evento"].value_counts().to_dict()

                salud_prom = float(salud_vals.mean()) if not salud_vals.empty else 0.0
                salud_min = float(salud_vals.min()) if not salud_vals.empty else 0.0
                salud_max = float(salud_vals.max()) if not salud_vals.empty else 0.0
                salud_actual = float(salud_vals.iloc[-1]) if not salud_vals.empty else 0.0

                # Tendencia de salud: comparar primera mitad vs segunda mitad
                if len(salud_vals) >= 4:
                    mid = len(salud_vals) // 2
                    salud_primera = salud_vals.iloc[:mid].mean()
                    salud_segunda = salud_vals.iloc[mid:].mean()
                    tendencia_salud = round(float(salud_segunda - salud_primera), 2)
                else:
                    tendencia_salud = 0.0

                tc_prom = float(tc_vals.mean()) if not tc_vals.empty else 0.0
                tc_obj = _tc_objetivo_maquina(lid, str(maq))
                tc_desviacion = round(((tc_prom - tc_obj) / tc_obj) * 100.0, 2) if tc_obj > 0 else 0.0

                total_eventos = len(dmaq)
                # Clasificar eventos reales del generador
                errores = int(eventos.get("CRITICAL", 0)) + int(eventos.get("SENSOR_FAIL", 0)) + int(eventos.get("STUCK", 0))
                scraps = int(eventos.get("SCRAP_PART", 0))
                micros = int(eventos.get("SPIKE", 0)) + int(eventos.get("AJUSTE_OP", 0))
                mtos = int(eventos.get("MANTENIMIENTO", 0))
                oks = int(eventos.get("OK", 0))

                # Riesgo compuesto por máquina (0-100):
                #  40% salud degradada, 30% eventos negativos, 30% desviación TC
                riesgo_salud = max(0.0, min(100.0, 100.0 - salud_actual))
                tasa_fallas = ((errores + scraps + micros) / total_eventos * 100.0) if total_eventos > 0 else 0.0
                riesgo_tc = min(100.0, max(0.0, tc_desviacion * 5.0))  # amplificar desviación
                riesgo_maq = round(riesgo_salud * 0.4 + tasa_fallas * 0.3 + riesgo_tc * 0.3, 2)
                riesgo_maq = min(100.0, max(0.0, riesgo_maq))

                # Nivel de alerta
                if riesgo_maq >= 70:
                    alerta = "CRITICO"
                elif riesgo_maq >= 40:
                    alerta = "ATENCION"
                else:
                    alerta = "NORMAL"

                # Últimos N timestamps para trend de salud
                ultimos = dmaq.sort_values("Timestamp").tail(30)
                salud_trend_labels = [
                    ts.strftime("%H:%M") if pd.notna(ts) else ""
                    for ts in ultimos["Timestamp"]
                ]
                salud_trend_vals = [float(v) for v in ultimos["Salud"].fillna(0)]

                maquinas_detalle.append({
                    "maquina": str(maq),
                    "salud_promedio": round(salud_prom, 2),
                    "salud_min": round(salud_min, 2),
                    "salud_max": round(salud_max, 2),
                    "salud_actual": round(salud_actual, 2),
                    "tendencia_salud": tendencia_salud,
                    "tc_promedio": round(tc_prom, 2),
                    "tc_objetivo": round(tc_obj, 2),
                    "tc_desviacion_pct": tc_desviacion,
                    "total_ciclos": total_eventos,
                    "ok": oks,
                    "errores": errores,
                    "scraps": scraps,
                    "micro_paros": micros,
                    "mantenimientos": mtos,
                    "riesgo": riesgo_maq,
                    "alerta": alerta,
                    "salud_trend": {"labels": salud_trend_labels, "valores": salud_trend_vals},
                })

        # Ordenar máquinas por riesgo descendente
        maquinas_detalle.sort(key=lambda m: m["riesgo"], reverse=True)

        # Riesgo global de línea: promedio ponderado de riesgos de máquinas + MTBF
        if maquinas_detalle:
            riesgo_logs = sum(m["riesgo"] for m in maquinas_detalle) / len(maquinas_detalle)
        else:
            riesgo_logs = 0.0

        # Combinar riesgo MTBF (si existe) con riesgo de logs
        if risk_mtbf is not None:
            riesgo_global = round(riesgo_logs * 0.6 + risk_mtbf * 0.4, 2)
        else:
            riesgo_global = round(riesgo_logs, 2)
        riesgo_global = min(100.0, max(0.0, riesgo_global))

        # Salud general de la línea
        df_salud = df_logs["Salud"].dropna() if not df_logs.empty else pd.Series(dtype=float)
        salud_linea = round(float(df_salud.mean()), 2) if not df_salud.empty else 0.0

        # Resumen de eventos de la línea
        ev_counts = df_logs["Evento"].value_counts().to_dict() if not df_logs.empty else {}

        shifts = _downtime_by_shift(df_mto, lid, start, end)

        resumen_lineas[str(lid)] = {
            "linea": lid,
            "riesgo_global": riesgo_global,
            "salud_promedio": salud_linea,
            "mtbf_hours": round(mtbf / 3600, 2) if mtbf is not None else None,
            "mttr_minutes": round(mttr / 60, 2) if mttr is not None else None,
            "last_maintenance": str(last_ts)[:19] if last_ts is not None else None,
            "predicted_remaining_hours": round(remaining / 3600, 2) if remaining is not None else None,
            "risk_mtbf": round(risk_mtbf, 2) if risk_mtbf is not None else None,
            "downtime_by_shift": shifts,
            "eventos": {k: int(v) for k, v in ev_counts.items()},
            "total_registros": len(df_logs),
            "maquinas": maquinas_detalle,
        }

    # Riesgo global del sistema
    riesgos = [v["riesgo_global"] for v in resumen_lineas.values()]
    riesgo_sistema = round(sum(riesgos) / len(riesgos), 2) if riesgos else 0.0

    return jsonify({
        "riesgo_sistema": riesgo_sistema,
        "lineas": resumen_lineas,
        "generated_at": datetime.now().isoformat(),
    })


def get_estado_proceso(script: str) -> str:
    if script not in procesos_activos:
        return "stopped"
    proceso = procesos_activos[script]["proceso"]
    return "running" if proceso.poll() is None else "stopped"


if __name__ == "__main__":
    print("=" * 60)
    print("TOP SYSTEM - LG INNOTEK")
    print("Portal Unificado Web v2.1")
    print("=" * 60)
    print(f"\nDirectorio base: {DIRECTORIO_BASE}")
    print("\nIniciando servidor Flask...")
    print("\nAccede desde:")
    print("   - Local:    http://localhost:5000")
    print("   - Red:      http://[TU_IP]:5000")
    print("\nPresiona Ctrl+C para detener\n")

    app.run(host="0.0.0.0", port=5000, debug=True)
