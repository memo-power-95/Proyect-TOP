import csv
import os
import datetime
import time
import logging
import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog

ARCHIVO = Path("bitacora_mantenimiento.csv")
CONFIG = Path("app_config.json")
CATALOGO = {
    1: ["Limpieza Sensor", 5, 100.0],
    2: ["Calibración Torque", 10, 100.0],
    3: ["Cambio Servomotor", 20, 100.0],
    4: ["Soft Reset", 3, 75.0]
}

MAQUINAS_POR_LINEA = {
    1: ["Top cover feeding", "Pre-weighing", "Tim dispensing", "Avl Tim", "Weighing", "Install PCB", "Fastening 1", "Fastening 2", "Avl screw", "Top unloader"],
    2: ["Top cover feeding", "Pre-weighing", "Tim dispensing", "Avl Tim", "Weighing", "Install PCB", "Fastening 1", "Fastening 2", "Avl screw", "Top unloader"],
}

# configurar logging básico
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')


def asegurar_archivo():
    try:
        if not ARCHIVO.exists():
            ARCHIVO.parent.mkdir(parents=True, exist_ok=True)
            with ARCHIVO.open('w', newline='') as f:
                csv.writer(f).writerow(["Timestamp", "Linea", "Maquina", "Accion", "Duracion", "Salud_Final"])
            logging.info('Archivo de bitácora creado: %s', ARCHIVO)
    except Exception as e:
        logging.exception('Error asegurando archivo: %s', e)


