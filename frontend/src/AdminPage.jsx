import React, { useEffect, useState } from 'react';

const AdminPage = () => {
    const [calls, setCalls] = useState([]);

    useEffect(() => {
        fetch("http://localhost:8000/admin/calls")
            .then(res => res.json())
            .then(data => setCalls(data));
    }, []);

    return (
        <div className="min-h-screen bg-flowing-green p-12" style={{ fontFamily: '"Outfit", sans-serif' }}>
            <div className="max-w-6xl mx-auto">
                <h1 className="text-4xl font-semibold mb-8">Call History & Analysis</h1>
                <div className="bg-white/70 backdrop-blur-md rounded-3xl border border-white shadow-xl overflow-hidden">
                    <table className="w-full text-left">
                        <thead className="bg-gray-50/50 border-b border-gray-100">
                            <tr>
                                <th className="p-6 font-semibold">Patient</th>
                                <th className="p-6 font-semibold">Sentiment</th>
                                <th className="p-6 font-semibold">Summary</th>
                                <th className="p-6 font-semibold">Time</th>
                            </tr>
                        </thead>
                        <tbody>
                            {calls.map(call => (
                                <tr key={call.id} className="border-b border-gray-50 hover:bg-white/50 transition-colors">
                                    <td className="p-6 font-medium">{call.patient_name}</td>
                                    <td className="p-6">
                                        <span className={`px-3 py-1 rounded-full text-xs font-semibold ${call.sentiment === 'Frustrated' ? 'bg-red-100 text-red-700' : 'bg-teal-100 text-teal-700'
                                            }`}>
                                            {call.sentiment}
                                        </span>
                                    </td>
                                    <td className="p-6 text-gray-600 text-sm">{call.summary}</td>
                                    <td className="p-6 text-gray-400 text-xs">
                                        {new Date(call.timestamp).toLocaleString()}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

export default AdminPage;