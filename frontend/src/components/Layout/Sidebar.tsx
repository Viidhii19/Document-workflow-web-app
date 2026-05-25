import React, { useRef, useState } from 'react';
import axios from 'axios';
import { useAppStore } from '../../store/useAppStore';
import { uploadDocument } from '../../services/api';

export const Sidebar: React.FC = () => {
  const { documents, activeDocument, setDocuments, setActiveDocument } = useAppStore();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      setIsUploading(true);
      const uploadedDocument = await uploadDocument(file);
      setDocuments([...documents, uploadedDocument]);
      setActiveDocument(uploadedDocument);
      e.target.value = '';
    } catch (error) {
      console.error("Upload failed", error);
      const msg = axios.isAxiosError(error)
        ? error.response?.data?.detail || "Failed to upload document."
        : "Failed to upload document.";
      alert(msg);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div style={{ 
      width: '300px', 
      backgroundColor: 'var(--bg-secondary)',
      borderRight: '1px solid var(--border-color)',
      display: 'flex',
      flexDirection: 'column'
    }}>
      <div style={{ padding: 'var(--spacing-lg)', borderBottom: '1px solid var(--border-color)' }}>
        <h1 style={{ fontSize: '1.25rem', margin: 0, fontWeight: 600 }}>Akino AI</h1>
        <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', margin: '4px 0 0' }}>Document Workflow</p>
      </div>
      
      <div style={{ padding: 'var(--spacing-md)', flex: 1, overflowY: 'auto' }}>
        <input 
          type="file" 
          accept="application/pdf" 
          style={{ display: 'none' }} 
          ref={fileInputRef}
          onChange={handleFileChange}
        />
        <button 
          onClick={handleUploadClick}
          disabled={isUploading}
          style={{
            width: '100%',
            padding: 'var(--spacing-sm)',
            backgroundColor: 'var(--accent-primary)',
            color: 'white',
            border: 'none',
            borderRadius: 'var(--radius-md)',
            cursor: isUploading ? 'not-allowed' : 'pointer',
            fontWeight: 500,
            marginBottom: 'var(--spacing-md)',
            opacity: isUploading ? 0.7 : 1
          }}
        >
          {isUploading ? 'Uploading...' : '+ Upload Document'}
        </button>
        
        <h2 style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-tertiary)', letterSpacing: '0.05em' }}>
          Your Documents
        </h2>
        
        <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
          {documents.map((doc) => (
            <li 
              key={doc.id}
              onClick={() => setActiveDocument(doc)}
              style={{
                padding: 'var(--spacing-sm)',
                borderRadius: 'var(--radius-sm)',
                cursor: 'pointer',
                marginBottom: '4px',
                fontSize: '0.875rem',
                backgroundColor: activeDocument?.id === doc.id ? 'var(--bg-elevated)' : 'transparent',
                color: activeDocument?.id === doc.id ? 'var(--text-primary)' : 'var(--text-secondary)',
              }}
            >
              📄 {doc.filename}
            </li>
          ))}
        </ul>
        
        {documents.length === 0 && !isUploading && (
          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>No documents yet.</p>
        )}
      </div>
    </div>
  );
};
