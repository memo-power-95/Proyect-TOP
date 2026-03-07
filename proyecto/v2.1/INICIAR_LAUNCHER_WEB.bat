@echo off
REM Script de inicio rápido para TOP SYSTEM Launcher Web
REM LG INNOTEK - v2.1

echo.
echo ============================================================
echo   TOP SYSTEM - LG INNOTEK
echo   Launcher Web v2.1 - Script de Inicio
echo ============================================================
echo.

REM Cambiar al directorio del script
cd /d "%~dp0"

echo [1/3] Verificando instalacion de Python...
python --version
if errorlevel 1 (
    echo.
    echo ERROR: Python no esta instalado o no esta en el PATH
    echo Por favor, instala Python 3.8 o superior desde python.org
    pause
    exit /b 1
)


echo.
echo [2/3] Instalando/Actualizando dependencias...
echo.
pip install flask psutil
if errorlevel 1 (
    echo.
    echo ERROR: No se pudieron instalar las dependencias
    pause
    exit /b 1
)

REM Obtener la IP local automaticamente
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| find "IPv4"') do (
    set IP=%%a
    goto :found_ip
)
:found_ip
REM Limpiar espacios en blanco
for /f "tokens=1" %%a in ("%IP%") do set IP=%%a

echo.
echo [3/3] Iniciando servidor Flask...
echo.
echo ------------------------------------------------------------
echo.
echo   Accede a la interfaz web desde:
echo.
echo   - Local:       http://localhost:5000
echo   - Red Local:   http://%IP%:5000
echo.
echo   Presiona Ctrl+C para detener el servidor
echo.
echo ------------------------------------------------------------
echo.

python launcher_flask.py

pause
