/*
 * app.js - toda a lógica da página.
 *
 * Organização do arquivo (de cima para baixo):
 *   1. Sessão do Comando (token no sessionStorage)
 *   2. chamarApi(): a ÚNICA função que fala com o backend
 *   3. Estado da página (o que está aberto, o que está a ser editado)
 *   4. Funções que DESENHAM a página (geram HTML)
 *   5. Ações (o que acontece quando se clica em cada botão)
 *   6. Login / logout
 *   7. Arranque (o que roda quando a página abre)
 *
 * A ideia geral: guardamos o "estado" em variáveis (seção 3). Sempre
 * que algo muda, chamamos desenharLista(), que apaga a lista e
 * desenha tudo de novo a partir desse estado. Assim nunca há dúvida
 * sobre o que está na tela: é sempre o reflexo das variáveis.
 */


// =====================================================================
// 1. SESSÃO DO COMANDO
//
// sessionStorage é uma "gaveta" do navegador, separada por site, que
// guarda textos (chave -> valor). Diferente do localStorage, ela é
// esvaziada quando a aba/navegador é fechado. Por isso o login não
// fica "esquecido aberto" num computador do quartel.
// =====================================================================
function pegarToken() {
    // Devolve o token guardado, ou null se ninguém fez login
    return sessionStorage.getItem("token");
}

function pegarNome() {
    return sessionStorage.getItem("nome");
}

function estaLogado() {
    // Esta é a pergunta que a página faz para decidir se mostra ou
    // não os botões de edição.
    return pegarToken() !== null;
}

function guardarSessao(token, nome) {
    sessionStorage.setItem("token", token);
    sessionStorage.setItem("nome", nome);
}

function limparSessao() {
    sessionStorage.removeItem("token");
    sessionStorage.removeItem("nome");
}


// =====================================================================
// 2. chamarApi(): TODA conversa com o backend passa por aqui
//
// Vantagem de ter uma função só: o token é colocado no cabeçalho num
// único lugar, e o tratamento do 401 (token expirado) também.
//
// Uso:  const dados = await chamarApi("GET", "/veiculos");
//       await chamarApi("PUT", "/materiais/5", { quantidade: 3 });
// =====================================================================
async function chamarApi(metodo, url, corpo) {
    const opcoes = { method: metodo, headers: {} };

    // Se há token guardado, ele vai no cabeçalho Authorization,
    // no formato que o backend espera: "Bearer <token>"
    const token = pegarToken();
    if (token) {
        opcoes.headers["Authorization"] = "Bearer " + token;
    }

    // Se há dados para enviar, eles vão em JSON no corpo
    if (corpo !== undefined) {
        opcoes.headers["Content-Type"] = "application/json";
        opcoes.body = JSON.stringify(corpo);
    }

    let resposta;
    try {
        resposta = await fetch(url, opcoes);
    } catch (e) {
        // fetch só "estoura" quando nem chegou ao servidor
        throw new Error("Não foi possível falar com o servidor. A API está ligada?");
    }

    // Lê a resposta como JSON. O ".catch" cobre respostas sem JSON
    // (ex: uma página de erro em HTML); aí ficamos com {}.
    const dados = await resposta.json().catch(() => ({}));

    // 401 COM token = o token expirou ou é inválido.
    // Saímos do modo Comando e avisamos, em vez de falhar calados.
    // (401 SEM token é outra coisa, ex: senha errada no login, e
    // segue para o tratamento normal de erro logo abaixo.)
    if (resposta.status === 401 && token) {
        sairPorSessaoExpirada();

        const erro = new Error("sessão expirada");
        erro.sessaoExpirada = true;  // marca para tratarErro() não repetir o aviso
        throw erro;
    }

    // resposta.ok = status entre 200 e 299. Fora disso, é erro:
    // usamos a mensagem que o backend mandou em {"erro": "..."}.
    if (!resposta.ok) {
        throw new Error(dados.erro || "Erro " + resposta.status);
    }

    return dados;
}


