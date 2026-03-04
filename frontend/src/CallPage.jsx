import React, { useState, useRef, useEffect } from 'react';

const PATIENTS = [
    { id: 1, name: "John Doe", problem: "Wisdom Tooth Extraction", example: '"My left side is really swollen and the ibuprofen isn\'t helping."' },
    { id: 2, name: "Sarah Connor", problem: "ACL Knee Surgery", example: '"My knee feels super stiff today, should I force the stretches?"' },
    { id: 3, name: "Michael Scott", problem: "Hypertension", example: '"I picked up the Lisinopril but I feel a little dizzy after taking it."' },
    { id: 4, name: "Emily Chen", problem: "Root Canal", example: '"I drank some hot coffee and my tooth started throbbing!"' },
    { id: 5, name: "David Wallace", problem: "Lower Back Pain", example: '"The pain is sharp when I bend over. Are my MRI results back?"' },
];

const CallPage = () => {
    const [selectedPatient, setSelectedPatient] = useState(null);
    const [isCalling, setIsCalling] = useState(false);
    const [agentVolume, setAgentVolume] = useState(0);
    const [userVolume, setUserVolume] = useState(0);

    const [transcript, setTranscript] = useState({ text: "", speaker: "" });
    const textScrollRef = useRef(null);

    const wsRef = useRef(null);
    const audioCtxRef = useRef(null);
    const nextPlayTimeRef = useRef(0);
    const mediaRecorderRef = useRef(null);
    const animationRef = useRef(null);
    const activeSources = useRef([]);

    const agentAnalyserRef = useRef(null);
    const userAnalyserRef = useRef(null);

    // Auto-scroll the transcript to the bottom when new text arrives
    useEffect(() => {
        if (textScrollRef.current) {
            textScrollRef.current.scrollTop = textScrollRef.current.scrollHeight;
        }
    }, [transcript.text]);

    const startCall = async () => {
        if (!selectedPatient) return;
        setIsCalling(true);
        setTranscript({ text: "Connecting...", speaker: "ai" });

        const AudioContext = window.AudioContext || window.webkitAudioContext;
        audioCtxRef.current = new AudioContext({ sampleRate: 24000 });
        nextPlayTimeRef.current = audioCtxRef.current.currentTime;

        agentAnalyserRef.current = audioCtxRef.current.createAnalyser();
        agentAnalyserRef.current.fftSize = 256;
        agentAnalyserRef.current.connect(audioCtxRef.current.destination);

        wsRef.current = new WebSocket(`ws://localhost:8000/ws/${selectedPatient.id}`);
        wsRef.current.binaryType = "arraybuffer";

        wsRef.current.onopen = async () => {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

                const userSource = audioCtxRef.current.createMediaStreamSource(stream);
                userAnalyserRef.current = audioCtxRef.current.createAnalyser();
                userAnalyserRef.current.fftSize = 256;
                userSource.connect(userAnalyserRef.current);

                mediaRecorderRef.current = new MediaRecorder(stream);
                mediaRecorderRef.current.ondataavailable = (event) => {
                    if (event.data.size > 0 && wsRef.current.readyState === WebSocket.OPEN) {
                        wsRef.current.send(event.data);
                    }
                };
                mediaRecorderRef.current.start(250);
                visualize();
            } catch (err) {
                console.error("🔴 Mic Error:", err);
            }
        };

        wsRef.current.onmessage = async (event) => {
            if (typeof event.data === "string") {
                if (event.data === "CLEAR") {
                    activeSources.current.forEach(source => {
                        try { source.stop(); source.disconnect(); } catch (e) { }
                    });
                    activeSources.current = [];

                    setTranscript({ text: "", speaker: "" });

                    if (audioCtxRef.current) {
                        nextPlayTimeRef.current = audioCtxRef.current.currentTime;
                    }
                    return;
                }

                try {
                    const data = JSON.parse(event.data);
                    if (data.type === "ai_text") {
                        setTranscript({ text: data.text, speaker: "ai" });
                    } else if (data.type === "user_text") {
                        setTranscript({ text: data.text, speaker: "user" });
                    }
                } catch (e) { }
                return;
            }

            const arrayBuffer = event.data;
            const int16Array = new Int16Array(arrayBuffer);
            const float32Array = new Float32Array(int16Array.length);
            for (let i = 0; i < int16Array.length; i++) { float32Array[i] = int16Array[i] / 32768.0; }

            const audioBuffer = audioCtxRef.current.createBuffer(1, float32Array.length, 24000);
            audioBuffer.getChannelData(0).set(float32Array);

            const source = audioCtxRef.current.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(agentAnalyserRef.current);

            source.onended = () => {
                activeSources.current = activeSources.current.filter(s => s !== source);
            };

            activeSources.current.push(source);

            const currentTime = audioCtxRef.current.currentTime;
            if (nextPlayTimeRef.current < currentTime) { nextPlayTimeRef.current = currentTime; }
            source.start(nextPlayTimeRef.current);
            nextPlayTimeRef.current += audioBuffer.duration;
        };
    };

    const endCall = () => {
        setIsCalling(false);
        if (wsRef.current) wsRef.current.close();
        if (mediaRecorderRef.current) mediaRecorderRef.current.stop();
        if (audioCtxRef.current) audioCtxRef.current.close();
        if (animationRef.current) cancelAnimationFrame(animationRef.current);
        setAgentVolume(0);
        setUserVolume(0);
        setTranscript({ text: "", speaker: "" });
    };

    const visualize = () => {
        const updateVolumes = () => {
            if (agentAnalyserRef.current) {
                const dataArray = new Uint8Array(agentAnalyserRef.current.frequencyBinCount);
                agentAnalyserRef.current.getByteFrequencyData(dataArray);
                setAgentVolume(dataArray.reduce((a, b) => a + b, 0) / dataArray.length);
            }
            if (userAnalyserRef.current) {
                const dataArray = new Uint8Array(userAnalyserRef.current.frequencyBinCount);
                userAnalyserRef.current.getByteFrequencyData(dataArray);
                setUserVolume(dataArray.reduce((a, b) => a + b, 0) / dataArray.length);
            }
            animationRef.current = requestAnimationFrame(updateVolumes);
        };
        updateVolumes();
    };

    const BackgroundOrbs = () => (
        <div className="fixed inset-0 overflow-hidden pointer-events-none z-0 bg-flowing-green">
            <div className="absolute top-0 left-0 w-[50vw] h-[50vw] bg-forestgreen/20 rounded-full blur-[100px] animate-orb-g-1 mix-blend-screen" />
            <div className="absolute top-0 right-0 w-[40vw] h-[40vw] bg-emerald/15 rounded-full blur-[100px] animate-orb-g-2 mix-blend-screen" />
            <div className="absolute bottom-0 left-1/4 w-[60vw] h-[60vw] bg-seagreen/20 rounded-full blur-[120px] animate-orb-g-3 mix-blend-screen" />
        </div>
    );

    if (!selectedPatient) {
        return (
            <div className="relative min-h-screen text-gray-900 p-12 selection:bg-teal-100/40" style={{ fontFamily: '"Outfit", sans-serif' }}>
                <BackgroundOrbs />
                <div className="relative z-10 max-w-6xl mx-auto">
                    <div className="mb-16 flex flex-col items-center justify-center text-center">
                        <h1 className="text-5xl font-semibold tracking-tight text-gray-900">Select a Persona</h1>
                        <p className="text-gray-600 mt-4 text-xl font-normal">Choose a patient to test the dynamic context injection.</p>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {PATIENTS.map((p) => (
                            <div
                                key={p.id}
                                onClick={() => setSelectedPatient(p)}
                                className="group relative flex flex-col p-6 cursor-pointer rounded-2xl bg-white/60 backdrop-blur-xl border border-white/40 overflow-hidden transition-all duration-500 hover:scale-[1.02] hover:bg-white hover:border-teal-100 hover:shadow-[0_20px_40px_rgba(20,184,166,0.1)]"
                            >
                                <div className="absolute inset-0 bg-gradient-to-br from-teal-100/40 via-transparent to-green-50/40 opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none" />
                                <div className="relative z-10">
                                    <div className="flex items-center justify-between mb-4">
                                        <h2 className="text-2xl font-semibold text-gray-900">{p.name}</h2>
                                        <span className="text-xs font-semibold px-3 py-1 rounded-full bg-teal-50 text-teal-700 border border-teal-100 shadow-sm">ID: {p.id}</span>
                                    </div>
                                    <div className="mb-6">
                                        <p className="text-sm font-semibold text-teal-600 uppercase tracking-wider mb-1">Condition</p>
                                        <p className="text-gray-700 font-normal">{p.problem}</p>
                                    </div>
                                    <div>
                                        <p className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-2">Try saying:</p>
                                        <p className="text-gray-700 font-normal italic bg-white/50 backdrop-blur-md p-4 rounded-xl border border-gray-100 group-hover:border-teal-50 transition-colors shadow-inner">
                                            {p.example}
                                        </p>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="relative flex flex-col items-center justify-center min-h-screen text-gray-900 selection:bg-teal-100/40 overflow-hidden" style={{ fontFamily: '"Outfit", sans-serif' }}>
            <BackgroundOrbs />

            <div className={`text-center z-10 p-8 bg-white/70 backdrop-blur-md rounded-3xl border border-white/60 shadow-[0_20px_40px_rgba(0,0,0,0.03)] transition-all duration-700 ${isCalling ? 'absolute top-8 scale-75 opacity-80' : 'mb-16'}`}>
                <h1 className="text-4xl font-semibold tracking-tight text-gray-900">Healthcare Support</h1>
                <p className="text-gray-600 mt-3 font-normal text-lg">Connecting to: <span className="text-black font-semibold">{selectedPatient.name}</span></p>
                <p className="text-teal-600 font-semibold mt-1">{selectedPatient.problem}</p>
            </div>

            {/* The Fading & Scrolling Transcript Box */}
            {isCalling && (
                <div className="relative z-10 w-full max-w-4xl px-8 h-[55vh] flex flex-col items-center justify-center pointer-events-auto">
                    <div
                        ref={textScrollRef}
                        className="w-full max-h-full overflow-y-auto [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none] scroll-smooth py-16"
                        style={{
                            maskImage: 'linear-gradient(to bottom, transparent 0%, black 15%, black 85%, transparent 100%)',
                            WebkitMaskImage: 'linear-gradient(to bottom, transparent 0%, black 15%, black 85%, transparent 100%)'
                        }}
                    >
                        <p
                            className={`text-2xl md:text-3xl lg:text-4xl font-medium leading-relaxed text-center transition-all duration-500 ease-out
                ${transcript.text ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}
                ${transcript.speaker === 'ai' ? 'text-teal-900 drop-shadow-sm' : 'text-gray-500 italic'}
              `}
                        >
                            {transcript.text || "Listening..."}
                        </p>
                    </div>
                </div>
            )}

            {/* Control Buttons */}
            <div className={`z-10 flex gap-6 transition-all duration-500 ${isCalling ? 'absolute bottom-12' : ''}`}>
                {!isCalling ? (
                    <button onClick={startCall} className="px-8 py-4 rounded-full bg-gray-900 text-white font-semibold hover:scale-105 transition-all shadow-[0_10px_30px_rgba(0,0,0,0.15)] text-lg">
                        Start Call
                    </button>
                ) : (
                    <button onClick={endCall} className="px-8 py-4 rounded-full bg-white text-red-500 border border-red-100 hover:bg-red-50 hover:border-red-200 transition-all shadow-md font-semibold text-lg z-20 relative">
                        End Call
                    </button>
                )}
            </div>

            {/* FIX: True "Sunrise" Radial Breathing Waveforms (Zero Hard Edges) */}
            <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">

                {/* AI Speaking Waveform (Teal) */}
                <div
                    className="absolute bottom-0 left-1/2 w-[120vw] h-[120vw] rounded-full mix-blend-multiply blur-[100px] transition-transform duration-100 ease-out"
                    style={{
                        backgroundColor: 'rgba(20, 184, 166, 0.4)',
                        transform: `translateX(-50%) translateY(65%) scale(${isCalling && transcript.speaker === 'ai' ? 0.7 + (agentVolume / 80) : 0})`,
                        opacity: isCalling && transcript.speaker === 'ai' ? 1 : 0
                    }}
                />

                {/* User Speaking Waveform (Gray) */}
                <div
                    className="absolute bottom-0 left-1/2 w-[120vw] h-[120vw] rounded-full mix-blend-multiply blur-[100px] transition-transform duration-100 ease-out"
                    style={{
                        backgroundColor: 'rgba(148, 163, 184, 0.4)',
                        transform: `translateX(-50%) translateY(65%) scale(${isCalling && transcript.speaker === 'user' ? 0.7 + (userVolume / 80) : 0})`,
                        opacity: isCalling && transcript.speaker === 'user' ? 1 : 0
                    }}
                />

            </div>
        </div>
    );
};

export default CallPage;