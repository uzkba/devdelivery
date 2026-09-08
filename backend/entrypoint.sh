#!/bin/sh
set -e

echo "======================================"
echo "Executando migrations do Alembic..."
echo "======================================"

alembic upgrade head

echo "======================================"
echo "Iniciando FastAPI..."
echo "======================================"

exec uvicorn main:app --host 0.0.0.0 --port 8000