from flask import Flask, request, redirect, render_template, session
import sqlite3
import os
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
import resend

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "resolveja-chave-secreta-2026")

from criar_banco import *

conn_debug = sqlite3.connect("banco.db")
print("=== PROFISSIONAIS NO RENDER ===", conn_debug.execute("SELECT COUNT(*) FROM profissionais").fetchone()[0]); print("=== COLUNAS ===", [x[1] for x in conn_debug.execute("PRAGMA table_info(profissionais)").fetchall()])
conn_debug.close()


def conectar_banco():
    conn = sqlite3.connect("banco.db")
    conn.row_factory = sqlite3.Row
    return conn


def gerar_token():
    return secrets.token_urlsafe(32)


def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def enviar_email_verificacao(email, nome, token):
    resend.api_key = os.environ.get("RESEND_API_KEY")

    base_url = os.environ.get(
        "APP_BASE_URL",
        "https://resolveja-wcp4.onrender.com"
    )

    link = f"{base_url}/verificar-email/{token}"

    resend.Emails.send({
        "from": "onboarding@resend.dev",
        "to": [email],
        "subject": "Confirme seu e-mail - ResolveJá",
        "html": f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;">
            <h1>Bem-vindo ao ResolveJá, {nome}!</h1>

            <p>Sua conta foi criada com sucesso.</p>

            <p>Para confirmar que este e-mail realmente pertence a você,
            clique no botão abaixo:</p>

            <p>
                <a href="{link}"
                   style="display:inline-block;padding:14px 22px;
                          background:#2563eb;color:white;
                          text-decoration:none;border-radius:8px;">
                    Confirmar meu e-mail
                </a>
            </p>

            <p>Se você não criou esta conta, ignore este e-mail.</p>

            <p>Equipe ResolveJá</p>
        </div>
        """
    })


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
    usuario_id = session.get("usuario_id")

    conn = conectar_banco()

    conn.execute("""
        INSERT INTO profissionais
        (nome, servico, telefone, cidade, descricao, preco, usuario_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        nome,
        servico,
        telefone,
        cidade,
        descricao,
        preco,
        usuario_id
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

        token = gerar_token()
        token_hash = hash_token(token)
        expiracao = datetime.now(timezone.utc) + timedelta(hours=24)

        conn = conectar_banco()

        try:
            cursor = conn.execute("""
                INSERT INTO usuarios
                (nome, telefone, email, senha, email_verificado)
                VALUES (?, ?, ?, ?, 0)
            """, (
                nome,
                telefone,
                email,
                generate_password_hash(senha)
            ))

            usuario_id = cursor.lastrowid

            conn.execute("""
                CREATE TABLE IF NOT EXISTS verificacoes_email (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario_id INTEGER NOT NULL,
                    token_hash TEXT NOT NULL UNIQUE,
                    expira_em TEXT NOT NULL,
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
                )
            """)

            conn.execute("""
                INSERT INTO verificacoes_email
                (usuario_id, token_hash, expira_em)
                VALUES (?, ?, ?)
            """, (
                usuario_id,
                token_hash,
                expiracao.isoformat()
            ))

            conn.commit()

        except sqlite3.IntegrityError:
            conn.close()
            return "Este e-mail já está cadastrado.", 400

        conn.close()

        try:
            enviar_email_verificacao(email, nome, token)
        except Exception as e:
            print(f"ERRO AO ENVIAR EMAIL: {e}")
            conn = conectar_banco()
            conn.execute(
                "DELETE FROM verificacoes_email WHERE usuario_id = ?",
                (usuario_id,)
            )
            conn.execute(
                "DELETE FROM usuarios WHERE id = ?",
                (usuario_id,)
            )
            conn.commit()
            conn.close()

            return "Não foi possível enviar o e-mail de verificação. Tente novamente.", 500

        return """
        <h2>Conta criada!</h2>
        <p>Enviamos um link de verificação para seu e-mail.</p>
        <p>Abra seu e-mail e confirme sua conta antes de fazer login.</p>
        """

    return render_template("criar_conta.html")


@app.route("/verificar-email/<token>")
def verificar_email(token):
    token_hash = hash_token(token)

    conn = conectar_banco()

    verificacao = conn.execute("""
        SELECT *
        FROM verificacoes_email
        WHERE token_hash = ?
    """, (token_hash,)).fetchone()

    if verificacao is None:
        conn.close()
        return "Link de verificação inválido ou já utilizado.", 400

    expiracao = datetime.fromisoformat(verificacao["expira_em"])

    if datetime.now(timezone.utc) > expiracao:
        conn.close()
        return "Este link de verificação expirou.", 400

    conn.execute("""
        UPDATE usuarios
        SET email_verificado = 1
        WHERE id = ?
    """, (verificacao["usuario_id"],))

    conn.execute("""
        DELETE FROM verificacoes_email
        WHERE id = ?
    """, (verificacao["id"],))

    conn.commit()
    conn.close()

    return """
    <h2>E-mail confirmado com sucesso! ✅</h2>
    <p>Sua conta do ResolveJá está verificada.</p>
    <p><a href="/login">Entrar na minha conta</a></p>
    """


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

            if not usuario["email_verificado"]:
                return """
                <h2>E-mail ainda não verificado.</h2>
                <p>Confira sua caixa de entrada e clique no link de confirmação.</p>
                """, 403

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

    conn = conectar_banco()
    profissional = conn.execute(
        "SELECT * FROM profissionais WHERE usuario_id=? ORDER BY id DESC LIMIT 1",
        (session["usuario_id"],)
    ).fetchone()
    conn.close()

    return render_template(
        "minha_conta.html",
        nome=session.get("usuario_nome"),
        email=session.get("usuario_email"),
        profissional=dict(profissional) if profissional else None
    )


@app.route("/editar-profissional/<int:id>", methods=["GET", "POST"])
def editar_profissional(id):
    if "usuario_id" not in session:
        return redirect("/login")

    conn = conectar_banco()

    profissional = conn.execute(
        "SELECT * FROM profissionais WHERE id=? AND usuario_id=?",
        (id, session["usuario_id"])
    ).fetchone()

    if profissional is None:
        conn.close()
        return "Você não tem permissão para editar este anúncio.", 403

    if request.method == "POST":
        nome = request.form["nome"]
        servico = request.form["servico"]
        telefone = request.form.get("telefone", "")
        cidade = request.form.get("cidade", "")
        descricao = request.form.get("descricao", "")
        preco = request.form.get("preco", "")

        conn.execute("""
            UPDATE profissionais
            SET nome=?, servico=?, telefone=?, cidade=?, descricao=?, preco=?
            WHERE id=? AND usuario_id=?
        """, (
            nome,
            servico,
            telefone,
            cidade,
            descricao,
            preco,
            id,
            session["usuario_id"]
        ))

        conn.commit()
        conn.close()
        return redirect(f"/profissional/{id}")

    conn.close()
    return render_template("editar_profissional.html", profissional=dict(profissional))


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
