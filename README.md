# BugSense AI

An AI-powered bug analysis and test case generation platform built for QA teams. The system uses Large Language Models with Retrieval-Augmented Generation (RAG) to automate bug classification and generate test cases from feature descriptions.

## Problem Statement

QA teams spend hours on repetitive tasks like classifying bug severity, writing test cases, and maintaining consistency in bug triage. This project automates these workflows using AI, achieving 90% accuracy in severity classification while reducing manual effort.

## Features

### Bug Analysis
Analyzes bug reports and automatically classifies them by severity (Critical, High, Medium, Low), priority (P1-P4), and component. The system uses uploaded guidelines as context to ensure classifications match your team's standards.

### Test Case Generation
Converts feature descriptions into ready-to-use Gherkin test cases. Generates scenarios for happy paths, edge cases, and error conditions that can be directly used with BDD frameworks like Cucumber or Behave.

### Knowledge Base
Upload your company's severity guidelines, documentation, or past bug reports. The RAG pipeline indexes these documents and uses them as context for more accurate, consistent classifications.

### Benchmark Testing
Import bug datasets to measure AI accuracy. Track severity and priority accuracy over time, compare configurations, and add custom examples to improve performance through few-shot learning.

### Multi-Provider Support
Switch between AI providers based on your needs:
- OpenAI GPT-4o-mini for best accuracy
- Groq LLaMA 3 for fast, free inference
- Ollama for local, offline processing

## Performance

| Metric | Result |
|--------|--------|
| Severity Accuracy | 90% |
| Priority Accuracy | 78% |
| Average Latency | 3.0s |
| Schema Validity | 100% |

Tested on a 50-case e-commerce bug dataset.

## Architecture

```
Frontend (Next.js + TypeScript + Tailwind)
                    |
                    v
Backend (FastAPI + Python)
    |               |               |
    v               v               v
PostgreSQL      ChromaDB        OpenAI/Groq
(bug data)      (vectors)       (LLM inference)
```

The backend implements a RAG pipeline that embeds user queries, retrieves relevant context from uploaded documents, and augments prompts before sending to the LLM. Results are validated against a Pydantic schema before returning to the frontend.

## Tech Stack

**Frontend**
- Next.js 14 with App Router
- TypeScript
- Tailwind CSS
- shadcn/ui components

**Backend**
- FastAPI (async Python)
- SQLAlchemy ORM
- Pydantic validation
- LangChain for LLM orchestration

**AI/ML**
- OpenAI API (GPT-4o-mini)
- Groq API (LLaMA 3)
- ChromaDB for vector storage
- OpenAI text-embedding-3-small

**Infrastructure**
- Docker and Docker Compose
- Kubernetes (production)
- PostgreSQL
- Minikube for local K8s

## Project Structure

```
bugsense-ai/
├── apps/
│   ├── api/                    # FastAPI backend
│   │   ├── app/
│   │   │   ├── routes/         # API endpoints
│   │   │   ├── services/       # Business logic
│   │   │   ├── db/             # Database models
│   │   │   └── config.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   └── web/                    # Next.js frontend
│       ├── src/
│       │   ├── app/            # Pages
│       │   ├── components/     # React components
│       │   └── lib/            # Utilities
│       ├── Dockerfile
│       └── package.json
│
├── k8s/                        # Kubernetes manifests
├── docker-compose.yml
└── README.md
```

## Getting Started

### Prerequisites
- Docker and Docker Compose installed
- OpenAI API key or Groq API key

### Setup

Clone the repository:
```bash
git clone https://github.com/jallurivardhan/bugsense-ai.git
cd bugsense-ai
```

Create environment file:
```bash
cp .env.example .env
```

Add your API keys to `.env`:
```
OPENAI_API_KEY=your-openai-key
GROQ_API_KEY=your-groq-key
```

Start the application:
```bash
docker-compose up --build
```

Access the app:
- Frontend: http://localhost:3000
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Usage

### Analyzing a Bug

Navigate to Bug Analysis, enter the bug details:

```
Title: Shopping cart items disappear after login

Description: Customers report their shopping cart items disappear 
completely after logging into their account. Items added as guest 
are lost. Affects all users. 200 support tickets received today.
```

The system returns:
- Severity: Critical
- Priority: P1
- Component: Cart/Session Management

### Generating Test Cases

Navigate to Test Generation, describe the feature:

```
User password reset via email link with expiration
```

The system generates Gherkin scenarios covering the main flow, invalid inputs, expired links, and edge cases.

### Running Benchmarks

1. Upload a CSV with columns: title, description, expected_severity
2. Import the test cases
3. Select sample size (5, 10, 20, or 50)
4. Run benchmark and view accuracy metrics

## API Endpoints

**POST /api/v1/bug-analysis**
```json
{
  "title": "Login button not working",
  "description": "Users cannot click login on mobile",
  "environment": "Production"
}
```

**POST /api/v1/test-generation**
```json
{
  "feature": "User password reset via email",
  "context": "E-commerce platform"
}
```

**POST /api/v1/documents/upload**
Multipart form with file attachment for knowledge base.

**POST /api/v1/benchmarks/run?sample_size=10**
Runs benchmark on imported test cases.

## Local Development

Backend:
```bash
cd apps/api
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend:
```bash
cd apps/web
npm install
npm run dev
```

## Kubernetes Deployment

```bash
minikube start
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/

kubectl create secret generic bugsense-secrets -n bugsense \
  --from-literal=OPENAI_API_KEY=your-key \
  --from-literal=DATABASE_URL=postgresql://postgres:bugsense123@postgres-service:5432/bugsense

minikube tunnel
```

## What I Built

- Complete full-stack application with Next.js frontend and FastAPI backend
- RAG pipeline with ChromaDB for context-aware bug classification
- Multi-provider AI integration supporting OpenAI, Groq, and Ollama
- Benchmark testing system to measure and improve accuracy
- Kubernetes deployment configuration for production use
- Docker Compose setup for local development

## Future Improvements

- Jira and GitHub integration for direct bug import
- Slack bot for instant analysis
- Custom model fine-tuning
- Team collaboration features
- Analytics dashboard

## Author

Jalluri Vardhan
- GitHub: [@jallurivardhan](https://github.com/jallurivardhan)
