"""
app.py

Rotas da API:

Frontend:
- GET  /                   -> a página (static/index.html + style.css + app.js)

Consulta (abertas, sem login - modo consulta para os bombeiros):
- GET  /veiculos           -> lista todas as viaturas
- GET  /veiculos?tipo=VSAT -> lista só as viaturas daquele tipo
- GET  /veiculos/<id>      -> detalhe completo: ficha + cofres + materiais
  Sem login, matrícula e nº SIRESP ficam de fora. Com o token do
  Comando, vem tudo.

Autenticação do Comando:
- POST /login              -> email + senha -> devolve token JWT e nome
- POST /comando/cadastro   -> PROTEGIDA: um usuário do Comando cadastra
                              outro. O PRIMEIRO usuário é criado com o
                              script criar_primeiro_comando.py

Alteração (PROTEGIDAS: exigem token do Comando):
- POST   /veiculos                -> cria viatura nova (só a ficha técnica)
- PUT    /veiculos/<id>           -> edita a ficha técnica de uma viatura
- POST   /veiculos/<id>/cofres    -> cria um cofre numa viatura
- POST   /cofres/<id>/materiais   -> adiciona um material a um cofre
- PUT    /materiais/<id>          -> edita quantidade e/ou descrição
- DELETE /materiais/<id>          -> remove um material
"""

import os
import sqlite3
import datetime
from functools import wraps

import bcrypt
import jwt
from dotenv import load_dotenv
from flask import Flask, jsonify, request

from database import criar_conexao, criar_tabelas

# Lê o arquivo .env (se existir) e coloca o que está nele nas
# variáveis de ambiente. Se o .env não existir (ex: no Render), não dá
# erro: as variáveis vêm do painel do servidor. E se uma variável já
# existir no ambiente, o .env NÃO a substitui.
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")

# Sem SECRET_KEY não dá pra assinar nem conferir tokens. Melhor a API
# nem arrancar do que dar um erro confuso só na hora do login.
if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY não encontrada. No seu PC: confira o arquivo .env. "
        "No servidor: cadastre a variável SECRET_KEY no painel."
    )

app = Flask(__name__)

# Por padrão o Flask troca acentos por códigos (ex: "Água" vira
# "\u00c1gua"). Desligando isso, o JSON sai legível.
app.json.ensure_ascii = False

# Garante que todas as tabelas existem (inclusive a nova "comando")
criar_tabelas()

# Colunas da ficha técnica que o Comando pode preencher/editar.
# O "id" fica de fora de propósito: quem gera o id é o banco.
COLUNAS_VEICULO = [
    "quartel", "codigo", "identificacao", "tipo", "marca", "modelo",
    "matricula", "numero_siresp", "guarnicao", "combustivel",
    "capacidade_agua", "capacidade_espumifero", "tracao",
    "entrada_servico", "comprimento", "largura", "altura",
    "verificador", "data_verificacao",
]

# Campos da ficha que SÓ o Comando (logado) pode ver. Nas consultas
# sem login eles são retirados da resposta. Para esconder mais algum
# campo no futuro, basta acrescentar o nome aqui.
CAMPOS_SENSIVEIS = ["matricula", "numero_siresp"]

# Mesma ideia para os materiais: só esses campos podem ser editados
COLUNAS_MATERIAL = ["quantidade", "descricao"]


def quantidade_valida(valor):
    """
    True se o valor é um número inteiro maior que zero.

    O "isinstance(valor, bool)" está aí por uma pegadinha do Python:
    True e False também contam como int (True == 1). Sem essa linha,
    {"quantidade": true} passaria como quantidade 1.
    """
    if isinstance(valor, bool) or not isinstance(valor, int):
        return False
    return valor > 0


