import csv
import os
import sqlite3
import unicodedata
from functools import wraps
from io import BytesIO, StringIO
from pathlib import Path

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from openpyxl import load_workbook

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LEGACY_DB = BASE_DIR / "people.db"
if os.environ.get("DATABASE_PATH"):
    DB_PATH = Path(os.environ["DATABASE_PATH"])
elif LEGACY_DB.exists():
    DB_PATH = LEGACY_DB
else:
    DB_PATH = DATA_DIR / "people.db"

DB_PATH = DB_PATH.resolve()

app = Flask(__name__)
app.secret_key = "change-me"  # Needed for flash messages.
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin")


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS gestors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            secretaria TEXT NOT NULL,
            coordenacao TEXT NOT NULL,
            email TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS bases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            ambiente TEXT NOT NULL,
            descricao TEXT NOT NULL,
            gestor_id INTEGER NOT NULL,
            substituto1_id INTEGER NOT NULL,
            substituto2_id INTEGER NOT NULL,
            FOREIGN KEY (gestor_id) REFERENCES gestors(id),
            FOREIGN KEY (substituto1_id) REFERENCES gestors(id),
            FOREIGN KEY (substituto2_id) REFERENCES gestors(id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        INSERT INTO users (username, password)
        VALUES (?, ?)
        ON CONFLICT(username) DO UPDATE SET password=excluded.password
        """,
        (ADMIN_USERNAME, ADMIN_PASSWORD),
    )
    conn.commit()
    conn.close()


def query_db(query, params=()):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(query, params)
    rows = cur.fetchall()
    conn.commit()
    conn.close()
    return rows


def execute_db(query, params=()):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(query, params)
    conn.commit()
    conn.close()


def normalize_field(label: str) -> str:
    cleaned = (
        unicodedata.normalize("NFKD", label)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
        .replace(" ", "")
        .replace("_", "")
    )
    return cleaned


def bulk_insert(records):
    conn = sqlite3.connect(DB_PATH)
    conn.executemany(
        "INSERT INTO gestors (name, secretaria, coordenacao, email) VALUES (?, ?, ?, ?)",
        records,
    )
    conn.commit()
    conn.close()


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("user"):
            flash("Faça login para continuar.", "error")
            return redirect(url_for("login", next=request.path))
        return view_func(*args, **kwargs)

    return wrapper


def parse_csv(file_storage, delimiter):
    content = file_storage.stream.read().decode("utf-8-sig")
    reader = csv.DictReader(StringIO(content), delimiter=delimiter)
    records = []
    for row in reader:
        normalized = {normalize_field(k): (v or "").strip() for k, v in row.items()}
        name = normalized.get("gestor") or normalized.get("nome")
        secretaria = normalized.get("secretaria")
        coordenacao = normalized.get("coordenacao")
        email = normalized.get("email")
        if name and secretaria and coordenacao and email:
            records.append((name, secretaria, coordenacao, email))
    return records


def parse_xlsx(file_storage):
    file_bytes = BytesIO(file_storage.read())
    workbook = load_workbook(filename=file_bytes, data_only=True)
    sheet = workbook.active
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [normalize_field(str(h)) for h in rows[0] if h is not None]
    records = []
    for data_row in rows[1:]:
        values = [str(cell).strip() if cell is not None else "" for cell in data_row]
        row_dict = {headers[i]: values[i] for i in range(min(len(headers), len(values)))}
        name = row_dict.get("gestor") or row_dict.get("nome")
        secretaria = row_dict.get("secretaria")
        coordenacao = row_dict.get("coordenacao")
        email = row_dict.get("email")
        if name and secretaria and coordenacao and email:
            records.append((name, secretaria, coordenacao, email))
    return records


@app.route("/")
@login_required
def landing():
    total_bases = query_db("SELECT COUNT(*) as total FROM bases")[0]["total"]
    total_gestors = query_db("SELECT COUNT(*) as total FROM gestors")[0]["total"]
    return render_template("landing.html", total_bases=total_bases, total_gestors=total_gestors)


def get_gestors(term=None):
    if term:
        like_term = f"%{term}%"
        return query_db(
            """
            SELECT * FROM gestors
            WHERE name LIKE ? OR secretaria LIKE ? OR coordenacao LIKE ? OR email LIKE ?
            ORDER BY name COLLATE NOCASE ASC
            """,
            (like_term, like_term, like_term, like_term),
        )
    return query_db("SELECT * FROM gestors ORDER BY name COLLATE NOCASE ASC")


def parse_gestor_id(raw_value):
    if not raw_value:
        return None
    candidate = raw_value.strip().split(" ", 1)[0]
    try:
        return int(candidate)
    except ValueError:
        return None


@app.route("/gestores")
@login_required
def list_gestors():
    search_term = request.args.get("q", "").strip()
    gestors = get_gestors(search_term)
    return render_template("gestors.html", gestors=gestors, query=search_term)


@app.route("/gestores/novo")
@login_required
def new_gestor_form():
    return render_template("gestor_form.html")


@app.route("/gestores/criar", methods=["POST"])
@login_required
def add_gestor():
    name = request.form.get("name", "").strip()
    secretaria = request.form.get("secretaria", "").strip()
    coordenacao = request.form.get("coordenacao", "").strip()
    email = request.form.get("email", "").strip()

    if not all([name, secretaria, coordenacao, email]):
        flash("Preencha todos os campos do gestor.", "error")
        return redirect(url_for("new_gestor_form"))

    execute_db(
        "INSERT INTO gestors (name, secretaria, coordenacao, email) VALUES (?, ?, ?, ?)",
        (name, secretaria, coordenacao, email),
    )
    flash("Gestor cadastrado com sucesso.", "success")
    return redirect(url_for("list_gestors"))


@app.route("/gestores/<int:gestor_id>/editar")
@login_required
def edit_gestor(gestor_id):
    gestor = query_db("SELECT * FROM gestors WHERE id = ?", (gestor_id,))
    if not gestor:
        flash("Gestor não encontrado.", "error")
        return redirect(url_for("list_gestors"))
    return render_template("gestor_form.html", gestor=gestor[0])


@app.route("/gestores/<int:gestor_id>/atualizar", methods=["POST"])
@login_required
def update_gestor(gestor_id):
    name = request.form.get("name", "").strip()
    secretaria = request.form.get("secretaria", "").strip()
    coordenacao = request.form.get("coordenacao", "").strip()
    email = request.form.get("email", "").strip()

    if not all([name, secretaria, coordenacao, email]):
        flash("Preencha todos os campos do gestor.", "error")
        return redirect(url_for("edit_gestor", gestor_id=gestor_id))

    execute_db(
        "UPDATE gestors SET name = ?, secretaria = ?, coordenacao = ?, email = ? WHERE id = ?",
        (name, secretaria, coordenacao, email, gestor_id),
    )
    flash("Gestor atualizado.", "success")
    return redirect(url_for("list_gestors"))


@app.route("/gestores/<int:gestor_id>/remover", methods=["POST"])
@login_required
def delete_gestor(gestor_id):
    in_use = query_db(
        "SELECT COUNT(*) as total FROM bases WHERE gestor_id = ? OR substituto1_id = ? OR substituto2_id = ?",
        (gestor_id, gestor_id, gestor_id),
    )[0]["total"]
    if in_use:
        flash("Não é possível remover: gestor vinculado a bases.", "error")
        return redirect(url_for("list_gestors"))

    execute_db("DELETE FROM gestors WHERE id = ?", (gestor_id,))
    flash("Gestor removido.", "success")
    return redirect(url_for("list_gestors"))


def gestor_choices(term=None):
    return [
        {
            "id": g["id"],
            "label": f"{g['id']} - {g['name']} ({g['secretaria']} / {g['coordenacao']})",
        }
        for g in get_gestors(term)
    ]


def selected_labels_from_base(base_row, options):
    label_map = {opt["id"]: opt["label"] for opt in options}
    return {
        "gestor": label_map.get(base_row["gestor_id"], ""),
        "sub1": label_map.get(base_row["substituto1_id"], ""),
        "sub2": label_map.get(base_row["substituto2_id"], ""),
    }


def ensure_gestor_exists(gestor_id, field_label):
    if not gestor_id:
        flash(f"Selecione um {field_label} válido a partir da lista.", "error")
        return False
    exists = query_db("SELECT id FROM gestors WHERE id = ?", (gestor_id,))
    if not exists:
        flash(f"{field_label} não encontrado.", "error")
        return False
    return True


@app.route("/bases")
@login_required
def list_bases():
    records = query_db(
        """
        SELECT b.*, g.name as gestor_name, gs1.name as sub1_name, gs2.name as sub2_name
        FROM bases b
        LEFT JOIN gestors g ON g.id = b.gestor_id
        JOIN gestors gs1 ON gs1.id = b.substituto1_id
        JOIN gestors gs2 ON gs2.id = b.substituto2_id
        ORDER BY b.id DESC
        """
    )
    return render_template("bases.html", bases=records)


@app.route("/bases/nova")
@login_required
def new_base_form():
    options = gestor_choices()
    if len(options) < 2:
        flash("Cadastre pelo menos dois gestores para definir substitutos.", "error")
        return redirect(url_for("new_gestor_form"))
    return render_template("base_form.html", gestors=options, selected_labels=None)


@app.route("/bases/criar", methods=["POST"])
@login_required
def add_base():
    name = request.form.get("name", "").strip()
    ambiente = request.form.get("ambiente", "").strip()
    descricao = request.form.get("descricao", "").strip()
    gestor_id = parse_gestor_id(request.form.get("gestor_id", ""))
    sub1_id = parse_gestor_id(request.form.get("substituto1_id", ""))
    sub2_id = parse_gestor_id(request.form.get("substituto2_id", ""))

    if not all([name, ambiente, descricao]):
        flash("Preencha todos os campos da base.", "error")
        return redirect(url_for("new_base_form"))

    if not (
        (not gestor_id or ensure_gestor_exists(gestor_id, "Gestor"))
        and ensure_gestor_exists(sub1_id, "1º substituto")
        and ensure_gestor_exists(sub2_id, "2º substituto")
    ):
        return redirect(url_for("new_base_form"))

    unique_ids = {sub1_id, sub2_id}
    if gestor_id:
        unique_ids.add(gestor_id)
    if len(unique_ids) < 2 or sub1_id == sub2_id:
        flash("Substitutos precisam ser pessoas diferentes.", "error")
        return redirect(url_for("new_base_form"))
    if gestor_id and (gestor_id == sub1_id or gestor_id == sub2_id):
        flash("Gestor titular não pode repetir um substituto.", "error")
        return redirect(url_for("new_base_form"))

    execute_db(
        """
        INSERT INTO bases (name, ambiente, descricao, gestor_id, substituto1_id, substituto2_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (name, ambiente, descricao, gestor_id, sub1_id, sub2_id),
    )
    flash("Base cadastrada com sucesso.", "success")
    return redirect(url_for("list_bases"))


@app.route("/bases/<int:base_id>/editar")
@login_required
def edit_base(base_id):
    record = query_db("SELECT * FROM bases WHERE id = ?", (base_id,))
    if not record:
        flash("Base não encontrada.", "error")
        return redirect(url_for("list_bases"))
    options = gestor_choices()
    labels = selected_labels_from_base(record[0], options)
    return render_template("base_form.html", base=record[0], gestors=options, selected_labels=labels)


@app.route("/bases/<int:base_id>/atualizar", methods=["POST"])
@login_required
def update_base(base_id):
    name = request.form.get("name", "").strip()
    ambiente = request.form.get("ambiente", "").strip()
    descricao = request.form.get("descricao", "").strip()
    gestor_id = parse_gestor_id(request.form.get("gestor_id", ""))
    sub1_id = parse_gestor_id(request.form.get("substituto1_id", ""))
    sub2_id = parse_gestor_id(request.form.get("substituto2_id", ""))

    if not all([name, ambiente, descricao]):
        flash("Preencha todos os campos da base.", "error")
        return redirect(url_for("edit_base", base_id=base_id))

    if not (
        (not gestor_id or ensure_gestor_exists(gestor_id, "Gestor"))
        and ensure_gestor_exists(sub1_id, "1º substituto")
        and ensure_gestor_exists(sub2_id, "2º substituto")
    ):
        return redirect(url_for("edit_base", base_id=base_id))

    unique_ids = {sub1_id, sub2_id}
    if gestor_id:
        unique_ids.add(gestor_id)
    if len(unique_ids) < 2 or sub1_id == sub2_id:
        flash("Substitutos precisam ser pessoas diferentes.", "error")
        return redirect(url_for("edit_base", base_id=base_id))
    if gestor_id and (gestor_id == sub1_id or gestor_id == sub2_id):
        flash("Gestor titular não pode repetir um substituto.", "error")
        return redirect(url_for("edit_base", base_id=base_id))

    execute_db(
        """
        UPDATE bases
        SET name = ?, ambiente = ?, descricao = ?, gestor_id = ?, substituto1_id = ?, substituto2_id = ?
        WHERE id = ?
        """,
        (name, ambiente, descricao, gestor_id, sub1_id, sub2_id, base_id),
    )
    flash("Base atualizada.", "success")
    return redirect(url_for("list_bases"))


@app.route("/bases/<int:base_id>/remover", methods=["POST"])
@login_required
def delete_base(base_id):
    execute_db("DELETE FROM bases WHERE id = ?", (base_id,))
    flash("Base removida.", "success")
    return redirect(url_for("list_bases"))


@app.route("/buscar")
@login_required
def search():
    term = request.args.get("q", "").strip()
    results = []
    if term:
        like_term = f"%{term}%"
        results = query_db(
            """
            SELECT b.*, g.name as gestor_name
            FROM bases b
            LEFT JOIN gestors g ON g.id = b.gestor_id
            WHERE b.name LIKE ? OR b.descricao LIKE ? OR g.name LIKE ? OR b.ambiente LIKE ?
            ORDER BY b.id DESC
            """,
            (like_term, like_term, like_term, like_term),
        )

    return render_template("search.html", query=term, results=results)


@app.route("/importar", methods=["GET", "POST"])
@login_required
def import_records():
    if request.method == "GET":
        return render_template("import.html")

    upload = request.files.get("file")
    delimiter = request.form.get("delimiter", ";").strip() or ";"

    if not upload or not upload.filename:
        flash("Selecione um arquivo CSV ou XLSX para importar.", "error")
        return redirect(url_for("import_records"))

    ext = upload.filename.rsplit(".", 1)[-1].lower()

    try:
        if ext == "csv":
            records = parse_csv(upload, delimiter)
        elif ext in {"xlsx", "xls"}:
            records = parse_xlsx(upload)
        else:
            flash("Formato não suportado. Envie um CSV ou XLSX.", "error")
            return redirect(url_for("import_records"))
    except Exception:
        flash("Não foi possível ler o arquivo enviado. Verifique o formato e tente novamente.", "error")
        return redirect(url_for("import_records"))

    if not records:
        flash("Nenhum registro válido encontrado. Confira as colunas e se há dados preenchidos.", "error")
        return redirect(url_for("import_records"))

    bulk_insert(records)
    flash(f"Importação concluída com {len(records)} registro(s).", "success")
    return redirect(url_for("list_gestors"))


@app.route("/configuracoes")
@login_required
def settings():
    users = query_db("SELECT id, username FROM users ORDER BY username ASC")
    return render_template("settings.html", users=users)


@app.route("/usuarios/criar", methods=["POST"])
@login_required
def create_user():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    if not username or not password:
        flash("Preencha usuário e senha para adicionar.", "error")
        return redirect(url_for("settings"))

    try:
        execute_db(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, password),
        )
    except sqlite3.IntegrityError:
        flash("Nome de usuário já existe.", "error")
        return redirect(url_for("settings"))

    flash("Usuário criado com sucesso.", "success")
    return redirect(url_for("settings"))


