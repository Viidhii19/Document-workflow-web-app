import axios from 'axios';
import type { Document, ChatMessage } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
});

export const getDocuments = async (): Promise<Document[]> => {
  const response = await api.get('/documents/');
  return response.data.documents;
};

export const uploadDocument = async (file: File): Promise<Document> => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await api.post('/documents/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data.document;
};

export const getChatHistory = async (documentId: string): Promise<ChatMessage[]> => {
  const response = await api.get(`/chat/${documentId}/history`);
  return response.data.history;
};

export const queryChat = async (documentId: string, message: string): Promise<ChatMessage> => {
  const response = await api.post(`/chat/query`, {
    document_id: documentId,
    message,
  });
  return response.data;
};

export const getPdfUrl = (documentId: string): string => {
  return `${API_BASE_URL}/documents/${documentId}/pdf`;
};