// =====================================================================
// 3. ESTADO DA PÁGINA
// =====================================================================
let listaVeiculos = [];         // o que veio de GET /veiculos
let filtroTipo = "";            // texto do filtro ("" = sem filtro)
let veiculoAberto = null;       // id da viatura expandida (null = nenhuma)
let detalhe = null;             // o que veio de GET /veiculos/<id>
let cofresAbertos = new Set();  // ids dos cofres abertos no accordion
let editandoFicha = false;      // true = ficha em modo formulário
let materialEmEdicao = null;    // id do material a ter a quantidade editada

// Campos da ficha técnica, na ordem em que aparecem, com o nome
// "bonito" de cada um. Para mudar um rótulo, é só mudar aqui.
const CAMPOS_FICHA = [
    ["quartel", "Quartel"],
    ["codigo", "Código"],
    ["identificacao", "Identificação"],
    ["tipo", "Tipo"],
    ["marca", "Marca"],
    ["modelo", "Modelo"],
    ["matricula", "Matrícula"],
    ["numero_siresp", "Nº SIRESP"],
    ["guarnicao", "Guarnição"],
    ["combustivel", "Combustível"],
    ["capacidade_agua", "Capacidade de água"],
    ["capacidade_espumifero", "Capacidade de espumífero"],
    ["tracao", "Tração"],
    ["entrada_servico", "Entrada ao serviço"],
    ["comprimento", "Comprimento"],
    ["largura", "Largura"],
    ["altura", "Altura"],
    ["verificador", "Verificador"],
    ["data_verificacao", "Data de verificação"],
];


