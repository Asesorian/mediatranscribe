"""
YT-Transcribe Launcher — GUI mínima para lanzar desde escritorio
Pega una o varias URLs/rutas (una por línea) → clic → transcribe → abre resultado
"""
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import threading
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(SCRIPT_DIR, "yt_transcribe.py")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "transcripciones")


class Launcher:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("YT-Transcribe")
        self.root.geometry("520x340")
        self.root.resizable(False, False)
        self.root.configure(bg="#1a1a2e")

        # Centrar en pantalla
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - 520) // 2
        y = (self.root.winfo_screenheight() - 340) // 2
        self.root.geometry(f"+{x}+{y}")

        # Título
        tk.Label(
            self.root, text="YT-Transcribe", font=("Segoe UI", 16, "bold"),
            fg="#e94560", bg="#1a1a2e"
        ).pack(pady=(15, 5))

        tk.Label(
            self.root, text="YouTube o archivos locales → Transcripción en Markdown",
            font=("Segoe UI", 9), fg="#8888aa", bg="#1a1a2e"
        ).pack()

        # Área de texto multilínea
        frame = tk.Frame(self.root, bg="#1a1a2e")
        frame.pack(pady=10, padx=20, fill="x")

        tk.Label(
            frame, text="URLs o archivos — uno por línea (batch mode):",
            font=("Segoe UI", 10), fg="#eeeeee", bg="#1a1a2e"
        ).pack(anchor="w")

        self.text = tk.Text(
            frame, font=("Segoe UI", 10),
            bg="#16213e", fg="#ffffff", insertbackground="#e94560",
            relief="flat", bd=0, height=5, wrap="none"
        )
        self.text.pack(fill="x", pady=(5, 0))
        self.text.focus()

        # Ctrl+Enter para transcribir
        self.text.bind("<Control-Return>", lambda e: self.transcribe())

        # Botones
        btn_frame = tk.Frame(self.root, bg="#1a1a2e")
        btn_frame.pack(pady=10)

        self.btn = tk.Button(
            btn_frame, text="Transcribir", font=("Segoe UI", 11, "bold"),
            bg="#e94560", fg="white", relief="flat", padx=20, pady=6,
            cursor="hand2", command=self.transcribe
        )
        self.btn.pack(side="left", padx=5)

        self.force_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            btn_frame, text="Forzar Groq (mejor calidad)",
            variable=self.force_var, font=("Segoe UI", 9),
            fg="#8888aa", bg="#1a1a2e", selectcolor="#16213e",
            activebackground="#1a1a2e", activeforeground="#eeeeee"
        ).pack(side="left", padx=10)

        # Status
        self.status_var = tk.StringVar(value="Listo — Ctrl+Enter para transcribir")
        self.status = tk.Label(
            self.root, textvariable=self.status_var, font=("Segoe UI", 9),
            fg="#8888aa", bg="#1a1a2e"
        )
        self.status.pack(pady=(0, 10))

        # Pegar desde clipboard al abrir si tiene URL de YouTube
        try:
            clip = self.root.clipboard_get()
            if "youtu" in clip:
                self.text.insert("1.0", clip)
                self.text.select_range = None
        except:
            pass

        self.root.mainloop()

    def transcribe(self):
        raw = self.text.get("1.0", "end").strip()
        sources = [line.strip() for line in raw.splitlines() if line.strip()]

        if not sources:
            messagebox.showwarning("Sin entrada", "Pega al menos una URL o ruta de archivo")
            return

        self.btn.config(state="disabled", text="Transcribiendo...")
        total = len(sources)
        label = f"{total} fuente{'s' if total > 1 else ''}"
        self.status_var.set(f"⏳ Procesando {label}...")

        def run():
            cmd = [sys.executable, SCRIPT] + sources
            if self.force_var.get():
                cmd.append("--force-audio")

            try:
                result = subprocess.run(
                    cmd, capture_output=True, text=True,
                    encoding="utf-8", cwd=SCRIPT_DIR
                )

                output = result.stdout

                # Buscar archivos guardados en la salida
                saved_lines = [l for l in output.split("\n") if "Guardado en:" in l]

                if result.returncode == 0 and saved_lines:
                    self.root.after(0, lambda: self.done(saved_lines))
                else:
                    error = result.stderr or result.stdout or "Error desconocido"
                    self.root.after(0, lambda: self.error(error[:400]))

            except Exception as e:
                self.root.after(0, lambda: self.error(str(e)))

        threading.Thread(target=run, daemon=True).start()

    def done(self, saved_lines):
        self.btn.config(state="normal", text="Transcribir")
        count = len(saved_lines)

        if count == 1:
            filepath = saved_lines[0].split("Guardado en:")[-1].strip()
            self.status_var.set(f"✅ {os.path.basename(filepath)}")
            self.text.delete("1.0", "end")
            if messagebox.askyesno("Transcripción lista", f"¿Abrir el archivo?\n\n{filepath}"):
                os.startfile(filepath)
        else:
            self.status_var.set(f"✅ {count} transcripciones completadas")
            self.text.delete("1.0", "end")
            names = "\n".join(
                os.path.basename(l.split("Guardado en:")[-1].strip())
                for l in saved_lines
            )
            if messagebox.askyesno(
                f"{count} transcripciones listas",
                f"Archivos guardados:\n\n{names}\n\n¿Abrir la carpeta?"
            ):
                os.startfile(OUTPUT_DIR)

    def error(self, msg):
        self.btn.config(state="normal", text="Transcribir")
        self.status_var.set("❌ Error")
        messagebox.showerror("Error", msg)


if __name__ == "__main__":
    Launcher()
