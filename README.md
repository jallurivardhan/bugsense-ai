# BugSense AI

AI-powered bug analysis and test case generation platform for QA teams.

## Features

- **Bug Analysis** - Paste a bug description, get instant severity (Critical/High/Medium/Low) and priority (P1-P4)
- **Test Case Generation** - Describe a feature, get Gherkin test cases automatically
- **Knowledge Base** - Upload your guidelines for context-aware AI decisions
- **Benchmarks** - Test AI accuracy with your own datasets

## Quick Start

### Prerequisites
- Docker & Docker Compose
- OpenAI API Key (or Groq API Key for free alternative)

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/bugsense-ai.git
cd bugsense-ai
```

### 2. Set up environment
```bash
# Create .env file
echo "OPENAI_API_KEY=your-openai-key-here" > .env
echo "GROQ_API_KEY=your-groq-key-here" >> .env
```

### 3. Run with Docker Compose
```bash
docker-compose up --build
```

### 4. Access the app
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000

## Tech Stack

- **Frontend**: Next.js, TypeScript, Tailwind CSS, shadcn/ui
- **Backend**: FastAPI, Python
- **Database**: PostgreSQL
- **Vector Store**: ChromaDB
- **AI**: OpenAI GPT-4o-mini / Groq / Ollama

## Usage

### Bug Analysis
1. Go to Bug Analysis page
2. Paste bug title and description
3. Click Analyze
4. Get severity, priority, and component classification

### Test Case Generation
1. Go to Test Case Generation page
2. Describe the feature to test
3. Click Generate
4. Get Gherkin-format test cases

### Benchmarks
1. Go to Benchmarks page
2. Upload a CSV with bug data (columns: title, description, expected_severity)
3. Import as test cases
4. Run benchmark to measure AI accuracy

## API Keys

### OpenAI (Recommended)
Get your key at: https://platform.openai.com/api-keys

### Groq (Free Alternative)
Get your free key at: https://console.groq.com/keys

## License

MIT
