Write-Host "Starting AI Assistant for Software Testing - Development Mode"
Write-Host "============================================================"

try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -ErrorAction Stop
} catch {
    Write-Host "Warning: Ollama is not running. Please start Ollama first."
    Write-Host "Install from: https://ollama.ai"
}

Set-Location "$PSScriptRoot\.."
docker-compose up -d db

Write-Host ""
Write-Host "PostgreSQL started on port 5432"
Write-Host ""
Write-Host "To start the backend:"
Write-Host "  cd apps\api; .\venv\Scripts\activate; uvicorn app.main:app --reload"
Write-Host ""
Write-Host "To start the frontend:"
Write-Host "  cd apps\web; npm run dev"
