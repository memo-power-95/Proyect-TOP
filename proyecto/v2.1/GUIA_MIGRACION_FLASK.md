# 🔄 Guía de Migración: Tkinter → Flask

## Resumen Ejecutivo

Se ha creado una **nueva versión del launcher** usando Flask que ofrece una interfaz web moderna, mantiendo toda la funcionalidad del launcher original en Tkinter.

---

## 📊 Comparativa Visual

### Antes (Tkinter - Launcher_TOP.py)
```
┌─────────────────────────────────────────┐
│  LG INNOTEK - TOP SYSTEM v2.1           │
│  Entorno de pruebas y operación         │
├─────────────────────────────────────────┤
│                                         │
│  ▶ 1. INICIAR MOTOR IOT [Iniciar]      │
│  📈 2. DASHBOARD VIVO   [Iniciar]      │
│  🗂️ 3. DASHBOARD LOGS   [Iniciar]      │
│  🛠️ 4. APP MANTENIMIENTO [Iniciar]     │
│  📊 5. DASHBOARD OEE     [Iniciar]      │
│  🤖 6. PREDICTIVO        [Iniciar]      │
│  🌐 6a. PREDICTIVE API   [Iniciar]      │
│                                         │
│  [Abrir carpeta] [Ver procesos]        │
│                                         │
│  [ ❌ CERRAR SISTEMA ]                  │
│                                         │
├─────────────────────────────────────────┤
│ Directorio: c:\...\v2.1                │
└─────────────────────────────────────────┘
```

**Limitaciones:**
- ❌ Solo accesible desde la PC local
- ❌ Interfaz básica con Tkinter
- ❌ No responsive
- ❌ Sin actualización automática de estado
- ❌ No muestra métricas de recursos

### Después (Flask - launcher_flask.py)
```
┌─────────────────────────────────────────────────────────────┐
│ 🖥️ TOP SYSTEM - LG INNOTEK                          [v2.1] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│        Panel de Control del Sistema                         │
│        Entorno de pruebas y operación                       │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  Módulos Activos: 3  │  Estado: OPERATIVO  │  CERRAR TODO  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [Todas] [Backend] [Operativo] [Técnico] [Gerencial]...    │
│                                                             │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ ▶ MOTOR IOT     │  │ 📈 DASHBOARD     │                │
│  │ [Backend]       │  │ [Operativo]      │                │
│  │ ● En Ejecución  │  │ ● En Ejecución   │                │
│  │ PID: 12345      │  │ PID: 12346       │                │
│  │ CPU: 2.5%       │  │ CPU: 1.8%        │                │
│  │ [⬛ Detener]    │  │ [⬛ Detener]     │                │
│  └──────────────────┘  └──────────────────┘                │
│                                                             │
│  Tabla de Procesos Activos:                                │
│  ┌─────────────┬──────┬─────────┬────────────┬─────┬──────┐│
│  │ Módulo      │ PID  │ Estado  │ Inicio     │ CPU │ RAM  ││
│  ├─────────────┼──────┼─────────┼────────────┼─────┼──────┤│
│  │ Motor IoT   │12345 │Running  │10:30:15 AM │2.5% │45 MB││
│  └─────────────┴──────┴─────────┴────────────┴─────┴──────┘│
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ Directorio: c:\Users\elpro\...\v2.1                        │
└─────────────────────────────────────────────────────────────┘
```

**Mejoras:**
- ✅ Accesible desde cualquier navegador en la red
- ✅ Interfaz moderna con Bootstrap 5
- ✅ 100% Responsive (móvil, tablet, PC)
- ✅ Actualización automática cada 3 segundos
- ✅ Muestra CPU y memoria de cada proceso
- ✅ Filtros por categoría
- ✅ Notificaciones elegantes
- ✅ Tabla de procesos detallada

---

## 🚀 Guía de Migración Paso a Paso

### Opción 1: Instalación Rápida (Recomendado)

1. **Ejecutar el script de instalación:**
   ```cmd
   cd C:\Users\elpro\Documents\Github\Proyecto-Starwing\proyecto\v2.1
   INICIAR_LAUNCHER_WEB.bat
   ```

2. **Abrir navegador:**
   - Ir a: http://localhost:5000

3. **¡Listo!** Ya puedes usar el nuevo launcher

### Opción 2: Instalación Manual

1. **Instalar dependencias:**
   ```cmd
   pip install flask psutil
   ```

2. **Ejecutar el servidor:**
   ```cmd
   python launcher_flask.py
   ```

3. **Acceder desde navegador:**
   - Local: http://localhost:5000
   - Red: http://[TU_IP]:5000

