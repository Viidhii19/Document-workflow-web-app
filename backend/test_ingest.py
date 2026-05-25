from app.services.pdf_parser import extract_text_from_pdf
from app.services.rag_pipeline import ingest_document
import time

# Create a dummy list of pages (200 pages, each with 1000 characters of text)
pages = []
for i in range(200):
    pages.append({
        "page_number": i + 1,
        "text": "This is a dummy text page. " * 50
    })

print(f"Ingesting {len(pages)} pages...")
start = time.time()
try:
    ingest_document("test_doc_123", pages)
    print(f"Successfully ingested in {time.time() - start:.2f} seconds!")
except Exception as e:
    import traceback
    traceback.print_exc()
