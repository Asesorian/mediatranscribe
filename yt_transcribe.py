#!/usr/bin/env python3
"""
YT-Transcribe v3.4: YouTube o archivo local → Transcripción en Markdown con timestamps

Cambios v3.4:
  - download_audio usa Popen streaming → progreso yt-dlp visible en log en tiempo real

Cambios v3.3:
  - Argumento --output-name para gestión de duplicados desde el launcher

Cambios v3.2:
  - CREATE_NO_WINDOW en todas las llamadas ffmpeg/ffprobe → sin pantalla negra

Cambios v3.1:
  - Añadido soporte nativo para .aac en AUDIO_EXTENSIONS
"""

import sys
import os
import json
import re
import argparse
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime

NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

AUDIO_EXTENSIONS = {".mp3", ".m4a", ".wav", ".ogg", ".flac", ".opus", ".weba", ".aac"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".wmv", ".ts", ".mts"}
LOCAL_EXTENSIONS = AUDIO_EXTENSIONS | VIDEO_EXTENSIONS

TRUNCATION_MARKERS = [
    "and so on", "y así sucesivamente", "etcétera, etcétera", "and so forth",
]

MIN_CHARS_PER_MINUTE = 400
OVERLAP_SECONDS = 5
MAX_CHUNK_MB = 24
MIN_CHUNK_DURATION = 60
PARAGRAPH_GAP_SECONDS = 45
DEDUP_TOLERANCE = 0.5

COOKIES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt")


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
                if line.startswith("GROQ_API_KEY=") and not line.startswith("#"):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    os.environ.setdefault("GROQ_API_KEY", key)


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


def get_audio_duration(audio_path):
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path)
    ]
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
        "title": path.stem,
        "duration": duration,
        "uploader": "Archivo local",
        "upload_date": "",
        "id": "",
        "source_path": str(filepath),
        "file_size_mb": file_size_mb,
    }


def extract_audio_from_video(video_path, output_dir):
    output_path = os.path.join(output_dir, "audio.mp3")
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-i", str(video_path),
        "-vn", "-acodec", "libmp3lame", "-q:a", "5",
        output_path, "-y"
    ]
    result = subprocess.run(cmd, capture_output=True, creationflags=NO_WINDOW)
    if result.returncode != 0:
        return None
    return output_path


def get_video_info(url):
    cmd = ["yt-dlp", "--dump-json", "--no-download"] + get_yt_args() + [url]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", creationflags=NO_WINDOW)
    if result.returncode != 0:
        print(f"  Error obteniendo info: {result.stderr[:200]}")
        return None
    info = json.loads(result.stdout)
    return {
        "title": info.get("title", "Sin título"),
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
            cmd = [
                "yt-dlp", sub_flag, "--sub-lang", lang,
                "--sub-format", "vtt", "--skip-download",
            ] + get_yt_args() + ["-o", output, url]
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
        chunk = " ".join(lines[i:i+5])
        paragraphs.append(chunk)
    return "\n\n".join(paragraphs)


def download_audio(url, output_dir):
    """Descargar audio con yt-dlp emitiendo progreso en tiempo real via stdout."""
    output_template = os.path.join(output_dir, "audio.%(ext)s")
    cmd = [
        "yt-dlp", "-x",
        "--audio-format", "mp3",
        "--audio-quality", "5",
        "--newline",          # fuerza una línea por evento de progreso
    ] + get_yt_args() + ["-o", output_template, url]

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=NO_WINDOW,
    )

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


def _extract_chunk(audio_path, start, duration, output_path):
    cmd = [
        "ffmpeg", "-y", "-ss", str(start), "-t", str(duration),
        "-i", audio_path, "-c:a", "libmp3lame", "-q:a", "5", output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, creationflags=NO_WINDOW)
    if result.returncode != 0:
        return False
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        return False
    return True