---

## 📋 Checklist de Funcionalidades

| Funcionalidad | Tkinter | Flask |
|--------------|---------|-------|
| Iniciar módulos | ✅ | ✅ |
| Detener módulos | ✅ | ✅ |
| Ver procesos activos | ✅ | ✅ |
| Detener todos | ✅ | ✅ |
| Monitoreo de estado | ⚠️ Manual | ✅ Auto 3s |
| Ver PID de procesos | ✅ | ✅ |
| Ver CPU/Memoria | ❌ | ✅ |
| Filtrar por categoría | ❌ | ✅ |
| Acceso remoto | ❌ | ✅ |
| Responsive design | ❌ | ✅ |
| Notificaciones | ⚠️ Básicas | ✅ Modernas |

---

## 🎯 Casos de Uso Mejorados

### 1. Monitoreo Remoto
**Antes:** Tenías que estar físicamente en la PC
**Ahora:** Puedes acceder desde cualquier dispositivo en la red
```
http://192.168.1.100:5000
```

### 2. Supervisión Multiusuario
**Antes:** Solo un usuario a la vez
**Ahora:** Múltiples usuarios pueden ver el estado simultáneamente

### 3. Monitoreo desde Móvil
**Antes:** No disponible
**Ahora:** Interfaz responsive funciona en smartphones

### 4. Métricas en Tiempo Real
**Antes:** No había información de recursos
**Ahora:** CPU y RAM de cada proceso visible

---

## 🔧 Diferencias Técnicas

### Arquitectura

**Tkinter (Desktop):**
```
Usuario → GUI Tkinter → subprocess → Procesos
```

**Flask (Web):**
```
Usuario → Navegador → Flask Server → subprocess → Procesos
                ↑                         ↓
                └─── Polling API (3s) ────┘
```

### Gestión de Procesos

**Ambas versiones:**
- Usan `subprocess.Popen()` para lanzar procesos
- `CREATE_NEW_CONSOLE` en Windows
- `.terminate()` y `.kill()` para detener
- Almacenan referencias de procesos activos

**Flask añade:**
- API REST para control remoto
- `psutil` para métricas de recursos
- Actualización automática de estado

### Archivos Involucrados

**Tkinter:**
```
Launcher_TOP.py (único archivo)
```

**Flask:**
```
launcher_flask.py          # Backend Flask
templates/
  └── launcher.html        # HTML principal
static/
  ├── css/
  │   └── style.css       # Estilos personalizados
  └── js/
      └── app.js          # Lógica del frontend
```

---

## 💡 Preguntas Frecuentes

### ¿Puedo seguir usando el launcher de Tkinter?
Sí, ambos pueden coexistir. El archivo `Launcher_TOP.py` sigue funcionando normalmente.

### ¿Necesito configurar algo en el firewall?
Si quieres acceder desde otros dispositivos en la red, puede que necesites permitir el puerto 5000.

### ¿El servidor Flask siempre debe estar corriendo?
Sí, el servidor Flask debe estar activo para usar la interfaz web. Es como el launcher de Tkinter, pero en este caso es un servidor web.

### ¿Puedo cambiar el puerto?
Sí, edita `launcher_flask.py` línea ~290:
```python
app.run(host='0.0.0.0', port=5000, debug=True)
```

### ¿Es seguro para producción?
La versión actual es para uso interno. Para producción se recomienda:
- Agregar autenticación
- Usar HTTPS
- Modo debug=False
- Usar un servidor WSGI (Gunicorn/uWSGI)

### ¿Funciona en Linux/Mac?
Sí, Flask es multiplataforma. Solo cambia el script de inicio:
```bash
#!/bin/bash
pip install flask psutil
python3 launcher_flask.py
```

---

## 📚 Recursos Adicionales

- **README Completo:** `README_LAUNCHER_WEB.md`
- **Script de Inicio:** `INICIAR_LAUNCHER_WEB.bat`
- **Código Fuente:** `launcher_flask.py`
- **Documentación Flask:** https://flask.palletsprojects.com/

---

## 🎉 Conclusión

La migración a Flask proporciona:
- ✨ Mejor experiencia de usuario
- 🌐 Acceso desde cualquier dispositivo
- 📊 Más información del sistema
- 🚀 Base para futuras mejoras

**Recomendación:** Probar el nuevo launcher Flask manteniendo el Tkinter como respaldo. Una vez validado, adoptar Flask como launcher principal.

---

**¿Preguntas o problemas?** 
Revisa `README_LAUNCHER_WEB.md` o consulta los logs de Flask en la consola.
