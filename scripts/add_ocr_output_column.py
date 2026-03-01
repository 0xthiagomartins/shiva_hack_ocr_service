"""One-off: adiciona coluna ocrOutput na tabela Receipt. Usa DATABASE_URL do .env."""
import os
import sys
from pathlib import Path

# carrega .env do diretório do serviço
root = Path(__file__).resolve().parent.parent
env_path = root / ".env"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)

url = os.environ.get("DATABASE_URL")
if not url:
    print("DATABASE_URL não definido.", file=sys.stderr)
    sys.exit(1)

import psycopg2

conn = psycopg2.connect(url)
conn.autocommit = True
cur = conn.cursor()
cur.execute('ALTER TABLE "Receipt" ADD COLUMN IF NOT EXISTS "ocrOutput" TEXT;')
print("Coluna ocrOutput adicionada na tabela Receipt.")
cur.close()
conn.close()
