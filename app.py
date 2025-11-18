import sqlite3
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "people.db"

app = Flask(__name__)
app.secret_key = "change-me"  # Needed for flash messages.


def init_db():
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


@app.route("/")
def index():
    records = query_db("SELECT * FROM people ORDER BY id DESC")
    return render_template("index.html", records=records)


@app.route("/add", methods=["POST"])
def add_person():
    name = request.form.get("name", "").strip()
    area = request.form.get("area", "").strip()
    database = request.form.get("database", "").strip()

    if not name or not area or not database:
        flash("Todos os campos são obrigatórios.", "error")
        return redirect(url_for("index"))

    query_db(
        "INSERT INTO people (name, area, database) VALUES (?, ?, ?)",
        (name, area, database),
    )
    flash("Cadastro criado com sucesso!", "success")
    return redirect(url_for("index"))


@app.route("/edit/<int:person_id>")
def edit_person(person_id):
    result = query_db("SELECT * FROM people WHERE id = ?", (person_id,))
    if not result:
        flash("Registro não encontrado.", "error")
        return redirect(url_for("index"))
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
    return redirect(url_for("index"))


@app.route("/delete/<int:person_id>", methods=["POST"])
def delete_person(person_id):
    query_db("DELETE FROM people WHERE id = ?", (person_id,))
    flash("Registro removido.", "success")
    return redirect(url_for("index"))


init_db()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
