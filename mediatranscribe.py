#!/usr/bin/env python3
"""
MediaTranscribe v4.3 (motor): YouTube, Vimeo, audio y video local → Markdown con timestamps

Cambios v4.3:
  - Motor Gemini actualizado: gemini-2.0-flash → gemini-2.5-flash

Cambios v4.2:
  - Progreso de descarga de modelos: MB descargados + porcentaje en tiempo real
  - Hilo vigilante que monitoriza el directorio cada 2s durante la primera descarga

Cambios v4.1:
  - Supresion de warnings HuggingFace en Windows (symlinks, token implicito)
  - Mensaje de progreso mejorado para descarga de modelos grandes

Cambios v4.0:
  - Motor local offline: faster-whisper (tiny/small/large-v3-turbo/large-v3)
  - Motor Gemini API: Gemini 2.0 Flash como alternativa cloud a Groq
  - Filtro VAD: silencio automatico en modo Local (nativo faster-whisper)
  - Selector de motor via --motor (groq/local/gemini)
  - load_env carga todas las claves de .env (GROQ_API_KEY, GEMINI_API_KEY)
  - process_source refactorizado con routing limpio por motor
"""

import sys
import os
import json
import re
import shutil
import argparse
import tempfile
import subprocess
import threading
from pathlib import Path
from datetime import datetime

NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

AUDIO_EXTENSIONS = {".mp3", ".m4a", ".wav", ".ogg", ".flac", ".opus", ".weba", ".aac"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".wmv", ".ts", ".mts"}
LOCAL_EXTENSIONS = AUDIO_EXTENSIONS | VIDEO_EXTENSIONS

MIN_CHARS_PER_MINUTE = 400
OVERLAP_SECONDS = 5
MAX_CHUNK_MB = 24
MIN_CHUNK_DURATION = 60
PARAGRAPH_GAP_SECONDS = 45
DEDUP_TOLERANCE = 0.5

COOKIES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt")
MODELS_DIR   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")

# Tamano aproximado total del directorio de cada modelo (MB)
# Ligeramente por encima del real para evitar mostrar >100%
MODEL_SIZES    = {"tiny": "39 MB", "small": "244 MB", "large-v3-turbo": "809 MB", "large-v3": "1.5 GB"}
MODEL_TARGET_MB = {"tiny": 80, "small": 480, "large-v3-turbo": 920, "large-v3": 1600}


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def safe_filename(title):
    return re.sub(r'[<>:"/\\|?*]', '', title).strip()[:80]


def get_yt_args():
    args = []
    if os.path.exists(COOKIES_FILE):
        args += ["--cookies", COOKIES_FILE]
    return args


def load_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                val = val.strip().strip('"').strip("'")
                os.environ.setdefault(key.strip(), val)


def is_local_file(source):
    path = Path(source)
    if path.exists() and path.is_file():
        return True
    if path.suffix.lower() in LOCAL_EXTENSIONS:
        return True
    return False


def fmt_time(seconds):
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def _dir_size_mb(path):
    """Calcula el tamano total de un directorio en MB."""
    try:
        return sum(f.stat().st_size for f in Path(path).rglob("*") if f.is_file()) / (1024 * 1024)
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Herramientas de audio
# ---------------------------------------------------------------------------

def get_audio_duration(audio_path):
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
           "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, creationflags=NO_WINDOW)
        return float(result.stdout.strip())
    except (ValueError, AttributeError):
        return 0.0


def get_local_file_info(filepath):
    path = Path(filepath)
    file_size_mb = path.stat().st_size / (1024 * 1024)
    duration = int(get_audio_duration(filepath))
    return {
        "title": path.stem, "duration": duration,
        "uploader": "Archivo local", "upload_date": "",
        "id": "", "source_path": str(filepath), "file_size_mb": file_size_mb,
    }


def extract_audio_from_video(video_path, output_dir):
    output_path = os.path.join(output_dir, "audio.mp3")
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(video_path),
           "-vn", "-acodec", "libmp3lame", "-q:a", "5", output_path, "-y"]
    result = subprocess.run(cmd, capture_output=True, creationflags=NO_WINDOW)
    return output_path if result.returncode == 0 else None


