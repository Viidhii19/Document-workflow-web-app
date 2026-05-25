import json
import os
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Optional

import chromadb
import requests

from app.core.config import settings


chroma_client = chromadb.PersistentClient(path=os.path.join(settings.DATA_DIR, "chromadb"))
collection = chroma_client.get_or_create_collection(name="documents")

CHUNK_SIZE = 1800
CHUNK_OVERLAP = 250
QUERY_TOP_K = 12
SUMMARY_CHUNK_LIMIT = 24
CONTEXT_CHAR_BUDGET = 18000
MAX_CITATION_CANDIDATES = 12
MAX_RETURNED_CITATIONS = 6
MAX_ACCEPTABLE_DISTANCE = 1.7
OPENROUTER_MODEL = os.environ.get(
    "OPENROUTER_MODEL",
    "qwen/qwen3-next-80b-a3b-instruct:free",
)

STOPWORDS = {
    "about",
    "after",
    "again",
    "also",
    "because",
    "been",
    "being",
    "between",
    "could",
    "document",
    "does",
    "from",
    "give",
    "have",
    "into",
    "more",
    "most",
    "other",
    "over",
    "show",
    "some",
    "such",
    "than",
    "that",
    "their",
    "them",
    "then",
    "there",
    "these",
    "this",
    "those",
    "what",
    "when",
    "where",
    "which",
    "with",
    "would",
}


@dataclass(frozen=True)
class RetrievedChunk:
    id: str
    text: str
    page: int
    rank: int
    distance: Optional[float] = None


@dataclass(frozen=True)
class CitationCandidate:
    id: str
    page: int
    quote: str
    chunk_id: str
    normalized_quote: str


def _normalize_storage_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", str(text)).replace("\x00", "")
    text = text.replace("\u00ad", "")
    return re.sub(r"\s+", " ", text).strip()


def _normalize_for_match(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text)).lower()
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _tokenize(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-zA-Z0-9]+", _normalize_for_match(text))
        if len(token) > 2 and token not in STOPWORDS
    ]


def _split_sentences(text: str) -> list[tuple[int, int, str]]:
    spans: list[tuple[int, int, str]] = []
    for match in re.finditer(r"[^.!?;:\n]+(?:[.!?;:]|$)", text):
        sentence = match.group(0).strip()
        if len(sentence.split()) >= 6:
            spans.append((match.start(), match.end(), sentence))

    if spans:
        return spans

    words = text.split()
    if not words:
        return []

    chunks: list[tuple[int, int, str]] = []
    cursor = 0
    for i in range(0, len(words), 28):
        quote = " ".join(words[i : i + 28])
        start = text.find(quote, cursor)
        if start < 0:
            start = cursor
        end = start + len(quote)
        chunks.append((start, end, quote))
        cursor = end
    return chunks


def _strip_candidate_prefix_noise(quote: str) -> str:
    quote = re.sub(r"^(?:[A-Z]?\d+[,\s]*)+", "", quote).strip()
    quote = re.sub(r"^(?:ABSTRACT|INTRODUCTION|CONCLUSION)\s+", "", quote, flags=re.IGNORECASE).strip()
    quote = re.sub(r"\s+(?:a|an|and|at|by|for|from|in|of|on|or|the|to|with)$", "", quote, flags=re.IGNORECASE)
    return quote


