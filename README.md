# YT-Transcribe

YouTube o archivos locales → Transcripción en Markdown. Una URL, varios archivos, o una mezcla — todo en un solo comando.

Busca subtítulos en YouTube primero (gratis, instantáneo). Si no hay, descarga el audio y transcribe con Groq Whisper (~300 min/día gratis) **con timestamps automáticos** `[HH:MM:SS]` por párrafo. Acepta archivos de audio y video locales directamente. **Modo batch incluido:** pasa varias fuentes a la vez y las procesa todas en secuencia.

```bash
# Un archivo
python yt_transcribe.py "https://youtube.com/watch?v=xxxxx"

# Varios a la vez (batch)
python yt_transcribe.py "URL1" "URL2" sesion.mp4 grabacion.mp3
```

---

## Compatibilidad

| Sistema | Estado |
|---|---|
| Windows | ✅ Instalación one shot (`install.bat`) |
| Mac / Linux | ✅ Funciona — instalación manual (ver abajo) |

---

## Instalación en Windows — One Shot

```bash
git clone https://github.com/Asesorian/yt-transcribe.git
cd yt-transcribe
install.bat
```

El instalador hace todo automáticamente:

1. **yt-dlp** — instala desde winget (o actualiza si ya está). La versión winget incluye el solver de JS challenges de YouTube; la versión pip no.
2. **groq** — instala vía pip
3. **ffmpeg** — instala desde winget (necesario para videos >25 min y archivos de video locales)
4. **API key de Groq** — te la pide y la guarda en `.env`
5. **Cookies de YouTube** — te guía paso a paso:
   - Pregunta si ya tienes la extensión instalada
   - Si no: abre Chrome Web Store directamente en la extensión correcta y espera a que la instales
   - Abre YouTube automáticamente con instrucciones en pantalla
   - Detecta `cookies.txt` solo y continúa sin que hagas nada más

Al terminar, el script está listo para usar.

> ℹ️ **Las cookies caducan** (semanas o meses). Cuando veas el error `Please sign in`, re-exporta `cookies.txt` desde la extensión del navegador y reemplaza el archivo. No hace falta reinstalar nada más.

---

## Instalación en Mac / Linux

```bash
# 1. yt-dlp desde GitHub (no usar pip)
# Mac:
brew install yt-dlp
# Linux:
sudo curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp
sudo chmod a+rx /usr/local/bin/yt-dlp

# 2. Clonar e instalar
git clone https://github.com/Asesorian/yt-transcribe.git
cd yt-transcribe
pip install groq

# ffmpeg (necesario para archivos de video locales y audios >25 min)
# Mac:
brew install ffmpeg
# Ubuntu/Debian:
sudo apt install ffmpeg

cp .env.example .env
# Edita .env y pon tu clave: GROQ_API_KEY=tu_clave_aqui
```

Después sigue el proceso de cookies de la sección siguiente.

---

## Autenticación con YouTube (requerida desde 2026)

**Por qué ocurre esto:** A principios de 2026 YouTube lanzó una campaña activa contra las herramientas de descarga automatizada. Todos los videos — incluso los públicos — empezaron a devolver el error `Sign in to confirm you're not a bot`. No es un bug del script ni de yt-dlp: es una decisión deliberada de YouTube para forzar el uso de su plataforma directamente.

Al mismo tiempo, YouTube eliminó el soporte OAuth2 en yt-dlp, y Chrome 127+ cambió el cifrado de sus cookies (App-Bound Encryption), lo que impide que yt-dlp las lea directamente con `--cookies-from-browser`. La única vía estable que queda es exportar las cookies manualmente como archivo `cookies.txt`.

**En Windows el instalador te guía por este proceso automáticamente.** Para Mac/Linux, o si necesitas renovar las cookies:

1. Instala la extensión **Get cookies.txt LOCALLY**:
   - Chrome: [chromewebstore.google.com](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
2. Abre [youtube.com](https://youtube.com) con tu sesión iniciada
3. Haz clic en el icono de la extensión → **Export**
4. Guarda el archivo como `cookies.txt` en la misma carpeta que `yt_transcribe.py`

El script detecta `cookies.txt` automáticamente. Verás `🍪 Usando cookies.txt` al procesar cualquier URL de YouTube.

> ⚠️ **No subas `cookies.txt` a Git.** Está en `.gitignore` — contiene tu sesión de YouTube y no debe ser pública.

---

## Obtener API key de Groq (gratis)

1. Ve a [console.groq.com](https://console.groq.com)
2. Crea una cuenta gratuita
3. API Keys → Create API Key
4. Copia la clave y pégala en tu `.env`

El plan gratuito incluye ~300 minutos de audio por día con Whisper Large v3.

---

## Uso

```bash
# URL de YouTube — subtítulos si hay, si no: Groq Whisper
python yt_transcribe.py "https://youtube.com/watch?v=xxxxx"

# Archivo de video local (mp4, mkv, avi, mov...)
python yt_transcribe.py "reunion.mp4"
python yt_transcribe.py "C:\grabaciones\meeting.mp4"

# Archivo de audio local (mp3, m4a, wav, ogg...)
python yt_transcribe.py "audio.mp3"
python yt_transcribe.py "C:\grabaciones\entrevista.m4a"

# Modo batch — varias fuentes a la vez (URLs y/o archivos mezclados)
python yt_transcribe.py "URL1" "URL2" "URL3"
python yt_transcribe.py sesion1.mp4 sesion2.mp4 sesion3.mp3
python yt_transcribe.py "https://youtube.com/watch?v=xxx" reunion.mp4 entrevista.mp3

# Forzar Groq Whisper (saltar subtítulos YouTube)
python yt_transcribe.py "URL" --force-audio

# Guardar en otra carpeta
python yt_transcribe.py "URL" -o "/ruta/a/mis_transcripciones"

# Buscar subtítulos en inglés
python yt_transcribe.py "URL" --lang en
```

---

## Modo batch

Pasa cualquier combinación de URLs de YouTube y archivos locales en un solo comando:

```bash
python yt_transcribe.py "URL1" "URL2" sesion.mp4 grabacion.mp3
```

- Se procesan en orden, uno a uno
- Si una fuente falla, el error se muestra y continúa con la siguiente
- Al final se imprime un resumen con todas las transcripciones completadas y los errores

---

## Cómo funciona

1. **Detecta automáticamente** si es una URL de YouTube o un archivo local
2. **Para YouTube:** busca subtítulos primero (gratis), si no los hay descarga el audio
3. **Para archivos de video** (mp4, mkv...): extrae el audio con ffmpeg y transcribe con Groq
4. **Para archivos de audio** (mp3, m4a...): envía directamente a Groq Whisper
5. **Si el audio supera 24 MB:** lo divide en partes con **5 segundos de overlap** entre chunks, valida tamaños reales y re-segmenta si hace falta. Al recomponer, **deduplica las zonas de solapamiento** para evitar texto repetido
6. **Timestamps automáticos:** cada ~45 segundos de contenido (o tras un silencio >3s) se abre un nuevo párrafo con `[HH:MM:SS]` global
7. **Si hay rate limit (429):** espera el tiempo exacto que indica Groq y reintenta solo
8. **Tolerancia a fallos por chunk:** si una parte concreta falla, se marca `[PARTE X FALLÓ]` y continúa con las siguientes (no aborta todo)
9. **Validación de completitud:** al final, comprueba caracteres / minuto y avisa si la densidad parece anormalmente baja
10. **Guarda** la transcripción como `.md` en la carpeta `transcripciones/`

---

## Formatos soportados

| Tipo | Extensiones |
|---|---|
| Video | `.mp4` `.mkv` `.avi` `.mov` `.webm` `.wmv` `.ts` `.mts` |
| Audio | `.mp3` `.m4a` `.wav` `.ogg` `.flac` `.opus` `.weba` |

---

## Formato de salida

```markdown
# Título del Video o Nombre del Archivo

> **Fuente:** NombreCanal / Archivo local
> **Fecha:** 2026-04-03
> **Duración:** 2h 25m 03s
> **Transcrito:** 2026-04-03 22:15
> **Método:** Groq Whisper (whisper-large-v3)
> **URL / Archivo:** ...

[transcripción completa]
```

---

## Requisitos

- Python 3.10+
- **yt-dlp** instalado desde GitHub o winget (no pip — ver Instalación)
- groq
- ffmpeg (necesario para archivos de video locales y audios >25 min)
- API key de Groq (gratuita)
- `cookies.txt` de YouTube (el instalador te guía — ver Autenticación)

---

## Troubleshooting

### Error: *"Please sign in"* / *"Sign in to confirm you're not a bot"*

YouTube requiere autenticación desde 2026. Ver sección **Autenticación** arriba.

Si ya tienes `cookies.txt` y vuelve a aparecer el error, las cookies han caducado. Re-expórtalas desde el navegador y reemplaza el archivo. No hace falta reinstalar nada.

### Error: *"Private video"* / *"Sign in if you've been granted access"*

El vídeo es privado o no listado. Las cookies solo funcionan para videos accesibles con tu cuenta. Si el video no es visible desde tu navegador, tampoco será descargable.

### yt-dlp falla de forma rara con vídeos de YouTube

YouTube cambia su sistema de protección frecuentemente. Si notas errores extraños:

1. **Actualiza yt-dlp:**
```bash
# Windows
winget upgrade yt-dlp

# Mac
brew upgrade yt-dlp

# Linux
sudo curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp
```
2. **Re-exporta cookies.txt** — las cookies antiguas pueden causar errores inesperados

### Aviso: *"transcripción posiblemente incompleta"*

Si ves un warning de densidad chars/minuto baja, busca marcas `[PARTE X FALLÓ]` en el output. Volver a lanzar el comando suele resolverlo (suelen ser rate limits puntuales).

---

## Changelog

### v3.1 (18 abril 2026)

**Autenticación YouTube obligatoria + instalador one shot.**

YouTube lanzó en 2026 una campaña contra downloaders que afecta a todos los videos públicos. OAuth2 también fue eliminado. Cambios:
- Instalador completamente reescrito: instala yt-dlp, groq, ffmpeg y guía el proceso de cookies paso a paso sin intervención manual salvo la exportación
- Si el usuario no tiene la extensión, el instalador abre Chrome Web Store directamente y espera confirmación antes de continuar
- El instalador abre YouTube automáticamente, muestra instrucciones en pantalla y detecta `cookies.txt` solo cuando aparece en la carpeta
- Soporte nativo `cookies.txt` en el script: se pasa automáticamente a yt-dlp si el archivo existe
- El script muestra `🍪 Usando cookies.txt` al procesar URLs de YouTube
- **Requisito actualizado:** yt-dlp debe instalarse desde GitHub o winget, no pip

### v3 (16 abril 2026)

**Timestamps y overlap para audios largos.**
- Output Markdown con `[HH:MM:SS]` por párrafo (~45s de contenido o silencio >3s)
- Chunking con overlap de 5 segundos entre partes consecutivas
- Groq Whisper usa `verbose_json` + `timestamp_granularities`
- Deduplicación en zona de overlap al recomponer timestamps globales
- Backup de v2 conservado como `yt_transcribe_v2_backup.py`

**Validado con:** video de 128 min → 105.620 caracteres en 3 chunks.

### v2 (12 abril 2026)

**Resuelto:** Bug serio en vídeos largos.
- `parse_vtt` perdía 80-95% del contenido por dedup global
- `split_audio` verifica tamaño real de cada chunk
- Tolerancia a fallos por chunk con marcas `[PARTE X FALLÓ]`
- Validación de completitud al final (chars/min)

### v1 (4 abril 2026)

Primera versión pública: soporte URLs YouTube + archivos locales, modo batch, retry automático en rate limit, instalador Windows.

---

## Estructura

```
yt-transcribe/
  yt_transcribe.py             Script principal (multiplataforma)
  yt_transcribe_v2_backup.py   Backup de v2 (sin timestamps)
  install.bat                  Instalador one shot (Windows)
  launcher.pyw                 Lanzador con doble clic (Windows)
  YT-Transcribe.bat            Acceso directo (Windows)
  .env.example                 Plantilla para tu API key
  .env                         Tu API key (no se sube a Git)
  cookies.txt                  Cookies de YouTube (no se sube a Git)
  transcripciones/             Aquí se guardan los .md (no se sube a Git)
  README.md                    Este archivo
```
