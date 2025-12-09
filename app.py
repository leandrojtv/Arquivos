import csv
import os
import sqlite3
import unicodedata
from io import BytesIO, StringIO
from pathlib import Path

from flask import Flask, render_template, request, redirect, url_for, flash
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


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS people (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            area TEXT NOT NULL,
            database TEXT NOT NULL
        )
        """
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
        "INSERT INTO people (name, area, database) VALUES (?, ?, ?)", records
    )
    conn.commit()
    conn.close()


def parse_csv(file_storage, delimiter):
    content = file_storage.stream.read().decode("utf-8-sig")
    reader = csv.DictReader(StringIO(content), delimiter=delimiter)
    records = []
    for row in reader:
        normalized = {normalize_field(k): (v or "").strip() for k, v in row.items()}
        base = normalized.get("basedados")
        gestor = normalized.get("gestor")
        area = normalized.get("area")
        if base and gestor and area:
            records.append((gestor, area, base))
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
        base = row_dict.get("basedados")
        gestor = row_dict.get("gestor")
        area = row_dict.get("area")
        if base and gestor and area:
            records.append((gestor, area, base))
    return records


@app.route("/")
def landing():
    total = query_db("SELECT COUNT(*) as total FROM people")[0]["total"]
    return render_template("landing.html", total=total)


@app.route("/cadastros")
def list_people():
    records = query_db("SELECT * FROM people ORDER BY id DESC")
    return render_template("list.html", records=records)


@app.route("/cadastro")
def new_person_form():
    return render_template("add.html")


@app.route("/add", methods=["POST"])
def add_person():
    name = request.form.get("name", "").strip()
    area = request.form.get("area", "").strip()
    database = request.form.get("database", "").strip()

    if not name or not area or not database:
        flash("Todos os campos são obrigatórios.", "error")
        return redirect(url_for("new_person_form"))

    query_db(
        "INSERT INTO people (name, area, database) VALUES (?, ?, ?)",
        (name, area, database),
    )
    flash("Cadastro criado com sucesso!", "success")
    return redirect(url_for("list_people"))


@app.route("/buscar")
def search():
    term = request.args.get("q", "").strip()
    results = []
    if term:
        like_term = f"%{term}%"
        results = query_db(
            """
            SELECT * FROM people
            WHERE name LIKE ? OR area LIKE ? OR database LIKE ?
            ORDER BY id DESC
            """,
            (like_term, like_term, like_term),
        )

    return render_template("search.html", query=term, results=results)


@app.route("/edit/<int:person_id>")
def edit_person(person_id):
    result = query_db("SELECT * FROM people WHERE id = ?", (person_id,))
    if not result:
        flash("Registro não encontrado.", "error")
        return redirect(url_for("list_people"))
    return render_template("edit.html", person=result[0])


@app.route("/update/<int:person_id>", methods=["POST"])
def update_person(person_id):
    name = request.form.get("name", "").strip()
    area = request.form.get("area", "").strip()
    database = request.form.get("database", "").strip()

    if not name or not area or not database:
        flash("Todos os campos são obrigatórios.", "error")
        return redirect(url_for("edit_person", person_id=person_id))

    query_db(
        "UPDATE people SET name = ?, area = ?, database = ? WHERE id = ?",
        (name, area, database, person_id),
    )
    flash("Cadastro atualizado com sucesso!", "success")
    return redirect(url_for("list_people"))


@app.route("/delete/<int:person_id>", methods=["POST"])
def delete_person(person_id):
    query_db("DELETE FROM people WHERE id = ?", (person_id,))
    flash("Registro removido.", "success")
    return redirect(url_for("list_people"))


@app.route("/importar", methods=["GET", "POST"])
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
    return redirect(url_for("list_people"))


init_db()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(debug=True, host="0.0.0.0", port=port)
