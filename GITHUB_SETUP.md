# Criar repositório público no GitHub

Execute a partir da pasta **shiva_hack_ocr_service** (raiz do projeto).

## 1. Criar o repositório no GitHub

- Acesse [github.com/new](https://github.com/new)
- **Repository name:** `shiva_hack_ocr_service`
- **Description:** OCR service for receipt/cupom fiscal (Shiva Hack) — FastAPI, Tesseract, LiteLLM, SQLModel
- Marque **Public**
- **Não** marque "Add a README" (você já tem um)
- Clique em **Create repository**

## 2. Inicializar git e fazer o primeiro push

No terminal, na pasta do projeto:

```bash
cd /caminho/para/shiva_hack_ocr_service

git init
git add .
git commit -m "Initial commit: OCR service for receipt processing (Shiva Hack)"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/shiva_hack_ocr_service.git
git push -u origin main
```

Substitua `SEU_USUARIO` pelo seu usuário do GitHub.

Se usar SSH:

```bash
git remote add origin git@github.com:SEU_USUARIO/shiva_hack_ocr_service.git
git push -u origin main
```

## 3. (Opcional) Usar GitHub CLI

Se tiver `gh` instalado:

```bash
cd /caminho/para/shiva_hack_ocr_service
git init
git add .
git commit -m "Initial commit: OCR service for receipt processing (Shiva Hack)"
gh repo create shiva_hack_ocr_service --public --source=. --push
```
