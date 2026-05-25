# 🚀 Akino: AI-Powered Document Workflow

Akino is a local, fullstack AI-powered document workflow application that delivers high-precision Retrieval-Augmented Generation (RAG) over PDF documents. It enables users to upload PDFs, read them via a highly polished in-app PDF viewer, ask document-specific questions, and view interactive, pixel-perfect text highlights of citation sources directly within the rendered PDF pages.

---

## ✨ Features & Architecture Highlights

*   **⚡ Modern Fullstack Architecture:** Powered by a React + TypeScript frontend (Vite, Zustand, Tailwind/Vanilla CSS) and a robust Python FastAPI backend.
*   **📚 In-App PDF Workspace:** Implements premium side-by-side reading and chatting using `react-pdf` and standard HTML5 Canvas text layers.
*   **🎯 Strict Backend-Driven Citation Contract:** Rather than allowing the LLM to hallucinate or manufacture sources, the FastAPI backend constructs deterministic citation candidates from actual retrieved chunks. The LLM only returns the matching candidate IDs, which the backend then maps back to the precise page and source text.
*   **🖋️ Precise DOM-Range Highlighting:** The frontend dynamically builds a normalized character index of the rendered PDF text-layer DOM nodes, matches citation quotes, and draws custom overlay highlight shapes over multi-line text spans.
*   **🗄️ Hybrid Local Vector Storage:** Combines local JSON metadata storage for document structures with ChromaDB for highly efficient vector embeddings and vector similarity queries.
*   **🤖 Multi-LLM Provider Support:** Optimized for OpenRouter's free and premium models, with seamless environment overrides.

---

## 🛠️ Setup Instructions

### 1. Prerequisites
Ensure you have the following installed on your machine:
*   **Node.js** (v16 or higher)
*   **Python** (v3.9 or higher)
*   **An OpenRouter or Gemini API Key**

---

### 2. Backend Setup (FastAPI)

1. **Navigate to the backend directory:**
   ```bash
   cd backend
   ```

2. **Create and activate a virtual environment:**
   *   **Windows (cmd):**
       ```cmd
       python -m venv venv
       venv\Scripts\activate
       ```
   *   **Windows (PowerShell):**
       ```powershell
       python -m venv venv
       .\venv\Scripts\Activate.ps1
       ```
   *   **macOS / Linux:**
       ```bash
       python3 -m venv venv
       source venv/bin/activate
       ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure your environment variables:**
   Create a `.env` file directly inside the `backend/` folder:
   ```env
   # API Keys
   OPENROUTER_API_KEY="your_openrouter_key_here"
   GEMINI_API_KEY=""  # Optional: For direct Gemini API usage
   
   # Optional configurations
   OPENROUTER_MODEL="google/gemini-2.5-flash"  # Custom model override
   ```

   > [!IMPORTANT]
   > Ensure `.env` is never committed to Git. The root `.gitignore` is pre-configured to safely block all `.env` files from being tracked.

5. **Launch the FastAPI application:**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   *   The server will start at `http://localhost:8000`.
   *   Interactive OpenAPI docs are available at `http://localhost:8000/docs`.

---

### 3. Frontend Setup (React + Vite)

1. **Navigate to the frontend directory:**
   ```bash
   cd ../frontend
   ```

2. **Install node dependencies:**
   ```bash
   npm install
   ```

3. **Run the local development server:**
   ```bash
   npm run dev
   ```
   *   The web application will launch at `http://localhost:5173`.

---

## 💡 How To Use the Workspace

1. **Upload a PDF:** Drag and drop or click upload in the sidebar panel to ingest your document.
2. **Select & View:** Click on any uploaded document in the list to load it into the central PDF rendering viewport.
3. **Conversational Q&A:** Use the right chat assistant panel to ask questions. 
4. **Trace Citations:** Click on the generated citation markers (e.g., `[1]`) in the chat response. The PDF viewer will automatically scroll to the cited page and draw a vibrant highlighted overlay over the source text.

---

### 📄 Parser Failures
*   **PyMuPDF vs. pypdf:** The system tries to use PyMuPDF for accurate text layer alignment. If it fails to compile on your system, the backend automatically falls back to `pypdf` to parse text and load the database.
