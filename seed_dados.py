"""
seed_dados.py

Insere no banco os dados reais da viatura VSAT-01 (C.B. Murtosa),
transcritos da ficha/checklist física (verificação de 15/01/2026).

"Seed" (semente) é o nome que se dá a um script que popula o banco
com dados iniciais.

Ordem das inserções (e porquê):
1. Primeiro o veículo  -> ele ganha um id (ex: 1)
2. Depois cada cofre   -> usa esse id do veículo em veiculo_id
3. Depois os materiais -> usam o id do cofre em cofre_id

Não dá pra inserir um cofre antes do veículo existir, porque o cofre
precisa saber a QUEM pertence (é a foreign key).

Itens agrupados na ficha (ex: "Saco riscos elétricos 30Kv", que tem
vários itens dentro) ficam com o nome do grupo entre [colchetes] no
início da descrição, porque a nossa tabela não tem "sub-cofres".
"""

import json
import sys

from database import criar_conexao, criar_tabelas

# Arquivo com os dados sensíveis (matrícula, nº SIRESP e nome do
# verificador). Ele NÃO vai para o GitHub (está no .gitignore), igual
# ao .env. No repositório fica só o modelo dados_sensiveis.exemplo.json.
ARQUIVO_SENSIVEIS = "dados_sensiveis.json"


# ---------------------------------------------------------------------
# DADOS: ficha técnica
# ---------------------------------------------------------------------
VEICULO = {
    "quartel": "C.B. Murtosa",
    "codigo": "0125",
    "identificacao": "VSAT-01",
    "tipo": "VSAT",
    "marca": "RENAULT",
    "modelo": "MIDLUM FPTL 240 E6",
    # matricula e numero_siresp vêm de dados_sensiveis.json
    "guarnicao": "6",
    "combustivel": "100 Lt. gasóleo",
    "capacidade_agua": "1800 Lt.",
    "capacidade_espumifero": "100 Lt",
    "tracao": "4x2 com bloqueio traseiro",
    "entrada_servico": "22/03/2019",
    "comprimento": "6400mm",
    "largura": "2350mm",
    "altura": "3150mm",
    # verificador também vem de dados_sensiveis.json (nome real)
    "data_verificacao": "15/01/2026",
}


