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
    usuario_id INTEGER,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

conn.execute("""
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    telefone TEXT,
    email TEXT UNIQUE NOT NULL,
    senha TEXT NOT NULL,
    email_verificado INTEGER DEFAULT 0,
    tipo TEXT NOT NULL DEFAULT 'cliente',
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()
conn.close()

print("Banco de dados criado com sucesso!")

# Recuperação inicial dos profissionais
conn = sqlite3.connect("banco.db")
qtd = conn.execute("SELECT COUNT(*) FROM profissionais").fetchone()[0]
if qtd == 0:
    conn.executemany("""
        INSERT INTO profissionais (nome, servico, telefone, cidade, descricao, preco)
        VALUES (?, ?, ?, ?, ?, ?)
    """, [
        ('Thiago teste', 'Eletricista', '31998575530', 'Viçosa', 'Faço todo tipo se serviço em obras', 100.0),
        ('Lucas teste', 'Encanador', '31998575530', 'Viçosa', 'Faço tudo', 80.0),
        ('Teste Resolveja', 'Eletricista', '31999999999', 'Viçosa', 'Servico teste', 100.0),
        ('Tales', 'Limpeza', '31999999999', 'Viçosa', 'Teste', 90.0),
        ('João', 'Pintor', '31999999999', 'Viçosa', 'Teste', 120.0)
    ])
    conn.commit()
conn.close()
