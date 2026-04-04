# YT-Transcribe

YouTube → Transcripción en Markdown. Un solo comando.

Busca subtítulos en YouTube primero (gratis, instantáneo). Si no hay, descarga el audio y transcribe con Groq Whisper (~300 min/día gratis).

---

## Compatibilidad

| Sistema | Estado |
|---|---|
| Windows | ✅ Instalación automática (`install.bat`) |
| Mac / Linux | ✅ Funciona — instalación manual (ver abajo) |

---

## Instalación en Windows

```bash
# 1. Clona el repo
git clone https://github.com/Asesorian/yt-transcribe.git
cd yt-transcribe

# 2. Ejecuta el instalador
install.bat
```

El instalador hace tres cosas:
- Instala `yt-dlp` y `groq` vía pip
- Detecta si tienes ffmpeg (necesario solo para videos >25 min)
- Te pide tu API key de Groq y la guarda en `.env`

---

## Instalación en Mac / Linux

```bash
# 1. Clona el repo
git clone https://github.com/Asesorian/yt-transcribe.git
cd yt-transcribe

# 2. Instala dependencias
pip install yt-dlp groq

# 3. Instala ffmpeg (opcional, solo para videos largos)
# Mac:
brew install ffmpeg
# Ubuntu/Debian:
sudo apt install ffmpeg

# 4. Crea el archivo .env con tu API key de Groq
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
# Básico — subtítulos YouTube si hay, si no: Groq Whisper
python yt_transcribe.py "https://youtube.com/watch?v=xxxxx"

# Forzar audio + Groq (mejor calidad, gasta minutos Groq)
python yt_transcribe.py "URL" --force-audio

# Guardar en otra carpeta
python yt_transcribe.py "URL" -o "/ruta/a/mis_transcripciones"

# Buscar subtítulos en inglés
python yt_transcribe.py "URL" --lang en
```

---

## Cómo funciona

1. **Primero** busca subtítulos en YouTube (gratis, instantáneo)
2. **Si no hay**, descarga el audio y transcribe con Groq Whisper
3. **Si el audio es >25 MB**, lo divide automáticamente en partes (requiere ffmpeg)
4. **Si hay rate limit** (429), espera el tiempo exacto que indica Groq y reintenta solo
5. **Guarda** la transcripción como `.md` en la carpeta `transcripciones/`

---

## Formato de salida

```markdown
# Título del Video

> **Canal:** NombreCanal
> **Duración:** 2h 25m 03s
> **Transcrito:** 2026-04-03 22:15
> **Método:** Groq Whisper (whisper-large-v3)
> **URL:** https://www.youtube.com/watch?v=...

[transcripción completa]
```

---

## Requisitos

- Python 3.10+
- yt-dlp
- groq
- ffmpeg (opcional, solo para videos >25 min / >25 MB de audio)
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
