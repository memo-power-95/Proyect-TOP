import sqlite3
from pathlib import Path
from datetime import datetime
import streamlit as st
import pandas as pd


DB_PATH = Path(__file__).resolve().parents[1] / "data" / "data.db"


def get_conn():
    DB_PATH.parent.mkdir(exist_ok=True)
    return sqlite3.connect(DB_PATH)


def ensure_table():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS maintenance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_id TEXT,
            title TEXT,
            description TEXT,
            due_date TEXT,
            assigned_to TEXT,
            status TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def fetch_tasks():
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM maintenance ORDER BY due_date IS NULL, due_date", conn)
    conn.close()
    return df


def add_task(task):
    conn = get_conn()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    cur.execute(
        "INSERT INTO maintenance (machine_id, title, description, due_date, assigned_to, status, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)",
        (
            task.get("machine_id"),
            task.get("title"),
            task.get("description"),
            task.get("due_date"),
            task.get("assigned_to"),
            task.get("status", "pending"),
            now,
            now,
        ),
    )
    conn.commit()
    conn.close()


def update_task(task_id, updates):
    conn = get_conn()
    cur = conn.cursor()
    sets = []
    vals = []
    for k, v in updates.items():
        sets.append(f"{k} = ?")
        vals.append(v)
    vals.append(datetime.utcnow().isoformat())
    vals.append(task_id)
    sql = f"UPDATE maintenance SET {', '.join(sets)}, updated_at = ? WHERE id = ?"
    cur.execute(sql, vals)
    conn.commit()
    conn.close()


def delete_task(task_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM maintenance WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()


def main():
    st.set_page_config(page_title="App Mantenimiento", layout="wide")
    ensure_table()

    st.title("App de Mantenimiento")

    with st.sidebar:
        st.header("Nueva tarea")
        machine_id = st.text_input("ID máquina")
        title = st.text_input("Título")
        description = st.text_area("Descripción")
        due_date = st.date_input("Fecha objetivo", value=None)
        assigned_to = st.text_input("Asignado a")
        if st.button("Crear tarea"):
            task = {
                "machine_id": machine_id or None,
                "title": title,
                "description": description or None,
                "due_date": due_date.isoformat() if due_date else None,
                "assigned_to": assigned_to or None,
                "status": "pending",
            }
            add_task(task)
            st.success("Tarea creada")

    st.subheader("Tareas existentes")
    df = fetch_tasks()
    if df.empty:
        st.info("No hay tareas programadas")
        return

    # Filters
    cols = st.columns([2, 1, 1, 1, 1])
    with cols[0]:
        filt_machine = st.text_input("Filtrar por máquina")
    with cols[1]:
        filt_status = st.selectbox("Estado", options=["all", "pending", "in_progress", "done"], index=0)
    with cols[2]:
        filt_assigned = st.text_input("Asignado a")

    q = df
    if filt_machine:
        q = q[q["machine_id"].str.contains(filt_machine, na=False)]
    if filt_status != "all":
        q = q[q["status"] == filt_status]
    if filt_assigned:
        q = q[q["assigned_to"].str.contains(filt_assigned, na=False)]

    st.dataframe(q.reset_index(drop=True))

    st.subheader("Acciones")
    sel_id = st.number_input("ID tarea (para acciones)", min_value=0, step=1, value=0)
    if sel_id:
        task_row = df[df["id"] == sel_id]
        if task_row.empty:
            st.error("ID no encontrado")
        else:
            t = task_row.iloc[0].to_dict()
            st.write(t)
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("Marcar como realizada"):
                    update_task(sel_id, {"status": "done"})
                    st.success("Marcada como realizada")
            with col2:
                new_status = st.selectbox("Cambiar estado", ["pending", "in_progress", "done"], index=["pending","in_progress","done"].index(t.get("status","pending")))
                if st.button("Aplicar estado"):
                    update_task(sel_id, {"status": new_status})
                    st.success("Estado actualizado")
            with col3:
                if st.button("Eliminar tarea"):
                    delete_task(sel_id)
                    st.success("Tarea eliminada")


if __name__ == "__main__":
    main()
