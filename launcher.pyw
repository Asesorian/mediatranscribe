"""
MediaTranscribe v2.3 — YouTube, Vimeo, audio y video local → Markdown con timestamps
"""
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import subprocess
import threading
import os
import sys
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT     = os.path.join(SCRIPT_DIR, "mediatranscribe.py")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "transcripciones")
ENV_PATH   = os.path.join(SCRIPT_DIR, ".env")
NO_WINDOW  = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

# ── Colores ───────────────────────────────────────────────────────────────
BG_DARK    = "#0f0f1a"
BG_INPUT   = "#12122a"
BG_LOG     = "#0a0a14"
ACCENT     = "#7c5cbf"
ACCENT_HOV = "#9370db"
TITLE_COL  = "#e8a838"
TEXT_MAIN  = "#e0e0e0"
TEXT_DIM   = "#888899"
TEXT_HINT  = "#555568"
BTN_SEC    = "#2a2a40"
BTN_SEC_FG = "#aaaacc"

LOG_SUCCESS  = "#00cc88"
LOG_INFO     = "#5599ff"
LOG_PROGRESS = "#e8a838"
LOG_WARNING  = "#ff8844"
LOG_ERROR    = "#ff4455"
LOG_DIM      = "#444466"

# ── Fuentes (cambiar aqui para ajuste global de tamano) ───────────────────
F_TITLE    = ("Segoe UI", 20, "bold")
F_SUBTITLE = ("Segoe UI", 11)
F_BODY     = ("Segoe UI", 11)
F_BODY_B   = ("Segoe UI", 11, "bold")
F_BTN      = ("Segoe UI", 11, "bold")
F_HINT     = ("Segoe UI", 10)
F_LOG      = ("Consolas", 10)
F_ENTRY    = ("Segoe UI", 11)
F_KEY      = ("Consolas", 10)

# ── Datos UI ──────────────────────────────────────────────────────────────
AUDIO_TYPES = [
    ("Archivos de audio/video", "*.mp3 *.m4a *.wav *.ogg *.flac *.opus *.aac *.mp4 *.mkv *.avi *.mov *.webm"),
    ("Audio AAC", "*.aac"),
    ("Audio MP3", "*.mp3"),
    ("Audio M4A", "*.m4a"),
    ("Audio WAV", "*.wav"),
    ("Video MP4", "*.mp4"),
    ("Todos los archivos", "*.*"),
]

MOTORES   = ["Groq API", "Gemini API", "Local Whisper"]
MOTOR_MAP = {"Groq API": "groq", "Gemini API": "gemini", "Local Whisper": "local"}
MOTOR_KEY = {"Groq API": "GROQ_API_KEY", "Gemini API": "GEMINI_API_KEY"}

MODELOS    = ["tiny", "small", "large-v3-turbo", "large-v3"]
MODEL_INFO = {
    "tiny":           "39 MB - rapido, calidad basica",
    "small":          "244 MB - equilibrado (recomendado)",
    "large-v3-turbo": "809 MB - alta calidad",
    "large-v3":       "1.5 GB - maxima calidad",
}

BTN_W    = 16
UTF8_ENV = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}


# ---------------------------------------------------------------------------
# Helpers .env
# ---------------------------------------------------------------------------

def read_env_key(key_name):
    if not os.path.exists(ENV_PATH):
        return ""
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith(f"{key_name}=") and not line.startswith("#"):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def write_env_key(key_name, value):
    lines = []
    found = False
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith(f"{key_name}="):
                    lines.append(f"{key_name}={value}\n")
                    found = True
                else:
                    lines.append(line)
    if not found:
        lines.append(f"{key_name}={value}\n")
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)


# ---------------------------------------------------------------------------
# Helpers UI
# ---------------------------------------------------------------------------

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
    if any(k in l for k in ("error", "fallo", "no se pudo", "not found")):
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
        "parte ", "desde ", "mb)", "tamano",
        "audio grande", "descargado", "renombrado", "reemplazando"
    )):
        return "progress"
    return "info"


