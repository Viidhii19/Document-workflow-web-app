export interface Document {
  id: string;
  filename: string;
  upload_path: string;
  created_at: string;
}

export interface Citation {
  id?: string;
  page: number;
  quote: string;
  normalized_quote?: string;
  chunk_id?: string;
  match_strategy?: string;
}

export interface ChatMessage {
  id: string;
  document_id: string;
  role: 'user' | 'assistant';
  message: string;
  citations?: Citation[];
  created_at: string;
}
