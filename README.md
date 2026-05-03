# MediaTranscribe v2.3

> Transcripción de audio y video a Markdown con timestamps — YouTube, Vimeo, archivos locales.

Soporta tres motores: **Groq API** (recomendado), **Gemini API** y **Local Whisper** (offline).

---

## ¿Qué hace?

Convierte cualquier fuente de audio o video en un archivo Markdown con timestamps cada ~45 segundos.

**Fuentes soportadas:**
- URLs de YouTube y Vimeo
- Archivos de audio: `.mp3` `.m4a` `.aac` `.wav` `.ogg` `.flac` `.opus`
- Archivos de video: `.mp4` `.mkv` `.avi` `.mov` `.webm`

**Salida:** archivo `.md` con cabecera de metadatos y transcripción con timestamps `[HH:MM:SS]`.

---

## Motores de transcripción

| Motor | Velocidad | Requiere | Ideal para |
|-------|-----------|----------|------------|
| **Groq API** | ⚡ Muy rápido | API key (gratis) | Uso habitual |
| **Gemini API** | ⚡ Rápido | API key (gratis) | Alternativa cloud |
| **Local Whisper** | 🐢 Lento | Sin internet | Uso offline / privacidad |

> ⚠ **Local Whisper** usa procesamiento en CPU sin GPU. Un audio de 1h puede tardar 10–30 min según el modelo.
> Para uso habitual recomendamos **Groq API** o **Gemini API**.

---

## Instalación

### Opción A — Instalador automático (recomendado)

Doble clic en **`install.bat`** y sigue las instrucciones en pantalla.

El instalador comprueba e instala:
- Python 3.10+
- ffmpeg (via winget)
- yt-dlp, groq (dependencias Python)
- google-generativeai (para motor Gemini)

### Opción B — Manual

```bash
# 1. Clonar el repositorio
git clone https://github.com/Asesorian/yt-transcribe.git
cd yt-transcribe

# 2. Instalar dependencias Python
pip install groq yt-dlp google-generativeai

# 3. Solo si vas a usar Local Whisper
pip install faster-whisper

# 4. Crear .env con tu(s) API key(s)
echo GROQ_API_KEY=tu_clave_groq > .env
echo GEMINI_API_KEY=tu_clave_gemini >> .env
```

**Obtener API keys (gratuitas):**
- Groq: https://console.groq.com/
- Gemini: https://aistudio.google.com/app/apikey

---

## Uso

### Interfaz gráfica (recomendado)

Doble clic en **`MediaTranscribe.vbs`** — abre la GUI sin ventana de consola.

```bash
# O directamente:
pythonw launcher.pyw
```

**Opciones:**
- **Motor** — elige Groq API (default), Gemini API o Local Whisper
- **Examinar...** — selecciona archivos desde el explorador de Windows
- **Forzar audio** — omite subtítulos de YouTube y transcribe con el motor elegido
- **Filtrar silencio** (solo Local) — VAD para reducir tiempo en audios con pausas largas
- **Abrir carpeta transcripciones** — abre la carpeta de salida

### Línea de comandos (motor `mediatranscribe.py`)

```bash
# Con Groq (default)
python mediatranscribe.py "reunion.mp3"
python mediatranscribe.py "https://youtube.com/watch?v=xxxxx"

# Con Gemini
python mediatranscribe.py "reunion.mp3" --motor gemini

# Local Whisper (offline)
python mediatranscribe.py "reunion.mp3" --motor local --model-size small

# Modelos Local Whisper disponibles:
#   tiny           39 MB  — rápido, calidad básica
#   small         244 MB  — equilibrado (default)
#   large-v3-turbo 809 MB — alta calidad
#   large-v3       1.5 GB — máxima calidad

# Opciones comunes
python mediatranscribe.py URL --force-audio    # forzar descarga audio
python mediatranscribe.py URL --lang en        # subtítulos en inglés
python mediatranscribe.py a.mp3 b.mp3 URL     # batch multi-fuente
python mediatranscribe.py a.mp3 --vad         # filtro silencio (solo local)
python mediatranscribe.py a.mp3 -o "C:\salida" # carpeta de salida
```

---

## Arquitectura

```
mediatranscribe.py   # Motor CLI (Groq / Gemini / Local)
launcher.pyw         # GUI Tkinter v2.3
MediaTranscribe.vbs  # Lanzador sin ventana negra
install.bat          # Instalador automático
transcripciones/     # Carpeta de salida (auto-creada)
models/              # Modelos Local Whisper (auto-descargados)
.env                 # GROQ_API_KEY, GEMINI_API_KEY (NO subir a git)
cookies.txt          # Cookies YouTube opcionales (NO subir a git)
```

**Flujo YouTube/Vimeo (Groq/Gemini):**
1. yt-dlp obtiene metadatos
2. Busca subtítulos nativos → si los hay, los usa directamente
3. Si no → descarga audio y transcribe con el motor elegido
4. Output: Markdown con timestamps `[MM:SS]` cada ~45s

**Flujo archivo local:**
1. ffprobe obtiene duración
2. Si >24 MB → ffmpeg divide en chunks con 5s de overlap
3. Transcripción chunk a chunk con deduplicación de zonas de solape
4. Recomposición de timestamps globales

---

## Gestión de duplicados

Si el archivo de salida ya existe, la GUI pregunta:
- **Reemplazar** — sobreescribe
- **Guardar como nuevo** — crea `archivo (2).md`, etc.
- **Omitir** — salta (útil en batch)

---

## Notas por motor

**Groq API (gratis):**
- Plan gratuito: ~7.200 seg/hora de audio
- Rate limit gestionado automáticamente con reintentos
- Modelo: `whisper-large-v3`
- Coste pago: ~$0.111/hora de audio

**Gemini API (gratis):**
- Modelo: `gemini-2.5-flash`
- Sube el audio a la File API de Google y lo elimina tras transcribir
- Límites gratuitos generosos para uso personal

**Local Whisper:**
- Totalmente offline, sin coste
- Primera ejecución descarga el modelo (39 MB–1.5 GB según tamaño)
- Requiere `pip install faster-whisper`
- La GUI lo instala automáticamente si no está presente

---

## Changelog

### v2.3 / motor v4.3 — Mayo 2026
- Advertencia visible al seleccionar Local Whisper (fondo amarillo, explica lentitud en CPU)
- Motor Gemini actualizado: `gemini-2.0-flash` → `gemini-2.5-flash`
- README completo reescrito con guía de instalación y motores

### v2.2 / motor v4.2 — Mayo 2026
- Soporte multi-motor en GUI: Groq API, Gemini API, Local Whisper
- Motor local con descarga de modelo con barra de progreso y hilo vigilante
- Instalador automático `install.bat`

### v1.0 / motor v3.x — Abril 2026
- Renombrado de YT-Transcribe a MediaTranscribe
- GUI rediseñada (colores morado/negro, log multicolor)
- Soporte `.aac`, botón Examinar, detección de duplicados

### v3.x (YT-Transcribe) — Marzo 2026
- Chunking con overlap de 5s, timestamps por segmento vía Groq verbose_json
- Deduplicación de zonas de solape, output Markdown con `[HH:MM:SS]`

---

## Licencia

MIT