// =====================================================================
// 4. DESENHAR A PÁGINA
//
// Estas funções montam HTML como texto e colocam na página com
// innerHTML. Todo valor que vem do banco passa por esc() antes: se
// alguém gravasse "<script>..." numa descrição, isso apareceria como
// texto, em vez de ser executado pelo navegador.
// =====================================================================
function esc(valor) {
    if (valor === null || valor === undefined) {
        return "";
    }
    return String(valor)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

let temporizadorMensagem = null;

function mostrarMensagem(texto) {
    const caixa = document.getElementById("mensagem");
    caixa.textContent = texto;
    caixa.classList.remove("escondido");

    // Some sozinha depois de 6 segundos
    clearTimeout(temporizadorMensagem);
    temporizadorMensagem = setTimeout(() => caixa.classList.add("escondido"), 6000);
}

function tratarErro(erro) {
    // O aviso de sessão expirada já foi mostrado por sairPorSessaoExpirada()
    if (erro.sessaoExpirada) {
        return;
    }
    mostrarMensagem(erro.message);
}

// --- Topo: botão de login OU nome de quem está logado ---
function desenharTopo() {
    const area = document.getElementById("area-login");

    if (estaLogado()) {
        area.innerHTML = `
            <span class="usuario-logado">Logado como <strong>${esc(pegarNome())}</strong></span>
            <button class="secundario" onclick="sair()">Sair</button>
        `;
    } else {
        area.innerHTML = `<button onclick="abrirLogin()">Login Comando</button>`;
    }
}

// --- Lista de cards ---
function desenharLista() {
    const lista = document.getElementById("lista-veiculos");

    if (listaVeiculos.length === 0) {
        const complemento = filtroTipo ? ` do tipo "${esc(filtroTipo)}"` : "";
        lista.innerHTML = `<p class="vazio">Nenhuma viatura encontrada${complemento}.</p>`;
        return;
    }

    // .map() transforma cada viatura num pedaço de HTML;
    // .join("") cola todos os pedaços num texto só
    lista.innerHTML = listaVeiculos.map(desenharCard).join("");
}

function desenharCard(v) {
    const aberto = v.id === veiculoAberto;

    // A matrícula só vem da API quando o Comando está logado.
    // Se não veio, simplesmente não desenhamos nada no lugar.
    const matricula = v.matricula ? ` · ${esc(v.matricula)}` : "";

    let html = `
        <div class="card">
            <div class="card-cabecalho" onclick="abrirVeiculo(${v.id})">
                <div class="card-titulo">
                    ${aberto ? "▾" : "▸"} ${esc(v.identificacao)}
                    <span class="card-tipo">${esc(v.tipo)}</span>
                </div>
                <div class="card-subtitulo">${esc(v.marca)} ${esc(v.modelo)}${matricula}</div>
            </div>
    `;

    if (aberto) {
        html += `<div class="card-detalhe">`;
        html += detalhe ? desenharDetalhe(detalhe) : `<p class="vazio">A carregar...</p>`;
        html += `</div>`;
    }

    html += `</div>`;
    return html;
}

// --- Detalhe: ficha + cofres ---
function desenharDetalhe(d) {
    let html = "";

    // Cabeçalho da ficha. O botão "Editar" só é desenhado se logado.
    html += `
        <div class="secao-titulo">
            <h3>Ficha técnica</h3>
            ${estaLogado() && !editandoFicha
                ? `<button class="pequeno" onclick="comecarEdicaoFicha()">Editar</button>`
                : ""}
        </div>
    `;

    html += editandoFicha ? desenharFormFicha(d) : desenharFicha(d);

    html += `<div class="secao-titulo"><h3>Cofres</h3></div>`;

    if (d.cofres.length === 0) {
        html += `<p class="vazio">Nenhum cofre cadastrado.</p>`;
    }
    html += d.cofres.map(desenharCofre).join("");

    // Formulário de cofre novo: só para o Comando
    if (estaLogado()) {
        html += `
            <form class="form-linha" onsubmit="adicionarCofre(event)">
                <input type="text" id="novo-cofre-nome" placeholder="Nome do cofre novo" required>
                <button type="submit">Adicionar cofre</button>
            </form>
        `;
    }

    return html;
}

function desenharFicha(d) {
    let linhas = "";

    for (const [campo, rotulo] of CAMPOS_FICHA) {
        // "campo in d" = a API mandou esse campo?
        // Sem login, matricula e numero_siresp não vêm -> a linha
        // inteira é pulada, sem deixar buraco.
        if (!(campo in d)) {
            continue;
        }
        const valor = d[campo] ? esc(d[campo]) : "—";
        linhas += `<dt>${rotulo}</dt><dd>${valor}</dd>`;
    }

    return `<dl class="ficha">${linhas}</dl>`;
}

function desenharFormFicha(d) {
    let campos = "";

    for (const [campo, rotulo] of CAMPOS_FICHA) {
        campos += `
            <label for="ficha-${campo}">${rotulo}</label>
            <input type="text" id="ficha-${campo}" value="${esc(d[campo])}">
        `;
    }

    return `
        <form onsubmit="salvarFicha(event)">
            <div class="ficha-edicao">${campos}</div>
            <div class="botoes" style="margin-bottom: 20px">
                <button type="submit">Salvar</button>
                <button type="button" class="secundario" onclick="cancelarEdicaoFicha()">Cancelar</button>
            </div>
        </form>
    `;
}

// --- Um cofre do accordion ---
function desenharCofre(cofre) {
    const aberto = cofresAbertos.has(cofre.id);
    const qtd = cofre.materiais.length;

    let html = `
        <div class="cofre">
            <button class="cofre-cabecalho" onclick="alternarCofre(${cofre.id})">
                <span>${aberto ? "▾" : "▸"} ${esc(cofre.nome)}</span>
                <span class="card-subtitulo">${qtd} ${qtd === 1 ? "item" : "itens"}</span>
            </button>
    `;

    // Fechado = só o cabeçalho. Aberto = cabeçalho + materiais.
    if (aberto) {
        html += `<div class="cofre-conteudo">`;

        if (qtd === 0) {
            html += `<p class="vazio">Cofre vazio.</p>`;
        } else {
            html += `<ul class="materiais">${cofre.materiais.map(desenharMaterial).join("")}</ul>`;
        }

        if (estaLogado()) {
            html += `
                <form class="form-linha" onsubmit="adicionarMaterial(event, ${cofre.id})">
                    <input type="number" id="novo-qtd-${cofre.id}" min="1" value="1" required>
                    <input type="text" id="novo-desc-${cofre.id}" placeholder="Descrição do material" required>
                    <button type="submit">Adicionar</button>
                </form>
            `;
        }

        html += `</div>`;
    }

    html += `</div>`;
    return html;
}

// --- Uma linha de material ---
function desenharMaterial(m) {
    // Modo edição: a quantidade vira um campo com Salvar/Cancelar
    if (m.id === materialEmEdicao) {
        return `
            <li class="material">
                <input type="number" id="editar-qtd-${m.id}" min="1" value="${m.quantidade}">
                <span class="material-descricao">${esc(m.descricao)}</span>
                <button class="pequeno" onclick="salvarMaterial(${m.id})">Salvar</button>
                <button class="pequeno secundario" onclick="cancelarEdicaoMaterial()">Cancelar</button>
            </li>
        `;
    }

    // Modo normal. Botões só se logado.
    const botoes = estaLogado()
        ? `<button class="pequeno secundario" onclick="comecarEdicaoMaterial(${m.id})">Editar</button>
           <button class="pequeno perigo" onclick="apagarMaterial(${m.id})">Apagar</button>`
        : "";

    return `
        <li class="material">
            <span class="material-qtd">${m.quantidade}</span>
            <span class="material-descricao">${esc(m.descricao)}</span>
            ${botoes}
        </li>
    `;
}


// =====================================================================
// 5. AÇÕES
//
// "async" + "await": fetch demora (vai ao servidor e volta). O await
// faz a função esperar a resposta antes de passar para a linha
// seguinte, sem travar a página enquanto isso.
// =====================================================================

// --- Buscar dados ---
async function carregarLista() {
    let url = "/veiculos";
    if (filtroTipo) {
        // encodeURIComponent protege caracteres especiais na URL
        url += "?tipo=" + encodeURIComponent(filtroTipo);
    }

    try {
        listaVeiculos = await chamarApi("GET", url);
    } catch (erro) {
        tratarErro(erro);
        return;
    }

    // Se a viatura aberta sumiu da lista (ex: pelo filtro), fecha
    if (!listaVeiculos.some(v => v.id === veiculoAberto)) {
        veiculoAberto = null;
        detalhe = null;
    }

    desenharLista();
}

async function carregarDetalhe() {
    if (veiculoAberto === null) {
        return;
    }
    try {
        detalhe = await chamarApi("GET", "/veiculos/" + veiculoAberto);
    } catch (erro) {
        tratarErro(erro);
    }
    desenharLista();
}

// Recarrega lista e detalhe (depois de login, logout ou edição)
async function recarregarTudo() {
    await carregarLista();
    await carregarDetalhe();
}

// --- Abrir/fechar ---
async function abrirVeiculo(id) {
    // Clicar no card que já está aberto = fechar
    if (veiculoAberto === id) {
        veiculoAberto = null;
        detalhe = null;
        desenharLista();
        return;
    }

    veiculoAberto = id;
    detalhe = null;
    cofresAbertos = new Set();
    editandoFicha = false;
    materialEmEdicao = null;
    desenharLista();          // mostra "A carregar..."
    await carregarDetalhe();  // busca e desenha o detalhe
}

function alternarCofre(id) {
    // Não precisa ir ao servidor: os materiais já vieram no detalhe
    if (cofresAbertos.has(id)) {
        cofresAbertos.delete(id);
    } else {
        cofresAbertos.add(id);
    }
    desenharLista();
}

// --- Filtro ---
function filtrar(evento) {
    // Sem isto, o formulário recarregaria a página inteira
    evento.preventDefault();
    filtroTipo = document.getElementById("campo-tipo").value.trim();
    carregarLista();
}

function limparFiltro() {
    document.getElementById("campo-tipo").value = "";
    filtroTipo = "";
    carregarLista();
}

// --- Ficha técnica ---
function comecarEdicaoFicha() {
    editandoFicha = true;
    desenharLista();
}

function cancelarEdicaoFicha() {
    editandoFicha = false;
    desenharLista();
}

async function salvarFicha(evento) {
    evento.preventDefault();

    // Manda só os campos que mudaram (o PUT do backend é parcial)
    const alteracoes = {};
    for (const [campo] of CAMPOS_FICHA) {
        const novoValor = document.getElementById("ficha-" + campo).value.trim();
        const valorAntigo = detalhe[campo] ?? "";  // null vira ""
        if (novoValor !== valorAntigo) {
            alteracoes[campo] = novoValor;
        }
    }

    if (Object.keys(alteracoes).length === 0) {
        cancelarEdicaoFicha();  // nada mudou
        return;
    }

    try {
        await chamarApi("PUT", "/veiculos/" + veiculoAberto, alteracoes);
        editandoFicha = false;
        mostrarMensagem("Ficha técnica salva.");
        await recarregarTudo();  // a lista também muda (ex: identificação)
    } catch (erro) {
        tratarErro(erro);
    }
}

// --- Cofres ---
async function adicionarCofre(evento) {
    evento.preventDefault();
    const nome = document.getElementById("novo-cofre-nome").value.trim();

    try {
        const novo = await chamarApi("POST", `/veiculos/${veiculoAberto}/cofres`, { nome });
        cofresAbertos.add(novo.id);  // já abre o cofre novo
        await carregarDetalhe();
    } catch (erro) {
        tratarErro(erro);
    }
}

// --- Materiais ---
async function adicionarMaterial(evento, cofreId) {
    evento.preventDefault();
    const quantidade = Number(document.getElementById("novo-qtd-" + cofreId).value);
    const descricao = document.getElementById("novo-desc-" + cofreId).value.trim();

    try {
        await chamarApi("POST", `/cofres/${cofreId}/materiais`, { quantidade, descricao });
        await carregarDetalhe();
    } catch (erro) {
        tratarErro(erro);
    }
}

function comecarEdicaoMaterial(id) {
    materialEmEdicao = id;
    desenharLista();
}

function cancelarEdicaoMaterial() {
    materialEmEdicao = null;
    desenharLista();
}

async function salvarMaterial(id) {
    const quantidade = Number(document.getElementById("editar-qtd-" + id).value);

    try {
        await chamarApi("PUT", "/materiais/" + id, { quantidade });
        materialEmEdicao = null;
        await carregarDetalhe();
    } catch (erro) {
        tratarErro(erro);
    }
}

async function apagarMaterial(id) {
    // confirm() abre a janelinha "OK / Cancelar" do navegador
    if (!confirm("Apagar este material?")) {
        return;
    }

    try {
        await chamarApi("DELETE", "/materiais/" + id);
        await carregarDetalhe();
    } catch (erro) {
        tratarErro(erro);
    }
}


// =====================================================================
// 6. LOGIN / LOGOUT
// =====================================================================
function abrirLogin() {
    document.getElementById("login-erro").textContent = "";
    document.getElementById("modal-login").classList.remove("escondido");
    document.getElementById("login-email").focus();
}

function fecharLogin() {
    document.getElementById("modal-login").classList.add("escondido");
    document.getElementById("form-login").reset();  // limpa email e senha
}

async function entrar(evento) {
    evento.preventDefault();
    const email = document.getElementById("login-email").value.trim();
    const senha = document.getElementById("login-senha").value;

    try {
        const resposta = await chamarApi("POST", "/login", { email, senha });

        // O coração do login: guardar o token para os próximos pedidos
        guardarSessao(resposta.token, resposta.nome);

        fecharLogin();
        desenharTopo();
        // Busca de novo: agora, com o token, a API manda a matrícula
        // e o SIRESP, e os botões de edição passam a ser desenhados
        await recarregarTudo();
    } catch (erro) {
        document.getElementById("login-erro").textContent = erro.message;
    }
}

// Volta a página ao estado "bombeiro sem login"
function voltarParaModoConsulta() {
    limparSessao();
    editandoFicha = false;
    materialEmEdicao = null;
    desenharTopo();
}

function sair() {
    voltarParaModoConsulta();
    // Busca de novo SEM token: matrícula e SIRESP deixam de vir
    recarregarTudo();
}

function sairPorSessaoExpirada() {
    voltarParaModoConsulta();
    mostrarMensagem("A sua sessão expirou. Faça login novamente.");
    // Redesenha já, para os botões de edição sumirem na hora, e
    // busca tudo de novo SEM token (a página continua a funcionar
    // em modo consulta, sem matrícula e SIRESP)
    desenharLista();
    recarregarTudo();
}


// =====================================================================
// 7. ARRANQUE: liga os formulários às funções e carrega a lista
// =====================================================================
document.getElementById("form-filtro").addEventListener("submit", filtrar);
document.getElementById("botao-limpar").addEventListener("click", limparFiltro);
document.getElementById("form-login").addEventListener("submit", entrar);
document.getElementById("botao-cancelar-login").addEventListener("click", fecharLogin);

desenharTopo();
carregarLista();
