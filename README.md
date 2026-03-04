# 🎙️ Real-Time Healthcare Voice AI Agent

![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Deepgram](https://img.shields.io/badge/Deepgram-STT-black?style=for-the-badge)
![Cartesia](https://img.shields.io/badge/Cartesia-TTS-blue?style=for-the-badge)
![Groq](https://img.shields.io/badge/Groq-LLM-orange?style=for-the-badge)

A full-duplex, ultra-low latency voice AI agent designed for healthcare triage and patient follow-ups. This project features dynamic context injection, sub-second conversational latency, true interruption (barge-in) handling, and a live React dashboard with dynamic audio waveforms.

## ✨ Key Features

* **Ultra-Low Latency Streaming:** Achieves near-human response times by piping Deepgram STT transcripts into a LangGraph/Groq (Llama 3.1) brain, and streaming the output directly to Cartesia Sonic TTS via WebSockets.
* **True Barge-In (Interruption):** Hardware-level audio buffer flushing allows patients to interrupt the AI mid-sentence smoothly, instantly halting the backend generation and frontend audio queue.
* **Dynamic Context Injection:** The AI adapts its persona and greeting based on live SQLite database records (e.g., medical history, recent surgeries).
* **Siri-Style UI & Live Captions:** A premium React frontend utilizing the Web Audio API to render volume-reactive radial gradients and synchronized, scrolling live transcripts.
* **Automated Post-Call Analytics:** Once a call disconnects, LangGraph automatically summarizes the clinical encounter, runs sentiment analysis, and posts the data to an Admin Dashboard.

## 🏗️ System Architecture

1.  **Client (React):** Captures raw microphone bytes (`getUserMedia`) and streams them over a WebSocket. Receives raw PCM audio bytes and JSON text payloads to render the UI.
2.  **Server (FastAPI):** Acts as the asynchronous orchestration layer. Manages the WebSocket pools and handles the `AsyncExitStack` for resource teardown.
3.  **STT (Deepgram):** Processes the incoming audio stream and returns real-time transcripts.
4.  **LLM (LangGraph + Groq):** Maintains conversational state. Generates clinical responses token-by-token.
5.  **TTS (Cartesia):** Receives fully-formed sentences from the LLM via a buffering generator and returns high-fidelity PCM audio chunks.

## 🚀 Engineering Challenges Solved

* **The "Token Spam" WebSocket Collapse:** Fast LLMs generate tokens too quickly for TTS WebSockets to handle natively. **Solution:** Implemented an asynchronous sentence buffer that parses punctuation in real-time, yielding complete sentences to Cartesia. This eliminated API disconnects and preserved natural speech prosody.
* **Ghost Audio & Desync:** Backend generation is faster than audio playback, causing old audio to play even after an interruption. **Solution:** Decoupled the interruption logic. A `CLEAR` socket event is fired the exact millisecond user audio is detected, flushing the React `AudioContext` instantly while the backend `asyncio` tasks cancel gracefully.
* **Idle Timeouts (Cold Starts):** TTS connections drop if the LLM takes too long to fetch context on the first turn. **Solution:** Built a dynamic connection shield using Python's `AsyncExitStack` to guarantee the Cartesia WebSocket only opens the exact millisecond the first buffered sentence is ready.

## ⚙️ Local Setup & Installation

### Prerequisites
You will need API keys for the following services:
* [Deepgram](https://deepgram.com/) (Speech-to-Text)
* [Cartesia](https://cartesia.ai/) (Text-to-Speech)
* [Groq](https://groq.com/) (LLM Inference)

### Backend Setup (FastAPI)
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
pip install -r requirements.txt
```
### Create a .env file in the backend directory:

```bash
DEEPGRAM_API_KEY=your_deepgram_key
CARTESIA_API_KEY=your_cartesia_key
GROQ_API_KEY=your_groq_key
```
### Start the backend server:

```
uvicorn main:app --reload
```
### Frontend Setup (React)
```
cd frontend
npm install
npm run dev
```
## 💻 Usage
Navigate to http://localhost:5173

Select a patient persona to load their medical context.

Click Start Call and speak into your microphone.

Click Admin Panel after ending the call to view the automated clinical summary and sentiment analysis.
