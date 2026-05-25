import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { useAppStore } from '../../store/useAppStore';
import { getChatHistory, queryChat } from '../../services/api';

export const ChatInterface: React.FC = () => {
  const { activeDocument, chatHistory, setChatHistory, addChatMessage, setActiveCitation } = useAppStore();
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (activeDocument) {
      // Load history
      getChatHistory(activeDocument.id).then(setChatHistory).catch(console.error);
    }
  }, [activeDocument, setChatHistory]);

  useEffect(() => {
    // Scroll to bottom on new message
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory, isTyping]);

  const handleSend = async () => {
    if (!input.trim() || !activeDocument) return;
    
    const userMessage = input.trim();
    setInput('');
    setActiveCitation(null);
    
    // Optimistically add user message
    addChatMessage({
      id: Date.now().toString(),
      document_id: activeDocument.id,
      role: 'user',
      message: userMessage,
      created_at: new Date().toISOString()
    });
    
    setIsTyping(true);
    
    try {
      const response = await queryChat(activeDocument.id, userMessage);
      addChatMessage(response);
      
      // Auto highlight the first citation if available
      if (response.citations && response.citations.length > 0) {
        setActiveCitation(response.citations[0]);
      }
    } catch (error) {
      console.error("Chat error", error);
      alert("Failed to get response.");
    } finally {
      setIsTyping(false);
    }
  };

  if (!activeDocument) return null;

  return (
    <div style={{ width: '400px', backgroundColor: 'var(--bg-secondary)', display: 'flex', flexDirection: 'column', borderLeft: '1px solid var(--border-color)' }}>
      <div style={{ padding: 'var(--spacing-md)', borderBottom: '1px solid var(--border-color)' }}>
        <h3 style={{ margin: 0, fontSize: '1rem' }}>AI Assistant</h3>
      </div>
      
      <div style={{ flex: 1, padding: 'var(--spacing-md)', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)' }}>
        {chatHistory.length === 0 && (
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', textAlign: 'center', marginTop: '2rem' }}>
            Ask me anything about this document.
          </p>
        )}
        
        {chatHistory.map((msg) => (
          <div 
            key={msg.id} 
            style={{ 
              alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
              backgroundColor: msg.role === 'user' ? 'var(--accent-primary)' : 'var(--bg-elevated)',
              padding: '12px 16px',
              borderRadius: 'var(--radius-lg)',
              borderBottomRightRadius: msg.role === 'user' ? 0 : 'var(--radius-lg)',
              borderBottomLeftRadius: msg.role === 'assistant' ? 0 : 'var(--radius-lg)',
              maxWidth: '85%',
              fontSize: '0.875rem'
            }}
          >
            {msg.role === 'assistant' ? (
               <div className="markdown-content">
                  <ReactMarkdown>{msg.message}</ReactMarkdown>
               </div>
            ) : (
               msg.message
            )}
            
            {msg.citations && msg.citations.length > 0 && (
              <div style={{ marginTop: '8px', paddingTop: '8px', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>Sources: </span>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  {msg.citations.map((cit, idx) => (
                    <button
                      key={idx}
                      onClick={() => setActiveCitation(cit)}
                      style={{
                        background: 'rgba(255, 255, 0, 0.2)',
                        border: '1px solid rgba(255, 255, 0, 0.4)',
                        color: '#ffeb3b',
                        borderRadius: '4px',
                        padding: '2px 6px',
                        fontSize: '0.75rem',
                        cursor: 'pointer'
                      }}
                    >
                      Page {cit.page}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
        {isTyping && (
          <div style={{ alignSelf: 'flex-start', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
            Thinking...
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      
      <div style={{ padding: 'var(--spacing-md)', borderTop: '1px solid var(--border-color)' }}>
         <input 
            type="text" 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Type a message..." 
            style={{ 
              width: '100%', 
              padding: '10px 12px',
              backgroundColor: 'var(--bg-primary)',
              border: '1px solid var(--border-color)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--text-primary)',
              outline: 'none'
            }} 
         />
      </div>
    </div>
  );
};
