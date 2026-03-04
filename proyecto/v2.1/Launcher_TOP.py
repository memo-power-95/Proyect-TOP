import tkinter as tk
from tkinter import messagebox, ttk
import subprocess
import os
import sys

# Configuración Visual
COLOR_FONDO = "#2c3e50"
COLOR_ACCENT = "#e67e22"
COLOR_PANEL = "#34495e"

# Tipografías
FONT_TITLE = ("Segoe UI", 16, "bold")
FONT_SUBTITLE = ("Segoe UI", 9)
FONT_BUTTON = ("Segoe UI", 10)
FONT_FOOTER = ("Consolas", 8)

# temas disponibles (ttk)
AVAILABLE_THEMES = ['clam', 'alt', 'default', 'vista']


class LauncherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("LG INNOTEK - TOP SYSTEM v2.1")
        self.root.geometry("620x620")
        self.root.configure(bg=COLOR_FONDO)
        self.procesos = []
        # Diccionario para mapear scripts -> botones y control de polling
        self.botones = {}
        self.poll_interval_ms = 1000
        self.status_var = tk.StringVar(value="")

        # Ruta base (carpeta v2.1)
        self.directorio_base = os.path.dirname(os.path.abspath(__file__))

        # Estilo ttk
        style = ttk.Style(self.root)
        try:
            style.theme_use('clam')
        except:
            pass
        style.configure('TButton', font=FONT_BUTTON, padding=8)
        style.configure('Accent.TButton', background=COLOR_ACCENT, foreground='white')

        # menú de configuración (temas, etc.)
        self.setup_menu()

        # --- Header ---
        header = tk.Frame(self.root, bg=COLOR_PANEL, pady=12)
        header.grid(row=0, column=0, sticky='ew')
        tk.Label(header, text="TOP SYSTEM - LG INNOTEK", font=FONT_TITLE, bg=COLOR_PANEL, fg='white').pack()
        tk.Label(header, text="Entorno de pruebas y operación (v2.1)", font=FONT_SUBTITLE, bg=COLOR_PANEL, fg='#bdc3c7').pack()

        # Contenedor principal
        main = tk.Frame(self.root, bg=COLOR_FONDO, padx=16, pady=12)
        main.grid(row=1, column=0, sticky='nsew')
        self.root.rowconfigure(1, weight=1)
        self.root.columnconfigure(0, weight=1)

        # Botones agrupados en frame
        buttons = tk.Frame(main, bg=COLOR_FONDO)
        buttons.grid(row=0, column=0, sticky='nsew')
        main.rowconfigure(0, weight=1)
        main.columnconfigure(0, weight=1)

        # Botones principales (usar sys.executable para lanzar)
        self.crear_boton(buttons, "▶ 1. INICIAR MOTOR IOT (Backend)", "1_Generador_Maquinas.py", 'green', row=0)
        self.crear_boton(buttons, "📈 2. DASHBOARD VIVO (Operativo)", "2_Dashboard_Vivo.py", COLOR_PANEL, row=1)
        self.crear_boton(buttons, "🗂️ 3. DASHBOARD LOGS (Histórico)", "3_Dashboard_Logs.py", COLOR_PANEL, row=2)
        self.crear_boton(buttons, "🛠️ 4. APP MANTENIMIENTO (Técnico)", "4_App_Mantenimiento.py", COLOR_ACCENT, accent=True, row=3)
        self.crear_boton(buttons, "📊 5. DASHBOARD OEE (Gerencial)", "5_Dashboard_OEE.py", '#8e44ad', row=4)
        self.crear_boton(buttons, "🤖 6. PREDICTIVO (Mantenimiento)", "6_Predictive_Maintenance.py", '#16a085', row=5)
        self.crear_boton(buttons, "🌐 6a. PREDICTIVE API (REST)", "predictive_api.py", '#1abc9c', row=6)

        # Acciones secundarias
        sec = tk.Frame(main, bg=COLOR_FONDO)
        sec.grid(row=1, column=0, sticky='w', pady=12)
        ttk.Button(sec, text='Abrir carpeta', command=self.abrir_carpeta).pack(side='left')
        ttk.Button(sec, text='Ver procesos activos', command=self.mostrar_procesos).pack(side='left', padx=8)

        # Kill switch (mejor manejo de procesos)
        tk.Button(main, text="❌  CERRAR SISTEMA (cerrar procesos lanzados)", command=self.cerrar_todo,
                  font=(FONT_BUTTON[0], 10, 'bold'), bg='#c0392b', fg='white', width=36, height=2).grid(row=2, column=0, pady=6)

        # Footer
        footer = tk.Frame(self.root, bg=COLOR_FONDO)
        footer.grid(row=2, column=0, sticky='ew')
        tk.Label(footer, text=f"Directorio: {self.directorio_base}", bg=COLOR_FONDO, fg='#95a5a6', font=FONT_FOOTER).pack(side='left', padx=8, pady=6)
        tk.Label(footer, textvariable=self.status_var, bg=COLOR_FONDO, fg='#95a5a6', font=FONT_FOOTER).pack(side='right', padx=8, pady=6)

    def crear_boton(self, parent, texto, script, color=None, accent=False, row=None):
        # el parámetro `color` se utiliza para generar un estilo específico si se proporciona
        if accent:
            style_name = 'Accent.TButton'
        else:
            style_name = 'TButton'
            if color:
                # crear estilo temporal basado en el texto para que no colisionen
                style_name = f"{texto}.TButton"
                style = ttk.Style(self.root)
                style.configure(style_name, font=FONT_BUTTON, padding=8, background=color, foreground='white')
        b = ttk.Button(parent, text=texto, style=style_name, command=lambda: self.lanzar_script(script))
        # almacenar referencia para habilitar/deshabilitar según el proceso
        self.botones[script] = b
        if row is not None:
            b.grid(row=row, column=0, sticky='ew', pady=6)
        else:
            b.pack(fill='x', pady=6)

    def lanzar_script(self, nombre_script):
        ruta_completa = os.path.join(self.directorio_base, nombre_script)
        if not os.path.exists(ruta_completa):
            messagebox.showerror("Error de Ruta", f"No encuentro el archivo:\n{ruta_completa}\n\nVerifica que esté en la carpeta v2.1")
            return
        # Se eliminó el diálogo de confirmación: al pulsar el botón se abrirá el módulo directamente

        try:
            print(f"[LAUNCHER] Abriendo: {ruta_completa}")
            # Lanzar con el mismo intérprete usado por el launcher
            if os.name == 'nt':
                # En Windows abrimos en nueva consola
                creationflags = getattr(subprocess, 'CREATE_NEW_CONSOLE', 0)
                p = subprocess.Popen([sys.executable, ruta_completa], creationflags=creationflags)
            else:
                # En Linux/Mac intentamos abrir en emulador de terminal
                try:
                    p = subprocess.Popen(['x-terminal-emulator', '-e', sys.executable, ruta_completa])
                except Exception:
                    p = subprocess.Popen([sys.executable, ruta_completa])
            self.procesos.append(p)
            # deshabilitar botón correspondiente mientras el proceso esté activo
            btn = self.botones.get(nombre_script)
            if btn:
                try:
                    btn.configure(state='disabled')
                except Exception:
                    pass
            # actualizar estado en footer
            self.status_var.set(f'Lanzado: {nombre_script} pid={getattr(p, "pid", "N/A")}')
            # iniciar monitor para re-habilitar cuando termine
            self.root.after(self.poll_interval_ms, lambda proc=p, scr=nombre_script: self._monitor_process(proc, scr))
        except Exception as e:
            messagebox.showerror("Error", f"Fallo al abrir Python: {e}")

    def mostrar_procesos(self):
        texto = "Procesos lanzados:\n"
        for i, p in enumerate(self.procesos):
            try:
                alive = p.poll() is None
            except Exception:
                alive = False
            texto += f"[{i}] pid={getattr(p, 'pid', 'N/A')} alive={alive}\n"
        messagebox.showinfo('Procesos', texto)

    def abrir_carpeta(self):
        try:
            if os.name == 'nt':
                os.startfile(self.directorio_base)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', self.directorio_base])
            else:
                subprocess.Popen(['xdg-open', self.directorio_base])
        except Exception as e:
            messagebox.showerror('Error', f'No se pudo abrir la carpeta: {e}')

    def setup_menu(self):
        """Construye barra de menús con opciones de tema/configuración."""
        menubar = tk.Menu(self.root)
        config_menu = tk.Menu(menubar, tearoff=0)
        tema_menu = tk.Menu(config_menu, tearoff=0)
        for t in AVAILABLE_THEMES:
            tema_menu.add_radiobutton(label=t, command=lambda th=t: self.cambiar_tema(th))
        config_menu.add_cascade(label='Tema', menu=tema_menu)
        menubar.add_cascade(label='Configuración', menu=config_menu)
        self.root.config(menu=menubar)

    def cambiar_tema(self, tema):
        """Aplica un tema ttk distinto en tiempo de ejecución."""
        style = ttk.Style(self.root)
        try:
            style.theme_use(tema)
        except Exception as e:
            messagebox.showerror('Tema', f'No se pudo aplicar el tema {tema}: {e}')

    def _monitor_process(self, proc, script):
        """Verifica periódicamente si `proc` terminó; si es así, re-habilita el botón."""
        try:
            running = proc.poll() is None
        except Exception:
            running = False
        if running:
            self.root.after(self.poll_interval_ms, lambda: self._monitor_process(proc, script))
            return

        # proceso terminado: re-habilitar botón y actualizar estado
        btn = self.botones.get(script)
        if btn:
            try:
                btn.configure(state='normal')
            except Exception:
                pass
        self.status_var.set(f'Proceso terminado: {script} pid={getattr(proc, "pid", "N/A")}')

    def cerrar_todo(self):
        if not messagebox.askyesno("Confirmar", "¿Cerrar los módulos lanzados por el launcher?"):
            return

        # Intentar cerrar procesos lanzados
        for p in list(self.procesos):
            try:
                if p.poll() is None:
                    p.terminate()
                    p.wait(timeout=2)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass

        # Si todavía hay procesos python sueltos, preguntar si aplicar fallback (taskkill/pkill)
        restantes = [p for p in self.procesos if getattr(p, 'poll', lambda: 1)() is None]
        if restantes:
            if messagebox.askyesno('Forzar cierre', 'Algunos procesos no respondieron. Forzar cierre global de Python?'):
                if os.name == 'nt':
                    os.system('taskkill /f /im python.exe')
                else:
                    os.system('pkill -f python')

        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = LauncherApp(root)
    root.mainloop()