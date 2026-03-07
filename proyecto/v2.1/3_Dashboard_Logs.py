import pandas as pd
import matplotlib.pyplot as plt
import os
import time

ARCHIVO_LOGS = "logs_tiempo_real.csv"
LINEAS_ACTIVAS = [1, 2]
CYCLE_TIME_IDEAL_LINE = {1: 855.78, 2: 138.0}


def _tc_obj_maq(linea, maquina):
    base = {
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
    }
    return float(base.get(str(maquina), CYCLE_TIME_IDEAL_LINE.get(linea, 138.0)))

def generar_reporte_logs():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("="*80)
    print("   ANALIZADOR HISTÓRICO DE LOGS (FIN DE TURNO)")
    print("="*80)

    if not os.path.exists(ARCHIVO_LOGS):
        print(" [!] No hay logs para analizar.")
        return

    df = pd.read_csv(ARCHIVO_LOGS)
    
    # Limpiamos los datos de Mantenimiento para las métricas de calidad
    df_prod = df[df['Evento'] != 'MANTENIMIENTO']
    
    total_ciclos = len(df_prod)
    if total_ciclos == 0: return
    
    # KPIs Generales
    ok_count = len(df_prod[df_prod['Evento'] == 'OK'])
    scrap_count = len(df_prod[df_prod['Evento'].str.contains('SCRAP', na=False)])
    micro_count = len(df_prod[df_prod['Evento'].str.contains('MICRO', na=False)])
    
    rendimiento = (ok_count / total_ciclos) * 100

    print(f"\n [KPIs GLOBALES DE LA PLANTA]")
    print(f" > Total Ciclos Analizados: {total_ciclos}")
    print(f" > Producción OK:           {ok_count} piezas ({rendimiento:.1f}%)")
    print(f" > Total Scrap:             {scrap_count} piezas")
    print(f" > Eventos Micro-Paros:     {micro_count} incidencias")

    if 'Linea' in df_prod.columns:
        print("\n [RENDIMIENTO POR LINEA]")
        for lid in LINEAS_ACTIVAS:
            dline = df_prod[df_prod['Linea'] == lid]
            if dline.empty:
                print(f" > Linea {lid}: sin datos")
                continue
            tc_obj = CYCLE_TIME_IDEAL_LINE.get(lid, 138.0)
            tc_real = float(dline['Tiempo_Ciclo'].mean() or 0)
            tc_adj = max(tc_real, tc_obj)
            rend = (tc_obj / tc_adj) * 100.0 if tc_adj > 0 else 0.0
            print(f" > Linea {lid}: Rendimiento {rend:.1f}% | TC real {tc_real:.2f}s | Obj {tc_obj:.2f}s")

            if 'Maquina' in dline.columns:
                print(f"   - Por maquina (L{lid}):")
                for maq, dmaq in dline.groupby('Maquina'):
                    tc_obj_m = _tc_obj_maq(lid, maq)
                    tc_real_m = float(dmaq['Tiempo_Ciclo'].mean() or 0)
                    tc_adj_m = max(tc_real_m, tc_obj_m)
                    rend_m = (tc_obj_m / tc_adj_m) * 100.0 if tc_adj_m > 0 else 0.0
                    print(f"     * {maq}: {rend_m:.1f}% (TC {tc_real_m:.2f}s / Obj {tc_obj_m:.2f}s)")
    
    # --- GRÁFICAS DE ANÁLISIS ---
    plt.style.use('ggplot')
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle('REPORTE GERENCIAL DE LOGS - TOP', fontsize=16)

    # 1. Gráfica de Pareto (Tipos de Errores)
    # Filtramos solo los errores
    errores = df_prod[df_prod['Evento'] != 'OK']['Evento'].value_counts()
    
    if not errores.empty:
        errores.plot(kind='bar', color='#e74c3c', ax=ax1)
        ax1.set_title('Pareto de Fallas (Causa Raíz)')
        ax1.set_ylabel('Frecuencia')
        ax1.tick_params(axis='x', rotation=45)
    else:
        ax1.text(0.5, 0.5, 'CERO FALLAS DETECTADAS', ha='center', fontsize=12)

    # 2. Gráfica de Calidad (Pie Chart)
    labels = ['OK', 'SCRAP', 'MICRO-PAROS']
    sizes = [ok_count, scrap_count, micro_count]
    colores = ['#2ecc71', '#e74c3c', '#f1c40f']
    
    # Filtramos los que sean 0 para no romper la gráfica
    labels_filtrados = [l for l, s in zip(labels, sizes) if s > 0]
    sizes_filtrados = [s for s in sizes if s > 0]
    colores_filtrados = [c for c, s in zip(colores, sizes) if s > 0]

    ax2.pie(sizes_filtrados, labels=labels_filtrados, colors=colores_filtrados, autopct='%1.1f%%', startangle=90)
    ax2.set_title('Distribución de Calidad')

    plt.tight_layout()
    plt.savefig('Reporte_Logs.png')
    print("\n [VISUALIZACIÓN] Gráficas generadas. Cierra la ventana para continuar.")
    plt.show()

if __name__ == "__main__":
    # Si quieres que se actualice cada cierto tiempo, lo metemos en un loop
    while True:
        generar_reporte_logs()
        opcion = input("\n ¿Actualizar reporte? (s/n): ")
        if opcion.lower() != 's': break