# ---------------------------------------------------------------------
# DADOS: cofres e materiais
# Cada cofre é um par: (nome do cofre, lista de (quantidade, descrição))
# ---------------------------------------------------------------------
COFRES = [
    ("Cabine", [
        (1, "Rádio móvel banda Baixa YAESU 1011"),
        (1, "Rádio móvel ROB VERTEX VX 2200"),
        (1, "Rádio móvel SIRESP MOTOROLA"),
        (3, "Rádios portátil ROB"),
        (4, "Lanternas portáteis antideflagrantes"),
        (1, "Lanterna sinalização"),
        (1, "Conversor corrente 24V/230V 1000W"),
        (1, "Extintor 2 Kg Pó"),
        (1, "Emergency Plug"),
        (1, "Bolsa ferramentas Holmatro"),
        (3, "Espias de cintura"),
        (1, "Machado FORCE"),
        (1, "Hooligan cortadora"),
        (1, "Hooligan arrombador"),
        (1, "Caixa Luvas Nitrilo"),
        (1, "Mochila 1ºs socorros"),
        (1, "Colete extração"),
        (2, "Imobilizadores Cab."),
        (1, "Cinto tipo aranha"),
        (1, "Plano Duro flutuante"),
        (8, "Colares cervicais"),
        (1, "Maca tipo Pluma"),
        (1, "Saco Doc. SGO"),
        (1, "Saco Doc. Veículo"),
        (5, "ARICAS Drager"),
        (6, "Reservas ARICA"),
        (1, "Macaco do Veículo"),
        (1, "Escora da cabine"),
        (1, "Bolsa ferra. Veículo"),
        (2, "Cintas 6mt 6T"),
        (1, "Cinta 6mt 20T"),
        (6, "Sacos lixo grandes"),
        (1, "Extensão 220V 16A"),
        (1, "Roldana guincho"),
        (1, "Comando guincho"),
        (1, "Mangueira pneumática"),
        (1, "Cabo encosto rápido baterias veículo"),
        (1, "Chave rodas grande"),
    ]),

    ("Cofre 1", [
        (2, "Extintor CO2 2Kg"),
        (1, "Gerador 230V Lombardini MG7000"),
        (2, "Óculos proteção"),
        (2, "Tripés para projetores"),
        (1, "Chave de rodas pequena"),
        (2, "Bobines 25mt cabo elétrico com proteção 4x230V"),
        (1, "Caixa ferramentas Vito"),
        (1, "Tesoura corta arame grande, punhos isolados"),
        (1, "Extensão cabo elétrico com tomada (ATEX)"),
        (1, "Adaptador tomadas 16A para 220 normal"),
        (2, "Projetores 30W 6000k LED"),
        (1, "Carregador baterias CTEK MXT14"),
        (1, "Parafusadora Einhell"),
        (1, "Rebarbadora Einhell AXXIO 18/115 Q"),
        (2, "Discos rebarbadora"),
        (1, "Serra Sabre Einhell"),
        (2, "Lâminas sabre"),
        (1, "[Saco riscos elétricos 30Kv] Detetor de tensão luminoso"),
        (1, "[Saco riscos elétricos 30Kv] Croque isolado"),
        (1, "[Saco riscos elétricos 30Kv] Gancho de salvamento"),
        (1, "[Saco riscos elétricos 30Kv] Tesoura isolada"),
        (1, "[Saco riscos elétricos 30Kv] Par de luvas isoladas"),
        (1, "[Saco riscos elétricos 30Kv] Par de botins isolados"),
        (1, "[Saco riscos elétricos 30Kv] Rolo fita sinalização"),
        (1, "[Saco riscos elétricos 30Kv] Pó de talco"),
    ]),

    ("Cofre 2", [
        (2, "Calços de roda"),
        (2, "Macacos HI-LIFT 3 Toneladas"),
        (2, "Conjuntos de 2 Steps"),
        (2, "Conjuntos 5 Blocos 10 Cunhas"),
        (1, "Proteção rígida (madeira)"),
        (2, "Barreiras proteção rígida transparente Holmatro"),
        (2, "Proteções maneáveis transparentes (vítimas)"),
        (2, "Lonas para criar área trabalho"),
        (2, "Almofadas alta pressão 200KN / 120KN Holmatro"),
        (1, "Kit em caixa com 1 comando, 2 mangueiras, 1 regulador de pressão, "
            "1 ponteira, 4 placas borracha neoprene"),
        (1, "Bomba de pedal Holmatro PA 18 F2 C CORE"),
        (1, "Mangueira hidráulica Holmatro CORE C05 ZU"),
        (1, "Caixa com acessórios escoramento PSH-1 e pregos"),
        (1, "Caixa com 10 coberturas proteção"),
        (1, "Caixa com cintas com roquete"),
        (2, "[Caixa] Cintas com roquete 2mt"),
        (2, "[Caixa] Cintas com roquete 6mt"),
        (2, "[Caixa] Cintas com roquete 8mt"),
    ]),

    ("Cofre 3", [
        (1, "Serra manual Madeira"),
        (1, "Motosserra de corrente"),
        (1, "Eletrobomba submersível"),
        (1, "Tirfor 16KN elevação 24KN tração c/cabo 20m e manilha própria"),
        (1, "Ventilador elétrico 230V ATEX pressão positiva / negativa "
            "Ramfan EFI 120XX"),  # CONFERIR: "Ramfan" ou "Ranfan"; "120XX" na ficha
        (1, "Manga Ventilador anti estática c/7,6mt /40cm"),
        (2, "Jerrican STIHL 5Lts Gasolina SC 98"),
        (1, "Jerrican STIHL 5Lts de Gasolina Mistura e óleo para corrente"),
        (1, "Caixa com 4 manilhas, 12 cintas de carga, 1 estropo de aço"),
        (1, "Extintor 6 Kg Pó Químico ABC"),
        (6, "Kits individuais de S. Grande ângulo"),
        (2, "Kits de grupo de S. Grande ângulo"),
        (3, "Kits com cabos de 100m"),
        (4, "Tapetes proteção cabos"),
    ]),

    ("Cofre 4", [
        (1, "Grupo Energético Holmatro SR 40 PC 2"),
        (1, "Suporte do RAM HRS 22"),
        (1, "Tesoura Holmatro CU3035"),
        (1, "Mini tesoura Holmatro CU4007C"),
        (1, "Expansor Holmatro SP5240"),
        (1, "Extensor RAM Holmatro RA3321"),
        (1, "Cilindro para extensor Holmatro"),
        (1, "Corta vidros Glass-Master"),
        (1, "Punção quebra vidros"),
        (1, "Corta cintos segurança"),
        (2, "Anuladores de airbag Holmatro"),
        (1, "Maço de borracha"),
        (1, "Pé de Cabra"),
        (1, "Marreta grande 2 Kg"),
        (1, 'Chave de grifos Heavy duty 36"'),
        (1, "Triângulo de Sinalização"),
        (2, 'Placas sinalização "ACIDENTE"'),
        (1, "Conjunto escoramento hidráulico PSH-1 (check list no saco Doc. SGO)"),
        (2, "Mangueiras hidráulicas Holmatro CORE C15OU e C15BU"),
        (2, "Escoras estabilização V-Strut"),
        (2, "Bombas manuais Holmatro PA 09 H 2 S 10 (escoras)"),
    ]),

    ("Cofre 5", [
        (1, "Motobomba Honda QP205SLT 480 l/m 9.5bar"),
        (2, "Lanços manga DN 25 storz D 25"),
        (4, "Lanços manga DN 45 storz C 52"),
        (1, "Transportador manual"),
        (1, "Lanço manga DN 70 storz B 75"),
        (2, "Estancadores DN45"),  # CONFERIR: na ficha está "Estançadores"
        (2, "Estancadores DN70"),  # CONFERIR: na ficha está "Estançadores"
        (1, "Disjuntor storz (B 75 para 2 x C 52)"),
        (1, "Agulheta storz D 25"),
        (1, "Agulheta storz C 52"),
        (1, "Agulheta storz B 75"),
        (1, "Agulheta Water shield storz C 52"),
        (1, "Monitor BLITZFIRE oscilante 2000 Lt/m com 1 cinta de segurança"),
        (1, "Agulheta Max force para monitor"),
        (1, "Disjuntor storz (C 52 para 2 x D 25)"),
        (1, "Adaptador storz C 52 para rosca fêmea SI"),
    ]),

    ("Cofre 6", [
        (2, "Jerrican 20Lt espumífero AFFF"),
        (2, "Recipientes com absorvente/antiderrapante"),
        (1, "Extintor 6Kg Pó Químico ABC"),
        (2, "Extintor 6Lt espuma AFFF"),
        (2, "Lanços Manga DN 25 storz D 25"),
        (4, "Lanços Manga DN 45 storz C 52"),
        (1, "Transportador manual"),
        (1, "Lanço Manga DN 70 storz B 75"),
        (2, "Tripés para placas sinalização de acidente"),
        (1, "Doseador espumífero Z2 + tubo aspiração"),
        (1, "Agulheta espuma média expansão M2 200 Lt/m"),
        (1, "Agulheta espuma baixa expansão S2 200 Lt/m"),
        (10, "Cones sinalização 50 Cm"),
        (2, "Rolos fita sinalizadora"),
    ]),

    ("Cofre 7", [
        (1, "Bomba Godiva Prima P2_2010 alta e baixa pressão e doseador espumífero"),
        (1, "Carretel elétrico Alta pressão 80m c/ manivela e agulheta storz D 25 "
            "sist. Homem morto"),
        (1, "Agulheta storz C 52"),
        (1, "Adaptador storz C 52 para rosca SI fêmea"),
        (1, "Adaptador storz C 52 para rosca SI macho"),
        (2, "Reduções storz B 75 para C 52"),
        (2, "Reduções storz C 52 para D 25"),
        (1, "Tampão storz B 75"),
        (2, "Chave Storz simples"),
        (2, "Chave Storz dupla"),
        (2, "Chave Boca-de-incêndio (Jacinto)"),
        (1, "Chave tipo cruz portinhola"),
        (1, "Chave artesanal"),
        (1, "Guincho elétrico"),
        (2, "Manilhas 8,5T"),
    ]),

    ("Acond. Superior", [
        (1, "Escada telescópica 14mt 3 lanços com 5,23mt"),
        (1, "Escada telescópica 8mt 3 lanços com 2,98mt lanço"),
        (1, "Escada Gancho 4,28mt"),
        (3, "Corpos chupadores DN110 C/2m STORZ"),
        (1, "Ralo com storz A 110"),
        (1, "Cesto proteção do Ralo"),
        (1, "Corpo chupador motobomba DN 45 storz C 52 com ralo"),
        (1, "Manga rígida DN 45 storz C 52 eletrobomba"),
        (1, "Croque"),
        (1, "Desforradeira"),
        (1, "Plataforma Resgate e Salvamento"),
        (1, "Estrado isolante 45Kva em saco próprio"),
        (1, "Cabo de aço 20 mt"),
    ]),

    ("Cofre Sup 1 e 2", [
        (2, "Pás de Bico"),
        (2, "Pás quadradas"),
        (2, "Vassouras"),
        (2, "Enxadas"),
        (1, "Machado 1 gume"),
        (1, "Alavanca grande"),
        (1, "Maca Resgate Ferno"),
        (1, "Kit c/ arnês da Maca resgate e cabos apoio"),
        # Na ficha: "8 - Barrotes madeira", divididos em 4 medidas de 2 cada
        (2, "[Cofre 2 escoramento] Barrotes madeira 60 x 10 x 10cm"),
        (2, "[Cofre 2 escoramento] Barrotes madeira 80 x 10 x 10cm"),
        (2, "[Cofre 2 escoramento] Barrotes madeira 120 x 10 x 10cm"),
        (2, "[Cofre 2 escoramento] Barrotes madeira 160 x 10 x 10cm"),
        (2, "[Cofre 2 escoramento] Calços madeira"),
        (4, "[Cofre 2 escoramento] Pranchas aglomerado marítimo 150 x 30 x 3,5cm"),
    ]),
]


