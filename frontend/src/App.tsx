import { useEffect } from 'react';
import { useAppStore } from './store/useAppStore';
import { getDocuments } from './services/api';
import { Sidebar } from './components/Layout/Sidebar';
import { PdfViewer } from './components/DocumentViewer/PdfViewer';
import { ChatInterface } from './components/Chat/ChatInterface';
import './index.css';

function App() {
  const { setDocuments, activeDocument } = useAppStore();

  useEffect(() => {
    // Fetch initial document list
    getDocuments()
      .then(setDocuments)
      .catch(console.error);
  }, [setDocuments]);

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      <Sidebar />

      <div style={{ flex: 1, display: 'flex' }}>
        {activeDocument ? (
          <>
            <PdfViewer />
            <ChatInterface />
          </>
        ) : (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', color: 'var(--text-secondary)' }}>
            <h2 style={{ marginBottom: '8px' }}>Select or upload a document</h2>
            <p>Start chatting with your PDFs instantly.</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