def _find_chunk_end(text: str, start: int, target_end: int) -> int:
    if target_end >= len(text):
        return len(text)

    search_start = max(start + CHUNK_SIZE // 2, target_end - 500)
    window = text[search_start:target_end]
    boundary_matches = list(re.finditer(r"[.!?]\s+", window))
    if boundary_matches:
        return search_start + boundary_matches[-1].end()

    whitespace = text.rfind(" ", search_start, target_end)
    if whitespace > start:
        return whitespace

    return target_end


def _chunk_page_text(text: str) -> list[str]:
    text = _normalize_storage_text(text)
    if not text:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(text):
        target_end = min(start + CHUNK_SIZE, len(text))
        end = _find_chunk_end(text, start, target_end)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        next_start = max(0, end - CHUNK_OVERLAP)
        if next_start <= start:
            next_start = end
        while next_start < len(text) and text[next_start].isalnum():
            next_start += 1
        start = next_start

    return chunks


def ingest_document(document_id: str, pages: list[dict[str, Any]]) -> None:
    """Normalize, chunk, and index page text in ChromaDB."""
    documents: list[str] = []
    metadatas: list[dict[str, Any]] = []
    ids: list[str] = []

    try:
        collection.delete(where={"document_id": document_id})
    except Exception:
        pass

    for page in pages:
        page_num = int(page["page_number"])

        for chunk_index, chunk_text in enumerate(_chunk_page_text(page.get("text", ""))):
            chunk_id = f"{document_id}_p{page_num}_c{chunk_index}"
            documents.append(chunk_text)
            metadatas.append(
                {
                    "document_id": document_id,
                    "page_number": page_num,
                    "chunk_index": chunk_index,
                }
            )
            ids.append(chunk_id)

    if not documents:
        return

    batch_size = 50
    for i in range(0, len(documents), batch_size):
        collection.add(
            documents=documents[i : i + batch_size],
            metadatas=metadatas[i : i + batch_size],
            ids=ids[i : i + batch_size],
        )


def _is_summary_query(query: str) -> bool:
    query_lower = query.lower()
    return any(term in query_lower for term in ("summarize", "summarise", "summary"))


def _result_to_chunks(results: dict[str, Any]) -> list[RetrievedChunk]:
    documents = results.get("documents") or [[]]
    metadatas = results.get("metadatas") or [[]]
    ids = results.get("ids") or [[]]
    distances = results.get("distances") or [[]]

    chunks: list[RetrievedChunk] = []
    for index, text in enumerate(documents[0]):
        metadata = metadatas[0][index] or {}
        chunks.append(
            RetrievedChunk(
                id=str(ids[0][index]),
                text=_normalize_storage_text(text),
                page=int(metadata.get("page_number", 0)),
                rank=index,
                distance=distances[0][index] if distances and distances[0] else None,
            )
        )
    return chunks


def _get_summary_chunks(document_id: str) -> list[RetrievedChunk]:
    all_docs = collection.get(
        where={"document_id": document_id},
        include=["documents", "metadatas"],
    )
    documents = all_docs.get("documents") or []
    metadatas = all_docs.get("metadatas") or []
    ids = all_docs.get("ids") or []

    chunks = [
        RetrievedChunk(
            id=str(ids[index]),
            text=_normalize_storage_text(text),
            page=int((metadatas[index] or {}).get("page_number", 0)),
            rank=index,
        )
        for index, text in enumerate(documents)
    ]
    chunks.sort(key=lambda chunk: (chunk.page, chunk.id))
    return chunks[:SUMMARY_CHUNK_LIMIT]


def _retrieve_chunks(document_id: str, query: str) -> list[RetrievedChunk]:
    if _is_summary_query(query):
        return _get_summary_chunks(document_id)

    results = collection.query(
        query_texts=[query],
        n_results=QUERY_TOP_K,
        where={"document_id": document_id},
        include=["documents", "metadatas", "distances"],
    )
    return _result_to_chunks(results)


def _has_confident_retrieval(chunks: list[RetrievedChunk], query: str) -> bool:
    if not chunks:
        return False

    if _is_summary_query(query):
        return True

    best_distance = chunks[0].distance
    if best_distance is not None and best_distance <= MAX_ACCEPTABLE_DISTANCE:
        return True

    query_tokens = set(_tokenize(query))
    if not query_tokens:
        return False

    top_text = " ".join(chunk.text for chunk in chunks[:3])
    top_tokens = set(_tokenize(top_text))
    return len(query_tokens & top_tokens) >= max(2, min(4, len(query_tokens)))


def _trim_quote(sentence: str, query_tokens: set[str]) -> str:
    words = sentence.split()
    if len(words) <= 28 and len(sentence) <= 260:
        return _strip_candidate_prefix_noise(sentence)

    normalized_words = [_normalize_for_match(word) for word in words]
    hit_indexes = [
        index
        for index, word in enumerate(normalized_words)
        if any(token and token in word.split() for token in query_tokens)
    ]

    center = hit_indexes[0] if hit_indexes else 0
    start = max(0, center - 10)
    end = min(len(words), start + 28)
    start = max(0, end - 28)
    return _strip_candidate_prefix_noise(" ".join(words[start:end]))


def _score_sentence(sentence: str, query_tokens: set[str]) -> tuple[int, int]:
    sentence_tokens = set(_tokenize(sentence))
    overlap = len(sentence_tokens & query_tokens)
    return overlap, min(len(sentence), 260)


def _build_citation_candidates(
    chunks: list[RetrievedChunk],
    query: str,
) -> list[CitationCandidate]:
    query_tokens = set(_tokenize(query))
    candidates: list[CitationCandidate] = []
    seen: set[str] = set()

    for chunk in chunks:
        sentence_spans = _split_sentences(chunk.text)
        ranked_sentences = sorted(
            sentence_spans,
            key=lambda item: _score_sentence(item[2], query_tokens),
            reverse=True,
        )

        for _, _, sentence in ranked_sentences[:2]:
            quote = _trim_quote(sentence, query_tokens)
            normalized = _normalize_for_match(quote)
            word_count = len(normalized.split())

            if word_count < 6 or normalized in seen or quote not in chunk.text:
                continue

            citation_id = f"c{len(candidates) + 1}"
            candidates.append(
                CitationCandidate(
                    id=citation_id,
                    page=chunk.page,
                    quote=quote,
                    chunk_id=chunk.id,
                    normalized_quote=normalized,
                )
            )
            seen.add(normalized)

            if len(candidates) >= MAX_CITATION_CANDIDATES:
                return candidates

    return candidates


def _build_context(chunks: list[RetrievedChunk]) -> str:
    context_parts: list[str] = []
    used_chars = 0

    for chunk in chunks:
        if not chunk.text:
            continue

        header = f"[CHUNK {chunk.id} | PAGE {chunk.page}]\n"
        part = f"{header}{chunk.text}\n"

        if used_chars + len(part) > CONTEXT_CHAR_BUDGET:
            remaining = CONTEXT_CHAR_BUDGET - used_chars - len(header)
            if remaining <= 500:
                break
            part = f"{header}{chunk.text[:remaining].rsplit(' ', 1)[0]}\n"

        context_parts.append(part)
        used_chars += len(part)

    return "\n".join(context_parts)


def _build_candidate_context(candidates: list[CitationCandidate]) -> str:
    return "\n".join(
        f'[{candidate.id} | page {candidate.page} | chunk {candidate.chunk_id}] "{candidate.quote}"'
        for candidate in candidates
    )


def _strip_code_fences(content: str) -> str:
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?", "", content).strip()
        content = re.sub(r"```$", "", content).strip()
    return content


def _parse_model_json(content: str) -> dict[str, Any]:
    content = _strip_code_fences(content)
    try:
        parsed = json.loads(content)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start >= 0 and end > start:
            try:
                parsed = json.loads(content[start : end + 1])
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                return {}
    return {}


def _extract_citation_ids(response_data: dict[str, Any]) -> list[str]:
    raw_ids = response_data.get("citation_ids")
    if raw_ids is None:
        raw_ids = response_data.get("citations", [])

    ids: list[str] = []
    if not isinstance(raw_ids, list):
        return ids

    for item in raw_ids:
        citation_id: Optional[str] = None
        if isinstance(item, str):
            citation_id = item
        elif isinstance(item, dict):
            raw_id = item.get("id") or item.get("citation_id") or item.get("source_id")
            citation_id = str(raw_id) if raw_id is not None else None

        if citation_id and citation_id not in ids:
            ids.append(citation_id)

    return ids


def _format_citations(
    citation_ids: list[str],
    candidates: list[CitationCandidate],
    answer: str,
) -> list[dict[str, Any]]:
    candidate_by_id = {candidate.id: candidate for candidate in candidates}
    selected = [candidate_by_id[citation_id] for citation_id in citation_ids if citation_id in candidate_by_id]

    return [
        {
            "id": candidate.id,
            "page": candidate.page,
            "quote": candidate.quote,
            "normalized_quote": candidate.normalized_quote,
            "chunk_id": candidate.chunk_id,
            "match_strategy": "normalized-text-layer",
        }
        for candidate in selected[:MAX_RETURNED_CITATIONS]
    ]


def _call_openrouter(prompt: str) -> dict[str, Any]:
    if not settings.OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not configured")

    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": OPENROUTER_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a careful document QA assistant. Answer only from the "
                        "provided context. Return valid JSON only."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        },
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    return _parse_model_json(data["choices"][0]["message"]["content"])