def split_audio_with_overlap(audio_path, max_size_mb=MAX_CHUNK_MB, overlap_seconds=OVERLAP_SECONDS):
    file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    total_duration = get_audio_duration(audio_path)
    if file_size_mb <= max_size_mb:
        return [(audio_path, 0.0)]
    if total_duration <= 0:
        total_duration = 3600
    print(f"  Audio grande ({file_size_mb:.1f} MB), dividiendo en partes...", flush=True)
    output_dir = os.path.dirname(audio_path)
    chunk_duration = int((max_size_mb / file_size_mb) * total_duration * 0.8)
    chunk_duration = max(chunk_duration, MIN_CHUNK_DURATION)

    def build_chunks(chunk_dur):
        for f in Path(output_dir).glob("chunk_*.mp3"):
            try:
                os.remove(f)
            except OSError:
                pass
        chunks = []
        start = 0.0
        idx = 0
        step = chunk_dur - overlap_seconds
        if step <= 0:
            raise ValueError("overlap >= chunk_duration")
        while start < total_duration:
            chunk_path = os.path.join(output_dir, f"chunk_{idx:03d}.mp3")
            effective_duration = min(chunk_dur, total_duration - start + 1)
            print(f"  Parte {idx+1} [desde {fmt_time(start)}]... ", end="", flush=True)
            if not _extract_chunk(audio_path, start, effective_duration, chunk_path):
                raise RuntimeError(f"No se pudo extraer chunk {idx}")
            chunk_size = os.path.getsize(chunk_path) / (1024 * 1024)
            print(f"ok ({chunk_size:.1f} MB)", flush=True)
            chunks.append((chunk_path, start))
            start += step
            idx += 1
        return chunks

    chunks = build_chunks(chunk_duration)
    print(f"  Dividido en {len(chunks)} partes", flush=True)
    return chunks


def transcribe_with_groq(audio_path, api_key, max_retries=5):
    import time
    from groq import Groq, RateLimitError
    client = Groq(api_key=api_key)
    for attempt in range(max_retries):
        try:
            with open(audio_path, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    file=audio_file,
                    model="whisper-large-v3",
                    language="es",
                    response_format="verbose_json",
                    timestamp_granularities=["segment"],
                )
            if hasattr(transcription, "segments"):
                raw_segments = transcription.segments or []
            elif isinstance(transcription, dict):
                raw_segments = transcription.get("segments", [])
            else:
                raw_segments = []
            segments = []
            for seg in raw_segments:
                if isinstance(seg, dict):
                    start = float(seg.get("start", 0))
                    end = float(seg.get("end", start))
                    text = (seg.get("text") or "").strip()
                else:
                    start = float(getattr(seg, "start", 0))
                    end = float(getattr(seg, "end", start))
                    text = (getattr(seg, "text", "") or "").strip()
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


def transcribe_chunks(chunks_with_offset, api_key, total_duration_seconds=0):
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
                raise RuntimeError("Groq devolvió 0 segments")
            for seg in segments:
                global_start = offset + seg["start"]
                global_end = offset + seg["end"]
                if global_start < max_end_so_far - DEDUP_TOLERANCE:
                    dedup_skipped += 1
                    continue
                all_global_segments.append({"start": global_start, "end": global_end, "text": seg["text"]})
                if global_end > max_end_so_far:
                    max_end_so_far = global_end
            if n > 1:
                print(f"  Parte {i+1}/{n}: ok", flush=True)
        except Exception as e:
            failures.append((i + 1, str(e)))
            print(f"  Parte {i+1}/{n} FALLO: {e}", flush=True)

    all_global_segments.sort(key=lambda s: s["start"])
    transcript = format_transcript_with_timestamps(all_global_segments)
    real_chars = sum(len(s["text"]) for s in all_global_segments)

    stats = {
        "total_chunks": n, "failed_chunks": len(failures), "failures": failures,
        "real_chars": real_chars, "total_segments": len(all_global_segments),
        "dedup_skipped_segments": dedup_skipped, "completeness_warning": False,
    }

    if total_duration_seconds > 0:
        expected_min_chars = (total_duration_seconds / 60) * MIN_CHARS_PER_MINUTE
        if real_chars < expected_min_chars:
            print(f"\n  ALERTA: transcripcion posiblemente incompleta", flush=True)
            stats["completeness_warning"] = True

    return transcript, stats


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
    video_id = info.get("id", "")
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


