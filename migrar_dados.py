"""
migrar_dados.py

Copia TUDO do banco antigo (SQLite, arquivo viaturas.db) para o banco
novo (PostgreSQL, endereço em DATABASE_URL no .env).

Como usar (dentro da pasta api-viaturas):
    ./venv/bin/python migrar_dados.py

Garantias:
- O viaturas.db é aberto em modo SÓ LEITURA: o script não consegue
  alterar o arquivo, nem por engano. Ele continua a ser o seu backup.
- Os ids são copiados iguais (viatura 1 continua a ser 1, cofre 7
  continua a ser 7...). Assim as ligações cofre -> viatura e
  material -> cofre continuam certas sem precisar "traduzir" nada.
- Tudo acontece numa única transação: ou copia tudo, ou (se der
  qualquer erro no meio) não copia nada. Nunca fica meio migrado.
- Se o PostgreSQL já tiver dados, o script PARA sem mexer em nada.
  Para apagar o que está lá e copiar de novo, use:
      ./venv/bin/python migrar_dados.py --apagar-antes
  (ele mostra o que vai apagar e pede confirmação).
"""

import sqlite3
import sys

from database import criar_conexao, criar_tabelas

ARQUIVO_SQLITE = "viaturas.db"

# A ORDEM importa: primeiro quem não depende de ninguém, depois quem
# aponta para as anteriores (um cofre precisa da viatura já existir,
# um material precisa do cofre já existir).
TABELAS = ["comando", "veiculos", "cofres", "materiais"]


def abrir_sqlite_so_leitura():
    """
    "mode=ro" (read-only) = só leitura. Se o arquivo não existir, dá
    erro em vez de criar um banco vazio novo (que é o que o
    sqlite3.connect normal faria).
    """
    try:
        return sqlite3.connect(f"file:{ARQUIVO_SQLITE}?mode=ro", uri=True)
    except sqlite3.OperationalError:
        sys.exit(f"Não encontrei o {ARQUIVO_SQLITE} nesta pasta.")


def contar_linhas(cursor_pg):
    """Devolve {tabela: quantidade de linhas} no PostgreSQL."""
    contagem = {}
    for tabela in TABELAS:
        cursor_pg.execute(f"SELECT COUNT(*) AS total FROM {tabela}")
        contagem[tabela] = cursor_pg.fetchone()["total"]
    return contagem


def copiar_tabela(sqlite_con, cursor_pg, tabela):
    """Lê todas as linhas de uma tabela do SQLite e insere no PostgreSQL."""
    cursor_sqlite = sqlite_con.execute(f"SELECT * FROM {tabela} ORDER BY id")

    # cursor.description = informação das colunas do resultado;
    # o [0] de cada item é o nome da coluna
    colunas = [coluna[0] for coluna in cursor_sqlite.description]
    linhas = cursor_sqlite.fetchall()

    lista_colunas = ", ".join(colunas)
    marcadores = ", ".join("%s" for _ in colunas)
    cursor_pg.executemany(
        f"INSERT INTO {tabela} ({lista_colunas}) VALUES ({marcadores})",
        linhas,
    )

    # Acerta o "contador" do SERIAL. Como inserimos os ids à mão, o
    # PostgreSQL não ficou sabendo que o 1, 2, 3... já foram usados:
    # o próximo INSERT da API tentaria usar id=1 de novo e daria erro.
    # setval diz a ele: "o próximo id livre é o maior que existe + 1".
    cursor_pg.execute(f"""
        SELECT setval(
            pg_get_serial_sequence('{tabela}', 'id'),
            COALESCE((SELECT MAX(id) FROM {tabela}), 0) + 1,
            false
        )
    """)

    return len(linhas)


def main():
    apagar_antes = "--apagar-antes" in sys.argv

    sqlite_con = abrir_sqlite_so_leitura()
    criar_tabelas()  # garante que as tabelas existem no PostgreSQL

    pg_con = criar_conexao()
    cursor_pg = pg_con.cursor()

    ja_existe = contar_linhas(cursor_pg)
    tem_dados = any(ja_existe.values())

    if tem_dados and not apagar_antes:
        print("O PostgreSQL JÁ TEM DADOS. Nada foi feito.")
        for tabela, total in ja_existe.items():
            print(f"  {tabela}: {total} linhas")
        print("\nSe a migração já foi feita, está tudo certo: não precisa rodar de novo.")
        print("Para APAGAR tudo no PostgreSQL e copiar de novo do viaturas.db:")
        print("  ./venv/bin/python migrar_dados.py --apagar-antes")
        pg_con.close()
        return

    if tem_dados and apagar_antes:
        print("ATENÇÃO: isto vai APAGAR no PostgreSQL:")
        for tabela, total in ja_existe.items():
            print(f"  {tabela}: {total} linhas")
        print("(o viaturas.db NÃO é tocado)")
        resposta = input('Digite "apagar" para confirmar: ').strip().lower()
        if resposta != "apagar":
            print("Cancelado. Nada foi feito.")
            pg_con.close()
            return
        # Ordem inversa: primeiro quem aponta (materiais), por último
        # quem é apontado. Senão a foreign key impede o DELETE.
        for tabela in reversed(TABELAS):
            cursor_pg.execute(f"DELETE FROM {tabela}")

    try:
        for tabela in TABELAS:
            total = copiar_tabela(sqlite_con, cursor_pg, tabela)
            print(f"  {tabela}: {total} linhas copiadas")

        # Conferência: as quantidades batem com o SQLite?
        depois = contar_linhas(cursor_pg)
        for tabela in TABELAS:
            no_sqlite = sqlite_con.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]
            if depois[tabela] != no_sqlite:
                raise RuntimeError(
                    f"{tabela}: SQLite tem {no_sqlite}, PostgreSQL ficou com {depois[tabela]}"
                )

        # Só aqui as mudanças ficam gravadas de verdade
        pg_con.commit()
        print("\nMigração concluída. As quantidades conferem com o viaturas.db.")
    except Exception as erro:
        # Qualquer erro: desfaz TUDO o que foi feito nesta execução
        pg_con.rollback()
        print(f"\nERRO: {erro}")
        print("Nada foi gravado no PostgreSQL (a transação foi desfeita).")
        sys.exit(1)
    finally:
        pg_con.close()
        sqlite_con.close()


if __name__ == "__main__":
    main()