def query_document(document_id: str, query: str) -> dict[str, Any]:
    """Retrieve grounded context, ask the model, and return verified citations."""
    chunks = _retrieve_chunks(document_id, query)
    if not _has_confident_retrieval(chunks, query):
        return {
            "answer": "I don't know based on the provided document.",
            "citations": [],
        }

    candidates = _build_citation_candidates(chunks, query)
    context_str = _build_context(chunks)
    candidate_str = _build_candidate_context(candidates)

    prompt = f"""Use the document context to answer the user question.

Rules:
- Use only facts supported by the context.
- If the answer is not supported, answer exactly: I don't know based on the provided document.
- Cite evidence by returning citation IDs only. Do not create quote text or page numbers.
- citation_ids must contain only IDs from the Citation candidates list.
- Every factual paragraph should be supported by at least one citation ID.
- Return one JSON object and no surrounding prose.

JSON schema:
{{
  "answer": "Markdown answer grounded in the provided context.",
  "citation_ids": ["c1"]
}}

Citation candidates:
{candidate_str or "No citation candidates available."}

Document context:
{context_str}

User question:
{query}
"""

    try:
        response_data = _call_openrouter(prompt)
        answer = str(
            response_data.get(
                "answer",
                "I don't know based on the provided document.",
            )
        ).strip()
        citation_ids = _extract_citation_ids(response_data)
        citations = _format_citations(citation_ids, candidates, answer)

        if "don't know" not in answer.lower() and not citations:
            return {
                "answer": "I don't know based on the provided document.",
                "citations": [],
            }

        return {
            "answer": answer,
            "citations": citations,
        }
    except Exception as exc:
        print(f"Error calling OpenRouter: {exc}")
        return {
            "answer": "Sorry, I encountered an error while processing your request with the AI model.",
            "citations": [],
        }
