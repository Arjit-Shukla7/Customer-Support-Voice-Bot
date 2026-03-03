import { useState, useRef, useCallback } from 'react';

export const useVoiceAgent = () => {
    const [isRecording, setIsRecording] = useState(false);
    const [status, setStatus] = useState('Disconnected');

    const mediaRecorder = useRef(null);
    const socket = useRef(null);
    const audioStream = useRef(null);

    const startCall = useCallback(async () => {
        try {
            // 1. Request microphone access
            audioStream.current = await navigator.mediaDevices.getUserMedia({ audio: true });

            // 2. Open WebSocket connection to FastAPI
            socket.current = new WebSocket('ws://localhost:8000/ws');

            socket.current.onopen = () => {
                setStatus('Connected');

                // 3. Start recording and sending audio
                mediaRecorder.current = new MediaRecorder(audioStream.current);
                mediaRecorder.current.ondataavailable = (event) => {
                    if (event.data.size > 0 && socket.current.readyState === WebSocket.OPEN) {
                        socket.current.send(event.data);
                    }
                };

                // Fire off an audio chunk every 250ms
                mediaRecorder.current.start(250);
                setIsRecording(true);
            };

            // 4. Handle incoming audio (The Echo)
            socket.current.onmessage = async (event) => {
                // Convert the incoming bytes back into an audio object and play it
                const audioBlob = new Blob([event.data], { type: 'audio/webm' });
                const audioUrl = URL.createObjectURL(audioBlob);
                const audio = new Audio(audioUrl);
                audio.play().catch(e => console.error("Playback failed:", e));
            };

            socket.current.onclose = () => {
                setStatus('Disconnected');
                stopCall();
            };

        } catch (error) {
            console.error('Error accessing microphone:', error);
            setStatus('Error accessing microphone');
        }
    }, []);

    const stopCall = useCallback(() => {
        if (mediaRecorder.current && mediaRecorder.current.state !== 'inactive') {
            mediaRecorder.current.stop();
        }
        if (audioStream.current) {
            audioStream.current.getTracks().forEach(track => track.stop());
        }
        if (socket.current) {
            socket.current.close();
        }
        setIsRecording(false);
        setStatus('Disconnected');
    }, []);

    return { isRecording, status, startCall, stopCall };
};