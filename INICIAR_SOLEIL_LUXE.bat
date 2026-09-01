@echo off
title SOLEIL LUXE - Sistema de gestion
cd /d "%~dp0"
echo.
echo ==========================================
echo       SOLEIL LUXE - SISTEMA DE GESTION
echo ==========================================
echo.
echo [1/3] Verificando Python...
python --version
if errorlevel 1 (
    echo.
    echo No se encontro Python.
    echo Instala Python y vuelve a abrir este archivo.
    pause
    exit /b
)
echo.
echo [2/3] Instalando/verificando Flask...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo No se pudo instalar Flask.
    pause
    exit /b
)
echo.
echo [3/3] Iniciando Soleil Luxe...
echo.
echo Cuando aparezca "Running on http://127.0.0.1:5000", abre esa direccion en Chrome.
echo.
python app.py
pause
