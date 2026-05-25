import os
import uuid
import shutil
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from typing import List

from app.core.config import settings
from app.models import database
from app.services.pdf_parser import extract_text_from_pdf
from app.services.rag_pipeline import ingest_document

router = APIRouter()

@router.post("/upload")
def upload_document(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
    document_id = str(uuid.uuid4())
    safe_filename = f"{document_id}_{file.filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, safe_filename)
    
    # Save the file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Extract text
    try:
        pages = extract_text_from_pdf(file_path)
    except Exception as e:
        # Cleanup if failed
        os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Failed to parse PDF: {str(e)}")
        
    # Ingest into Vector DB
    try:
        ingest_document(document_id, pages)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to embed document: {str(e)}")
        
    # Save Metadata
    document_record = {
        "id": document_id,
        "filename": file.filename,
        "upload_path": file_path,
        "created_at": datetime.utcnow().isoformat()
    }
    database.save_document(document_record)
    
    return {"message": "Document uploaded and processed successfully", "document": document_record}

@router.get("/")
def list_documents():
    docs = database.get_all_documents()
    return {"documents": docs}

@router.get("/{document_id}/pdf")
def get_pdf(document_id: str):
    doc = database.get_document_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    return FileResponse(doc["upload_path"], media_type="application/pdf")
