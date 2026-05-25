import json
import os
from typing import List, Dict, Any
from app.core.config import settings

DOCUMENTS_DB = os.path.join(settings.DATA_DIR, "documents.json")
CHAT_HISTORY_DB = os.path.join(settings.DATA_DIR, "chat_history.json")

def _read_json(filepath: str) -> List[Dict[str, Any]]:
    """Reads a JSON file and returns the list of objects. Creates it if missing."""
    if not os.path.exists(filepath):
        _write_json(filepath, [])
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def _write_json(filepath: str, data: List[Dict[str, Any]]) -> None:
    """Writes a list of objects to a JSON file."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# --- Documents ---
def get_all_documents() -> List[Dict[str, Any]]:
    return _read_json(DOCUMENTS_DB)

def get_document_by_id(doc_id: str) -> Dict[str, Any]:
    docs = get_all_documents()
    for doc in docs:
        if doc.get("id") == doc_id:
            return doc
    return None

def save_document(document: Dict[str, Any]) -> None:
    docs = get_all_documents()
    docs.append(document)
    _write_json(DOCUMENTS_DB, docs)

# --- Chat History ---
def get_chat_history(document_id: str) -> List[Dict[str, Any]]:
    history = _read_json(CHAT_HISTORY_DB)
    return [msg for msg in history if msg.get("document_id") == document_id]

def save_chat_message(message: Dict[str, Any]) -> None:
    history = _read_json(CHAT_HISTORY_DB)
    history.append(message)
    _write_json(CHAT_HISTORY_DB, history)
