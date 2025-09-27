"""Script para criar e popular o banco de dados SQLite com dados de exemplo."""

import sqlite3
import os

# Define o nome do arquivo do banco de dados
DB_FILE = "db/database.db"

# Apaga o banco de dados antigo, se existir, para começar do zero
if os.path.exists(DB_FILE):
    os.remove(DB_FILE)

# Conecta ao banco de dados (será criado se não existir)
conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

# --- 1. CRIAR AS TABELAS ---
print("Criando tabelas...")

cursor.execute("""
CREATE TABLE clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    cidade TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE
);
""")

cursor.execute("""
CREATE TABLE produtos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    preco REAL NOT NULL
);
""")

cursor.execute("""
CREATE TABLE vendas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER,
    produto_id INTEGER,
    quantidade INTEGER NOT NULL,
    data_venda TEXT NOT NULL,
    FOREIGN KEY (cliente_id) REFERENCES clientes (id),
    FOREIGN KEY (produto_id) REFERENCES produtos (id)
);
""")

print("Tabelas criadas com sucesso!")

# --- 2. INSERIR DADOS DE EXEMPLO ---
print("Inserindo dados de exemplo...")

# Dados para a tabela de clientes
clientes_data = [
    ('Alice Silva', 'São Paulo', 'alice.silva@email.com'),
    ('Beto Costa', 'Rio de Janeiro', 'beto.costa@email.com'),
    ('Carlos Souza', 'Belo Horizonte', 'carlos.souza@email.com'),
    ('Diana Martins', 'Porto Alegre', 'diana.martins@email.com'),
    ('Eduardo Lima', 'Salvador', 'eduardo.lima@email.com')
]
cursor.executemany("INSERT INTO clientes (nome, cidade, email) VALUES (?, ?, ?)", clientes_data)

# Dados para a tabela de produtos
produtos_data = [
    ('Laptop Pro', 4500.00),
    ('Mouse Gamer', 250.00),
    ('Teclado Mecânico', 350.50),
    ('Monitor 4K', 1800.75),
    ('Webcam HD', 150.00),
    ('Fone de Ouvido', 299.90)
]
cursor.executemany("INSERT INTO produtos (nome, preco) VALUES (?, ?)", produtos_data)

# Dados para a tabela de vendas
vendas_data = [
    # Vendas de Alice (cliente_id=1)
    (1, 1, 1, '2024-01-15'),  # Comprou 1 Laptop Pro
    (1, 2, 2, '2024-01-18'),  # Comprou 2 Mouse Gamer
    (1, 4, 1, '2024-02-10'),  # Comprou 1 Monitor 4K

    # Vendas de Beto (cliente_id=2) - O que mais gastou
    (2, 1, 2, '2024-01-20'),  # Comprou 2 Laptop Pro
    (2, 3, 2, '2024-01-25'),  # Comprou 2 Teclado Mecânico
    (2, 6, 1, '2024-03-05'),  # Comprou 1 Fone de Ouvido

    # Vendas de Carlos (cliente_id=3)
    (3, 5, 3, '2024-02-01'),  # Comprou 3 Webcam HD

    # Vendas de Diana (cliente_id=4)
    (4, 2, 1, '2024-02-12'),  # Comprou 1 Mouse Gamer
    (4, 3, 1, '2024-02-12'),  # Comprou 1 Teclado Mecânico

    # Vendas de Eduardo (cliente_id=5)
    (5, 4, 1, '2024-03-10'),  # Comprou 1 Monitor 4K
    (5, 6, 1, '2024-03-15'),  # Comprou 1 Fone de Ouvido
]

cursor.executemany(
    "INSERT INTO vendas (cliente_id, produto_id, quantidade, data_venda) VALUES (?, ?, ?, ?)", 
    vendas_data
)


# --- 3. FINALIZAR ---
# Salvar (commit) as alterações e fechar a conexão
conn.commit()
conn.close()

print("\nBanco de dados 'database.db' criado e populado com sucesso!")
print(f"O arquivo está localizado em: {os.path.abspath(DB_FILE)}")
