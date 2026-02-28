# shiva_hack_ocr_service

Serviço de OCR para cupons fiscais — **Shiva Hack**. Recebe imagem em base64 via HTTPS, extrai texto com Tesseract (4 variações de pré-processamento), estrutura via LiteLLM/OpenAI e persiste em banco (SQLModel, alinhado ao Prisma do frontend). Status do processamento por `process_id`.

---

## Stack

- **Python** — linguagem
- **FastAPI** — API HTTPS
- **Tesseract** — OCR (via `pytesseract`)
- **LiteLLM** + **OpenAI** (modelo mini) — estruturação do texto em modelo do banco (LiteLLM para abstração; modelo mini para baixo custo)
- **Banco de dados** — **SQLModel** (SQLite em `data/receipts.db` por padrão; `DATABASE_URL` opcional). Modelos alinhados ao Prisma (User, Receipt, Item).

---

## Fluxo (passo a passo)

1. **Entrada**
   - Cliente envia requisição HTTPS com:
     - `process_id`: ID do processo gerado no app Telegram (para rastrear sucesso/falha).
     - Imagem do cupom em **base64**.

2. **Pré-processamento e OCR**
   - Serviço gera **4 variações** de pré-processamento da imagem.
   - Executa OCR (Tesseract) em cada variação.
   - Resultados (raw text das 4 variações) são gravados em um arquivo **`.toon`** (para debug/auditoria e uso na etapa seguinte).

3. **Estruturação com LLM**
   - Conteúdo do `.toon` (ou texto consolidado das 4 variações) é enviado via **LiteLLM** ao **OpenAI (modelo mini)**.
   - LLM devolve dados no **modelo esperado pelo banco** (itens, quantidades, valores, etc.).

4. **Persistência**
   - Serviço insere os dados estruturados no **banco de dados**.

5. **Status do processo**
   - Enquanto processa: processo fica como **em processamento** (via `process_id`).
   - Ao terminar com sucesso: status **processado**.
   - Se falhar em qualquer etapa (pré-processamento, OCR, LLM, banco): status **erro** (parametrizado para o `process_id`).

---

## Contrato da API (resumido)

- **Método:** POST (ex.: `/process` ou `/ingest`).
- **Body:** JSON com `process_id`, `user_id`, `image_b64`.
- **Resposta:** confirmação de recebimento e que o processamento será/está sendo feito (status “em processamento”); resultado final (sucesso/erro) consultado via `process_id` (ou callback/outro endpoint a definir).

---

## Estrutura do diretório

```
shiva_hack_ocr_service/
├── README.md
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── .gitignore
├── app/
│   ├── main.py
│   ├── preprocess.py
│   ├── ocr.py
│   ├── llm.py
│   ├── db.py
│   └── models.py       # User, Receipt, Item, ProcessStatus (Prisma-aligned)
└── tests/
    └── test_api.py
```

---

## Arquivo `.toon`

- Armazena o texto bruto das **4 variações** de OCR (uma por pré-processamento).
- Formato exato (por variação, delimitadores, etc.) a definir na implementação.
- Uso: input para o LLM e eventual suporte a reprocessamento/debug.

---

## Status por `process_id`

| Estado            | Quando |
|-------------------|--------|
| Em processamento  | Requisição aceita; job em execução. |
| Processado        | OCR + LLM + inserção no banco concluídos com sucesso. |
| Erro              | Falha em qualquer step (pré-processamento, OCR, LLM, banco); status parametrizado como erro para o `process_id`. |

---

## Como rodar (local)

Use sempre o Python e o pip do venv (evita `ModuleNotFoundError` e `externally-managed-environment`):

```bash
cd shiva_hack_ocr_service

# 1. Criar venv (se ainda não existir)
python3 -m venv .venv

# 2. Instalar dependências no venv (obrigatório)
.venv/bin/pip install -r requirements.txt

# 3. Configurar .env (OPENAI_API_KEY, DATABASE_URL)
cp .env.example .env   # editar .env

# 4. Tesseract no sistema (Linux): sudo apt install tesseract-ocr tesseract-ocr-por

# 5. Subir o servidor (usar o uvicorn do venv)
.venv/bin/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Não use `uvicorn` nem `pip` do sistema: use `.venv/bin/python -m uvicorn` e `.venv/bin/pip`.

## Testes

```bash
cd shiva_hack_ocr_service
.venv/bin/pip install -r requirements.txt
.venv/bin/python3 -m pytest tests/ -v
```

(Pipeline é mockado nos testes; não exige Tesseract nem OPENAI_API_KEY.)

## Como rodar no Docker

1. **Crie um `.env`** na pasta do projeto (ou exporte as variáveis) com:
   - `DATABASE_URL` — URL do banco (PostgreSQL ou SQLite). Ex.: `postgresql://user:password@host:5432/dbname`
   - `OPENAI_API_KEY` — chave da OpenAI para o LLM

2. **Build e subida:**

```bash
cd shiva_hack_ocr_service
docker compose build
docker compose up -d
```

3. **API:** `http://localhost:8000`  
   - Docs: `http://localhost:8000/docs`  
   - **POST /process** — body: `{"process_id": "...", "user_id": "...", "image_b64": "..."}`  
   - **GET /status/{process_id}** — consulta status

4. **Logs:** `docker compose logs -f ocr_service`  
   **Parar:** `docker compose down`

Com `DATABASE_URL` em Postgres, as tabelas são criadas no primeiro request (init_db). Os arquivos `.toon` ficam no volume `ocr_toon`; com SQLite, o DB ficaria no volume `ocr_data`.

- **POST /process** — body JSON: `{"process_id": "...", "user_id": "...", "image_b64": "..."}`
- **GET /status/{process_id}** — consulta status do processamento.

---

## Pendências / a definir

- Banco: SQLite + SQLModel em `data/receipts.db` (configurável por `DATABASE_URL`).
- `.toon`: `{process_id}.toon` em `TOON_DIR` (env ou `toon_output/`).

---

## Repositório

Repositório público: clone com `git clone https://github.com/<seu-user>/shiva_hack_ocr_service.git`
