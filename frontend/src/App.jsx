import React, { useState } from 'react';
import CallPage from './CallPage';
import AdminPage from './AdminPage';

function App() {
  const [currentView, setCurrentView] = useState('caller'); // 'caller' or 'admin'

  return (
    <>
      {/* Top Navigation Bar */}
      <div className="fixed top-0 right-0 p-6 z-50 flex gap-4">
        <button
          onClick={() => setCurrentView('caller')}
          className={`px-4 py-2 rounded-full text-sm font-semibold transition-all backdrop-blur-md ${currentView === 'caller' ? 'bg-white shadow-sm text-teal-800' : 'bg-white/40 text-gray-600 hover:bg-white/60'}`}
        >
          Call Agent
        </button>
        <button
          onClick={() => setCurrentView('admin')}
          className={`px-4 py-2 rounded-full text-sm font-semibold transition-all backdrop-blur-md ${currentView === 'admin' ? 'bg-white shadow-sm text-teal-800' : 'bg-white/40 text-gray-600 hover:bg-white/60'}`}
        >
          Admin Panel
        </button>
      </div>

      {/* Render the selected view */}
      {currentView === 'caller' ? (
        <CallPage />
      ) : (
        <AdminPage onNavigateBack={() => setCurrentView('caller')} />
      )}
    </>
  );
}

export default App;