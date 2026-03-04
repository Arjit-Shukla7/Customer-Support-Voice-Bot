import asyncio
import os
import uuid
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from sqlmodel import Session, select
from contextlib import AsyncExitStack

# --- IMPORTS ---
from core.database import engine, Patient, get_session, CallRecord
from agent.graph import app as langgraph_app
from agent.summarizer import PostCallAnalyst
from deepgram import AsyncDeepgramClient
from deepgram.core.events import EventType
from deepgram.listen.v1.types import ListenV1Results
from cartesia import AsyncCartesia

load_dotenv()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/admin/calls")
async def get_calls(session: Session = Depends(get_session)):
    statement = select(CallRecord, Patient).join(Patient)
    results = session.exec(statement).all()
    
    output = []
    for record, patient in results:
        output.append({
            "id": record.id,
            "patient_name": patient.name,
            "sentiment": record.sentiment,
            "summary": record.summary,
            "timestamp": record.created_at
        })
    return output

@app.websocket("/ws/{patient_id}")
async def voice_agent_endpoint(websocket: WebSocket, patient_id: int):
    await websocket.accept()
    print(f"\n🟢 Call Connected for Patient #{patient_id}")

    with Session(engine) as session:
        patient = session.get(Patient, patient_id)
        if not patient:
            print("🔴 Patient not found in DB.")
            await websocket.close()
            return
            
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    initial_state = {
        "patient_context": f"Name: {patient.name}. Medical History: {patient.medical_history}",
        "appointment_booked": False
    }

    dg_client = AsyncDeepgramClient()
    analyst = PostCallAnalyst()
    cartesia_api_key = os.getenv("CARTESIA_API_KEY")

    if not cartesia_api_key:
        print("🔴 ERROR: CARTESIA_API_KEY is missing from .env")
        await websocket.close()
        return

    try:
        async with AsyncCartesia(api_key=cartesia_api_key) as cartesia_client:
            async with dg_client.listen.v1.connect(model="nova-3", smart_format="true", interim_results="true", endpointing="500") as dg_connection:
                print("🟢 Deepgram and Cartesia Engines Online")

                current_ai_task = None
                user_transcript_buffer = ""
                
                # THE FIX 1: Track if we already flushed the frontend this turn
                turn_interrupted = False 

                # --- THE TTS GENERATION PIPELINE ---
                async def generate_and_speak(text_prompt: str, is_initial=False):
                    nonlocal turn_interrupted
                    turn_interrupted = False # Reset the flush flag for the new generation
                    audio_task = None # Initialize to prevent UnboundLocalError on cancellation
                    
                    print(f"\n🧠 AI Thinking about: {text_prompt[:40]}...")
                    
                    try:
                        input_msg = [] if is_initial else [HumanMessage(content=text_prompt)]
                        
                        async with AsyncExitStack() as stack:
                            cartesia_ws = None
                            ctx = None
                            text_buffer = ""
                            print("Agent: ", end="", flush=True)

                            async for event in langgraph_app.astream_events(
                                {**initial_state, "messages": input_msg}, 
                                config, 
                                version="v2"
                            ):
                                if event["event"] == "on_chat_model_stream":
                                    chunk = event["data"]["chunk"]
                                    if chunk.content:
                                        clean_chunk = chunk.content.replace('\n', ' ').replace('*', '')
                                        print(clean_chunk, end="", flush=True)
                                        text_buffer += clean_chunk
                                        
                                        if any(p in text_buffer for p in ['.', '?', '!']):
                                            if cartesia_ws is None:
                                                cartesia_ws = await stack.enter_async_context(
                                                    cartesia_client.tts.websocket_connect()
                                                )
                                                ctx = cartesia_ws.context(
                                                    model_id="sonic-3",
                                                    voice={"mode": "id", "id": "694f9389-aac1-45b6-b726-9d9369183238"},
                                                    output_format={"container": "raw", "encoding": "pcm_s16le", "sample_rate": 24000} 
                                                )

                                                async def pipe_audio_to_react():
                                                    try:
                                                        async for output in ctx.receive():
                                                            if output.type == "chunk" and output.audio:
                                                                await websocket.send_bytes(output.audio)
                                                            elif output.type == "error":
                                                                print(f"\n🔴 Cartesia Error: {output.error}")
                                                    except asyncio.CancelledError:
                                                        pass 
                                                        
                                                audio_task = asyncio.create_task(pipe_audio_to_react())

                                            await ctx.push(text_buffer)
                                            text_buffer = ""
                            
                            if text_buffer.strip():
                                if cartesia_ws is None:
                                    cartesia_ws = await stack.enter_async_context(
                                        cartesia_client.tts.websocket_connect()
                                    )
                                    ctx = cartesia_ws.context(
                                        model_id="sonic-3",
                                        voice={"mode": "id", "id": "694f9389-aac1-45b6-b726-9d9369183238"},
                                        output_format={"container": "raw", "encoding": "pcm_s16le", "sample_rate": 24000} 
                                    )
                                    async def pipe_audio_fallback():
                                        try:
                                            async for output in ctx.receive():
                                                if output.type == "chunk" and output.audio:
                                                    await websocket.send_bytes(output.audio)
                                        except asyncio.CancelledError:
                                            pass
                                    audio_task = asyncio.create_task(pipe_audio_fallback())

                                await ctx.push(text_buffer)
                            
                            if ctx:
                                await ctx.no_more_inputs()
                                await audio_task
                                print("\n✅ Response Complete.")
                                
                    except asyncio.CancelledError:
                        print("\n🛑 AI Generation Cancelled (Barge-in).")
                        if audio_task and not audio_task.done():
                            audio_task.cancel()
                        raise
                    except Exception as e:
                        print(f"\n🔴 TTS/Graph Error: {e}")

                # --- THE STT LISTENING PIPELINE ---
                async def on_message(message, **kwargs):
                    nonlocal user_transcript_buffer, current_ai_task, turn_interrupted
                    
                    if isinstance(message, ListenV1Results) and message.channel and message.channel.alternatives:
                        transcript = message.channel.alternatives[0].transcript
                        
                        if transcript.strip():
                            # THE FIX 2: Send CLEAR instantly to wipe React's buffered audio queue!
                            if not turn_interrupted:
                                turn_interrupted = True
                                print("\n💥 BARGE-IN: Flushing frontend audio buffer...")
                                await websocket.send_text("CLEAR")
                                
                                # Also kill the backend brain if it's still generating
                                if current_ai_task and not current_ai_task.done():
                                    current_ai_task.cancel()
                                    current_ai_task = None

                            if message.is_final:
                                user_transcript_buffer += transcript + " "
                                if message.speech_final:
                                    final_text = user_transcript_buffer.strip()
                                    print(f"\n✅ Patient: {final_text}")
                                    current_ai_task = asyncio.create_task(generate_and_speak(final_text))
                                    user_transcript_buffer = ""
                            else:
                                print(f"⏳ Listening... {user_transcript_buffer}{transcript}", end="\r")

                async def on_error(error, **kwargs):
                    print(f"\n🔴 Deepgram Connection Error: {error}")

                dg_connection.on(EventType.MESSAGE, on_message)
                dg_connection.on(EventType.ERROR, on_error)
                
                dg_task = asyncio.create_task(dg_connection.start_listening())
                
                kickoff_prompt = f"Greet {patient.name} and ask how they are feeling given their history: {patient.medical_history}"
                current_ai_task = asyncio.create_task(generate_and_speak(kickoff_prompt, is_initial=True))

                while True:
                    data = await websocket.receive_bytes()
                    await dg_connection.send_media(data)

    except WebSocketDisconnect:
        print("\n🔴 User Disconnected. Call Ended.")
        try:
            final_state = langgraph_app.get_state(config)
            chat_history = final_state.values.get("messages", [])
            
            print(f"📦 Found {len(chat_history)} messages in memory.")
            if len(chat_history) > 1: 
                print("📝 Sending transcript to Analyst (Groq)...")
                analyst.analyze_and_save(messages=chat_history, patient_id=patient_id)
                print("✅ Call successfully saved to Admin Database!")
            else:
                print("⚠️ Conversation was too short to summarize.")
                
        except Exception as e:
            print(f"🔴 Summarizer/Database Error: {e}")
            
    except Exception as e:
        print(f"\n🔴 Fatal Pipeline Error: {e}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)