from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
import os
from dotenv import load_dotenv

# Imports exactly as shown in the Deepgram GitHub snippet
from deepgram import AsyncDeepgramClient
from deepgram.core.events import EventType
from deepgram.listen.v1.types import ListenV1Results

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the global Async client
deepgram_client = AsyncDeepgramClient(api_key=os.getenv("DEEPGRAM_API_KEY"))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("🟢 Client connected to FastAPI!")

    try:
        # Use the exact async context manager from the snippet
        # We use nova-3 without encoding parameters so it accepts WebM natively
        async with deepgram_client.listen.v1.connect(
            model="nova-3", 
            smart_format="true", 
            interim_results="true"
        ) as connection:
            print("🟢 Deepgram connection opened successfully!")

            # 1. Define the message handler using the snippet's logic
            async def on_message(message, **kwargs):
                # Extract transcription exactly as the snippet shows
                if isinstance(message, ListenV1Results):
                    if message.channel and message.channel.alternatives:
                        transcript = message.channel.alternatives[0].transcript
                        if transcript:
                            if message.is_final:
                                print(f"\n✅ User (Final): {transcript}")
                            else:
                                print(f"⏳ Typing... {transcript}", end="\r")

            async def on_error(error, **kwargs):
                print(f"🔴 Deepgram Error: {error}")

            # Bind the events
            connection.on(EventType.MESSAGE, on_message)
            connection.on(EventType.ERROR, on_error)

            # 2. Define a background loop to constantly read your microphone
            async def receive_audio_from_react():
                try:
                    while True:
                        data = await websocket.receive_bytes()
                        # Send audio to Deepgram
                        await connection.send_media(data)
                except Exception as e:
                    print(f"React connection closed: {e}")

            # 3. Start the microphone loop concurrently
            mic_task = asyncio.create_task(receive_audio_from_react())

            # 4. Start listening to Deepgram (This blocks safely until the call ends)
            await connection.start_listening()

            # Clean up the microphone loop if Deepgram closes
            mic_task.cancel()

    except WebSocketDisconnect:
        print("\n🔴 Client disconnected from FastAPI.")
    except Exception as e:
        print(f"\n🔴 Fatal Error: {e}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)