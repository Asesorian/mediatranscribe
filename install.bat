@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ============================================================
echo   YT-Transcribe - Instalador One Shot
echo ============================================================
echo.

:: ─────────────────────────────────────────
:: PASO 1: yt-dlp desde winget (no pip)
:: ─────────────────────────────────────────
echo [1/5] Verificando yt-dlp...
where yt-dlp >nul 2>&1
if %errorlevel% neq 0 (
    echo   yt-dlp no encontrado. Instalando con winget...
    winget install yt-dlp --silent --accept-source-agreements --accept-package-agreements
    if %errorlevel% neq 0 (
        echo.
        echo   ERROR: winget no pudo instalar yt-dlp.
        echo   Instala manualmente desde: https://github.com/yt-dlp/yt-dlp/releases
        echo   Descarga yt-dlp.exe y copialo a C:\Windows\System32\
        echo.
        pause
        exit /b 1
    )
    echo   OK - yt-dlp instalado
) else (
    echo   OK - yt-dlp encontrado
    echo   Actualizando a la ultima version...
    winget upgrade yt-dlp --silent --accept-source-agreements --accept-package-agreements >nul 2>&1
    echo   OK
)

:: ─────────────────────────────────────────
:: PASO 2: dependencias Python
:: ─────────────────────────────────────────
echo.
echo [2/5] Instalando dependencias Python...
pip install groq -q
echo   OK - groq instalado

:: ─────────────────────────────────────────
:: PASO 3: ffmpeg
:: ─────────────────────────────────────────
echo.
echo [3/5] Verificando ffmpeg...
where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    echo   ffmpeg no encontrado. Instalando con winget...
    winget install ffmpeg --silent --accept-source-agreements --accept-package-agreements
    if %errorlevel% neq 0 (
        echo   AVISO: ffmpeg no se pudo instalar automaticamente.
        echo   Sin ffmpeg los videos de mas de 25 minutos no funcionaran.
        echo   Instala manualmente: winget install ffmpeg
    ) else (
        echo   OK - ffmpeg instalado
    )
) else (
    echo   OK - ffmpeg encontrado
)

:: ─────────────────────────────────────────
:: PASO 4: API key de Groq
:: ─────────────────────────────────────────
echo.
echo [4/5] Configurando API key de Groq...
if exist .env (
    echo   OK - .env ya existe
) else (
    echo   Necesitas una API key gratuita de Groq para transcribir audio.
    echo   Obtenla en: https://console.groq.com (gratis, ~300 min/dia)
    echo.
    set /p GROQ_KEY="  Introduce tu GROQ_API_KEY (Enter para saltar y configurar despues): "
    if defined GROQ_KEY (
        echo GROQ_API_KEY=!GROQ_KEY!> .env
        echo   OK - API key guardada en .env
    ) else (
        echo GROQ_API_KEY=tu_clave_aqui> .env
        echo   PENDIENTE - Edita .env con tu clave antes de usar el script
    )
)

:: ─────────────────────────────────────────
:: PASO 5: cookies.txt de YouTube
:: ─────────────────────────────────────────
echo.
echo [5/5] Configurando autenticacion con YouTube...
echo.

if exist cookies.txt (
    echo   OK - cookies.txt ya existe. Autenticacion lista.
    goto :cookies_ok
)

echo   YouTube requiere login desde 2026 para todos los videos.
echo   Necesitas exportar tus cookies de sesion una vez (30 segundos).
echo.
echo   PASO A: Instalar la extension en Chrome
echo   ─────────────────────────────────────────────────────────
echo   Se abrira Chrome Web Store con la extension necesaria.
echo   Haz clic en "Anadir a Chrome" e instalala.
echo.
set /p TIENE_EXT="  Ya tienes instalada la extension 'Get cookies.txt LOCALLY'? (S/N): "
if /i "!TIENE_EXT!"=="S" goto :abrir_youtube
if /i "!TIENE_EXT!"=="s" goto :abrir_youtube

echo.
echo   Abriendo Chrome Web Store para instalar la extension...

where chrome >nul 2>&1
if %errorlevel% equ 0 (
    start chrome "https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc"
) else (
    where msedge >nul 2>&1
    if %errorlevel% equ 0 (
        start msedge "https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc"
    ) else (
        start "" "https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc"
    )
)

echo.
set /p EXT_OK="  Pulsa Enter cuando hayas instalado la extension..."

:abrir_youtube
echo.
echo   PASO B: Exportar cookies desde YouTube
echo   ─────────────────────────────────────────────────────────
echo   1. Se abrira YouTube en tu navegador
echo   2. Asegurate de estar LOGUEADO en YouTube
echo   3. Haz clic en el icono de la extension (arriba a la derecha)
echo   4. Pulsa "Export"
echo   5. Guarda el archivo como "cookies.txt" en esta carpeta:
echo      %~dp0
echo   ─────────────────────────────────────────────────────────
echo.
echo   Abriendo YouTube...
echo.

where chrome >nul 2>&1
if %errorlevel% equ 0 (
    start chrome "https://www.youtube.com"
) else (
    where msedge >nul 2>&1
    if %errorlevel% equ 0 (
        start msedge "https://www.youtube.com"
    ) else (
        start "" "https://www.youtube.com"
    )
)

echo   Esperando cookies.txt en: %~dp0
echo   (Continuara automaticamente cuando lo detecte)
echo   Pulsa Ctrl+C para cancelar.
echo.

:wait_cookies
if exist cookies.txt (
    echo.
    echo   OK - cookies.txt detectado!
    goto :cookies_ok
)
timeout /t 3 /nobreak >nul
echo|set /p="."
goto :wait_cookies

:cookies_ok
echo.
echo.
echo ============================================================
echo   Instalacion completada! Todo listo para usar.
echo ============================================================
echo.
echo   Uso basico:
echo     python yt_transcribe.py "https://youtube.com/watch?v=xxxxx"
echo.
echo   Modo batch (varios videos a la vez):
echo     python yt_transcribe.py "URL1" "URL2" video.mp4
echo.
echo   Las transcripciones se guardan en:
echo     %~dp0transcripciones\
echo.
echo   ─────────────────────────────────────────────────────────
echo   SOBRE LAS COOKIES:
echo   Las cookies de YouTube caducan periodicamente (semanas o meses).
echo   Cuando veas el error "Please sign in", simplemente:
echo     1. Abre YouTube en el navegador (ya logueado)
echo     2. Haz clic en la extension "Get cookies.txt LOCALLY"
echo     3. Pulsa "Export" y reemplaza el cookies.txt de esta carpeta
echo   No hace falta reinstalar nada mas.
echo   ─────────────────────────────────────────────────────────
echo.
pause
