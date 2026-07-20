import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox
import logging
from queue import Queue

from main import OrganizerContext, run_once, run_undo


class QueueLogHandler(logging.Handler):
    """Handler care pune log-uri intr-o coada, pentru a fi afisate in GUI fara threading issues."""
    def __init__(self, queue):
        super().__init__()
        self.queue = queue

    def emit(self, record):
        try:
            msg = self.format(record)
            self.queue.put(msg)
        except Exception:
            self.handleError(record)


class OrganizerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestiune Download-uri")
        self.root.geometry("700x600")

        self.config_path = "config/config.yaml"
        self.ctx = None
        self.log_queue = Queue()

        # titlu
        title = tk.Label(root, text="📁 Organizator Download-uri", font=("Arial", 16, "bold"))
        title.pack(pady=10)

        # butoane de actiune
        button_frame = tk.Frame(root)
        button_frame.pack(pady=10)

        self.run_btn = tk.Button(button_frame, text="▶️ Rulare normala", command=self._run_organize, bg="green", fg="white", padx=10, pady=5)
        self.run_btn.pack(side=tk.LEFT, padx=5)

        self.dry_run_btn = tk.Button(button_frame, text="🧪 Dry-run", command=self._run_dry_run, bg="blue", fg="white", padx=10, pady=5)
        self.dry_run_btn.pack(side=tk.LEFT, padx=5)

        self.undo_btn = tk.Button(button_frame, text="↩️ Undo", command=self._run_undo, bg="orange", fg="white", padx=10, pady=5)
        self.undo_btn.pack(side=tk.LEFT, padx=5)

        # zona de log
        log_label = tk.Label(root, text="Log:", font=("Arial", 10, "bold"))
        log_label.pack(anchor=tk.W, padx=10, pady=(10, 0))

        self.log_text = scrolledtext.ScrolledText(root, height=20, width=80, bg="black", fg="lime", font=("Courier", 9))
        self.log_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # incepe polling pentru log-uri
        self._poll_log_queue()

    def _attach_gui_handler(self):
        """Ataseaza QueueLogHandler la logger-ul aplicatiei."""
        if self.ctx and self.ctx.logger:
            handler = QueueLogHandler(self.log_queue)
            handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
            self.ctx.logger.addHandler(handler)

    def _poll_log_queue(self):
        """Verifica periodic daca sunt log-uri noi in coada."""
        while True:
            try:
                msg = self.log_queue.get_nowait()
                self.log_text.insert(tk.END, msg + "\n")
                self.log_text.see(tk.END)  # scroll to bottom
            except:
                break
        self.root.after(100, self._poll_log_queue)

    def _run_in_thread(self, func):
        """Ruleaza o functie pe un thread separat (ca GUI-ul sa nu se blocheze)."""
        thread = threading.Thread(target=func, daemon=True)
        thread.start()

    def _run_organize(self):
        """Incepe rularea normala."""
        self.log_text.delete(1.0, tk.END)
        self.log_text.insert(tk.END, "Incepe organizare... (rulare normala)\n")
        self._run_in_thread(self._do_run_organize)

    def _do_run_organize(self):
        try:
            self.ctx = OrganizerContext(self.config_path, dry_run=False)
            self._attach_gui_handler()
            run_once(self.ctx)
            self.log_text.insert(tk.END, "\n✅ Organizare finalizata!\n")
        except Exception as e:
            self.log_text.insert(tk.END, f"\n❌ Eroare: {e}\n")

    def _run_dry_run(self):
        """Incepe rularea in modul dry-run (simulare)."""
        self.log_text.delete(1.0, tk.END)
        self.log_text.insert(tk.END, "Incepe simulare (dry-run)...\n")
        self._run_in_thread(self._do_dry_run)

    def _do_dry_run(self):
        try:
            self.ctx = OrganizerContext(self.config_path, dry_run=True)
            self._attach_gui_handler()
            run_once(self.ctx)
            self.log_text.insert(tk.END, "\n✅ Simulare finalizata!\n")
        except Exception as e:
            self.log_text.insert(tk.END, f"\n❌ Eroare: {e}\n")

    def _run_undo(self):
        """Anuleaza ultima rulare."""
        self.log_text.delete(1.0, tk.END)
        self.log_text.insert(tk.END, "Se anuleaza ultima rulare...\n")
        self._run_in_thread(self._do_undo)

    def _do_undo(self):
        try:
            self.ctx = OrganizerContext(self.config_path)
            self._attach_gui_handler()
            run_undo(self.ctx)
            self.log_text.insert(tk.END, "\nUndo finalizat!\n")
        except Exception as e:
            self.log_text.insert(tk.END, f"\nEroare: {e}\n")


def main():
    root = tk.Tk()
    app = OrganizerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