def ler_token():
    """
    Lê e confere o token JWT do cabeçalho "Authorization".

    Devolve um par (dados_do_token, erro):
    - token válido       -> (dados, None)
    - nenhum token veio  -> (None, None)
    - token com problema -> (None, "mensagem de erro")

    Fica separado dos decorators para os dois (obrigatório e
    opcional) usarem exatamente a mesma verificação.
    """
    # O token vem no cabeçalho (header) HTTP "Authorization",
    # no formato: "Bearer <token>"
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        return None, None

    # auth_header é algo como "Bearer eyJhbGci..."
    # .split() separa por espaço, e pegamos a segunda parte (o token)
    try:
        token = auth_header.split(" ")[1]
    except IndexError:
        return None, "formato do token inválido"

    try:
        # jwt.decode verifica a assinatura (usando a mesma SECRET_KEY
        # que usamos pra criar o token) e também confere o "exp"
        # (data de expiração) automaticamente
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"]), None
    except jwt.ExpiredSignatureError:
        return None, "token expirado, faça login novamente"
    except jwt.InvalidTokenError:
        return None, "token inválido"


def token_obrigatorio(funcao):
    """
    Decorator: verifica se a requisição trouxe um token JWT válido
    ANTES de deixar a rota protegida executar.

    Como usar: coloca @token_obrigatorio em cima de qualquer rota
    que só deve funcionar pra quem está logado.
    """

    @wraps(funcao)
    def rota_protegida(*args, **kwargs):
        dados_token, erro = ler_token()

        if erro:
            return jsonify({"erro": erro}), 401
        if dados_token is None:
            return jsonify({"erro": "token não fornecido"}), 401

        # Guardamos os dados do usuário (extraídos do token) para a
        # rota poder usar, sem precisar consultar o banco de novo
        request.usuario = dados_token

        return funcao(*args, **kwargs)

    return rota_protegida


def token_opcional(funcao):
    """
    Decorator para rotas ABERTAS que mostram mais coisas a quem está
    logado (ex: a consulta de viaturas).

    - Sem token        -> a rota roda com request.usuario = None
    - Token válido     -> a rota roda com request.usuario = dados
    - Token com problema -> 401. Assim o frontend fica sabendo que o
      login expirou, em vez de o Comando ver a ficha "cortada" sem
      entender porquê.
    """

    @wraps(funcao)
    def rota(*args, **kwargs):
        dados_token, erro = ler_token()

        if erro:
            return jsonify({"erro": erro}), 401

        request.usuario = dados_token
        return funcao(*args, **kwargs)

    return rota


def esconder_campos_sensiveis(veiculo):
    """
    Tira da viatura os campos que só o Comando pode ver, se quem
    pediu não está logado. Altera o dicionário recebido.
    """
    if request.usuario is None:
        for campo in CAMPOS_SENSIVEIS:
            # pop(campo, None): remove se existir, sem dar erro se não
            veiculo.pop(campo, None)


# =====================================================================
# FRONTEND
# =====================================================================
@app.route("/")
def pagina_inicial():
    """
    Entrega a página do frontend (static/index.html).

    O Flask já serve sozinho tudo o que está na pasta "static" no
    endereço /static/... (é daí que o index.html puxa o style.css e o
    app.js). Esta rota só faz o endereço principal (/) abrir a página.
    """
    return app.send_static_file("index.html")


# =====================================================================
# AUTENTICAÇÃO DO COMANDO
# =====================================================================
@app.route("/comando/cadastro", methods=["POST"])
@token_obrigatorio
def cadastro_comando():
    """
    Cria um usuário do Comando. Exige token: só quem já é do Comando
    pode cadastrar outro.

    E o primeiro usuário, se ninguém tem token ainda? Esse é criado
    direto no banco pelo script criar_primeiro_comando.py.
    """
    # get_json(silent=True): se o corpo não for JSON, devolve None em
    # vez de estourar um erro. O "or {}" transforma None em dicionário
    # vazio, e aí caímos na mensagem de "obrigatórios" abaixo.
    dados = request.get_json(silent=True) or {}
    nome = dados.get("nome")
    email = dados.get("email")
    senha = dados.get("senha")

    if not nome or not email or not senha:
        return jsonify({"erro": "nome, email e senha são obrigatórios"}), 400

    senha_hash = bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt())

    conexao = criar_conexao()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            "INSERT INTO comando (nome, email, senha_hash) VALUES (?, ?, ?)",
            (nome, email, senha_hash.decode("utf-8")),
        )
        conexao.commit()
    except sqlite3.IntegrityError:
        # IntegrityError = o banco recusou por quebrar uma regra
        # (aqui, o UNIQUE do email)
        conexao.close()
        return jsonify({"erro": "email já cadastrado"}), 409

    novo_id = cursor.lastrowid
    conexao.close()

    return jsonify({"id": novo_id, "nome": nome, "email": email}), 201


