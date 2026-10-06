from flask import Flask, request, redirect, render_template, session
import sqlite3

app = Flask(__name__)
app.secret_key = "resolveja-chave-secreta-2026"

from criar_banco import *

def conectar_banco():
    conn = sqlite3.connect("banco.db")
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def inicio():
    conn = conectar_banco()

    profissionais = [
        dict(row)
        for row in conn.execute(
            "SELECT * FROM profissionais ORDER BY id DESC"
        ).fetchall()
    ]

    conn.close()

    return render_template(
        "index.html",
        profissionais=profissionais
    )


@app.route("/cadastrar", methods=["POST"])
def cadastrar():
    nome = request.form["nome"]
    servico = request.form["servico"]
    telefone = request.form.get("telefone", "")
    cidade = request.form.get("cidade", "")
    descricao = request.form.get("descricao", "")
    preco = request.form.get("preco", "")

    conn = conectar_banco()

    conn.execute("""
        INSERT INTO profissionais
        (nome, servico, telefone, cidade, descricao, preco)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        nome,
        servico,
        telefone,
        cidade,
        descricao,
        preco
    ))

    conn.commit()
    conn.close()

    return redirect("/")


@app.route("/profissionais")
def profissionais():
    conn = conectar_banco()

    lista = [
        dict(row)
        for row in conn.execute(
            "SELECT * FROM profissionais ORDER BY id DESC"
        ).fetchall()
    ]

    conn.close()

    return render_template(
        "index.html",
        profissionais=lista
    )


@app.route("/profissional/<int:id>")
def perfil_profissional(id):
    conn = conectar_banco()

    profissional = conn.execute(
        "SELECT * FROM profissionais WHERE id = ?",
        (id,)
    ).fetchone()

    conn.close()

    if profissional is None:
        return "Profissional não encontrado", 404

    return render_template(
        "perfil.html",
        profissional=dict(profissional)
    )


@app.route("/criar-conta", methods=["GET", "POST"])
def criar_conta():
    if request.method == "POST":
        from werkzeug.security import generate_password_hash

        nome = request.form["nome"].strip()
        telefone = request.form.get("telefone", "").strip()
        email = request.form["email"].strip().lower()
        senha = request.form["senha"]

        if not nome or not email or not senha:
            return "Preencha nome, e-mail e senha.", 400

        conn = conectar_banco()

        try:
            conn.execute("""
                INSERT INTO usuarios (nome, telefone, email, senha)
                VALUES (?, ?, ?, ?)
            """, (
                nome,
                telefone,
                email,
                generate_password_hash(senha)
            ))

            conn.commit()

        except sqlite3.IntegrityError:
            conn.close()
            return "Este e-mail já está cadastrado.", 400

        conn.close()

        return "Conta criada com sucesso!"

    return render_template("criar_conta.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        from werkzeug.security import check_password_hash

        email = request.form["email"].strip().lower()
        senha = request.form["senha"]

        conn = conectar_banco()

        usuario = conn.execute(
            "SELECT * FROM usuarios WHERE email = ?",
            (email,)
        ).fetchone()

        conn.close()

        if usuario and check_password_hash(usuario["senha"], senha):
            session["usuario_id"] = usuario["id"]
            session["usuario_nome"] = usuario["nome"]
            session["usuario_email"] = usuario["email"]
            return "Login realizado com sucesso!"

        return "E-mail ou senha incorretos.", 401

    return render_template("login.html")


@app.route("/minha-conta")
def minha_conta():
    if "usuario_id" not in session:
        return redirect("/login")

    return render_template(
        "minha_conta.html",
        nome=session.get("usuario_nome"),
        email=session.get("usuario_email")
    )


@app.route("/sair")
def sair():
    session.clear()
    return "Você saiu da sua conta."


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8080,
        debug=False
    )