def bind_checkbox_color(cb, var, color_on=LOG_SUCCESS, color_off=TEXT_DIM):
    def _update(*_):
        cb.config(fg=color_on if var.get() else color_off)
    var.trace("w", _update)


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
    dw, dh = 460, 200
    dialog.geometry(f"{dw}x{dh}+{pw - dw//2}+{ph - dh//2}")
    tk.Label(dialog, text="Archivo ya existe",
             font=F_BODY_B, fg=TITLE_COL, bg=BG_DARK).pack(pady=(18, 4))
    tk.Label(dialog, text=f"{filename}.md",
             font=F_BODY, fg=TEXT_MAIN, bg=BG_DARK).pack()
    tk.Label(dialog, text="Que deseas hacer?",
             font=F_BODY, fg=TEXT_DIM, bg=BG_DARK).pack(pady=(6, 10))
    btn_frame = tk.Frame(dialog, bg=BG_DARK)
    btn_frame.pack()
    def choose(val):
        result["choice"] = val
        dialog.destroy()
    tk.Button(btn_frame, text="Reemplazar", font=F_BTN,
              bg="#8b2020", fg="white", relief="flat", padx=12, pady=6, cursor="hand2",
              command=lambda: choose("replace")).pack(side="left", padx=5)
    tk.Button(btn_frame, text="Guardar como nuevo", font=F_BTN,
              bg=ACCENT, fg="white", relief="flat", padx=12, pady=6, cursor="hand2",
              command=lambda: choose("rename")).pack(side="left", padx=5)
    tk.Button(btn_frame, text="Omitir", font=F_BTN,
              bg=BTN_SEC, fg=BTN_SEC_FG, relief="flat", padx=12, pady=6, cursor="hand2",
              command=lambda: choose("skip")).pack(side="left", padx=5)
    dialog.wait_window()
    return result["choice"]


# ---------------------------------------------------------------------------
# App principal
# ---------------------------------------------------------------------------