@app.route("/login", methods=["POST"])
def login():
    dados = request.get_json(silent=True) or {}
    email = dados.get("email")
    senha = dados.get("senha")

    if not email or not senha:
        return jsonify({"erro": "email e senha são obrigatórios"}), 400

    conexao = criar_conexao()
    cursor = conexao.cursor()
    cursor.execute(
        "SELECT id, nome, senha_hash FROM comando WHERE email = ?", (email,)
    )
    usuario = cursor.fetchone()
    conexao.close()

    # Mesma mensagem para "email não existe" e "senha errada": assim
    # quem estiver tentando adivinhar não descobre quais emails existem
    if usuario is None:
        return jsonify({"erro": "email ou senha inválidos"}), 401

    usuario_id, nome, senha_hash = usuario

    senha_confere = bcrypt.checkpw(
        senha.encode("utf-8"), senha_hash.encode("utf-8")
    )

    if not senha_confere:
        return jsonify({"erro": "email ou senha inválidos"}), 401

    payload = {
        "usuario_id": usuario_id,
        "nome": nome,
        # datetime.now(timezone.utc) é o jeito atual de pegar a hora
        # UTC (o utcnow() do projeto anterior está obsoleto no Python 3.12)
        "exp": datetime.datetime.now(datetime.timezone.utc)
               + datetime.timedelta(hours=2),
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

    # O nome vai junto para o frontend poder mostrar "Logado como ..."
    return jsonify({"token": token, "nome": nome}), 200


# =====================================================================
# VIATURAS
# =====================================================================
@app.route("/veiculos", methods=["GET"])
@token_opcional
def listar_veiculos():
    """
    Devolve a lista de viaturas com os dados principais.
    O detalhe completo (cofres + materiais) fica na rota
    GET /veiculos/<id>.

    Sem login, a matrícula não vem (ver CAMPOS_SENSIVEIS).

    Filtro opcional pela URL: /veiculos?tipo=VSAT devolve só as VSAT.
    Sem o "?tipo=...", devolve todas, como antes.
    """
    # request.args são os parâmetros que vêm depois do "?" na URL.
    # .get("tipo") devolve None se o parâmetro não foi enviado.
    tipo = request.args.get("tipo")

    conexao = criar_conexao()

    # row_factory = sqlite3.Row faz cada linha do resultado se
    # comportar como um dicionário: dá pra fazer linha["marca"] em
    # vez de linha[4]. Assim fica fácil transformar em JSON.
    conexao.row_factory = sqlite3.Row

    if tipo:
        # .strip().upper(): aceita "vsat" ou " VSAT " e procura "VSAT",
        # que é como os tipos estão gravados no banco.
        # O "?" continua protegendo contra SQL injection: nunca colamos
        # o texto da URL direto dentro do SQL.
        linhas = conexao.execute("""
            SELECT id, quartel, codigo, identificacao, tipo, marca, modelo, matricula
            FROM veiculos
            WHERE tipo = ?
            ORDER BY identificacao
        """, (tipo.strip().upper(),)).fetchall()
    else:
        linhas = conexao.execute("""
            SELECT id, quartel, codigo, identificacao, tipo, marca, modelo, matricula
            FROM veiculos
            ORDER BY identificacao
        """).fetchall()
    conexao.close()

    # Converte cada linha em dicionário -> jsonify transforma em JSON.
    # Se o filtro não achar nada, devolve lista vazia [] (não é erro).
    veiculos = [dict(linha) for linha in linhas]
    for veiculo in veiculos:
        esconder_campos_sensiveis(veiculo)

    return jsonify(veiculos), 200


@app.route("/veiculos/<int:veiculo_id>", methods=["GET"])
@token_opcional
def detalhe_veiculo(veiculo_id):
    """
    Devolve a ficha técnica completa da viatura + todos os cofres
    + todos os materiais de cada cofre.

    Sem login, matrícula e nº SIRESP não vêm (ver CAMPOS_SENSIVEIS).

    O <int:veiculo_id> na rota pega o número da URL: em /veiculos/1,
    veiculo_id vale 1. O "int:" garante que só números são aceites
    (/veiculos/abc dá 404 automaticamente).
    """
    conexao = criar_conexao()
    conexao.row_factory = sqlite3.Row

    # 1) Ficha técnica
    veiculo = conexao.execute(
        "SELECT * FROM veiculos WHERE id = ?", (veiculo_id,)
    ).fetchone()

    if veiculo is None:
        conexao.close()
        return jsonify({"erro": "viatura não encontrada"}), 404

    # 2) Cofres + materiais numa só consulta (o JOIN).
    # LEFT JOIN em vez de JOIN: se um cofre estiver vazio (sem
    # materiais), ele continua a aparecer no resultado.
    linhas = conexao.execute("""
        SELECT cofres.id   AS cofre_id,
               cofres.nome AS cofre_nome,
               materiais.id AS material_id,
               materiais.quantidade,
               materiais.descricao
        FROM cofres
        LEFT JOIN materiais ON materiais.cofre_id = cofres.id
        WHERE cofres.veiculo_id = ?
        ORDER BY cofres.id, materiais.id
    """, (veiculo_id,)).fetchall()
    conexao.close()

    # 3) O JOIN devolve uma tabela "achatada" (1 linha por material,
    # com o nome do cofre repetido). Aqui agrupamos por cofre para o
    # JSON ficar em árvore: viatura -> cofres -> materiais.
    cofres = {}
    for linha in linhas:
        cofre_id = linha["cofre_id"]
        if cofre_id not in cofres:
            cofres[cofre_id] = {
                "id": cofre_id,
                "nome": linha["cofre_nome"],
                "materiais": [],
            }
        if linha["material_id"] is not None:  # cofre vazio -> sem material
            cofres[cofre_id]["materiais"].append({
                "id": linha["material_id"],
                "quantidade": linha["quantidade"],
                "descricao": linha["descricao"],
            })

    resultado = dict(veiculo)
    esconder_campos_sensiveis(resultado)
    resultado["cofres"] = list(cofres.values())

    return jsonify(resultado), 200


@app.route("/veiculos", methods=["POST"])
@token_obrigatorio
def criar_veiculo():
    """
    Cria uma viatura nova (só a ficha técnica; cofres e materiais
    ficam para um próximo passo). Exige token do Comando.

    Corpo JSON: qualquer coluna de COLUNAS_VEICULO.
    Obrigatórios: identificacao e tipo.
    """
    dados = request.get_json(silent=True) or {}

    if not dados.get("identificacao") or not dados.get("tipo"):
        return jsonify({"erro": "identificacao e tipo são obrigatórios"}), 400

    # Fica só com as chaves que são colunas conhecidas. Qualquer outra
    # coisa que vier no JSON (ex: "id", "hacker": ...) é ignorada.
    # Isso é importante porque os NOMES das colunas vão entrar no SQL
    # por f-string (o "?" só protege VALORES, não nomes de colunas).
    veiculo = {col: dados[col] for col in COLUNAS_VEICULO if col in dados}
    veiculo["tipo"] = veiculo["tipo"].strip().upper()  # igual ao filtro

    colunas = ", ".join(veiculo.keys())
    marcadores = ", ".join("?" for _ in veiculo)

    conexao = criar_conexao()
    cursor = conexao.cursor()
    cursor.execute(
        f"INSERT INTO veiculos ({colunas}) VALUES ({marcadores})",
        tuple(veiculo.values()),
    )
    conexao.commit()
    novo_id = cursor.lastrowid
    conexao.close()

    veiculo["id"] = novo_id
    return jsonify(veiculo), 201


@app.route("/veiculos/<int:veiculo_id>", methods=["PUT"])
@token_obrigatorio
def editar_veiculo(veiculo_id):
    """
    Edita a ficha técnica de uma viatura. Exige token do Comando.

    Só precisa mandar os campos que mudaram. Ex: {"verificador": "..."}
    altera só o verificador; o resto fica como estava.
    """
    dados = request.get_json(silent=True) or {}

    # Mesmo filtro de segurança do POST: só colunas conhecidas
    alteracoes = {col: dados[col] for col in COLUNAS_VEICULO if col in dados}

    if not alteracoes:
        return jsonify({"erro": "nenhum campo válido para alterar"}), 400

    if "tipo" in alteracoes:
        if not alteracoes["tipo"]:
            return jsonify({"erro": "tipo não pode ficar vazio"}), 400
        alteracoes["tipo"] = alteracoes["tipo"].strip().upper()

    # Monta "marca = ?, modelo = ?" só com os campos enviados
    trechos_set = ", ".join(f"{col} = ?" for col in alteracoes)

    conexao = criar_conexao()
    conexao.row_factory = sqlite3.Row
    cursor = conexao.cursor()
    cursor.execute(
        f"UPDATE veiculos SET {trechos_set} WHERE id = ?",
        (*alteracoes.values(), veiculo_id),
    )

    # rowcount = quantas linhas o UPDATE alterou. 0 = esse id não existe
    if cursor.rowcount == 0:
        conexao.close()
        return jsonify({"erro": "viatura não encontrada"}), 404

    conexao.commit()
    atualizado = cursor.execute(
        "SELECT * FROM veiculos WHERE id = ?", (veiculo_id,)
    ).fetchone()
    conexao.close()

    return jsonify(dict(atualizado)), 200


# =====================================================================
# COFRES E MATERIAIS
# =====================================================================
@app.route("/veiculos/<int:veiculo_id>/cofres", methods=["POST"])
@token_obrigatorio
def criar_cofre(veiculo_id):
    """
    Cria um cofre novo numa viatura. Exige token do Comando.
    Corpo JSON: {"nome": "Cofre 8"}
    """
    dados = request.get_json(silent=True) or {}
    nome = dados.get("nome")

    if not nome:
        return jsonify({"erro": "nome é obrigatório"}), 400

    conexao = criar_conexao()
    cursor = conexao.cursor()

    # Confere se a viatura existe antes de pendurar um cofre nela
    cursor.execute("SELECT id FROM veiculos WHERE id = ?", (veiculo_id,))
    if cursor.fetchone() is None:
        conexao.close()
        return jsonify({"erro": "viatura não encontrada"}), 404

    cursor.execute(
        "INSERT INTO cofres (veiculo_id, nome) VALUES (?, ?)",
        (veiculo_id, nome),
    )
    conexao.commit()
    novo_id = cursor.lastrowid
    conexao.close()

    return jsonify({"id": novo_id, "veiculo_id": veiculo_id, "nome": nome}), 201


@app.route("/cofres/<int:cofre_id>/materiais", methods=["POST"])
@token_obrigatorio
def criar_material(cofre_id):
    """
    Adiciona um material a um cofre. Exige token do Comando.
    Corpo JSON: {"quantidade": 2, "descricao": "Extintor CO2"}
    """
    dados = request.get_json(silent=True) or {}
    quantidade = dados.get("quantidade")
    descricao = dados.get("descricao")

    if quantidade is None or not descricao:
        return jsonify({"erro": "quantidade e descricao são obrigatórios"}), 400

    if not quantidade_valida(quantidade):
        return jsonify({"erro": "quantidade deve ser um número inteiro maior que zero"}), 400

    conexao = criar_conexao()
    cursor = conexao.cursor()

    cursor.execute("SELECT id FROM cofres WHERE id = ?", (cofre_id,))
    if cursor.fetchone() is None:
        conexao.close()
        return jsonify({"erro": "cofre não encontrado"}), 404

    cursor.execute(
        "INSERT INTO materiais (cofre_id, quantidade, descricao) VALUES (?, ?, ?)",
        (cofre_id, quantidade, descricao),
    )
    conexao.commit()
    novo_id = cursor.lastrowid
    conexao.close()

    return jsonify({
        "id": novo_id,
        "cofre_id": cofre_id,
        "quantidade": quantidade,
        "descricao": descricao,
    }), 201


@app.route("/materiais/<int:material_id>", methods=["PUT"])
@token_obrigatorio
def editar_material(material_id):
    """
    Edita quantidade e/ou descrição de um material. Exige token.
    Mesmo padrão do PUT /veiculos/<id>: só manda o que mudou.
    """
    dados = request.get_json(silent=True) or {}

    # Mesmo filtro de segurança: só colunas conhecidas
    alteracoes = {col: dados[col] for col in COLUNAS_MATERIAL if col in dados}

    if not alteracoes:
        return jsonify({"erro": "nenhum campo válido para alterar"}), 400

    if "quantidade" in alteracoes and not quantidade_valida(alteracoes["quantidade"]):
        return jsonify({"erro": "quantidade deve ser um número inteiro maior que zero"}), 400

    if "descricao" in alteracoes and not alteracoes["descricao"]:
        return jsonify({"erro": "descricao não pode ficar vazia"}), 400

    trechos_set = ", ".join(f"{col} = ?" for col in alteracoes)

    conexao = criar_conexao()
    conexao.row_factory = sqlite3.Row
    cursor = conexao.cursor()
    cursor.execute(
        f"UPDATE materiais SET {trechos_set} WHERE id = ?",
        (*alteracoes.values(), material_id),
    )

    if cursor.rowcount == 0:
        conexao.close()
        return jsonify({"erro": "material não encontrado"}), 404

    conexao.commit()
    atualizado = cursor.execute(
        "SELECT * FROM materiais WHERE id = ?", (material_id,)
    ).fetchone()
    conexao.close()

    return jsonify(dict(atualizado)), 200


@app.route("/materiais/<int:material_id>", methods=["DELETE"])
@token_obrigatorio
def remover_material(material_id):
    """Remove um material de vez. Exige token do Comando."""
    conexao = criar_conexao()
    cursor = conexao.cursor()
    cursor.execute("DELETE FROM materiais WHERE id = ?", (material_id,))

    # Mesmo truque do PUT: 0 linhas apagadas = esse id não existe
    if cursor.rowcount == 0:
        conexao.close()
        return jsonify({"erro": "material não encontrado"}), 404

    conexao.commit()
    conexao.close()

    return jsonify({"mensagem": "material removido", "id": material_id}), 200


if __name__ == "__main__":
    # Este bloco só roda com "python app.py" (desenvolvimento).
    # Em produção quem arranca a API é o Gunicorn (ver Procfile), e
    # ele importa o "app" direto, sem passar por aqui.
    #
    # O debug só liga se a variável FLASK_DEBUG for "1" (o seu .env
    # local tem FLASK_DEBUG=1). Sem ela, fica DESLIGADO: assim, se
    # alguém esquecer de configurar, o servidor nasce seguro.
    # (Com debug ligado, a página de erro permite executar código
    # Python no servidor - nunca pode estar ligado na internet.)
    debug = os.getenv("FLASK_DEBUG") == "1"
    app.run(debug=debug, port=5000)