def get_video_info(url):
    cmd = ["yt-dlp", "--dump-json", "--no-download"] + get_yt_args() + [url]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", creationflags=NO_WINDOW)
    if result.returncode != 0:
        print(f"  Error obteniendo info: {result.stderr[:200]}")
        return None
    info = json.loads(result.stdout)
    return {
        "title": info.get("title", "Sin titulo"),
        "duration": info.get("duration", 0),
        "uploader": info.get("uploader", "Desconocido"),
        "upload_date": info.get("upload_date", ""),
        "id": info.get("id", ""),
        "description": info.get("description", "")[:500],
    }


def try_youtube_subtitles(url, lang="es"):
    with tempfile.TemporaryDirectory() as tmpdir:
        output = os.path.join(tmpdir, "subs")
        for sub_flag in ["--write-sub", "--write-auto-sub"]:
            cmd = ["yt-dlp", sub_flag, "--sub-lang", lang, "--sub-format", "vtt",
                   "--skip-download"] + get_yt_args() + ["-o", output, url]
            subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", creationflags=NO_WINDOW)
            for f in Path(tmpdir).glob("*.vtt"):
                text = parse_vtt(f)
                if text and len(text) > 100:
                    return text
        if lang != "en":
            return try_youtube_subtitles(url, "en")
    return None


