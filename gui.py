import threading
import tkinter as tk
from tkinter import scrolledtext
import logging
from queue import Queue

from main import OrganizerContext, run_once, run_undo


class QueueLogHandler(logging.Handler):
    """Handler care trimite log-uri în coadă pentru afișare în GUI"""

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
    """Interfață grafică pentru organizator"""

    def __init__(self, root):
        self.root = root
        self.root.title("Organizare Download-uri")
        self.root.geometry("700x600")
        
        self.config_path = "config/config.yaml"
        self.ctx = None
        self.log_queue = Queue()
        
        # ================================================================
        # INTERFAȚĂ - Titlu și butoane
        # ================================================================
        
        # Titlu
        title = tk.Label(root, text="Organizare Download-uri", font=("Arial", 16, "bold"))
        title.pack(pady=10)
        
        # Butoane de acțiune
        button_frame = tk.Frame(root)
        button_frame.pack(pady=10)
        
        self.run_btn = tk.Button(
            button_frame, text="Rulare", command=self._run_organize,
            bg="green", fg="white", padx=10, pady=5
        )
        self.run_btn.pack(side=tk.LEFT, padx=5)
        
        self.dry_run_btn = tk.Button(
            button_frame, text="Dry-run", command=self._run_dry_run,
            bg="blue", fg="white", padx=10, pady=5
        )
        self.dry_run_btn.pack(side=tk.LEFT, padx=5)
        
        self.undo_btn = tk.Button(
            button_frame, text="Undo", command=self._run_undo,
            bg="orange", fg="white", padx=10, pady=5
        )
        self.undo_btn.pack(side=tk.LEFT, padx=5)
        
        # ================================================================
        # LOG - Zona de afișare
        # ================================================================
        
        log_label = tk.Label(root, text="Log:", font=("Arial", 10, "bold"))
        log_label.pack(anchor=tk.W, padx=10, pady=(10, 0))
        
        self.log_text = scrolledtext.ScrolledText(
            root, height=20, width=80,
            bg="black", fg="lime", font=("Courier", 9)
        )
        self.log_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Pornește polling pentru log-uri
        self._poll_log_queue()

    # ================================================================
    # LOG HANDLER - Citire din coadă
    # ================================================================

    def _attach_gui_handler(self):
        """Atașează handler-ul la logger"""
        if self.ctx and self.ctx.logger:
            handler = QueueLogHandler(self.log_queue)
            handler.setFormatter(logging.Formatter("%(message)s"))
            self.ctx.logger.addHandler(handler)

    def _poll_log_queue(self):
        """Verifică periodic dacă sunt log-uri noi în coadă"""
        while True:
            try:
                msg = self.log_queue.get_nowait()
                self.log_text.insert(tk.END, msg + "\n")
                self.log_text.see(tk.END)  # Scroll la final
            except:
                break
        
        # Reîncep polling în 100ms
        self.root.after(100, self._poll_log_queue)

    # ================================================================
    # THREADING - Executie în background
    # ================================================================

    def _run_in_thread(self, func):
        """Rulează o funcție pe thread separat (GUI-ul rămâne responsiv)"""
        thread = threading.Thread(target=func, daemon=True)
        thread.start()

    # ================================================================
    # RULARE NORMALĂ
    # ================================================================

    def _run_organize(self):
        """Inițiază rularea normală"""
        self.log_text.delete(1.0, tk.END)
        self.log_text.insert(tk.END, "Incepe organizare...\n")
        self._run_in_thread(self._do_run_organize)

    def _do_run_organize(self):
        """Execută organizarea pe thread"""
        try:
            self.ctx = OrganizerContext(self.config_path, dry_run=False)
            self._attach_gui_handler()
            run_once(self.ctx)
            self.log_text.insert(tk.END, "\nGata!\n")
        except Exception as e:
            self.log_text.insert(tk.END, f"\nEroare: {e}\n")

    # ================================================================
    # DRY-RUN (SIMULARE)
    # ================================================================

    def _run_dry_run(self):
        """Inițiază simulare (dry-run)"""
        self.log_text.delete(1.0, tk.END)
        self.log_text.insert(tk.END, "Incepe simulare...\n")
        self._run_in_thread(self._do_dry_run)

    def _do_dry_run(self):
        """Execută simularea pe thread"""
        try:
            self.ctx = OrganizerContext(self.config_path, dry_run=True)
            self._attach_gui_handler()
            run_once(self.ctx)
            self.log_text.insert(tk.END, "\nSimulare finalizata!\n")
        except Exception as e:
            self.log_text.insert(tk.END, f"\nEroare: {e}\n")

    # ================================================================
    # UNDO (ANULARE)
    # ================================================================

    def _run_undo(self):
        """Inițiază anularea ultimei rulări"""
        self.log_text.delete(1.0, tk.END)
        self.log_text.insert(tk.END, "Se anuleaza ultima rulare...\n")
        self._run_in_thread(self._do_undo)

    def _do_undo(self):
        """Execută anularea pe thread"""
        try:
            self.ctx = OrganizerContext(self.config_path)
            self._attach_gui_handler()
            run_undo(self.ctx)
            self.log_text.insert(tk.END, "\nUndo finalizat!\n")
        except Exception as e:
            self.log_text.insert(tk.END, f"\nEroare: {e}\n")


# ================================================================
# START
# ================================================================

def main():
    """Pornește aplicația GUI"""
    root = tk.Tk()
    app = OrganizerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()