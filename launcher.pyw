"""
MediaTranscribe v1.0 — YouTube, Vimeo, audio y video local → Markdown con timestamps
"""
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import subprocess
import threading
import os
import sys
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(SCRIPT_DIR, "yt_transcribe.py")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "transcripciones")

BG_DARK    = "#0f0f1a"
BG_INPUT   = "#12122a"
BG_LOG     = "#0a0a14"
ACCENT     = "#7c5cbf"
ACCENT_HOV = "#9370db"
TITLE_COL  = "#e8a838"
TEXT_MAIN  = "#e0e0e0"
TEXT_DIM   = "#888899"
BTN_SEC    = "#2a2a40"
BTN_SEC_FG = "#aaaacc"

LOG_SUCCESS  = "#00cc88"
LOG_INFO     = "#5599ff"
LOG_PROGRESS = "#e8a838"
LOG_WARNING  = "#ff8844"
LOG_ERROR    = "#ff4455"
LOG_DIM      = "#444466"

AUDIO_TYPES = [
    ("Archivos de audio/video", "*.mp3 *.m4a *.wav *.ogg *.flac *.opus *.aac *.mp4 *.mkv *.avi *.mov *.webm"),
    ("Audio AAC", "*.aac"),
    ("Audio MP3", "*.mp3"),
    ("Audio M4A", "*.m4a"),
    ("Audio WAV", "*.wav"),
    ("Video MP4", "*.mp4"),
    ("Todos los archivos", "*.*"),
]

BTN_W = 16
UTF8_ENV = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}


def safe_filename(title):
    return re.sub(r'[<>:"/\\|?*]', '', title).strip()[:80]


def next_available_name(base_name, output_dir):
    candidate = base_name
    counter = 2
    while os.path.exists(os.path.join(output_dir, candidate + ".md")):
        candidate = f"{base_name} ({counter})"
        counter += 1
    return candidate


def classify_line(line):
    l = line.lower()
    if set(line.strip()) <= {"─", "-", "="}:
        return "dim"
    if any(k in l for k in ("error", "fallo", "falló", "no se pudo", "not found")):
        return "error"
    if any(k in l for k in ("rate limit", "alerta", "esperando", "reintentando", "warning")):
        return "warning"
    if any(k in l for k in (
        "ok (", "completado", "completa", "encontrados", "guardado en",
        "subtitulos encontrados", "audio descargado", "dividido en"
    )):
        return "success"
    if any(k in l for k in (
        "%", "[download]", "[ffmpeg]", "[extractaudio]",
        "parte ", "desde ", "mb)", "tamano", "tamaño",
        "audio grande", "descargado", "renombrado", "reemplazando"
    )):
        return "progress"
    return "info"


def ask_conflict(parent, filename):
    result = {"choice": None}
    dialog = tk.Toplevel(parent)
    dialog.title("Archivo existente")
    dialog.configure(bg=BG_DARK)
    dialog.resizable(False, False)
    dialog.grab_set()
    dialog.update_idletasks()
    pw = parent.winfo_x() + parent.winfo_width() // 2
    ph = parent.winfo_y() + parent.winfo_height() // 2
    dw, dh = 420, 190
    dialog.geometry(f"{dw}x{dh}+{pw - dw//2}+{ph - dh//2}")
    tk.Label(dialog, text="Archivo ya existe",
             font=("Segoe UI", 12, "bold"), fg=TITLE_COL, bg=BG_DARK).pack(pady=(18, 4))
    tk.Label(dialog, text=f"{filename}.md",
             font=("Segoe UI", 9), fg=TEXT_MAIN, bg=BG_DARK).pack()
    tk.Label(dialog, text="¿Qué deseas hacer?",
             font=("Segoe UI", 9), fg=TEXT_DIM, bg=BG_DARK).pack(pady=(6, 10))
    btn_frame = tk.Frame(dialog, bg=BG_DARK)
    btn_frame.pack()
    def choose(val):
        result["choice"] = val
        dialog.destroy()
    tk.Button(btn_frame, text="Reemplazar", font=("Segoe UI", 9, "bold"),
              bg="#8b2020", fg="white", relief="flat", padx=12, pady=6, cursor="hand2",
              command=lambda: choose("replace")).pack(side="left", padx=5)
    tk.Button(btn_frame, text="Guardar como nuevo", font=("Segoe UI", 9, "bold"),
              bg=ACCENT, fg="white", relief="flat", padx=12, pady=6, cursor="hand2",
              command=lambda: choose("rename")).pack(side="left", padx=5)
    tk.Button(btn_frame, text="Omitir", font=("Segoe UI", 9, "bold"),
              bg=BTN_SEC, fg=BTN_SEC_FG, relief="flat", padx=12, pady=6, cursor="hand2",
              command=lambda: choose("skip")).pack(side="left", padx=5)
    dialog.wait_window()
    return result["choice"]


