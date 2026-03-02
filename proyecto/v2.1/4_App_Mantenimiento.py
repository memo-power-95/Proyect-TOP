import csv
import os
import datetime
import time
import tkinter as tk
from tkinter import ttk, messagebox

ARCHIVO = "bitacora_mantenimiento.csv"
CATALOGO = {
    1: ["Limpieza Sensor", 5, 100.0],
    2: ["Calibración Torque", 10, 100.0],
    3: ["Cambio Servomotor", 20, 100.0],
    4: ["Soft Reset", 3, 75.0]
}


def asegurar_archivo():
    if not os.path.exists(ARCHIVO):
        with open(ARCHIVO, 'w', newline='') as f:
            csv.writer(f).writerow(["Timestamp", "Linea", "Accion", "Duracion", "Salud_Final"])


def registrar_mantenimiento(linea, accion_id):
    ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    accion = CATALOGO[accion_id][0]
    dur = CATALOGO[accion_id][1]
    salud = CATALOGO[accion_id][2]
    with open(ARCHIVO, 'a', newline='') as f:
        csv.writer(f).writerow([ahora, linea, accion, dur, salud])


def leer_ultimos(n=20):
    if not os.path.exists(ARCHIVO):
        return []
    with open(ARCHIVO, 'r', newline='') as f:
        reader = list(csv.reader(f))
        if len(reader) <= 1:
            return []
        return reader[1:][-n:]


def crear_gui():
    asegurar_archivo()
    root = tk.Tk()
    root.title("App Mantenimiento - TOP")
    root.geometry('720x420')

    frm = ttk.Frame(root, padding=10)
    frm.pack(fill='both', expand=True)

    # Controles de registro
    ctrl = ttk.LabelFrame(frm, text='Registrar mantenimiento', padding=10)
    ctrl.pack(fill='x')

    ttk.Label(ctrl, text='Línea:').grid(column=0, row=0, sticky='w')
    linea_cb = ttk.Combobox(ctrl, values=[1, 2, 3], width=5)
    linea_cb.set(1)
    linea_cb.grid(column=1, row=0, padx=6, pady=4)

    ttk.Label(ctrl, text='Acción:').grid(column=2, row=0, sticky='w')
    acciones = [f"{k} - {v[0]} ({v[1]}s, {v[2]}%)" for k, v in CATALOGO.items()]
    accion_cb = ttk.Combobox(ctrl, values=acciones, width=40)
    accion_cb.current(0)
    accion_cb.grid(column=3, row=0, padx=6, pady=4)

    def on_registrar():
        try:
            linea = int(linea_cb.get())
        except:
            messagebox.showerror('Error', 'Línea inválida')
            return
        sel = accion_cb.get()
        if not sel:
            messagebox.showerror('Error', 'Seleccione una acción')
            return
        accion_id = int(sel.split(' - ')[0])
        registrar_mantenimiento(linea, accion_id)
        messagebox.showinfo('Registrado', f'Registro guardado para Línea {linea}')
        cargar_tabla()

    btn_reg = ttk.Button(ctrl, text='Registrar', command=on_registrar)
    btn_reg.grid(column=4, row=0, padx=6)

    # Tabla de últimos registros
    tbl_frm = ttk.LabelFrame(frm, text='Últimos registros', padding=6)
    tbl_frm.pack(fill='both', expand=True, pady=10)

    cols = ("Timestamp", "Linea", "Accion", "Duracion", "Salud_Final")
    tree = ttk.Treeview(tbl_frm, columns=cols, show='headings')
    for c in cols:
        tree.heading(c, text=c)
        tree.column(c, anchor='center')
    tree.pack(fill='both', expand=True, side='left')

    scrollbar = ttk.Scrollbar(tbl_frm, orient='vertical', command=tree.yview)
    tree.configure(yscroll=scrollbar.set)
    scrollbar.pack(side='right', fill='y')

    def cargar_tabla():
        for r in tree.get_children():
            tree.delete(r)
        rows = leer_ultimos(100)
        for row in reversed(rows):
            tree.insert('', 0, values=row)

    cargar_tabla()

    # Footer
    footer = ttk.Frame(frm)
    footer.pack(fill='x', pady=6)
    ttk.Label(footer, text='Archivo de bitácora:').pack(side='left')
    ttk.Label(footer, text=ARCHIVO, foreground='blue').pack(side='left', padx=6)

    root.mainloop()


if __name__ == '__main__':
    crear_gui()