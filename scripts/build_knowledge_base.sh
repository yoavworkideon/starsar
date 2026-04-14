#!/bin/bash
# Build the full STARDAR knowledge base — run once after docker-compose up

set -e
cd "$(dirname "$0")/.."
source .venv/bin/activate

echo "=== STARDAR Knowledge Base Builder ==="
echo ""

echo "[1/4] Ingesting architecture docs..."
python -m rag.ingest --source ARCHITECTURE.md --collection architecture --reset
python -m rag.ingest --source README.md       --collection architecture

echo ""
echo "[2/4] Ingesting simulation code..."
python -m rag.ingest --source simulation/ --collection simulation_code --reset

echo ""
echo "[3/4] Ingesting formulas and theory notes..."
python -m rag.ingest --source data/formulas/ --collection papers --reset
python -m rag.ingest --source data/notes/    --collection papers

echo ""
echo "[4/4] Ingesting fine-tune seed dataset..."
python -m rag.ingest --source finetune/dataset/ --collection papers

echo ""
echo "=== Knowledge base ready ==="
echo "Collections: architecture, simulation_code, papers"
echo ""
echo "To add research papers (PDFs):"
echo "  python -m rag.ingest --source data/papers/ --collection papers"
