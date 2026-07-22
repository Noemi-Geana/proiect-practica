"""
Web interface pentru monitorizare și control al aplicației
Utilizare: python3 web_app.py, apoi http://localhost:5000
"""

from flask import Flask, render_template_string, redirect, url_for, request
from main import OrganizerContext, run_once, run_undo


app = Flask(__name__)

# ================================================================
# HTML TEMPLATE - Interfața web
# ================================================================

PAGE_TEMPLATE = """
<!DOCTYPE html>
<html lang="ro">
<head>
    <meta charset="UTF-8">
    <title>Gestiune Download-uri</title>
    <style>
        body {
            font-family: sans-serif;
            max-width: 800px;
            margin: 40px auto;
            padding: 0 20px;
        }
        h1 { color: #333; }
        .card {
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 16px;
        }
        .stat {
            display: flex;
            justify-content: space-between;
            padding: 4px 0;
        }
        button {
            padding: 8px 16px;
            margin-right: 8px;
            cursor: pointer;
        }
        .recent-item {
            font-size: 0.9em;
            color: #555;
            padding: 2px 0;
        }
        .message {
            background: #eef;
            padding: 10px;
            border-radius: 6px;
            margin-bottom: 16px;
        }
    </style>
</head>
<body>
    <h1>Gestiune Download-uri</h1>

    {% if message %}
    <div class="message">{{ message }}</div>
    {% endif %}

    <!-- Butoane de acțiune -->
    <div class="card">
        <h2>Actiuni</h2>
        <form method="post" action="{{ url_for('run_organizer') }}" style="display:inline;">
            <button type="submit" name="mode" value="normal">Rulare</button>
            <button type="submit" name="mode" value="dry_run">Dry-run</button>
        </form>
        <form method="post" action="{{ url_for('run_undo') }}" style="display:inline;">
            <button type="submit" onclick="return confirm('Anulezi ultima rulare?')">Undo</button>
        </form>
    </div>

    <!-- Statistici -->
    <div class="card">
        <h2>Statistici</h2>
        <div class="stat"><strong>Total fisiere:</strong> <span>{{ total_files }}</span></div>
        <h3>Spatiu ocupat</h3>
        {% for category, size in usage.items() %}
        <div class="stat"><span>{{ category }}</span><span>{{ size }}</span></div>
        {% endfor %}
    </div>

    <!-- Adaugari recente -->
    <div class="card">
        <h2>Adaugari recente</h2>
        {% if recent %}
            {% for item in recent %}
            <div class="recent-item">{{ item.timestamp }} — {{ item.filename }}</div>
            {% endfor %}
        {% else %}
            <p>Nicio adaugare.</p>
        {% endif %}
    </div>
</body>
</html>
"""


# ================================================================
# HELPER - Creeaza context
# ================================================================

def build_context(dry_run: bool = False):
    """Creeaza si returneaza contextul aplicatiei"""
    return OrganizerContext("config/config.yaml", dry_run=dry_run)


# ================================================================
# ROUTES - Endpoint-uri web
# ================================================================

@app.route("/")
def index():
    """Pagina principala: afiseaza statistici si butoane"""
    ctx = build_context()
    
    usage = ctx.stats.disk_usage_by_category(ctx.config)
    total_files = ctx.stats.total_files_organized()
    recent = list(reversed(ctx.stats._global.get("history_additions", [])[-10:]))
    message = request.args.get("message", "")
    
    return render_template_string(
        PAGE_TEMPLATE,
        usage=usage,
        total_files=total_files,
        recent=recent,
        message=message
    )


@app.route("/run", methods=["POST"])
def run_organizer():
    """Declanseaza o rulare (normala sau dry-run)"""
    mode = request.form.get("mode", "normal")
    dry_run = (mode == "dry_run")
    
    try:
        ctx = build_context(dry_run=dry_run)
        run_once(ctx)
        moved = ctx.stats.get("moved")
        msg = f"Gata: {moved} fisiere (dry-run: {dry_run})"
    except Exception as e:
        msg = f"Eroare: {e}"
    
    return redirect(url_for("index", message=msg))


@app.route("/undo", methods=["POST"])
def run_undo():
    """Anuleaza ultima rulare"""
    try:
        ctx = build_context()
        success, failed = ctx.history.undo_last_run()
        msg = f"Undo: {success} reușite, {failed} eșuate"
    except Exception as e:
        msg = f"Eroare undo: {e}"
    
    return redirect(url_for("index", message=msg))


# ================================================================
# START
# ================================================================

if __name__ == "__main__":
    app.run(debug=True, port=5000)