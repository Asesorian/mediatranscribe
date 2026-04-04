# YT-Transcribe

YouTube o archivo local → Transcripción en Markdown. Un solo comando.

Busca subtítulos en YouTube primero (gratis, instantáneo). Si no hay, descarga el audio y transcribe con Groq Whisper (~300 min/día gratis). También acepta archivos de audio y video locales directamente.

---

## Compatibilidad

| Sistema | Estado |
|---|---|
| Windows | ✅ Instalación automática (`install.bat`) |
| Mac / Linux | ✅ Funciona — instalación manual (ver abajo) |

---

## Instalación en Windows

```bash
git clone https://github.com/Asesorian/yt-transcribe.git
cd yt-transcribe
install.bat
```

El instalador hace tres cosas:
- Instala `yt-dlp` y `groq` vía pip
- Detecta si tienes ffmpeg (necesario para videos >25 min y para archivos de video locales)
- Te pide tu API key de Groq y la guarda en `.env`

---

## Instalación en Mac / Linux

```bash
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

# Forzar Groq Whisper (saltar subtítulos YouTube)
python yt_transcribe.py "URL" --force-audio

# Guardar en otra carpeta
python yt_transcribe.py "URL" -o "/ruta/a/mis_transcripciones"

# Buscar subtítulos en inglés
python yt_transcribe.py "URL" --lang en
```

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
| Audio | `.mp3` `.m4a` `.wav` `.ogg` `.flac` `.opus` |

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
- yt-dlp
- groq
- ffmpeg (necesario para archivos de video locales y audios >25 min)
- API key de Groq (gratuita)

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