def process_source(source, args, output_dir):
    local_mode = is_local_file(source)
    output_name = getattr(args, "output_name", None)

    if local_mode:
        filepath = Path(source)
        if not filepath.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {source}")
        print(f"\nArchivo local: {filepath.name}", flush=True)
        info = get_local_file_info(filepath)
        file_size_mb = info["file_size_mb"]
        duration = info["duration"]
        print(f"   Tamano: {file_size_mb:.1f} MB", flush=True)
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError("No se encontro GROQ_API_KEY en .env")
        method = "Groq Whisper (whisper-large-v3)"
        if filepath.suffix.lower() in VIDEO_EXTENSIONS:
            print(f"\nExtrayendo audio del video...", flush=True)
            with tempfile.TemporaryDirectory() as tmpdir:
                audio_path = extract_audio_from_video(filepath, tmpdir)
                if not audio_path:
                    raise RuntimeError("Error extrayendo audio. Instala ffmpeg.")
                chunks = split_audio_with_overlap(audio_path)
                transcript, stats = transcribe_chunks(chunks, api_key, total_duration_seconds=duration)
        else:
            print(f"\nTranscribiendo con Groq Whisper...", flush=True)
            if file_size_mb > MAX_CHUNK_MB:
                with tempfile.TemporaryDirectory() as tmpdir:
                    import shutil
                    tmp_audio = os.path.join(tmpdir, filepath.name)
                    shutil.copy2(str(filepath), tmp_audio)
                    chunks = split_audio_with_overlap(tmp_audio)
                    transcript, stats = transcribe_chunks(chunks, api_key, total_duration_seconds=duration)
            else:
                transcript, stats = transcribe_chunks(
                    [(str(filepath), 0.0)], api_key, total_duration_seconds=duration
                )
        print(f"  Transcripcion completa ({len(transcript):,} caracteres)", flush=True)
    else:
        print(f"\nObteniendo info del video...", flush=True)
        info = get_video_info(source)
        if not info:
            raise RuntimeError(f"No se pudo obtener info: {source}")
        dur = int(info["duration"])
        print(f"   Titulo: {info['title']}", flush=True)
        print(f"   Duracion: {dur // 60}:{dur % 60:02d}", flush=True)
        transcript = None
        method = ""
        if not args.force_audio:
            print(f"\nBuscando subtitulos ({args.lang})...", flush=True)
            transcript = try_youtube_subtitles(source, args.lang)
            if transcript:
                method = f"Subtitulos YouTube ({args.lang})"
                print(f"  Subtitulos encontrados ({len(transcript):,} chars)", flush=True)
            else:
                print(f"  No hay subtitulos, descargando audio...", flush=True)
        if not transcript:
            api_key = os.environ.get("GROQ_API_KEY")
            if not api_key:
                raise EnvironmentError("No se encontro GROQ_API_KEY en .env")
            print(f"\nDescargando audio con yt-dlp...", flush=True)
            with tempfile.TemporaryDirectory() as tmpdir:
                audio_path = download_audio(source, tmpdir)
                if not audio_path:
                    raise RuntimeError("Error descargando audio")
                audio_mb = os.path.getsize(audio_path) / (1024 * 1024)
                print(f"  Audio descargado: {audio_mb:.1f} MB", flush=True)
                print(f"\nTranscribiendo con Groq Whisper...", flush=True)
                chunks = split_audio_with_overlap(audio_path)
                transcript, stats = transcribe_chunks(chunks, api_key, total_duration_seconds=dur)
                method = "Groq Whisper (whisper-large-v3)"
        print(f"  Transcripcion completa ({len(transcript):,} caracteres)", flush=True)

    filepath_out = save_transcript(transcript, info, output_dir, method, output_name=output_name)
    return filepath_out, method, len(transcript)


def main():
    parser = argparse.ArgumentParser(description="YT-Transcribe v3.4")
    parser.add_argument("sources", nargs="+")
    parser.add_argument("-o", "--output", default=None)
    parser.add_argument("--output-name", default=None)
    parser.add_argument("--force-audio", action="store_true")
    parser.add_argument("--lang", default="es")
    args = parser.parse_args()
    load_env()
    output_dir = args.output or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "transcripciones"
    )
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
