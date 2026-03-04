import asyncio
import os
import uuid
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from sqlmodel import Session, select

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

# ==========================================
# ADMIN DASHBOARD API
# ==========================================
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

# ==========================================
# REAL-TIME VOICE WEBSOCKET
# ==========================================
@app.websocket("/ws/{patient_id}")
async def voice_agent_endpoint(websocket: WebSocket, patient_id: int):
    await websocket.accept()
    print(f"\n🟢 Call Connected for Patient #{patient_id}")

    # Fetch Medical Context
    with Session(engine) as session:
        patient = session.get(Patient, patient_id)
        if not patient:
            print("🔴 Patient not found in DB.")
            await websocket.close()
            return
            
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    # LangGraph State (No empty messages array to prevent amnesia)
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
        # Keep the main client open for the duration of the call
        async with AsyncCartesia(api_key=cartesia_api_key) as cartesia_client:
            async with dg_client.listen.v1.connect(model="nova-3", smart_format="true", interim_results="true", endpointing="500") as dg_connection:
                print("🟢 Deepgram and Cartesia Engines Online")

                current_ai_task = None
                user_transcript_buffer = ""

                # --- THE TTS GENERATION PIPELINE ---
                async def generate_and_speak(text_prompt: str, is_initial=False):
                    print(f"\n🧠 AI Thinking about: {text_prompt[:40]}...")
                    
                    try:
                        # FIX: Open a fresh WS for Cartesia every turn to prevent Idle Timeouts
                        async with cartesia_client.tts.websocket_connect() as cartesia_ws:
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
                                            print(f"\n🔴 Cartesia API Error: {output.error}")
                                except asyncio.CancelledError:
                                    pass 
                                except Exception as e:
                                    print(f"\n🔴 Audio Pipe Error: {e}")

                            audio_task = asyncio.create_task(pipe_audio_to_react())
                            
                            input_msg = [] if is_initial else [HumanMessage(content=text_prompt)]
                            
                            try:
                                print("Agent: ", end="", flush=True)
                                async for event in langgraph_app.astream_events(
                                    {**initial_state, "messages": input_msg}, 
                                    config, 
                                    version="v2"
                                ):
                                    if event["event"] == "on_chat_model_stream":
                                        chunk = event["data"]["chunk"]
                                        if chunk.content:
                                            print(chunk.content, end="", flush=True)
                                            # Strip newlines to prevent Cartesia frame crashes
                                            clean_text = chunk.content.replace('\n', ' ')
                                        
                                            # THE FIX: Only push if the string isn't pure whitespace!
                                            if clean_text.strip():
                                                await ctx.push(clean_text)
                                
                                print("\n✅ Response Complete.")
                                await ctx.no_more_inputs()
                                await audio_task
                            except asyncio.CancelledError:
                                print("\n🛑 AI Generation Cancelled (Barge-in).")
                                await ctx.no_more_inputs()
                                audio_task.cancel()
                                raise
                    except Exception as e:
                        print(f"\n🔴 TTS/Graph Error: {e}")

                # --- THE STT LISTENING PIPELINE ---
                async def on_message(message, **kwargs):
                    nonlocal user_transcript_buffer, current_ai_task
                    
                    if isinstance(message, ListenV1Results) and message.channel and message.channel.alternatives:
                        transcript = message.channel.alternatives[0].transcript
                        
                        if transcript.strip():
                            # HAIR-TRIGGER BARGE-IN: Kill AI instantly if user makes a sound
                            if current_ai_task and not current_ai_task.done():
                                current_ai_task.cancel()
                                current_ai_task = None
                                await websocket.send_text("CLEAR")

                            if message.is_final:
                                user_transcript_buffer += transcript + " "
                                if message.speech_final:
                                    final_text = user_transcript_buffer.strip()
                                    print(f"\n✅ Patient: {final_text}")
                                    # Trigger the new AI thought
                                    current_ai_task = asyncio.create_task(generate_and_speak(final_text))
                                    user_transcript_buffer = ""
                            else:
                                print(f"⏳ Listening... {user_transcript_buffer}{transcript}", end="\r")

                async def on_error(error, **kwargs):
                    print(f"\n🔴 Deepgram Connection Error: {error}")

                dg_connection.on(EventType.MESSAGE, on_message)
                dg_connection.on(EventType.ERROR, on_error)
                
                dg_task = asyncio.create_task(dg_connection.start_listening())
                
                # Kickoff the conversation
                kickoff_prompt = f"Greet {patient.name} and ask how they are feeling given their history: {patient.medical_history}"
                current_ai_task = asyncio.create_task(generate_and_speak(kickoff_prompt, is_initial=True))

                # Stream mic bytes to Deepgram continuously
                while True:
                    data = await websocket.receive_bytes()
                    await dg_connection.send_media(data)

    except WebSocketDisconnect:
        print("\n🔴 User Disconnected.")
        try:
            final_state = langgraph_app.get_state(config)
            chat_history = final_state.values.get("messages", [])
            if chat_history:
                print("📝 Generating call summary...")
                analyst.analyze_and_save(chat_history, patient_id)
        except Exception as e:
            print(f"🔴 Summarizer Error: {e}")
            
    except Exception as e:
        print(f"\n🔴 Fatal Pipeline Error: {e}")

# THIS MUST REMAIN AT THE VERY BOTTOM
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)