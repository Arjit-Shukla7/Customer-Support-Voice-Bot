import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import CallPage from './CallPage';
import AdminPage from './AdminPage';

function App() {
  return (
    <Router>
      <div className="relative font-outfit">
        {/* Minimalist Floating Nav */}
        <nav className="fixed top-6 right-8 z-50 flex gap-4 p-2 bg-white/30 backdrop-blur-md rounded-full border border-white/20 shadow-sm">
          <Link to="/" className="px-4 py-2 rounded-full hover:bg-white/50 transition-all text-sm font-semibold text-gray-800">Call Agent</Link>
          <Link to="/admin" className="px-4 py-2 rounded-full hover:bg-white/50 transition-all text-sm font-semibold text-gray-800">Admin Panel</Link>
        </nav>

        <Routes>
          <Route path="/" element={<CallPage />} />
          <Route path="/admin" element={<AdminPage />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;