def load_config():
    try:
        if CONFIG.exists():
            with CONFIG.open('r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        logging.exception('No se pudo leer configuración, se usará por defecto')
    return {"linea": 1}


def save_config(cfg: dict):
    try:
        with CONFIG.open('w', encoding='utf-8') as f:
            json.dump(cfg, f)
        logging.info('Configuración guardada')
    except Exception:
        logging.exception('Error guardando configuración')


def registrar_mantenimiento(linea, maquina, accion_id):
    try:
        ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        accion = CATALOGO[accion_id][0]
        dur = CATALOGO[accion_id][1]
        salud = CATALOGO[accion_id][2]
        with ARCHIVO.open('a', newline='') as f:
            csv.writer(f).writerow([ahora, linea, maquina, accion, dur, salud])
        logging.info('Registro guardado: linea=%s maquina=%s accion_id=%s', linea, maquina, accion_id)
    except Exception as e:
        logging.exception('Error registrando mantenimiento: %s', e)


def leer_ultimos(n=20):
    try:
        if not ARCHIVO.exists():
            return []
        with ARCHIVO.open('r', newline='') as f:
            reader = list(csv.reader(f))
            if len(reader) <= 1:
                return []
            return reader[1:][-n:]
    except Exception as e:
        logging.exception('Error leyendo registros: %s', e)
        return []


def crear_gui():
    asegurar_archivo()
    root = tk.Tk()
    root.title("App Mantenimiento - TOP")
    root.geometry('720x420')

    # configuración
    cfg = load_config()

    # Menú de configuración
    menubar = tk.Menu(root)
    cfg_menu = tk.Menu(menubar, tearoff=0)
    def set_default_line():
        try:
            val = simpledialog.askinteger('Línea por defecto', 'Ingrese número de línea:', initialvalue=cfg.get('linea', 1), minvalue=1)
            if val is None:
                return
            cfg['linea'] = int(val)
            save_config(cfg)
            linea_cb.set(cfg['linea'])
            messagebox.showinfo('Configuración', f'Línea por defecto establecida a {cfg["linea"]}')
        except Exception:
            logging.exception('Error estableciendo línea por defecto')
            messagebox.showerror('Error', 'No se pudo establecer la línea')
    cfg_menu.add_command(label='Establecer línea por defecto...', command=set_default_line)
    menubar.add_cascade(label='Config', menu=cfg_menu)
    root.config(menu=menubar)

    frm = ttk.Frame(root, padding=10)
    frm.pack(fill='both', expand=True)

    # Controles de registro
    ctrl = ttk.LabelFrame(frm, text='Registrar mantenimiento', padding=10)
    ctrl.pack(fill='x')

    ttk.Label(ctrl, text='Línea:').grid(column=0, row=0, sticky='w')
    linea_cb = ttk.Combobox(ctrl, values=[1, 2], width=5, state='readonly')
    linea_cb.set(cfg.get('linea', 1))
    linea_cb.grid(column=1, row=0, padx=6, pady=4)

    ttk.Label(ctrl, text='Acción:').grid(column=2, row=0, sticky='w')
    acciones = [f"{k} - {v[0]} ({v[1]}s, {v[2]}%)" for k, v in CATALOGO.items()]
    display_to_id = {f"{k} - {v[0]} ({v[1]}s, {v[2]}%)": k for k, v in CATALOGO.items()}
    accion_cb = ttk.Combobox(ctrl, values=acciones, width=40, state='readonly')
    accion_cb.current(0)
    accion_cb.grid(column=3, row=0, padx=6, pady=4)

    use_default_var = tk.BooleanVar(value=True)
    def toggle_default():
        if use_default_var.get():
            linea_cb.set(cfg.get('linea', 1))
            linea_cb.configure(state='disabled')
        else:
            linea_cb.configure(state='readonly')

    chk = ttk.Checkbutton(ctrl, text='Usar línea por defecto', variable=use_default_var, command=toggle_default)
    chk.grid(column=0, row=1, columnspan=2, sticky='w', pady=(6,0))
    toggle_default()

    def on_registrar():
        try:
            linea = int(linea_cb.get())
        except:
            messagebox.showerror('Error', 'Línea inválida')
            return
        maquina = maquina_cb.get()
        if not maquina:
            messagebox.showerror('Error', 'Seleccione una máquina')
            return
        sel = accion_cb.get()
        if not sel:
            messagebox.showerror('Error', 'Seleccione una acción')
            return
        accion_id = display_to_id.get(sel)
        if accion_id is None:
            messagebox.showerror('Error', 'Acción inválida')
            logging.warning('Selección de acción inválida: %s', sel)
            return
        registrar_mantenimiento(linea, maquina, accion_id)
        msg = f'Registro guardado para {maquina} en Línea {linea}'
        messagebox.showinfo('Registrado', msg)
        cargar_tabla()

    btn_reg = ttk.Button(ctrl, text='Registrar', command=on_registrar)
    btn_reg.grid(column=4, row=0, padx=6)

    # Selector de máquina
    ttk.Label(ctrl, text='Máquina:').grid(column=0, row=2, sticky='w')
    maquina_cb = ttk.Combobox(ctrl, values=["Toda la línea"], width=30, state='readonly')
    maquina_cb.set("Toda la línea")
    maquina_cb.grid(column=1, row=2, columnspan=2, padx=6, pady=4)
    
    def actualizar_maquinas():
        try:
            linea = int(linea_cb.get())
            maquinas = ["Toda la línea"] + MAQUINAS_POR_LINEA.get(linea, [])
            maquina_cb.configure(values=maquinas)
            maquina_cb.set("Toda la línea")
        except:
            pass
    
    linea_cb_original_command = linea_cb.bind('<<ComboboxSelected>>', lambda e: actualizar_maquinas())
    actualizar_maquinas()

    # Tabla de últimos registros
    tbl_frm = ttk.LabelFrame(frm, text='Últimos registros', padding=6)
    tbl_frm.pack(fill='both', expand=True, pady=10)

    cols = ("Timestamp", "Linea", "Maquina", "Accion", "Duracion", "Salud_Final")
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

    def eliminar_seleccionado():
        sel = tree.selection()
        if not sel:
            messagebox.showerror('Error', 'No hay registro seleccionado')
            return
        vals = tree.item(sel[0], 'values')
        if not messagebox.askyesno('Confirmar', f'Eliminar registro: {vals}?'):
            return
        try:
            # leer todos, eliminar la primera coincidencia exacta
            with ARCHIVO.open('r', newline='') as f:
                rows = list(csv.reader(f))
            header = rows[:1]
            body = rows[1:]
            target = list(vals)
            removed = False
            for i, r in enumerate(body):
                if r == target:
                    del body[i]
                    removed = True
                    break
            if removed:
                with ARCHIVO.open('w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerows(header + body)
                logging.info('Registro eliminado: %s', target)
                cargar_tabla()
            else:
                messagebox.showwarning('Aviso', 'No se encontró el registro en archivo')
        except Exception:
            logging.exception('Error eliminando registro')
            messagebox.showerror('Error', 'No se pudo eliminar el registro')

    def exportar_para_linea():
        try:
            linea_f = int(linea_cb.get())
        except:
            messagebox.showerror('Error', 'Línea inválida para exportar')
            return
        path = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV','*.csv')], title='Exportar registros')
        if not path:
            return
        try:
            with ARCHIVO.open('r', newline='') as f:
                rows = list(csv.reader(f))
            header = rows[:1]
            body = [r for r in rows[1:] if str(r[1]) == str(linea_f)]
            with open(path, 'w', newline='') as out:
                writer = csv.writer(out)
                writer.writerows(header + body)
            messagebox.showinfo('Exportado', f'{len(body)} registros exportados a {path}')
            logging.info('Exportados %s registros para linea %s a %s', len(body), linea_f, path)
        except Exception:
            logging.exception('Error exportando')
            messagebox.showerror('Error', 'No se pudo exportar')

    cargar_tabla()

    # Footer
    footer = ttk.Frame(frm)
    footer.pack(fill='x', pady=6)
    btn_del = ttk.Button(footer, text='Eliminar seleccionado', command=eliminar_seleccionado)
    btn_del.pack(side='right', padx=6)
    btn_exp = ttk.Button(footer, text='Exportar (línea)', command=exportar_para_linea)
    btn_exp.pack(side='right')

    ttk.Label(footer, text='Archivo de bitácora:').pack(side='left')
    ttk.Label(footer, text=ARCHIVO, foreground='blue').pack(side='left', padx=6)

    root.mainloop()


if __name__ == '__main__':
    crear_gui()