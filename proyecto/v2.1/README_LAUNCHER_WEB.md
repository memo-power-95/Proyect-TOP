# 🚀 TOP SYSTEM - Launcher Web v2.1

**Interfaz web moderna con Flask para el sistema TOP de LG INNOTEK**

## 📋 Descripción

Launcher web que permite gestionar todos los módulos del sistema TOP desde una interfaz web moderna, intuitiva y responsive. Reemplaza el launcher de escritorio (Tkinter) con una solución basada en navegador con actualizaciones en tiempo real.

## ✨ Características

- 🎨 **Interfaz Moderna**: Diseño responsive con Bootstrap 5
- 🔄 **Actualización en Tiempo Real**: Monitoreo automático del estado de los módulos cada 3 segundos
- 📊 **Dashboard Completo**: Vista general del estado del sistema con métricas en vivo
- 🎯 **Gestión de Procesos**: Iniciar, detener y monitorear módulos individualmente
- 📈 **Monitoreo de Recursos**: CPU y memoria de cada proceso
- 🔍 **Filtros por Categoría**: Backend, Operativo, Técnico, Gerencial, Analítico, API
- 🌐 **Acceso en Red**: Disponible desde cualquier dispositivo en la red local
- 🔔 **Notificaciones**: Sistema de alertas para acciones y eventos

## 📦 Módulos Gestionados

1. **Motor IoT (Backend)** - `1_Generador_Maquinas.py`
2. **Dashboard Vivo** - `2_Dashboard_Vivo.py`
3. **Dashboard Logs** - `3_Dashboard_Logs.py`
4. **App Mantenimiento** - `4_App_Mantenimiento.py`
5. **Dashboard OEE** - `5_Dashboard_OEE.py`
6. **Mantenimiento Predictivo** - `6_Predictive_Maintenance.py`
7. **Predictive API** - `predictive_api.py`

## 🛠️ Instalación

### Requisitos Previos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)

### Pasos de Instalación

1. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

   Las nuevas dependencias necesarias son:
   - `flask` - Framework web
   - `psutil` - Monitoreo de procesos del sistema

2. **Verificar estructura de archivos:**
   ```
   v2.1/
   ├── launcher_flask.py
   ├── templates/
   │   └── launcher.html
   ├── static/
   │   ├── css/
   │   │   └── style.css
   │   └── js/
   │       └── app.js
   └── [otros módulos del sistema...]
   ```

## 🚀 Uso

### Iniciar el Launcher Web

```bash
cd proyecto/v2.1
python launcher_flask.py
```

### Acceder a la Interfaz

Una vez iniciado, el servidor estará disponible en:

- **Local**: http://localhost:5000
- **Red Local**: http://[TU_IP]:5000

Por ejemplo: `http://192.168.1.100:5000`

### Operaciones Disponibles

#### 1. **Iniciar un Módulo**
   - Clic en el botón verde "▶ Iniciar" del módulo deseado
   - El módulo se abrirá en una nueva consola
   - El estado cambiará a "En Ejecución"

#### 2. **Detener un Módulo**
   - Clic en el botón rojo "⬛ Detener" del módulo activo
   - Confirmar la acción en el diálogo
   - El proceso se detendrá de forma controlada

#### 3. **Monitorear Estado**
   - La interfaz se actualiza automáticamente cada 3 segundos
   - Vista de métricas: CPU, Memoria, PID de cada proceso
   - Tabla de procesos activos en la parte inferior

#### 4. **Filtrar por Categoría**
   - Usar los botones de categoría en la parte superior
   - Opciones: Backend, Operativo, Técnico, Gerencial, Analítico, API

#### 5. **Detener Todo**
   - Botón rojo "CERRAR TODO" en el panel superior
   - Detiene todos los módulos activos simultáneamente

## 🔧 API REST Endpoints

El launcher expone varios endpoints API:

- `GET /` - Página principal
- `GET /api/modulos` - Lista de módulos con estado
- `POST /api/lanzar/<id>` - Iniciar módulo
- `POST /api/detener/<id>` - Detener módulo
- `POST /api/detener_todos` - Detener todos los módulos
- `GET /api/estado` - Estado general del sistema

## 📱 Acceso desde Dispositivos Móviles

La interfaz es completamente responsive y funciona en:
- 📱 Smartphones
- 📱 Tablets
- 💻 Laptops/PCs

## ⚙️ Configuración

### Cambiar Puerto

Editar en `launcher_flask.py`:
```python
app.run(
    host='0.0.0.0',
    port=5000,  # Cambiar aquí
    debug=True
)
```

### Intervalo de Actualización

Editar en `static/js/app.js`:
```javascript
const INTERVALO_REFRESH = 3000; // milisegundos (3s)
```

## 🆚 Comparación con Launcher Tkinter

| Característica | Tkinter (Antiguo) | Flask (Nuevo) |
|---------------|-------------------|---------------|
| Tipo | Aplicación de escritorio | Aplicación web |
| Acceso | Solo local | Local + Red |
| UI/UX | Básica | Moderna y responsive |
| Actualizaciones | Manual/polling | Automáticas en tiempo real |
| Multiplataforma | Requiere GUI | Solo navegador |
| Personalización | Limitada | CSS/JS flexible |

## 🔒 Seguridad

**⚠️ IMPORTANTE**: Este launcher está diseñado para uso en redes locales de confianza.

Para uso en producción se recomienda:
- Implementar autenticación (Flask-Login, JWT)
- Usar HTTPS con certificado SSL
- Configurar firewall y restricciones de red
- Validación de permisos por usuario

## 🐛 Solución de Problemas

### El servidor no inicia
```bash
# Verificar que el puerto 5000 esté disponible
netstat -ano | findstr :5000

# Si está ocupado, cambiar el puerto en launcher_flask.py
```

### Los módulos no se inician
- Verificar que los scripts existan en la carpeta v2.1
- Comprobar permisos de ejecución
- Revisar la consola de depuración de Flask

### Error de importación
```bash
# Reinstalar dependencias
pip install --upgrade -r requirements.txt
```

## 📞 Soporte

Para problemas o sugerencias:
1. Revisar los logs de Flask en la consola
2. Verificar errores en la consola del navegador (F12)
3. Consultar documentación de Flask: https://flask.palletsprojects.com/

## 🎯 Próximas Mejoras

- [ ] Autenticación de usuarios
- [ ] Logs en tiempo real de cada módulo
- [ ] Gráficos de uso de recursos
- [ ] Programación de tareas (cron)
- [ ] Notificaciones push
- [ ] Temas personalizables (modo oscuro)
- [ ] Export de reportes del sistema

## 📄 Licencia

Uso interno - LG INNOTEK TOP SYSTEM

---

**Desarrollado para el Sistema TOP v2.1 - LG INNOTEK**
