"""
database.py

Cria a estrutura do banco de dados do projeto de viaturas.
O banco é um PostgreSQL (hoje no Neon), e o endereço dele vem da
variável de ambiente DATABASE_URL (no seu PC, dentro do .env).

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

import os

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Lê o .env (se existir). Em produção a DATABASE_URL vem do painel.
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")


def criar_conexao():
    """
    Abre uma conexão com o PostgreSQL.

    cursor_factory=RealDictCursor faz cada linha do resultado vir
    como dicionário: linha["marca"] em vez de linha[4]. É o mesmo
    papel que o "row_factory = sqlite3.Row" fazia no SQLite, só que
    agora vale para TODAS as consultas, sem precisar ligar em cada rota.

    Não há mais "PRAGMA foreign_keys = ON": o PostgreSQL fiscaliza
    as foreign keys sempre, sem precisar pedir.
    """
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL não encontrada. No seu PC: confira o arquivo .env. "
            "No servidor: cadastre a variável DATABASE_URL no painel."
        )
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def criar_tabelas():
    conexao = criar_conexao()
    cursor = conexao.cursor()

    # --- Tabela dos veículos (ficha técnica) ---
    # SERIAL = número inteiro que o banco preenche sozinho (1, 2, 3...).
    # É o equivalente do "INTEGER PRIMARY KEY AUTOINCREMENT" do SQLite.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS veiculos (
            id SERIAL PRIMARY KEY,
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
            id SERIAL PRIMARY KEY,
            veiculo_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            FOREIGN KEY (veiculo_id) REFERENCES veiculos (id)
        )
    """)

    # --- Tabela dos materiais dentro de cada cofre ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS materiais (
            id SERIAL PRIMARY KEY,
            cofre_id INTEGER NOT NULL,
            quantidade INTEGER NOT NULL,
            descricao TEXT NOT NULL,
            FOREIGN KEY (cofre_id) REFERENCES cofres (id)
        )
    """)

    # --- Tabela dos usuários do Comando (login) ---
    # UNIQUE no email: o banco recusa dois usuários com o mesmo email.
    # senha_hash: NUNCA a senha em texto puro, só o hash do bcrypt.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comando (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            senha_hash TEXT NOT NULL
        )
    """)

    conexao.commit()
    conexao.close()


if __name__ == "__main__":
    criar_tabelas()
    print("Tabelas 'veiculos', 'cofres', 'materiais' e 'comando' criadas (ou já existiam).")
