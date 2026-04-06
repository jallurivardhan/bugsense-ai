#!/bin/bash
echo "Starting BugSense AI (AI Assistant for Software Testing) - Development Mode"
echo "============================================================"

if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "Warning: Ollama is not running. Please start Ollama first."
    echo "Install from: https://ollama.ai"
fi

cd "$(dirname "$0")/.."
docker-compose up -d db

echo ""
echo "PostgreSQL started on port 5432"
echo ""
echo "To start the backend:"
echo "  cd apps/api && source venv/bin/activate && uvicorn app.main:app --reload"
echo ""
echo "To start the frontend:"
echo "  cd apps/web && npm run dev"
