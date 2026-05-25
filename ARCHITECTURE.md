# Architecture Overview and Implementation Notes

Akino is a local fullstack RAG document workflow application. It lets users upload PDF files, view them in the browser, ask document-grounded questions, and highlight cited source text inside the PDF viewer.

## System Architecture

1. **Frontend: React + TypeScript + Vite**
   - Main shell: `frontend/src/App.tsx`
   - PDF viewer: `frontend/src/components/DocumentViewer/PdfViewer.tsx`
   - Chat UI: `frontend/src/components/Chat/ChatInterface.tsx`
   - Sidebar/document list: `frontend/src/components/Layout/Sidebar.tsx`
   - Global state: Zustand store in `frontend/src/store/useAppStore.ts`

2. **Backend: FastAPI**
   - App entry: `backend/app/main.py`
   - Document routes: `backend/app/api/endpoints/documents.py`
   - Chat routes: `backend/app/api/endpoints/chat.py`
   - Local metadata store: `backend/app/models/database.py`

3. **Document Processing**
   - PDF text extraction lives in `backend/app/services/pdf_parser.py`.
   - PyMuPDF is preferred when installed because it generally preserves text order well.
   - `pypdf` is kept as a fallback so the app can still parse text PDFs if PyMuPDF is unavailable.

4. **Vector Store**
   - ChromaDB persists embeddings locally under `backend/data/chromadb`.
   - Chunks include document ID, page number, and chunk index metadata.

5. **AI Provider**
   - OpenRouter is used for answer generation.
   - The default free model is configured in `backend/app/services/rag_pipeline.py`.
   - `OPENROUTER_MODEL` can override the default model.

## Core Workflows

### PDF Upload and Ingestion

1. The frontend sends a PDF as `multipart/form-data` to `/api/documents/upload`.
2. The backend stores the file under `backend/uploads`.
3. Text is extracted page by page.
4. Text is normalized and split into overlapping chunks.
5. Chunks are inserted into ChromaDB with document/page metadata.
6. Basic document metadata is saved to `backend/data/documents.json`.

### Chat and RAG Query

1. The frontend sends `{ document_id, message }` to `/api/chat/query`.
2. The backend verifies that the document exists.
3. ChromaDB retrieves relevant chunks for the query.
4. The backend checks retrieval confidence. Weak retrieval returns:

   ```text
   I don't know based on the provided document.
   ```

5. The backend creates exact citation candidates from retrieved chunk text.
6. The LLM receives:
   - retrieved document context
   - citation candidates
   - instructions to return JSON only
   - citation IDs only, not invented quotes or pages
7. The backend maps valid citation IDs back to exact quotes and pages.
8. If the model gives an unsupported answer without valid citations, the backend refuses instead of attaching unrelated citations.

## Citation and Highlighting Design

The citation pipeline is intentionally backend-owned:

- The model does **not** create quote text.
- The model does **not** create page numbers.
- The backend creates citation candidates from actual retrieved document text.
- The model returns only candidate IDs.
- The backend returns exact citation payloads to the frontend.

The frontend does not rely on PDF coordinate extraction from the backend. Instead:

1. `react-pdf` renders the page and text layer.
2. The viewer builds a normalized character index from text-layer DOM nodes.
3. The citation quote is normalized the same way.
4. A DOM `Range` is created over the matched text.
5. Highlight overlays are drawn from the range rectangles.
6. Highlights recompute after page render, citation changes, zoom changes, and resize events.

This approach is more robust than per-text-item matching and supports multiline citations across multiple PDF text spans.

## State Management

Zustand stores:

- uploaded document list
- active document
- chat history
- active citation
- loading state placeholder

Changing the active document clears stale chat/citation state to avoid highlighting a citation from the previous document.

## API Summary

- `POST /api/documents/upload` uploads and ingests a PDF.
- `GET /api/documents/` lists uploaded documents.
- `GET /api/documents/{document_id}/pdf` serves the original PDF.
- `POST /api/chat/query` sends a document question to the RAG pipeline.
- `GET /api/chat/{document_id}/history` returns stored chat history.

## Production Considerations

The current implementation is suitable for a local assignment/demo. For production:

- Move ingestion to a background queue such as Celery/RQ.
- Replace JSON files with PostgreSQL or SQLite plus proper locking.
- Add authentication and tenant isolation.
- Add upload size limits, MIME sniffing, and filename sanitization.
- Add OCR support for scanned PDFs.
- Add explicit embedding-model configuration and retrieval evaluation tests.
- Add better rate-limit handling for OpenRouter failures.