# ---------------------------------------------------------------------
# FUNÇÕES
# ---------------------------------------------------------------------
def inserir_veiculo(cursor, veiculo):
    """Insere a ficha técnica e devolve o id gerado para o veículo."""
    colunas = ", ".join(veiculo.keys())            # "quartel, codigo, ..."
    marcadores = ", ".join("?" for _ in veiculo)   # "?, ?, ..."
    cursor.execute(
        f"INSERT INTO veiculos ({colunas}) VALUES ({marcadores})",
        tuple(veiculo.values()),
    )
    # lastrowid = o id que o AUTOINCREMENT acabou de gerar
    return cursor.lastrowid


def inserir_cofre_com_materiais(cursor, veiculo_id, nome_cofre, materiais):
    """Cria um cofre ligado ao veículo e insere todos os materiais dele."""
    cursor.execute(
        "INSERT INTO cofres (veiculo_id, nome) VALUES (?, ?)",
        (veiculo_id, nome_cofre),
    )
    cofre_id = cursor.lastrowid

    # executemany = mesmo INSERT repetido para cada item da lista
    cursor.executemany(
        "INSERT INTO materiais (cofre_id, quantidade, descricao) VALUES (?, ?, ?)",
        [(cofre_id, qtd, descricao) for qtd, descricao in materiais],
    )
    return cofre_id


