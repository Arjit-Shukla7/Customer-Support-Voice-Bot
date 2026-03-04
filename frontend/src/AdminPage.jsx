import React, { useState, useEffect } from 'react';

const AdminPage = ({ onNavigateBack }) => {
    const [calls, setCalls] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchCalls = async () => {
        setIsLoading(true);
        setError(null);
        try {
            const response = await fetch('http://localhost:8000/admin/calls');
            if (!response.ok) throw new Error('Failed to fetch call logs');
            const data = await response.json();

            // Sort calls by newest first
            const sortedData = data.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
            setCalls(sortedData);
        } catch (err) {
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    };

    // Fetch data when the component mounts
    useEffect(() => {
        fetchCalls();
    }, []);

    // Helper to format the ISO timestamp into a readable date & time
    const formatDate = (dateString) => {
        if (!dateString) return "N/A";
        const date = new Date(dateString);
        return new Intl.DateTimeFormat('en-US', {
            month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit'
        }).format(date);
    };

    // Dynamic styling for the sentiment badges
    const getSentimentBadge = (sentiment) => {
        const s = sentiment?.toLowerCase() || "";
        if (s.includes('positive') || s.includes('happy') || s.includes('calm') || s.includes('better')) {
            return <span className="px-3 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-semibold tracking-wide">Positive</span>;
        }
        if (s.includes('frustrat') || s.includes('angry') || s.includes('pain') || s.includes('negative')) {
            return <span className="px-3 py-1 rounded-full bg-red-50 text-red-700 border border-red-200 text-xs font-semibold tracking-wide">Needs Attention</span>;
        }
        return <span className="px-3 py-1 rounded-full bg-gray-100 text-gray-700 border border-gray-200 text-xs font-semibold tracking-wide">{sentiment || "Neutral"}</span>;
    };

    // Background to match your Call Page
    const BackgroundOrbs = () => (
        <div className="fixed inset-0 overflow-hidden pointer-events-none z-0 bg-flowing-green">
            <div className="absolute top-0 left-0 w-[50vw] h-[50vw] bg-forestgreen/20 rounded-full blur-[100px] mix-blend-screen" />
            <div className="absolute top-0 right-0 w-[40vw] h-[40vw] bg-emerald/15 rounded-full blur-[100px] mix-blend-screen" />
            <div className="absolute bottom-0 left-1/4 w-[60vw] h-[60vw] bg-seagreen/20 rounded-full blur-[120px] mix-blend-screen" />
        </div>
    );

    return (
        <div className="relative min-h-screen text-gray-900 p-8 md:p-12 selection:bg-teal-100/40" style={{ fontFamily: '"Outfit", sans-serif' }}>
            <BackgroundOrbs />

            <div className="relative z-10 max-w-7xl mx-auto">

                {/* Header Section */}
                <div className="flex flex-col md:flex-row md:items-center justify-between mb-12 gap-6">
                    <div>
                        <h1 className="text-4xl font-semibold tracking-tight text-gray-900">Post-Call Analytics</h1>
                        <p className="text-gray-600 mt-2 text-lg font-normal">Review automated summaries and patient sentiment from the voice agent.</p>
                    </div>

                    <div className="flex items-center gap-4">
                        <button
                            onClick={fetchCalls}
                            className="px-6 py-3 rounded-full bg-white/60 backdrop-blur-md border border-white/40 text-teal-700 font-semibold hover:bg-white hover:shadow-sm transition-all flex items-center gap-2"
                        >
                            <svg className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                            Refresh
                        </button>
                        {/* If you are conditionally rendering this component in App.jsx, use this button to go back */}
                        {onNavigateBack && (
                            <button
                                onClick={onNavigateBack}
                                className="px-6 py-3 rounded-full bg-gray-900 text-white font-semibold hover:scale-105 transition-transform shadow-md"
                            >
                                Call Agent →
                            </button>
                        )}
                    </div>
                </div>

                {/* Glassmorphism Table Container */}
                <div className="bg-white/70 backdrop-blur-xl border border-white/60 rounded-3xl shadow-[0_20px_40px_rgba(0,0,0,0.03)] overflow-hidden">

                    {isLoading ? (
                        <div className="flex flex-col items-center justify-center py-32">
                            <div className="w-12 h-12 border-4 border-teal-100 border-t-teal-500 rounded-full animate-spin mb-4"></div>
                            <p className="text-gray-500 font-medium">Fetching call logs...</p>
                        </div>
                    ) : error ? (
                        <div className="text-center py-20 px-6">
                            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-red-50 text-red-500 mb-4">
                                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                            </div>
                            <h3 className="text-xl font-semibold text-gray-900 mb-2">Failed to load data</h3>
                            <p className="text-gray-600">{error}</p>
                        </div>
                    ) : calls.length === 0 ? (
                        <div className="text-center py-32 px-6">
                            <h3 className="text-xl font-semibold text-gray-900 mb-2">No calls recorded yet</h3>
                            <p className="text-gray-500">Make a test call on the Call Agent page to see data appear here.</p>
                        </div>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full text-left border-collapse">
                                <thead>
                                    <tr className="border-b border-gray-200/60 bg-white/40">
                                        <th className="py-5 px-6 font-semibold text-gray-500 uppercase tracking-wider text-xs">Date & Time</th>
                                        <th className="py-5 px-6 font-semibold text-gray-500 uppercase tracking-wider text-xs">Patient</th>
                                        <th className="py-5 px-6 font-semibold text-gray-500 uppercase tracking-wider text-xs">Sentiment</th>
                                        <th className="py-5 px-6 font-semibold text-gray-500 uppercase tracking-wider text-xs w-1/2">AI Summary</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-100/60">
                                    {calls.map((call) => (
                                        <tr key={call.id} className="hover:bg-white/60 transition-colors duration-200">
                                            <td className="py-5 px-6 whitespace-nowrap text-sm text-gray-600">
                                                {formatDate(call.timestamp)}
                                            </td>
                                            <td className="py-5 px-6 whitespace-nowrap">
                                                <span className="font-semibold text-gray-900">{call.patient_name}</span>
                                            </td>
                                            <td className="py-5 px-6 whitespace-nowrap">
                                                {getSentimentBadge(call.sentiment)}
                                            </td>
                                            <td className="py-5 px-6 text-sm text-gray-700 leading-relaxed min-w-[300px]">
                                                {call.summary}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}

                </div>
            </div>
        </div>
    );
};

export default AdminPage;