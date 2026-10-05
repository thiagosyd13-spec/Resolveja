from flask import Flask, request, redirect, render_template
import sqlite3

app = Flask(__name__)

def conectar_banco():
    conn = sqlite3.connect("banco.db")
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def inicio():
    conn = conectar_banco()
    profissionais = [dict(row) for row in conn.execute("SELECT * FROM profissionais ORDER BY id DESC").fetchall()]
    conn.close()
    return render_template("index.html", profissionais=profissionais)

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
    """, (nome, servico, telefone, cidade, descricao, preco))

    conn.commit()
    conn.close()

    return redirect("/")


@app.route("/profissionais")
def profissionais():
    conn = conectar_banco()
    lista = [dict(row) for row in conn.execute("SELECT * FROM profissionais ORDER BY id DESC").fetchall()]
    conn.close()
    return render_template("index.html", profissionais=lista)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
