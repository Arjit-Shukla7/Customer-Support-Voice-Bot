import React from 'react';
import { useVoiceAgent } from './hooks/useVoiceAgent';

function App() {
  const { isRecording, status, startCall, stopCall } = useVoiceAgent();

  return (
    <div style={{ backgroundColor: '#0A0A0B', color: 'white', height: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', fontFamily: 'sans-serif' }}>
      <h1>Healthcare Voice Agent</h1>
      <p style={{ color: status === 'Connected' ? '#4ade80' : '#f87171' }}>
        Status: {status}
      </p>

      <button
        onClick={isRecording ? stopCall : startCall}
        style={{
          padding: '12px 24px',
          fontSize: '16px',
          backgroundColor: isRecording ? '#ef4444' : '#3b82f6',
          color: 'white',
          border: 'none',
          borderRadius: '8px',
          cursor: 'pointer',
          marginTop: '20px'
        }}
      >
        {isRecording ? 'End Call' : 'Start Call'}
      </button>
    </div>
  );
}

export default App;