# Akino AI Document Workflow

A fullstack AI-powered document workflow application for uploading PDF documents, chatting with them through a RAG pipeline, and viewing highlighted response sources directly inside the PDF viewer.

For system design details, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Features

- **React + TypeScript frontend** built with Vite, Zustand, `react-pdf`, and `react-markdown`.
- **FastAPI Python backend** for document upload, document listing, PDF serving, chat history, and document Q&A.
- **PDF document workflow** with upload, list/select, in-app viewing, and chat against uploaded PDFs.
- **Local RAG pipeline** using ChromaDB for vector search and PyMuPDF when available, with a `pypdf` fallback for text extraction.
- **Free AI provider support** through OpenRouter. The default model is configured in `backend/app/services/rag_pipeline.py` and can be overridden with `OPENROUTER_MODEL`.
- **Deterministic citation contract** where the backend creates exact citation candidates from retrieved document text and the model returns only citation IDs.
- **PDF source highlighting** where the frontend matches citations against the rendered PDF text layer and draws highlight overlays over the referenced text.
- **Lightweight local metadata storage** using JSON files in `backend/data`.

## Setup Instructions

### 1. Prerequisites

- Node.js 16+
- Python 3.9+
- OpenRouter API key

### 2. Backend Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in the `backend` directory:

```env
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

Start the backend:

```bash
uvicorn app.main:app --reload --port 8000
```

The API runs at `http://localhost:8000`, and Swagger docs are available at `http://localhost:8000/docs`.

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The web app runs at `http://localhost:5173`.

## Usage

1. Open the frontend in your browser.
2. Upload a PDF document from the sidebar.
3. Select an uploaded document to view it inside the app.
4. Ask questions in the AI assistant panel.
5. Click citation buttons to jump to the referenced page and highlight the cited source text.

## Current Scope

- Document management includes uploading, listing, selecting, viewing, and chatting with PDFs.
- The citation system is designed to prefer refusal over unsupported answers when retrieval confidence is weak.
- Scanned or image-only PDFs require OCR, which is not included in this version.
- For production, replace JSON metadata storage with a database and move PDF ingestion into a background worker.
# AI-powered-document-workflow-web-app
# Document-workflow-web-app
