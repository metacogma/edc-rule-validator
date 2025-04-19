import './App.css';
import GoTGraph from './GoTGraph';
import ChatPanel from './ChatPanel';
import RuleUploadDashboard from './RuleUploadDashboard';
import React, { useState } from 'react';

function App() {
  const [messages, setMessages] = useState([
    { role: 'ai', content: 'Welcome! Ask me about rule validation, explanations, or see the reasoning graph.' }
  ]);
  const [results, setResults] = useState([]);

  const handleSend = async (input) => {
    setMessages(msgs => [...msgs, { role: 'user', content: input }]);
    try {
      const response = await fetch('/api/v1/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: input })
      });
      if (!response.ok) throw new Error('Chat API error');
      const data = await response.json();
      setMessages(msgs => [...msgs, { role: 'ai', content: data.answer }]);
    } catch (err) {
      setMessages(msgs => [...msgs, { role: 'ai', content: 'Error: ' + err.message }]);
    }
  };

  return (
    <div className="App" style={{ maxWidth: 900, margin: '0 auto', padding: 24 }}>
      <h2>Eclaire AI Rule Validator</h2>
      <div style={{ marginBottom: 24 }}>
        <GoTGraph />
      </div>
      <ChatPanel onSend={handleSend} messages={messages} />
      <RuleUploadDashboard onUpload={handleUpload} results={results} />
    </div>
  );
}

export default App;
