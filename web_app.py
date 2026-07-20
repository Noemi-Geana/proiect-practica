"""
web_app.py
----------
Interfata web minimala (Flask) pentru monitorizarea statusului aplicatiei
si a istoricului de organizare, plus posibilitatea de a declansa o rulare
direct din browser.

Utilizare:
    python3 web_app.py
    apoi deschide http://localhost:5000 in browser
"""

from flask import Flask, render_template_string, redirect, url_for, request

from main import OrganizerContext, run_once, run_undo

app = Flask(__name__)

PAGE_TEMPLATE = """
<!DOCTYPE html>
<html lang="ro">
<head>
    <meta charset="UTF-8">
    <title>Gestiune Download-uri</title>
    <style>
        body { font-family: sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; }
        h1 { color: #333; }
        .card { border: 1px solid #ddd; border-radius: 8px; padding: 16px; margin-bottom: 16px; }
        .stat { display: flex; justify-content: space-between; padding: 4px 0; }
        button { padding: 8px 16px; margin-right: 8px; cursor: pointer; }
        .recent-item { font-size: 0.9em; color: #555; padding: 2px 0; }
        .flash { background: #eef; padding: 10px; border-radius: 6px; margin-bottom: 16px; }
    </style>
</head>
<body>
    <h1>📁 Gestiune Download-uri</h1>

    {% if message %}
    <div class="flash">{{ message }}</div>
    {% endif %}

    <div class="card">
        <h2>Acțiuni</h2>
        <form method="post" action="{{ url_for('trigger_run') }}" style="display:inline;">
            <button type="submit" name="mode" value="normal">▶️ Rulare normală</button>
            <button type="submit" name="mode" value="dry_run">🧪 Dry-run</button>
        </form>
        <form method="post" action="{{ url_for('trigger_undo') }}" style="display:inline;">
            <button type="submit" onclick="return confirm('Sigur anulezi ultima rulare?')">↩️ Undo</button>
        </form>
    </div>

    <div class="card">
        <h2>Statistici globale</h2>
        <div class="stat"><strong>Total fișiere organizate:</strong> <span>{{ total_files }}</span></div>
        <h3>Spațiu ocupat pe categorie</h3>
        {% for category, size in usage.items() %}
        <div class="stat"><span>{{ category }}</span><span>{{ size }}</span></div>
        {% endfor %}
    </div>

    <div class="card">
        <h2>Cele mai recente adăugări</h2>
        {% if recent %}
            {% for item in recent %}
            <div class="recent-item">{{ item.timestamp }} — {{ item.filename }}</div>
            {% endfor %}
        {% else %}
            <p>Nicio adăugare încă.</p>
        {% endif %}
    </div>
</body>
</html>
"""


def _build_context():
    return OrganizerContext("config/config.yaml")


@app.route("/")
def index():
    ctx = _build_context()
    usage = ctx.stats.disk_usage_by_category(ctx.config)
    total_files = ctx.stats.total_files_organized()
    recent = list(reversed(ctx.stats._global.get("history_additions", [])[-10:]))
    message = request.args.get("message", "")
    return render_template_string(
        PAGE_TEMPLATE, usage=usage, total_files=total_files, recent=recent, message=message
    )


@app.route("/run", methods=["POST"])
def trigger_run():
    dry_run = request.form.get("mode") == "dry_run"
    try:
        ctx = OrganizerContext("config/config.yaml", dry_run=dry_run)
        run_once(ctx)
        moved = ctx.stats.get("moved")
        message = f"Rulare finalizată ({'dry-run' if dry_run else 'reală'}): {moved} fișiere mutate."
    except Exception as e:
        message = f"Eroare la rulare: {e}"
    return redirect(url_for("index", message=message))


@app.route("/undo", methods=["POST"])
def trigger_undo():
    try:
        ctx = OrganizerContext("config/config.yaml")
        success, failed = ctx.history.undo_last_run()
        message = f"Undo finalizat: {success} reușite, {failed} eșuate."
    except Exception as e:
        message = f"Eroare la undo: {e}"
    return redirect(url_for("index", message=message))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
