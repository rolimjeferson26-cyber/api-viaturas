"""
database.py

Cria a estrutura do banco de dados do projeto de viaturas.

3 tabelas, ligadas entre si:
- veiculos  -> ficha técnica (1 registro por viatura)
- cofres    -> compartimentos de cada viatura (Cabine, Cofre 1, Cofre 2...)
- materiais -> itens dentro de cada cofre

E 1 tabela à parte, sem ligação com as outras:
- comando   -> usuários do Comando, que podem criar/editar viaturas

Repara no "elo" entre elas:
- cofres.veiculo_id  aponta pra veiculos.id
- materiais.cofre_id aponta pra cofres.id

Isso é o que chamamos de chave estrangeira (foreign key, ou FK).
É assim que o banco sabe "esse cofre pertence a essa viatura" e
"esse material está dentro desse cofre".
"""

import sqlite3

NOME_BANCO = "viaturas.db"


def criar_conexao():
    conexao = sqlite3.connect(NOME_BANCO)
    # O SQLite vem com a fiscalização de foreign keys DESLIGADA por
    # padrão, e ela vale só para a conexão onde foi ligada. Ligando
    # aqui, toda conexão aberta no projeto já nasce fiscalizada.
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao


def criar_tabelas():
    conexao = criar_conexao()
    cursor = conexao.cursor()

    # --- Tabela dos veículos (ficha técnica) ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS veiculos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quartel TEXT,
            codigo TEXT,
            identificacao TEXT,
            tipo TEXT NOT NULL,
            marca TEXT,
            modelo TEXT,
            matricula TEXT,
            numero_siresp TEXT,
            guarnicao TEXT,
            combustivel TEXT,
            capacidade_agua TEXT,
            capacidade_espumifero TEXT,
            tracao TEXT,
            entrada_servico TEXT,
            comprimento TEXT,
            largura TEXT,
            altura TEXT,
            verificador TEXT,
            data_verificacao TEXT
        )
    """)

    # --- Tabela dos cofres/compartimentos ---
    # "FOREIGN KEY (veiculo_id) REFERENCES veiculos (id)" diz ao banco:
    # "todo cofre tem que pertencer a um veículo que exista de verdade"
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cofres (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            veiculo_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            FOREIGN KEY (veiculo_id) REFERENCES veiculos (id)
        )
    """)

    # --- Tabela dos materiais dentro de cada cofre ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS materiais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cofre_id INTEGER NOT NULL,
            quantidade INTEGER NOT NULL,
            descricao TEXT NOT NULL,
            FOREIGN KEY (cofre_id) REFERENCES cofres (id)
        )
    """)

    # --- Tabela dos usuários do Comando (login) ---
    # Mesma estrutura da tabela "usuarios" do api-cadastro-login.
    # UNIQUE no email: o banco recusa dois usuários com o mesmo email.
    # senha_hash: NUNCA a senha em texto puro, só o hash do bcrypt.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comando (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            senha_hash TEXT NOT NULL
        )
    """)

    conexao.commit()
    conexao.close()
    print("Tabelas 'veiculos', 'cofres', 'materiais' e 'comando' criadas (ou já existiam).")


if __name__ == "__main__":
    criar_tabelas()
