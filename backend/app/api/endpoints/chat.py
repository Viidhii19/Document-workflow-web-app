import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models import database
from app.services.rag_pipeline import query_document

router = APIRouter()

class ChatRequest(BaseModel):
    document_id: str
    message: str

@router.post("/query")
def chat_query(request: ChatRequest):
    # Verify doc exists
    doc = database.get_document_by_id(request.document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    # Save user message
    user_msg = {
        "id": str(uuid.uuid4()),
        "document_id": request.document_id,
        "role": "user",
        "message": request.message,
        "created_at": datetime.utcnow().isoformat()
    }
    database.save_chat_message(user_msg)
    
    # Query RAG Pipeline
    try:
        response_data = query_document(request.document_id, request.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error querying document: {str(e)}")
        
    # Save assistant message
    assistant_msg = {
        "id": str(uuid.uuid4()),
        "document_id": request.document_id,
        "role": "assistant",
        "message": response_data["answer"],
        "citations": response_data["citations"],
        "created_at": datetime.utcnow().isoformat()
    }
    database.save_chat_message(assistant_msg)
    
    return assistant_msg

@router.get("/{document_id}/history")
def get_history(document_id: str):
    history = database.get_chat_history(document_id)
    return {"history": history}
