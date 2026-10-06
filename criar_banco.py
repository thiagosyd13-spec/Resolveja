import sqlite3

conn = sqlite3.connect("banco.db")

conn.execute("""
CREATE TABLE IF NOT EXISTS profissionais (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    servico TEXT NOT NULL,
    telefone TEXT,
    cidade TEXT,
    descricao TEXT,
    preco REAL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()
conn.close()

print("Banco de dados criado com sucesso!")
