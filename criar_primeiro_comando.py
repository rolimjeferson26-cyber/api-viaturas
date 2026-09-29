"""
criar_primeiro_comando.py

Cria um usuário do Comando DIRETO no banco, sem passar pela API.

Por que existe: a rota POST /comando/cadastro exige token, e só quem
já é do Comando tem token. Então o PRIMEIRO usuário tem que nascer
por fora da API - é para isso que serve este script.

Como usar (dentro da pasta api-viaturas):
    ./venv/bin/python criar_primeiro_comando.py

Ele pergunta nome, email e senha no terminal. A senha não aparece
enquanto você digita (é normal, igual ao sudo do Linux).
"""

import sqlite3
from getpass import getpass

import bcrypt

from database import criar_conexao, criar_tabelas


def main():
    criar_tabelas()  # garante que a tabela "comando" existe

    nome = input("Nome: ").strip()
    email = input("Email: ").strip()
    # getpass = input() que esconde o que é digitado
    senha = getpass("Senha: ")
    confirmacao = getpass("Repita a senha: ")

    if not nome or not email or not senha:
        print("Erro: nome, email e senha são obrigatórios.")
        return

    if senha != confirmacao:
        print("Erro: as senhas não conferem.")
        return

    # Mesmo hash da rota /comando/cadastro
    senha_hash = bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt())

    conexao = criar_conexao()
    try:
        cursor = conexao.execute(
            "INSERT INTO comando (nome, email, senha_hash) VALUES (?, ?, ?)",
            (nome, email, senha_hash.decode("utf-8")),
        )
        conexao.commit()
    except sqlite3.IntegrityError:
        print(f"Erro: o email {email} já está cadastrado.")
        return
    finally:
        # "finally" roda sempre, com erro ou sem: a conexão nunca fica aberta
        conexao.close()

    print(f"Usuário do Comando criado: {nome} <{email}> (id={cursor.lastrowid})")
    print("Agora já dá pra fazer POST /login com esse email e senha.")


if __name__ == "__main__":
    main()