class Launcher:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("MediaTranscribe v2.3")
        self.root.geometry("720x780")
        self.root.resizable(True, True)
        self.root.configure(bg=BG_DARK)
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth()  - 720) // 2
        y = (self.root.winfo_screenheight() - 780) // 2
        self.root.geometry(f"+{x}+{y}")

        # ── Titulo ────────────────────────────────────────────────────────
        tk.Label(self.root, text="MediaTranscribe",
                 font=F_TITLE, fg=TITLE_COL, bg=BG_DARK).pack(pady=(16, 2))
        tk.Label(self.root,
                 text="YouTube · Vimeo · mp3 · aac · m4a · wav · mp4  →  Markdown con timestamps",
                 font=F_SUBTITLE, fg=TEXT_DIM, bg=BG_DARK).pack()
        tk.Frame(self.root, bg=ACCENT, height=1).pack(fill="x", padx=24, pady=(10, 0))

        # ── Entrada URL / ruta ────────────────────────────────────────────
        self.text = tk.Text(
            self.root, font=F_ENTRY,
            bg=BG_INPUT, fg="#ffffff", insertbackground=TITLE_COL,
            relief="flat", bd=0, height=3, wrap="none",
            highlightthickness=1, highlightbackground=ACCENT, highlightcolor=ACCENT,
        )
        self.text.pack(fill="x", padx=24, pady=(10, 0))
        self.text.focus()
        self.text.bind("<Control-Return>", lambda e: self.transcribe())

        # ── Fila motor + modelo ───────────────────────────────────────────
        motor_row = tk.Frame(self.root, bg=BG_DARK)
        motor_row.pack(fill="x", padx=24, pady=(12, 0))

        tk.Label(motor_row, text="Motor:", font=F_BODY_B,
                 fg=TEXT_DIM, bg=BG_DARK).pack(side="left")

        self.motor_var = tk.StringVar(value="Groq API")
        motor_menu = tk.OptionMenu(motor_row, self.motor_var, *MOTORES)
        motor_menu.config(
            bg=BG_INPUT, fg=TEXT_MAIN,
            activebackground=ACCENT, activeforeground="white",
            relief="flat", font=F_BODY,
            highlightthickness=1, highlightbackground=ACCENT,
            width=14, cursor="hand2",
        )
        motor_menu["menu"].config(bg=BG_INPUT, fg=TEXT_MAIN, font=F_BODY,
                                  activebackground=ACCENT, activeforeground="white")
        motor_menu.pack(side="left", padx=(8, 0))

        # Modelo + estado faster-whisper (solo Local Whisper)
        self.model_container = tk.Frame(motor_row, bg=BG_DARK)

        tk.Label(self.model_container, text="Modelo:", font=F_BODY,
                 fg=TEXT_DIM, bg=BG_DARK).pack(side="left", padx=(18, 0))

        self.model_var = tk.StringVar(value="small")
        model_menu = tk.OptionMenu(self.model_container, self.model_var, *MODELOS)
        model_menu.config(
            bg=BG_INPUT, fg=TEXT_MAIN,
            activebackground=ACCENT, activeforeground="white",
            relief="flat", font=F_BODY,
            highlightthickness=1, highlightbackground=ACCENT,
            width=16, cursor="hand2",
        )
        model_menu["menu"].config(bg=BG_INPUT, fg=TEXT_MAIN, font=F_BODY,
                                  activebackground=ACCENT, activeforeground="white")
        model_menu.pack(side="left", padx=(8, 0))

        self.model_info_label = tk.Label(
            self.model_container, text=MODEL_INFO["small"],
            font=F_HINT, fg=TEXT_HINT, bg=BG_DARK)
        self.model_info_label.pack(side="left", padx=(10, 0))

        # Label estado faster-whisper (aparece junto al modelo)
        self.fw_status_label = tk.Label(
            self.model_container, text="",
            font=F_HINT, fg=LOG_SUCCESS, bg=BG_DARK)
        self.fw_status_label.pack(side="left", padx=(12, 0))

        def on_model_change(*_):
            self.model_info_label.config(text=MODEL_INFO.get(self.model_var.get(), ""))
        self.model_var.trace("w", on_model_change)

        # ── Fila API Key (Groq / Gemini) ──────────────────────────────────
        self.key_frame = tk.Frame(self.root, bg=BG_DARK)

        key_inner = tk.Frame(self.key_frame, bg=BG_DARK)
        key_inner.pack(fill="x")

        self.key_label = tk.Label(
            key_inner, text="GROQ_API_KEY:",
            font=F_BODY, fg=TEXT_DIM, bg=BG_DARK, width=16, anchor="w")
        self.key_label.pack(side="left")

        self.key_var = tk.StringVar()
        self.key_entry = tk.Entry(
            key_inner, textvariable=self.key_var, show="•",
            width=36, font=F_KEY,
            bg=BG_INPUT, fg=TEXT_MAIN, insertbackground=TITLE_COL,
            relief="flat",
            highlightthickness=1, highlightbackground=ACCENT, highlightcolor=ACCENT,
        )
        self.key_entry.pack(side="left", padx=(8, 0), ipady=4)

        self.key_save_btn = tk.Button(
            key_inner, text="Guardar",
            font=F_BTN, bg=BTN_SEC, fg=BTN_SEC_FG,
            relief="flat", padx=12, pady=2,
            cursor="hand2", activebackground=ACCENT, activeforeground="white",
            command=self._save_api_key,
        )
        self.key_save_btn.pack(side="left", padx=(10, 0))

        self.key_status = tk.Label(
            key_inner, text="", font=F_HINT,
            fg=LOG_SUCCESS, bg=BG_DARK)
        self.key_status.pack(side="left", padx=(10, 0))

        # ── Advertencia Local Whisper ─────────────────────────────────────
        self.local_warning = tk.Frame(self.root, bg="#1a1200")
        tk.Label(self.local_warning, text="⚠",
                 font=("Segoe UI", 13), fg=LOG_WARNING, bg="#1a1200").pack(
                 side="left", padx=(12, 4), pady=6)
        tk.Label(self.local_warning,
                 text="Modo lento — procesamiento en CPU sin GPU.  "
                      "Un audio de 1h puede tardar 10–30 min según el modelo.\n"
                      "Para uso habitual recomendamos Groq API (rápido, gratis) o Gemini API.",
                 justify="left", font=F_HINT, fg=LOG_WARNING, bg="#1a1200",
                 wraplength=560).pack(side="left", pady=6, padx=(0, 12))

        # ── Callback motor ────────────────────────────────────────────────
        def on_motor_change(*_):
            motor = self.motor_var.get()
            if motor == "Local Whisper":
                self.model_container.pack(side="left")
                self.key_frame.pack_forget()
                self.local_warning.pack(fill="x", padx=24, pady=(4, 0))
                # Comprobar / instalar faster-whisper
                self._check_and_install_fw()
            else:
                self.model_container.pack_forget()
                self.local_warning.pack_forget()
                self._load_key_for_motor(motor)
                self.key_frame.pack(fill="x", padx=24, pady=(8, 0))

        self.motor_var.trace("w", on_motor_change)

        # Arranque con Groq API
        self._load_key_for_motor("Groq API")
        self.key_frame.pack(fill="x", padx=24, pady=(8, 0))

        # ── Checkbox Forzar audio ─────────────────────────────────────────
        force_row = tk.Frame(self.root, bg=BG_DARK)
        force_row.pack(fill="x", padx=24, pady=(10, 0))

        self.force_var = tk.BooleanVar(value=False)
        self.force_cb = tk.Checkbutton(
            force_row,
            text="Forzar y descargar audio  (Si los subtitulos son de baja calidad)",
            variable=self.force_var,
            font=F_BODY, fg=TEXT_DIM, bg=BG_DARK,
            selectcolor=BG_INPUT, activebackground=BG_DARK,
            activeforeground=LOG_SUCCESS, cursor="hand2",
        )
        self.force_cb.pack(side="left")
        bind_checkbox_color(self.force_cb, self.force_var)

        # ── Checkbox VAD + aviso ──────────────────────────────────────────
        vad_outer = tk.Frame(self.root, bg=BG_DARK)
        vad_outer.pack(fill="x", padx=24, pady=(6, 0))

        self.vad_var = tk.BooleanVar(value=False)
        self.vad_cb = tk.Checkbutton(
            vad_outer,
            text="Filtrar silencio  (Reduce tiempo en audios con pausas largas)",
            variable=self.vad_var,
            font=F_BODY, fg=TEXT_DIM, bg=BG_DARK,
            selectcolor=BG_INPUT, activebackground=BG_DARK,
            activeforeground=LOG_SUCCESS, cursor="hand2",
        )
        self.vad_cb.pack(anchor="w")
        bind_checkbox_color(self.vad_cb, self.vad_var)

        tk.Label(
            vad_outer,
            text="     Si hay musica de fondo intensa, revisa que no se pierda voz",
            font=F_HINT, fg=TEXT_HINT, bg=BG_DARK,
        ).pack(anchor="w")

        # ── Botones ───────────────────────────────────────────────────────
        btn_frame = tk.Frame(self.root, bg=BG_DARK)
        btn_frame.pack(pady=(12, 0))

        self.btn_browse = tk.Button(
            btn_frame, text="Examinar...", font=F_BTN,
            bg=BTN_SEC, fg=BTN_SEC_FG, relief="flat", width=BTN_W, pady=8,
            cursor="hand2", activebackground=ACCENT, activeforeground="#ffffff",
            command=self.browse_files)
        self.btn_browse.pack(side="left", padx=(0, 10))

        self.btn = tk.Button(
            btn_frame, text="Transcribir", font=F_BTN,
            bg=ACCENT, fg="white", relief="flat", width=BTN_W, pady=8,
            cursor="hand2", activebackground=ACCENT_HOV, activeforeground="#ffffff",
            command=self.transcribe)
        self.btn.pack(side="left")

        # ── Progreso ──────────────────────────────────────────────────────
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Custom.Horizontal.TProgressbar",
                        troughcolor=BG_INPUT, background=ACCENT,
                        darkcolor=ACCENT, lightcolor=ACCENT_HOV,
                        bordercolor=BG_DARK, thickness=6)
        self.progress = ttk.Progressbar(self.root, mode="indeterminate",
                                        style="Custom.Horizontal.TProgressbar")
        self.progress.pack(fill="x", padx=24, pady=(10, 0))

        # ── Log ───────────────────────────────────────────────────────────
        log_frame = tk.Frame(self.root, bg=BG_DARK)
        log_frame.pack(fill="both", expand=True, padx=24, pady=(8, 0))
        tk.Label(log_frame, text="Proceso", font=F_HINT,
                 fg=TEXT_DIM, bg=BG_DARK).pack(anchor="w")
        log_inner = tk.Frame(log_frame, bg=BG_LOG,
                             highlightthickness=1, highlightbackground=ACCENT)
        log_inner.pack(fill="both", expand=True)
        self.log = tk.Text(
            log_inner, font=F_LOG,
            bg=BG_LOG, fg=LOG_INFO, insertbackground=LOG_INFO,
            relief="flat", bd=4, state="disabled", wrap="word", height=10,
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

        # ── Barra inferior ────────────────────────────────────────────────
        bottom = tk.Frame(self.root, bg=BG_DARK)
        bottom.pack(fill="x", padx=24, pady=(8, 10))
        tk.Button(bottom, text="Abrir carpeta transcripciones",
                  font=F_BTN, bg=BG_DARK, fg="#d0d0e8",
                  relief="flat", cursor="hand2",
                  activebackground=BG_DARK, activeforeground="#ffffff",
                  command=lambda: os.startfile(OUTPUT_DIR) if os.path.exists(OUTPUT_DIR) else None
                  ).pack(side="left")
        self.status_var = tk.StringVar(value="Listo — pega URL / ruta de archivo o pulsa Examinar")
        tk.Label(bottom, textvariable=self.status_var,
                 font=F_HINT, fg=TEXT_DIM, bg=BG_DARK).pack(side="right")

        try:
            clip = self.root.clipboard_get()
            if "youtu" in clip or "vimeo" in clip:
                self.text.insert("1.0", clip)
        except Exception:
            pass

        self.root.mainloop()

    # ── faster-whisper: comprobar e instalar ──────────────────────────────

    def _check_and_install_fw(self):
        """
        Comprueba si faster-whisper está instalado.
        Si no lo está, lo instala en background (una sola vez).
        Muestra estado inline junto al selector de modelo.
        """
        try:
            import faster_whisper  # noqa: F401
            self.fw_status_label.config(text="faster-whisper listo", fg=LOG_SUCCESS)
            return
        except ImportError:
            pass

        # No instalado → instalar en background
        self.fw_status_label.config(text="Instalando faster-whisper...", fg=LOG_WARNING)
        self.btn.config(state="disabled", text="Instalando...")

        def do_install():
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "faster-whisper"],
                    capture_output=True, text=True,
                    creationflags=NO_WINDOW,
                )
                if result.returncode == 0:
                    self.root.after(0, self._on_fw_installed_ok)
                else:
                    err = result.stderr[-200:] if result.stderr else "error desconocido"
                    self.root.after(0, lambda: self._on_fw_installed_err(err))
            except Exception as e:
                self.root.after(0, lambda: self._on_fw_installed_err(str(e)))

        threading.Thread(target=do_install, daemon=True).start()

    def _on_fw_installed_ok(self):
        self.fw_status_label.config(text="faster-whisper instalado", fg=LOG_SUCCESS)
        self.btn.config(state="normal", text="Transcribir")
        self.log_append("faster-whisper instalado correctamente", "success")

    def _on_fw_installed_err(self, err):
        self.fw_status_label.config(text="Error al instalar", fg=LOG_ERROR)
        self.btn.config(state="normal", text="Transcribir")
        self.log_append(f"Error instalando faster-whisper: {err}", "error")
        self.log_append("Instala manualmente: pip install faster-whisper", "warning")

    # ── API Key ───────────────────────────────────────────────────────────

    def _load_key_for_motor(self, motor):
        key_name = MOTOR_KEY.get(motor, "")
        self.current_key_name = key_name
        self.key_label.config(text=f"{key_name}:")
        existing = read_env_key(key_name)
        if existing:
            self.key_var.set(existing)
            self.key_status.config(text="Configurada", fg=LOG_SUCCESS)
        else:
            self.key_var.set("")
            self.key_status.config(
                text="No configurada — pega tu clave y guarda", fg=LOG_WARNING)

    def _save_api_key(self):
        key_name = getattr(self, "current_key_name", None)
        if not key_name:
            return
        value = self.key_var.get().strip()
        if not value:
            self.key_status.config(text="La clave esta vacia", fg=LOG_ERROR)
            return
        write_env_key(key_name, value)
        self.key_status.config(text="Guardada", fg=LOG_SUCCESS)

    # ── Log ───────────────────────────────────────────────────────────────

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

    # ── Examinar ─────────────────────────────────────────────────────────

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
                f"OK {count} archivo{'s' if count > 1 else ''} anadido{'s' if count > 1 else ''}")

    # ── Conflictos ────────────────────────────────────────────────────────

    def check_conflicts(self, sources):
        from pathlib import Path as P
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        resolved = []
        for source in sources:
            path = P(source)
            if path.exists() and path.is_file():
                base_name = safe_filename(path.stem)
                if os.path.exists(os.path.join(OUTPUT_DIR, base_name + ".md")):
                    choice = ask_conflict(self.root, base_name)
                    if choice == "skip":
                        self.log_append(f"Omitido: {base_name}.md", "warning")
                        continue
                    elif choice == "rename":
                        new_name = next_available_name(base_name, OUTPUT_DIR)
                        self.log_append(f"Renombrado: {base_name}.md a {new_name}.md", "progress")
                        resolved.append((source, new_name))
                    else:
                        self.log_append(f"Reemplazando: {base_name}.md", "warning")
                        resolved.append((source, base_name))
                else:
                    resolved.append((source, None))
            else:
                resolved.append((source, None))
        return resolved

    # ── Transcribir ───────────────────────────────────────────────────────

    def transcribe(self):
        raw = self.text.get("1.0", "end").strip()
        sources = [line.strip() for line in raw.splitlines() if line.strip()]
        if not sources:
            messagebox.showwarning("Sin entrada", "Pega una URL, ruta o usa el boton Examinar")
            return

        motor_key  = MOTOR_MAP.get(self.motor_var.get(), "groq")
        model_size = self.model_var.get()

        if motor_key in ("groq", "gemini"):
            env_key_name = MOTOR_KEY.get(self.motor_var.get(), "")
            if not read_env_key(env_key_name):
                messagebox.showerror(
                    "API Key requerida",
                    f"No hay {env_key_name} guardada.\n\nPega tu clave en el campo y pulsa Guardar.")
                return

        self.log_clear()
        self.log_append("Comprobando archivos...", "info")
        resolved = self.check_conflicts(sources)
        if not resolved:
            self.log_append("Ninguna fuente para procesar (todas omitidas).", "warning")
            self.status_var.set("Sin archivos para procesar")
            return

        motor_label = self.motor_var.get()
        if motor_key == "local":
            motor_label += f" - {model_size}"
        self.log_append(f"Motor: {motor_label}", "info")

        self.btn.config(state="disabled", text="Procesando...")
        self.btn_browse.config(state="disabled")
        total = len(resolved)
        self.status_var.set(f"Transcribiendo {total} archivo{'s' if total > 1 else ''}...")
        self.progress.start(12)
        self.log_append("-" * 50, "dim")

        def run():
            saved_lines = []
            for source, output_name in resolved:
                cmd = [sys.executable, SCRIPT, source,
                       "--motor", motor_key,
                       "--model-size", model_size]
                if output_name:
                    cmd += ["--output-name", output_name]
                if self.force_var.get():
                    cmd.append("--force-audio")
                if self.vad_var.get():
                    cmd.append("--vad")
                try:
                    process = subprocess.Popen(
                        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, encoding="utf-8", errors="replace",
                        env=UTF8_ENV, cwd=SCRIPT_DIR,
                        creationflags=NO_WINDOW,
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
                self.root.after(0, lambda: self.error("No se genero ningun archivo. Revisa el log."))

        threading.Thread(target=run, daemon=True).start()

    # ── Fin ───────────────────────────────────────────────────────────────

    def done(self, saved_lines):
        self.progress.stop()
        self.btn.config(state="normal", text="Transcribir")
        self.btn_browse.config(state="normal")
        count = len(saved_lines)
        self.log_append("-" * 50, "dim")
        self.log_append(
            f"COMPLETADO - {count} transcripcion{'es' if count > 1 else ''} generada{'s' if count > 1 else ''}",
            "success")
        if count == 1:
            filepath = saved_lines[0].split("Guardado en:")[-1].strip()
            self.status_var.set(f"Listo: {os.path.basename(filepath)}")
            self.text.delete("1.0", "end")
            if messagebox.askyesno("Transcripcion lista", f"Abrir el archivo?\n\n{filepath}"):
                os.startfile(filepath)
        else:
            self.status_var.set(f"{count} transcripciones completadas")
            self.text.delete("1.0", "end")
            names = "\n".join(
                os.path.basename(l.split("Guardado en:")[-1].strip()) for l in saved_lines)
            if messagebox.askyesno(f"{count} listas", f"{names}\n\nAbrir carpeta?"):
                os.startfile(OUTPUT_DIR)

    def error(self, msg):
        self.progress.stop()
        self.btn.config(state="normal", text="Transcribir")
        self.btn_browse.config(state="normal")
        self.status_var.set("Error - revisa el log")
        self.log_append(f"ERROR: {msg}", "error")
        messagebox.showerror("Error", msg)


if __name__ == "__main__":
    Launcher()
