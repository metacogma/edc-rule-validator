// ChatPanel.js
// Conversational AI panel for Turing-level Validator
// Allows users to ask natural language questions and receive LLM-powered answers

import React, { useState } from "react";

function ChatPanel({ onSend, messages }) {
  const [input, setInput] = useState("");

  const handleSend = () => {
    if (input.trim()) {
      onSend(input);
      setInput("");
    }
  };

  return (
    <div style={{ border: "1px solid #ddd", borderRadius: 8, padding: 16, marginTop: 16, background: "#fafbff" }}>
      <div style={{ maxHeight: 200, overflowY: "auto", marginBottom: 8 }}>
        {messages.map((msg, idx) => (
          <div key={idx} style={{ marginBottom: 6, color: msg.role === "user" ? "#0074D9" : "#333" }}>
            <strong>{msg.role === "user" ? "You" : "AI"}:</strong> {msg.content}
          </div>
        ))}
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        <input
          style={{ flex: 1, padding: 8, borderRadius: 4, border: "1px solid #ccc" }}
          placeholder="Ask a question about validation, rules, or results..."
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter") handleSend(); }}
        />
        <button style={{ padding: "8px 16px", background: "#0074D9", color: "#fff", border: "none", borderRadius: 4 }} onClick={handleSend}>
          Send
        </button>
      </div>
    </div>
  );
}

export default ChatPanel;