def carregar_dados_sensiveis():
    """
    Lê dados_sensiveis.json e devolve um dicionário. Se o arquivo não
    existir, para o script com uma explicação (em vez de um erro feio).
    """
    try:
        with open(ARQUIVO_SENSIVEIS, encoding="utf-8") as arquivo:
            return json.load(arquivo)
    except FileNotFoundError:
        sys.exit(
            f"Arquivo {ARQUIVO_SENSIVEIS} não encontrado.\n"
            f"Copie dados_sensiveis.exemplo.json para {ARQUIVO_SENSIVEIS} "
            "e preencha com os dados reais."
        )


def main():
    # Junta a ficha pública com os dados sensíveis num só dicionário.
    # {**a, **b} = "tudo de a, mais tudo de b"
    veiculo = {**VEICULO, **carregar_dados_sensiveis()}

    criar_tabelas()  # garante que as tabelas existem

    conexao = criar_conexao()  # já vem com PRAGMA foreign_keys = ON
    cursor = conexao.cursor()

    # Evita duplicar a viatura se o script for rodado duas vezes
    cursor.execute(
        "SELECT id FROM veiculos WHERE matricula = ?", (veiculo["matricula"],)
    )
    if cursor.fetchone():
        print(f"Viatura {veiculo['identificacao']} já existe no banco. Nada foi inserido.")
        conexao.close()
        return

    veiculo_id = inserir_veiculo(cursor, veiculo)
    total_materiais = 0
    for nome_cofre, materiais in COFRES:
        inserir_cofre_com_materiais(cursor, veiculo_id, nome_cofre, materiais)
        total_materiais += len(materiais)
        print(f"  {nome_cofre}: {len(materiais)} itens")

    conexao.commit()  # só aqui as mudanças são gravadas de verdade
    conexao.close()
    print(
        f"Viatura {veiculo['identificacao']} inserida (id={veiculo_id}), "
        f"{len(COFRES)} cofres, {total_materiais} linhas de material."
    )


if __name__ == "__main__":
    main()
