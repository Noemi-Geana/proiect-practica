import shutil
import subprocess


class Notifier:
    def __init__(self, config, logger=None):
        self.enabled = config.behavior.get("notifications_enabled", True)
        self.logger = logger
        self._available = shutil.which("notify-send") is not None

    def _log(self, msg, level="info"):
        if self.logger:
            getattr(self.logger, level)(msg)

    def send(self, title: str, message: str, urgency: str = "normal"):
        
        if not self.enabled:
            return
        if not self._available:
            self._log("'notify-send' nu este instalat; notificare ignorata.", "warning")
            return
        try:
            subprocess.run(
                ["notify-send", "-u", urgency, title, message],
                check=True, capture_output=True, timeout=3,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as e:
            self._log(f"Nu s-a putut trimite notificarea: {e}", "warning")

    def notify_summary(self, moved: int, errors: int, duplicates: int):
        message = f"Fișiere organizate: {moved} | Duplicate: {duplicates} | Erori: {errors}"
        urgency = "critical" if errors > 0 else "normal"
        self.send("Organizare Downloads finalizată", message, urgency=urgency)

    def notify_error(self, error_message: str):
        self.send("Eroare la organizarea fișierelor", error_message, urgency="critical")