@echo off
chcp 65001 >nul
title YT-Transcribe
echo.
echo  ======================================
echo           YT-Transcribe v1.0
echo     YouTube - Transcripcion Markdown
echo  ======================================
echo.

:ask
set "SOURCES="
echo   Pega una o varias URLs / rutas de archivo
echo   (separa con espacios si son varias)
echo.
set /p SOURCES="  > "

if "%SOURCES%"=="" (
    echo.
    echo   No has pegado nada
    echo.
    goto ask
)

echo.
echo  Procesando...
echo.

cd /d "%~dp0"
python yt_transcribe.py %SOURCES%

echo.
echo  ----------------------------------------
echo.
set /p OTRO="  Transcribir mas? (s/n): "
if /i "%OTRO%"=="s" (
    echo.
    goto ask
)

echo.
echo  Hasta luego!
pause
