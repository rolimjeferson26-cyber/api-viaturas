# api-viaturas

Consulta e edição dos materiais das viaturas (cofres e materiais) do quartel.

**Em produção:** https://checklist-viaturas.onrender.com

## Como está hospedado

- **Servidor:** Render (Web Service, região Ohio, plano Free — "adormece" após ~15 min parado; o primeiro acesso depois disso pode levar até 1 min).
- **Banco:** PostgreSQL no Neon (região us-east-2 / Ohio).
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn app:app --bind 0.0.0.0:$PORT`

### Variáveis de ambiente no Render

| Variável | Valor |
|---|---|
| `PYTHON_VERSION` | `3.12.3` |
| `SECRET_KEY` | gerada pelo Render (botão Generate) |
| `DATABASE_URL` | string de conexão **pooled** do Neon |

Não definir `FLASK_DEBUG` em produção.

## Rodar localmente

1. Copiar `.env.example` para `.env` e preencher.
2. `python -m venv venv && venv/bin/pip install -r requirements.txt`
3. `venv/bin/python app.py` (com `FLASK_DEBUG=1` no `.env` para modo de depuração)