@app.route("/usuarios/<int:user_id>/resetar", methods=["POST"])
@login_required
def reset_user(user_id):
    password = request.form.get("password", "")
    if not password:
        flash("Informe uma nova senha para continuar.", "error")
        return redirect(url_for("settings"))

    execute_db("UPDATE users SET password = ? WHERE id = ?", (password, user_id))
    flash("Senha atualizada.", "success")
    return redirect(url_for("settings"))


@app.route("/usuarios/<int:user_id>/remover", methods=["POST"])
@login_required
def delete_user(user_id):
    user = query_db("SELECT username FROM users WHERE id = ?", (user_id,))
    if not user:
        flash("Usuário não encontrado.", "error")
        return redirect(url_for("settings"))

    username = user[0]["username"]
    if username == session.get("user"):
        flash("Não é possível remover o usuário logado.", "error")
        return redirect(url_for("settings"))

    if username == ADMIN_USERNAME:
        flash("O usuário administrador padrão não pode ser removido.", "error")
        return redirect(url_for("settings"))

    execute_db("DELETE FROM users WHERE id = ?", (user_id,))
    flash("Usuário removido.", "success")
    return redirect(url_for("settings"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user"):
        return redirect(url_for("landing"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = query_db(
            "SELECT username FROM users WHERE username = ? AND password = ?",
            (username, password),
        )

        if user:
            session["user"] = username
            next_page = request.args.get("next") or url_for("landing")
            flash("Login realizado com sucesso.", "success")
            return redirect(next_page)

        flash("Credenciais inválidas.", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Sessão encerrada.", "success")
    return redirect(url_for("login"))


init_db()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(debug=True, host="0.0.0.0", port=port)
