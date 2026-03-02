import pandas as pd
import matplotlib.pyplot as plt
import os
import time

ARCHIVO_LOGS = "logs_tiempo_real.csv"

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