class Launcher:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("MediaTranscribe v1.0")
        self.root.geometry("640x600")
        self.root.resizable(True, True)
        self.root.configure(bg=BG_DARK)
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - 640) // 2
        y = (self.root.winfo_screenheight() - 600) // 2
        self.root.geometry(f"+{x}+{y}")

        tk.Label(self.root, text="MediaTranscribe",
                 font=("Segoe UI", 18, "bold"), fg=TITLE_COL, bg=BG_DARK).pack(pady=(16, 2))
        tk.Label(self.root,
                 text="YouTube · Vimeo · mp3 · aac · m4a · wav · mp4 → Markdown con timestamps",
                 font=("Segoe UI", 9), fg=TEXT_DIM, bg=BG_DARK).pack()
        tk.Frame(self.root, bg=ACCENT, height=1).pack(fill="x", padx=24, pady=(10, 0))

        self.text = tk.Text(
            self.root, font=("Segoe UI", 10),
            bg=BG_INPUT, fg="#ffffff", insertbackground=TITLE_COL,
            relief="flat", bd=0, height=3, wrap="none",
            highlightthickness=1, highlightbackground=ACCENT, highlightcolor=ACCENT,
        )
        self.text.pack(fill="x", padx=24, pady=(10, 0))
        self.text.focus()
        self.text.bind("<Control-Return>", lambda e: self.transcribe())

        btn_frame = tk.Frame(self.root, bg=BG_DARK)
        btn_frame.pack(pady=10)
        self.btn_browse = tk.Button(
            btn_frame, text="Examinar...", font=("Segoe UI", 10, "bold"),
            bg=BTN_SEC, fg=BTN_SEC_FG, relief="flat", width=BTN_W, pady=6,
            cursor="hand2", activebackground=ACCENT, activeforeground="#ffffff",
            command=self.browse_files)
        self.btn_browse.pack(side="left", padx=(0, 8))
        self.btn = tk.Button(
            btn_frame, text="Transcribir", font=("Segoe UI", 10, "bold"),
            bg=ACCENT, fg="white", relief="flat", width=BTN_W, pady=6,
            cursor="hand2", activebackground=ACCENT_HOV, activeforeground="#ffffff",
            command=self.transcribe)
        self.btn.pack(side="left", padx=(0, 8))
        self.force_var = tk.BooleanVar(value=False)
        tk.Checkbutton(btn_frame, text="Forzar Groq", variable=self.force_var,
                       font=("Segoe UI", 9), fg=TEXT_DIM, bg=BG_DARK,
                       selectcolor=BG_INPUT, activebackground=BG_DARK,
                       activeforeground=TEXT_MAIN).pack(side="left")

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Custom.Horizontal.TProgressbar",
                        troughcolor=BG_INPUT, background=ACCENT,
                        darkcolor=ACCENT, lightcolor=ACCENT_HOV,
                        bordercolor=BG_DARK, thickness=5)
        self.progress = ttk.Progressbar(self.root, mode="indeterminate",
                                        style="Custom.Horizontal.TProgressbar")
        self.progress.pack(fill="x", padx=24)

        log_frame = tk.Frame(self.root, bg=BG_DARK)
        log_frame.pack(fill="both", expand=True, padx=24, pady=(8, 0))
        tk.Label(log_frame, text="Proceso", font=("Segoe UI", 8),
                 fg=TEXT_DIM, bg=BG_DARK).pack(anchor="w")
        log_inner = tk.Frame(log_frame, bg=BG_LOG,
                             highlightthickness=1, highlightbackground=ACCENT)
        log_inner.pack(fill="both", expand=True)
        self.log = tk.Text(
            log_inner, font=("Consolas", 9),
            bg=BG_LOG, fg=LOG_INFO, insertbackground=LOG_INFO,
            relief="flat", bd=4, state="disabled", wrap="word", height=12,
        )
        self.log.tag_configure("success",  foreground=LOG_SUCCESS)
        self.log.tag_configure("info",     foreground=LOG_INFO)
        self.log.tag_configure("progress", foreground=LOG_PROGRESS)
        self.log.tag_configure("warning",  foreground=LOG_WARNING)
        self.log.tag_configure("error",    foreground=LOG_ERROR)
        self.log.tag_configure("dim",      foreground=LOG_DIM)
        scrollbar = tk.Scrollbar(log_inner, command=self.log.yview, bg=BG_DARK)
        self.log.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.log.pack(fill="both", expand=True)

        bottom = tk.Frame(self.root, bg=BG_DARK)
        bottom.pack(fill="x", padx=24, pady=(6, 10))
        tk.Button(bottom, text="Abrir carpeta transcripciones",
                  font=("Segoe UI", 10, "bold"), bg=BG_DARK, fg="#d0d0e8",
                  relief="flat", cursor="hand2",
                  activebackground=BG_DARK, activeforeground="#ffffff",
                  command=lambda: os.startfile(OUTPUT_DIR) if os.path.exists(OUTPUT_DIR) else None
                  ).pack(side="left")
        self.status_var = tk.StringVar(value="Listo — pega URL / Ruta de archivo o pulsa Examinar")
        tk.Label(bottom, textvariable=self.status_var,
                 font=("Segoe UI", 9), fg=TEXT_DIM, bg=BG_DARK).pack(side="right")

        try:
            clip = self.root.clipboard_get()
            if "youtu" in clip or "vimeo" in clip:
                self.text.insert("1.0", clip)
        except:
            pass

        self.root.mainloop()

    def log_clear(self):
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")

    def log_append(self, line, tag=None):
        self.log.config(state="normal")
        color_tag = tag if tag else classify_line(line)
        self.log.insert("end", line + "\n", color_tag)
        self.log.see("end")
        self.log.config(state="disabled")

    def browse_files(self):
        files = filedialog.askopenfilenames(
            title="Seleccionar archivos de audio/video", filetypes=AUDIO_TYPES)
        if files:
            current = self.text.get("1.0", "end").strip()
            new_lines = "\n".join(files)
            if current:
                self.text.insert("end", "\n" + new_lines)
            else:
                self.text.insert("1.0", new_lines)
            count = len(files)
            self.status_var.set(
                f"✅ {count} archivo{'s' if count > 1 else ''} añadido{'s' if count > 1 else ''}")

    def check_conflicts(self, sources):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        resolved = []
        for source in sources:
            from pathlib import Path
            path = Path(source)
            if path.exists() and path.is_file():
                base_name = safe_filename(path.stem)
                if os.path.exists(os.path.join(OUTPUT_DIR, base_name + ".md")):
                    choice = ask_conflict(self.root, base_name)
                    if choice == "skip":
                        self.log_append(f"Omitido: {base_name}.md", "warning")
                        continue
                    elif choice == "rename":
                        new_name = next_available_name(base_name, OUTPUT_DIR)
                        self.log_append(f"Renombrado: {base_name}.md → {new_name}.md", "progress")
                        resolved.append((source, new_name))
                    else:
                        self.log_append(f"Reemplazando: {base_name}.md", "warning")
                        resolved.append((source, base_name))
                else:
                    resolved.append((source, None))
            else:
                resolved.append((source, None))
        return resolved

    def transcribe(self):
        raw = self.text.get("1.0", "end").strip()
        sources = [line.strip() for line in raw.splitlines() if line.strip()]
        if not sources:
            messagebox.showwarning("Sin entrada", "Pega una URL, ruta o usa el botón Examinar")
            return
        self.log_clear()
        self.log_append("Comprobando archivos...", "info")
        resolved = self.check_conflicts(sources)
        if not resolved:
            self.log_append("Ninguna fuente para procesar (todas omitidas).", "warning")
            self.status_var.set("Sin archivos para procesar")
            return
        self.btn.config(state="disabled", text="Procesando...")
        self.btn_browse.config(state="disabled")
        total = len(resolved)
        self.status_var.set(f"⏳ Transcribiendo {total} archivo{'s' if total > 1 else ''}...")
        self.progress.start(12)
        self.log_append("─" * 50, "dim")

        def run():
            saved_lines = []
            for source, output_name in resolved:
                cmd = [sys.executable, SCRIPT, source]
                if output_name:
                    cmd += ["--output-name", output_name]
                if self.force_var.get():
                    cmd.append("--force-audio")
                try:
                    process = subprocess.Popen(
                        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, encoding="utf-8", errors="replace",
                        env=UTF8_ENV, cwd=SCRIPT_DIR,
                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                    )
                    for line in process.stdout:
                        line = line.rstrip()
                        if line:
                            self.root.after(0, lambda l=line: self.log_append(l))
                        if "Guardado en:" in line:
                            saved_lines.append(line)
                    process.wait()
                except Exception as e:
                    self.root.after(0, lambda err=str(e): self.log_append(f"ERROR: {err}", "error"))
            if saved_lines:
                self.root.after(0, lambda: self.done(saved_lines))
            else:
                self.root.after(0, lambda: self.error("No se generó ningún archivo. Revisa el log."))

        threading.Thread(target=run, daemon=True).start()

    def done(self, saved_lines):
        self.progress.stop()
        self.btn.config(state="normal", text="Transcribir")
        self.btn_browse.config(state="normal")
        count = len(saved_lines)
        self.log_append("─" * 50, "dim")
        self.log_append(
            f"COMPLETADO — {count} transcripción{'es' if count > 1 else ''} generada{'s' if count > 1 else ''}",
            "success")
        if count == 1:
            filepath = saved_lines[0].split("Guardado en:")[-1].strip()
            self.status_var.set(f"✅ Listo: {os.path.basename(filepath)}")
            self.text.delete("1.0", "end")
            if messagebox.askyesno("Transcripción lista", f"¿Abrir el archivo?\n\n{filepath}"):
                os.startfile(filepath)
        else:
            self.status_var.set(f"✅ {count} transcripciones completadas")
            self.text.delete("1.0", "end")
            names = "\n".join(
                os.path.basename(l.split("Guardado en:")[-1].strip()) for l in saved_lines)
            if messagebox.askyesno(f"{count} listas", f"{names}\n\n¿Abrir carpeta?"):
                os.startfile(OUTPUT_DIR)

    def error(self, msg):
        self.progress.stop()
        self.btn.config(state="normal", text="Transcribir")
        self.btn_browse.config(state="normal")
        self.status_var.set("❌ Error — revisa el log")
        self.log_append(f"ERROR: {msg}", "error")
        messagebox.showerror("Error", msg)


if __name__ == "__main__":
    Launcher()
