# shiva_hack_ocr_service

Serviço de OCR para cupons fiscais — **Shiva Hack**. Recebe imagem em base64 via HTTPS, envia a **imagem pura** para **GLM-OCR hospedado na Modal.com**, estrutura o texto via LiteLLM/OpenAI e persiste em banco (SQLAlchemy, alinhado ao Prisma). Status por `process_id`.

---

## Stack

- **Python** — FastAPI
- **OCR** — **GLM-OCR** na Modal.com (sem pré-processamento; imagem pura)
- **LLM** — LiteLLM + OpenAI (estruturação dos itens)
- **Banco** — SQLAlchemy (SQLite local ou PostgreSQL)

---

## Fluxo

1. **Entrada:** `process_id`, `user_id`, `image_b64` (POST /process).
2. **OCR:** Imagem em base64 é enviada ao endpoint GLM-OCR na Modal; retorno é um único texto.
3. **LLM:** Texto é enviado à OpenAI para extrair itens (description, normalized_name, quantity, unit, etc.).
4. **Persistência:** Itens e receipt são gravados no banco; status atualizado (Processing → Processed ou Error).

---

## Contrato da API

- **POST /process** — Body: `{"process_id": "...", "user_id": "...", "image_b64": "..."}`. Resposta imediata com status "Processing".
- **GET /status/{process_id}** — Consulta status (Processing | Processed | Error) e `error_message` se houver.
- **GET /info** — Retorna o modelo LLM configurado (validação).

---

## Estrutura do diretório

```
shiva_hack_ocr_service/
├── README.md
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── app/
│   ├── main.py
│   ├── ocr.py      # Chamada HTTP ao GLM-OCR na Modal
│   ├── llm.py
│   ├── db.py
│   └── models.py
├── docs/
│   └── MODAL_GLM_OCR.md   # Guia: como hospedar GLM-OCR na Modal
└── tests/
```

---

## Como rodar (local)

```bash
cd shiva_hack_ocr_service
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # preencher MODAL_OCR_URL, OPENAI_API_KEY, DATABASE_URL
.venv/bin/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Obrigatório no .env:**

- `MODAL_OCR_URL` — URL do endpoint GLM-OCR na Modal (ver [docs/MODAL_GLM_OCR.md](docs/MODAL_GLM_OCR.md)).
- `OPENAI_API_KEY` — Chave OpenAI para a LLM.
- `DATABASE_URL` — SQLite ou PostgreSQL.

---

## Hospedar GLM-OCR na Modal

O OCR não roda neste repositório; ele chama um endpoint externo. Para subir o **GLM-OCR na Modal.com** e obter a URL:

→ **[Guia completo: docs/MODAL_GLM_OCR.md](docs/MODAL_GLM_OCR.md)**

---

## Testes

```bash
.venv/bin/pip install -r requirements.txt
.venv/bin/python3 -m pytest tests/ -v
```

---

## Docker

```bash
# No .env: MODAL_OCR_URL, OPENAI_API_KEY, DATABASE_URL
docker compose build
docker compose up -d
```

API em `http://localhost:8000`; docs em `http://localhost:8000/docs`.
