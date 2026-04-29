# MediaTranscribe v1.0

> Transcripción de audio y video a Markdown con timestamps — YouTube, Vimeo, archivos locales.

Anteriormente conocido como **YT-Transcribe**. Renombrado a MediaTranscribe para reflejar el soporte completo de fuentes locales y múltiples plataformas.

---

## ¿Qué hace?

Convierte cualquier fuente de audio o video en un archivo Markdown con timestamps cada ~45 segundos. Ideal para transcribir reuniones, ponencias, clases o cualquier contenido en audio.

**Fuentes soportadas:**
- URLs de YouTube y Vimeo
- Archivos de audio locales: `.mp3`, `.m4a`, `.aac`, `.wav`, `.ogg`, `.flac`, `.opus`
- Archivos de video locales: `.mp4`, `.mkv`, `.avi`, `.mov`, `.webm`

**Salida:** archivo `.md` con cabecera de metadatos y transcripción con timestamps `[HH:MM:SS]`.

---

## Instalación

### Requisitos
- Python 3.10+
- [ffmpeg](https://ffmpeg.org/) instalado y en el PATH
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) instalado (`pip install yt-dlp`)
- Cuenta en [Groq](https://console.groq.com/) (gratuita)

### Setup

```bash
# 1. Clonar el repositorio
git clone https://github.com/tu-usuario/yt-transcribe.git
cd yt-transcribe

# 2. Instalar dependencias Python
pip install groq yt-dlp

# 3. Configurar API key de Groq
cp .env.example .env
# Editar .env y añadir: GROQ_API_KEY=tu_clave_aqui
```

---

## Uso

### Interfaz gráfica (recomendado)

Doble clic en **`MediaTranscribe.vbs`** — abre la GUI sin ventana de consola.

O ejecutar directamente:
```bash
pythonw launcher.pyw
```

**Opciones en la GUI:**
- **Examinar...** — selecciona uno o varios archivos de audio/video desde el explorador
- **Transcribir** — procesa las fuentes (URL o rutas pegadas en el textarea)
- **Forzar Groq** — omite la búsqueda de subtítulos en YouTube e incluye la API de Groq directamente
- **Abrir carpeta transcripciones** — abre la carpeta de salida

### Línea de comandos

```bash
# Audio o video local
python yt_transcribe.py "reunion.aac"
python yt_transcribe.py "C:\grabaciones\meeting.mp3"

# URL de YouTube o Vimeo
python yt_transcribe.py "https://youtube.com/watch?v=xxxxx"

# Modo batch — varios archivos a la vez
python yt_transcribe.py "reunion1.mp3" "reunion2.aac" "https://youtu.be/xxxxx"

# Forzar Groq (sin subtítulos YouTube)
python yt_transcribe.py URL --force-audio

# Idioma de subtítulos
python yt_transcribe.py URL --lang en

# Carpeta de salida personalizada
python yt_transcribe.py archivo.mp3 -o "C:\mis_transcripciones"
```

---

## Gestión de duplicados

Cuando el archivo de salida ya existe, la GUI pregunta qué hacer:

- **Reemplazar** — sobreescribe el archivo existente
- **Guardar como nuevo** — crea `archivo (2).md`, `archivo (3).md`, etc.
- **Omitir** — salta este archivo y continúa con los demás (útil en batch)

---

## Log en tiempo real

La GUI muestra el progreso en color durante el procesamiento:

| Color | Significado |
|-------|-------------|
| 🔵 Azul | Pasos del proceso (transcribiendo, descargando...) |
| 🟡 Amarillo | Progreso y descargas (%, tamaños, partes) |
| 🟢 Verde | Éxitos (ok, completado, guardado) |
| 🟠 Naranja | Avisos (rate limit, espera, reemplazando) |
| 🔴 Rojo | Errores |

---

## Arquitectura

```
yt_transcribe.py     # Motor principal (CLI + lógica)
launcher.pyw         # GUI Tkinter (sin consola)
MediaTranscribe.vbs  # Lanzador sin ventana negra
transcripciones/     # Carpeta de salida (auto-creada)
.env                 # GROQ_API_KEY (no subir a git)
cookies.txt          # Cookies YouTube (opcional, para vídeos con login)
```

**Flujo para archivos locales:**
1. ffprobe obtiene duración y metadatos
2. Si >24 MB → ffmpeg divide en chunks con 5s de overlap
3. Cada chunk se envía a Groq Whisper API
4. Se recomponen timestamps globales y se deduplican zonas de overlap
5. Output: Markdown con párrafos de ~45s

**Flujo para YouTube/Vimeo:**
1. yt-dlp obtiene metadatos
2. Busca subtítulos nativos (gratis, sin Groq)
3. Si no hay subtítulos → descarga audio y usa flujo de archivo local

---

## Notas sobre Groq

- Plan gratuito: ~7200 segundos de audio por hora
- Para reuniones largas (>1h) puede haber esperas por rate limit — la app las gestiona automáticamente y reintenta
- Modelo usado: `whisper-large-v3`
- Coste plan de pago: ~$0.111/hora de audio

---

## Changelog

### v1.0 (MediaTranscribe) — Abril 2026
- Renombrado de YT-Transcribe a MediaTranscribe
- GUI rediseñada: colores morado/negro, log multicolor en tiempo real
- Soporte nativo `.aac` añadido
- Botón **Examinar** para selección de archivos locales
- Detección de duplicados con diálogo Reemplazar / Guardar como nuevo / Omitir
- Progreso yt-dlp visible en log en tiempo real (streaming con Popen)
- Sin ventana negra: `CREATE_NO_WINDOW` en todos los subprocesos
- Lanzador `.vbs` para abrir sin consola desde acceso directo
- Barra de progreso animada durante procesamiento
- `--output-name` arg para gestión de nombres desde el launcher

### v3.0 (YT-Transcribe) — Marzo 2026
- Chunking con overlap de 5s para evitar pérdida de palabras en bordes
- Groq con `verbose_json` + timestamps por segmento
- Recomposición de timestamps globales con deduplicación
- Output Markdown con `[HH:MM:SS]` cada ~45s

### v2.0 (YT-Transcribe)
- Modo batch multi-fuente
- Retry automático en rate limit de Groq
- Soporte archivos de video local con extracción de audio vía ffmpeg

---

## Licencia

MIT
