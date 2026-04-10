# YT-Transcribe

YouTube o archivos locales → Transcripción en Markdown. Una URL, varios archivos, o una mezcla — todo en un solo comando.

Busca subtítulos en YouTube primero (gratis, instantáneo). Si no hay, descarga el audio y transcribe con Groq Whisper (~300 min/día gratis). Acepta archivos de audio y video locales directamente. **Modo batch incluido:** pasa varias fuentes a la vez y las procesa todas en secuencia.

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
| Windows | ✅ Instalación automática (`install.bat`) |
| Mac / Linux | ✅ Funciona — instalación manual (ver abajo) |

---

## Instalación en Windows

```bash
# 1. Runtime JavaScript (requerido por yt-dlp para extraer info de YouTube)
winget install DenoLand.Deno

# 2. Clonar e instalar
git clone https://github.com/Asesorian/yt-transcribe.git
cd yt-transcribe
install.bat
```

El instalador hace tres cosas:
- Instala `yt-dlp` y `groq` vía pip
- Detecta si tienes ffmpeg (necesario para videos >25 min y para archivos de video locales)
- Te pide tu API key de Groq y la guarda en `.env`

> ⚠️ **Importante:** `install.bat` no instala Deno. Debes instalarlo antes manualmente con el comando de arriba, o yt-dlp fallará al obtener info de cualquier vídeo de YouTube con el error *"No supported JavaScript runtime could be found"*. Después de instalar Deno, **cierra y vuelve a abrir la terminal** para que coja el PATH actualizado.

---

## Instalación en Mac / Linux

```bash
# 1. Runtime JavaScript (requerido por yt-dlp)
# Mac:
brew install deno
# Linux:
curl -fsSL https://deno.land/install.sh | sh

# 2. Clonar e instalar
git clone https://github.com/Asesorian/yt-transcribe.git
cd yt-transcribe
pip install yt-dlp groq

# ffmpeg (necesario para videos locales y audios >25 min)
# Mac:
brew install ffmpeg
# Ubuntu/Debian:
sudo apt install ffmpeg

cp .env.example .env
# Edita .env y pon tu clave: GROQ_API_KEY=tu_clave_aqui
```

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
5. **Si el audio supera 25 MB:** lo divide en partes automáticamente (requiere ffmpeg)
6. **Si hay rate limit (429):** espera el tiempo exacto que indica Groq y reintenta solo
7. **Guarda** la transcripción como `.md` en la carpeta `transcripciones/`

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
- **Deno** (runtime JavaScript requerido por yt-dlp moderno para extraer info de YouTube)
- yt-dlp (mantener actualizado — ver Troubleshooting)
- groq
- ffmpeg (necesario para archivos de video locales y audios >25 min)
- API key de Groq (gratuita)

---

## Troubleshooting

### Error: *"No supported JavaScript runtime could be found"*

yt-dlp moderno requiere un runtime de JavaScript para extraer información de vídeos de YouTube (YouTube ofusca las URLs con JS). Por defecto busca Deno.

**Solución:**
```bash
# Windows
winget install DenoLand.Deno

# Mac
brew install deno

# Linux
curl -fsSL https://deno.land/install.sh | sh
```

Después **cierra y vuelve a abrir la terminal** para que coja el PATH actualizado.

### Error: *"Private video"* / *"Sign in if you've been granted access"*

El vídeo es privado o no listado. Esto ocurre con frecuencia en streams en directo que el organizador oculta tras terminar la retransmisión. Opciones:

- Esperar a que se republique como vídeo normal (suele pasar en eventos con charlas editadas posteriormente)
- Buscar una versión alternativa en otro canal
- Actualmente el script no soporta `--cookies-from-browser` de yt-dlp, pero se puede añadir modificando `yt_transcribe.py`

### yt-dlp falla de forma rara con vídeos de YouTube

YouTube cambia su ofuscador cada pocas semanas y las versiones viejas de yt-dlp dejan de funcionar sin previo aviso. Si notas errores extraños con vídeos que antes funcionaban, **actualiza yt-dlp primero**:

```bash
python -m pip install -U yt-dlp
```

Es buena práctica hacerlo cada pocas semanas o antes de transcribir vídeos importantes.

### Limitación conocida: subtítulos automáticos de YouTube en vídeos largos

La ruta de subtítulos YouTube (la que se usa por defecto, sin `--force-audio`) tiene un bug conocido con vídeos largos que usan subtítulos automáticos solapados: el deduplicado puede eliminar la mayor parte del contenido y devolver una transcripción muy incompleta sin avisar.

**Workaround fiable:** usa `--force-audio` para saltar los subtítulos de YouTube y transcribir directamente con Groq Whisper. Más lento, pero resultado completo garantizado.

```bash
python yt_transcribe.py "URL" --force-audio
```

---

## Estructura

```
yt-transcribe/
  yt_transcribe.py     Script principal (multiplataforma)
  install.bat          Instalador automático (Windows)
  launcher.pyw         Lanzador con doble clic (Windows)
  YT-Transcribe.bat    Acceso directo (Windows)
  .env.example         Plantilla para tu API key
  .env                 Tu API key (no se sube a Git)
  transcripciones/     Aquí se guardan los .md (no se sube a Git)
  README.md            Este archivo
```
