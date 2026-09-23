# HireScope

AI-103 team project. Extracts resume text with Azure AI Document Intelligence,
analyzes it with Azure AI Language (key phrases, entities, PII redaction,
sentiment, language detection, abstractive summarization), scores it against
an optional job description with local TF-IDF cosine similarity, and stores
every analysis in Azure Blob Storage. Runs as a Streamlit web app,hosted on
Azure App Services.

Full step-by-step Azure setup and deployment instructions are in the project
guide document — this repo is just the application code.

## Local setup

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # then fill in your real Azure values
streamlit run app.py
```

Open http://localhost:8501

## Files

- `app.py` — Streamlit UI (upload, analyze, history tabs)
- `analyzer.py` — the analysis pipeline (Document Intelligence, Language, match score, Blob Storage)
- `azure_clients.py` — shared Azure SDK client setup, reads credentials from environment variables
- `requirements.txt` — Python dependencies
- `.env.example` — template for required environment variables (copy to `.env`, never commit the real `.env`)

## Deploying to Azure App Service

```bash
az login
az webapp up --name <your-app-name> --resource-group <your-resource-group> --runtime "PYTHON:3.11"
```

Then set the same 6 values from `.env` as Application Settings in the App
Service's Configuration blade, and set the Startup Command to:

```
python -m streamlit run app.py --server.port 8000 --server.address 0.0.0.0
```

## Required Azure resources

- Azure AI Document Intelligence (Standard S0)
- Azure AI Language (Standard S — required for summarization)
- Azure Storage Account with a private `resumes` Blob container
- Azure App Service (Basic B1 recommended for a stable demo)