def parse_vtt(vtt_path):
    lines = []
    last_clean = None
    with open(vtt_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if (not line or line.startswith("WEBVTT") or line.startswith("Kind:")
                    or line.startswith("Language:") or "-->" in line
                    or line.startswith("NOTE")
                    or (line[0:1].isdigit() and line.endswith(":"))):
                continue
            clean = re.sub(r'<[^>]+>', '', line).strip()
            if clean and clean != last_clean:
                lines.append(clean)
                last_clean = clean
    paragraphs = []
    for i in range(0, len(lines), 5):
        paragraphs.append(" ".join(lines[i:i+5]))
    return "\n\n".join(paragraphs)


def download_audio(url, output_dir):
    output_template = os.path.join(output_dir, "audio.%(ext)s")
    cmd = ["yt-dlp", "-x", "--audio-format", "mp3", "--audio-quality", "5",
           "--newline"] + get_yt_args() + ["-o", output_template, url]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8", errors="replace", creationflags=NO_WINDOW)
    for line in process.stdout:
        line = line.rstrip()
        if line:
            print(line, flush=True)
    process.wait()
    if process.returncode != 0:
        return None
    for f in Path(output_dir).glob("audio.*"):
        if f.suffix in (".mp3", ".m4a", ".opus", ".webm", ".wav"):
            return str(f)
    return None


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def _extract_chunk(audio_path, start, duration, output_path):
    cmd = ["ffmpeg", "-y", "-ss", str(start), "-t", str(duration),
           "-i", audio_path, "-c:a", "libmp3lame", "-q:a", "5", output_path]
    result = subprocess.run(cmd, capture_output=True, text=True, creationflags=NO_WINDOW)
    return result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0


def split_audio_with_overlap(audio_path, max_size_mb=MAX_CHUNK_MB, overlap_seconds=OVERLAP_SECONDS):
    file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    total_duration = get_audio_duration(audio_path)
    if file_size_mb <= max_size_mb:
        return [(audio_path, 0.0)]
    if total_duration <= 0:
        total_duration = 3600
    print(f"  Audio grande ({file_size_mb:.1f} MB), dividiendo en partes...", flush=True)
    output_dir = os.path.dirname(audio_path)
    chunk_duration = max(int((max_size_mb / file_size_mb) * total_duration * 0.8), MIN_CHUNK_DURATION)
    for f in Path(output_dir).glob("chunk_*.mp3"):
        try:
            os.remove(f)
        except OSError:
            pass
    chunks = []
    start = 0.0
    idx = 0
    step = chunk_duration - overlap_seconds
    if step <= 0:
        raise ValueError("overlap >= chunk_duration")
    while start < total_duration:
        chunk_path = os.path.join(output_dir, f"chunk_{idx:03d}.mp3")
        eff_dur = min(chunk_duration, total_duration - start + 1)
        print(f"  Parte {idx+1} [desde {fmt_time(start)}]... ", end="", flush=True)
        if not _extract_chunk(audio_path, start, eff_dur, chunk_path):
            raise RuntimeError(f"No se pudo extraer chunk {idx}")
        chunk_size = os.path.getsize(chunk_path) / (1024 * 1024)
        print(f"ok ({chunk_size:.1f} MB)", flush=True)
        chunks.append((chunk_path, start))
        start += step
        idx += 1
    print(f"  Dividido en {len(chunks)} partes", flush=True)
    return chunks


def format_transcript_with_timestamps(global_segments, gap_seconds=PARAGRAPH_GAP_SECONDS):
    if not global_segments:
        return ""
    paragraphs = []
    current_text = []
    current_accum_start = global_segments[0]["start"]
    last_end = global_segments[0]["start"]
    for seg in global_segments:
        gap_from_last = seg["start"] - last_end
        elapsed_in_paragraph = seg["end"] - current_accum_start
        if current_text and (elapsed_in_paragraph > gap_seconds or gap_from_last > 3.0):
            paragraphs.append(f"[{fmt_time(current_accum_start)}] " + " ".join(current_text).strip())
            current_text = []
            current_accum_start = seg["start"]
        current_text.append(seg["text"])
        last_end = seg["end"]
    if current_text:
        paragraphs.append(f"[{fmt_time(current_accum_start)}] " + " ".join(current_text).strip())
    return "\n\n".join(paragraphs)


# ---------------------------------------------------------------------------
# Motor 1: Groq
# ---------------------------------------------------------------------------

def transcribe_with_groq(audio_path, api_key, max_retries=5):
    import time
    from groq import Groq, RateLimitError
    client = Groq(api_key=api_key)
    for attempt in range(max_retries):
        try:
            with open(audio_path, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    file=audio_file, model="whisper-large-v3", language="es",
                    response_format="verbose_json", timestamp_granularities=["segment"],
                )
            raw_segments = (transcription.segments if hasattr(transcription, "segments")
                            else transcription.get("segments", []) if isinstance(transcription, dict)
                            else []) or []
            segments = []
            for seg in raw_segments:
                if isinstance(seg, dict):
                    start, end, text = float(seg.get("start", 0)), float(seg.get("end", 0)), (seg.get("text") or "").strip()
                else:
                    start, end, text = float(getattr(seg, "start", 0)), float(getattr(seg, "end", 0)), (getattr(seg, "text", "") or "").strip()
                if text:
                    segments.append({"start": start, "end": end, "text": text})
            return segments
        except RateLimitError as e:
            if attempt >= max_retries - 1:
                raise
            wait_seconds = 750
            match = re.search(r'try again in (\d+)m([\d.]+)s', str(e))
            if match:
                wait_seconds = int(match.group(1)) * 60 + float(match.group(2)) + 10
            print(f"  Rate limit. Esperando {int(wait_seconds)}s...", flush=True)
            time.sleep(wait_seconds)
            print(f"  Reintentando ({attempt + 2}/{max_retries})...", flush=True)


def transcribe_chunks_groq(chunks_with_offset, api_key, total_duration_seconds=0):
    n = len(chunks_with_offset)
    all_global_segments = []
    failures = []
    max_end_so_far = -1.0
    dedup_skipped = 0
    for i, (chunk_path, offset) in enumerate(chunks_with_offset):
        if n > 1:
            print(f"  Parte {i+1}/{n} (offset {fmt_time(offset)})...", flush=True)
        try:
            segments = transcribe_with_groq(chunk_path, api_key)
            if not segments:
                raise RuntimeError("Groq devolvio 0 segments")
            for seg in segments:
                gs, ge = offset + seg["start"], offset + seg["end"]
                if gs < max_end_so_far - DEDUP_TOLERANCE:
                    dedup_skipped += 1
                    continue
                all_global_segments.append({"start": gs, "end": ge, "text": seg["text"]})
                if ge > max_end_so_far:
                    max_end_so_far = ge
            if n > 1:
                print(f"  Parte {i+1}/{n}: ok", flush=True)
        except Exception as e:
            failures.append((i + 1, str(e)))
            print(f"  Parte {i+1}/{n} FALLO: {e}", flush=True)
    all_global_segments.sort(key=lambda s: s["start"])
    transcript = format_transcript_with_timestamps(all_global_segments)
    real_chars = sum(len(s["text"]) for s in all_global_segments)
    if total_duration_seconds > 0:
        if real_chars < (total_duration_seconds / 60) * MIN_CHARS_PER_MINUTE:
            print(f"\n  ALERTA: transcripcion posiblemente incompleta", flush=True)
    return transcript


# ---------------------------------------------------------------------------
# Motor 2: Local Whisper (faster-whisper, offline)
# ---------------------------------------------------------------------------

def _watch_download_progress(model_cache_dir, target_mb, stop_event):
    """
    Hilo vigilante: monitoriza el tamano del directorio de descarga
    e imprime progreso cada vez que cambia en >=20 MB.
    """
    prev_mb = -1
    while not stop_event.is_set():
        if Path(model_cache_dir).exists():
            mb = _dir_size_mb(model_cache_dir)
            if mb - prev_mb >= 20:
                pct = min(99, int(mb / target_mb * 100))  # tope en 99 hasta confirmar
                print(f"  Descargando... {mb:.0f} / {target_mb} MB  ({pct}%)", flush=True)
                prev_mb = mb
        stop_event.wait(2)


def transcribe_with_local(audio_path, model_size="small", vad=False):
    """
    Transcripcion local offline con faster-whisper.
    Primera vez: descarga el modelo con progreso visible.
    Siguientes veces: carga desde cache en segundos.
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise ImportError(
            "faster-whisper no instalado.\n"
            "Ejecuta: pip install faster-whisper"
        )

    # Suprimir warnings de HuggingFace en Windows
    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
    os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"]   = "1"

    os.makedirs(MODELS_DIR, exist_ok=True)

    size_label  = MODEL_SIZES.get(model_size, "")
    target_mb   = MODEL_TARGET_MB.get(model_size, 500)
    cache_dir   = Path(MODELS_DIR) / f"models--Systran--faster-whisper-{model_size}"
    is_cached   = cache_dir.exists() and _dir_size_mb(cache_dir) > target_mb * 0.8

    if is_cached:
        print(f"  Cargando modelo {model_size} ({size_label}) desde cache...", flush=True)
        model = WhisperModel(model_size, device="cpu", compute_type="int8", download_root=MODELS_DIR)
    else:
        print(f"  Descargando modelo {model_size} ({size_label}) — primera vez, puede tardar varios minutos...", flush=True)

        stop_event = threading.Event()
        watcher = threading.Thread(
            target=_watch_download_progress,
            args=(str(cache_dir), target_mb, stop_event),
            daemon=True,
        )
        watcher.start()

        try:
            model = WhisperModel(model_size, device="cpu", compute_type="int8", download_root=MODELS_DIR)
        finally:
            stop_event.set()
            watcher.join(timeout=3)

        final_mb = _dir_size_mb(cache_dir)
        print(f"  Modelo descargado ({final_mb:.0f} MB). Iniciando transcripcion...", flush=True)

    vad_msg = " + filtro VAD" if vad else ""
    print(f"  Transcribiendo offline{vad_msg}...", flush=True)

    vad_params = {"min_silence_duration_ms": 500} if vad else None
    segments_iter, _ = model.transcribe(
        audio_path, language="es", beam_size=5,
        vad_filter=vad, vad_parameters=vad_params,
    )

    segments = []
    for seg in segments_iter:
        if seg.text.strip():
            segments.append({"start": seg.start, "end": seg.end, "text": seg.text.strip()})

    if not segments:
        raise RuntimeError("El modelo local no devolvio segmentos. Verifica el audio.")

    return segments


# ---------------------------------------------------------------------------
# Motor 3: Gemini API
# ---------------------------------------------------------------------------

def transcribe_with_gemini(audio_path, api_key):
    try:
        import google.generativeai as genai
    except ImportError:
        raise ImportError(
            "google-generativeai no instalado.\n"
            "Ejecuta: pip install google-generativeai"
        )
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
    print(f"  Subiendo audio a Gemini (File API)...", flush=True)
    audio_file = genai.upload_file(audio_path)
    print(f"  Transcribiendo con Gemini 2.5 Flash...", flush=True)
    prompt = (
        "Transcribe el audio completo de forma precisa y literal. "
        "Añade una marca de tiempo [MM:SS] al inicio de cada parrafo (cada ~45 segundos). "
        "Usa el idioma original del audio. "
        "Devuelve unicamente la transcripcion, sin comentarios ni introducciones."
    )
    response = model.generate_content([audio_file, prompt])
    try:
        genai.delete_file(audio_file.name)
    except Exception:
        pass
    return response.text


# ---------------------------------------------------------------------------
# Guardar transcripcion
# ---------------------------------------------------------------------------

def save_transcript(text, info, output_dir, method, output_name=None):
    if output_name:
        filename = output_name if output_name.endswith(".md") else output_name + ".md"
    else:
        filename = safe_filename(info["title"]) + ".md"
    filepath = os.path.join(output_dir, filename)
    upload_date = info.get("upload_date", "")
    if upload_date and len(upload_date) == 8:
        upload_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"
    duration = int(info.get("duration", 0))
    dur_min, dur_sec = divmod(duration, 60)
    dur_hour, dur_min = divmod(dur_min, 60)
    if dur_hour:
        dur_str = f"{dur_hour}h {dur_min:02d}m {dur_sec:02d}s"
    elif dur_min:
        dur_str = f"{dur_min}:{dur_sec:02d}"
    else:
        dur_str = "—"
    video_id   = info.get("id", "")
    source_path = info.get("source_path", "")
    if video_id:
        origen = f"> **URL:** https://www.youtube.com/watch?v={video_id}"
    elif source_path:
        origen = f"> **Archivo:** {Path(source_path).name}"
    else:
        origen = ""
    content = f"""# {info['title']}

> **Fuente:** {info['uploader']}
> **Fecha:** {upload_date or datetime.now().strftime('%Y-%m-%d')}
> **Duracion:** {dur_str}
> **Transcrito:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
> **Metodo:** {method}
{origen}

---

{text}
"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filepath


# ---------------------------------------------------------------------------
# Proceso principal
# ---------------------------------------------------------------------------

def process_source(source, args, output_dir):
    motor       = getattr(args, "motor",       "groq")
    model_size  = getattr(args, "model_size",  "small")
    use_vad     = getattr(args, "vad",          False)
    output_name = getattr(args, "output_name", None)
    local_mode  = is_local_file(source)

    tmpdir_obj = tempfile.TemporaryDirectory()
    tmpdir = tmpdir_obj.name

    try:
        audio_path = None
        info = None
        duration = 0

        if local_mode:
            filepath = Path(source)
            if not filepath.exists():
                raise FileNotFoundError(f"Archivo no encontrado: {source}")
            print(f"\nArchivo local: {filepath.name}", flush=True)
            info = get_local_file_info(filepath)
            duration = info["duration"]
            print(f"   Tamano: {info['file_size_mb']:.1f} MB", flush=True)
            if filepath.suffix.lower() in VIDEO_EXTENSIONS:
                print(f"\nExtrayendo audio del video...", flush=True)
                audio_path = extract_audio_from_video(filepath, tmpdir)
                if not audio_path:
                    raise RuntimeError("Error extrayendo audio. Instala ffmpeg.")
            else:
                audio_path = str(filepath)
        else:
            print(f"\nObteniendo info del video...", flush=True)
            info = get_video_info(source)
            if not info:
                raise RuntimeError(f"No se pudo obtener info: {source}")
            duration = int(info["duration"])
            print(f"   Titulo: {info['title']}", flush=True)
            print(f"   Duracion: {duration // 60}:{duration % 60:02d}", flush=True)
            if motor in ("groq", "gemini") and not args.force_audio:
                print(f"\nBuscando subtitulos ({args.lang})...", flush=True)
                subtitle_text = try_youtube_subtitles(source, args.lang)
                if subtitle_text:
                    method = f"Subtitulos YouTube ({args.lang})"
                    print(f"  Subtitulos encontrados ({len(subtitle_text):,} chars)", flush=True)
                    fp = save_transcript(subtitle_text, info, output_dir, method, output_name=output_name)
                    return fp, method, len(subtitle_text)
                else:
                    print(f"  No hay subtitulos, descargando audio...", flush=True)
            print(f"\nDescargando audio con yt-dlp...", flush=True)
            audio_path = download_audio(source, tmpdir)
            if not audio_path:
                raise RuntimeError("Error descargando audio")
            audio_mb = os.path.getsize(audio_path) / (1024 * 1024)
            print(f"  Audio descargado: {audio_mb:.1f} MB", flush=True)

        if motor == "local":
            print(f"\nMotor: Local Whisper ({model_size})", flush=True)
            segments = transcribe_with_local(audio_path, model_size, vad=use_vad)
            transcript = format_transcript_with_timestamps(segments)
            method = f"Local Whisper ({model_size})"

        elif motor == "gemini":
            if use_vad:
                print(f"  (VAD no disponible en modo Gemini — se omite)", flush=True)
            print(f"\nMotor: Gemini 2.5 Flash", flush=True)
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                raise EnvironmentError("No se encontro GEMINI_API_KEY en .env")
            transcript = transcribe_with_gemini(audio_path, api_key)
            method = "Gemini 2.5 Flash"

        else:  # groq
            if use_vad:
                print(f"  (VAD no disponible en modo Groq — se omite)", flush=True)
            print(f"\nMotor: Groq Whisper (whisper-large-v3)", flush=True)
            api_key = os.environ.get("GROQ_API_KEY")
            if not api_key:
                raise EnvironmentError("No se encontro GROQ_API_KEY en .env")
            groq_audio = audio_path
            if local_mode and Path(audio_path).parent != Path(tmpdir):
                if os.path.getsize(audio_path) / (1024 * 1024) > MAX_CHUNK_MB:
                    tmp_copy = os.path.join(tmpdir, Path(audio_path).name)
                    shutil.copy2(audio_path, tmp_copy)
                    groq_audio = tmp_copy
            chunks = split_audio_with_overlap(groq_audio)
            transcript = transcribe_chunks_groq(chunks, api_key, total_duration_seconds=duration)
            method = "Groq Whisper (whisper-large-v3)"

        print(f"  Transcripcion completa ({len(transcript):,} caracteres)", flush=True)

    finally:
        tmpdir_obj.cleanup()

    filepath_out = save_transcript(transcript, info, output_dir, method, output_name=output_name)
    return filepath_out, method, len(transcript)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="MediaTranscribe v4.2")
    parser.add_argument("sources", nargs="+")
    parser.add_argument("-o", "--output",   default=None)
    parser.add_argument("--output-name",    default=None)
    parser.add_argument("--force-audio",    action="store_true")
    parser.add_argument("--lang",           default="es")
    parser.add_argument("--motor",          default="groq",
                        choices=["groq", "local", "gemini"])
    parser.add_argument("--model-size",     default="small",
                        choices=["tiny", "small", "large-v3-turbo", "large-v3"])
    parser.add_argument("--vad",            action="store_true")
    args = parser.parse_args()
    load_env()
    output_dir = args.output or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "transcripciones")
    os.makedirs(output_dir, exist_ok=True)
    total = len(args.sources)
    for source in args.sources:
        try:
            filepath_out, method, chars = process_source(source, args, output_dir)
            print(f"\n  Guardado en: {filepath_out}", flush=True)
        except Exception as e:
            print(f"\n  Error: {e}", flush=True)
            if total == 1:
                sys.exit(1)


if __name__ == "__main__":
    main()
