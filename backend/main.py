from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()

# Allow React to communicate with FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("🟢 Client connected!")
    try:
        while True:
            # Wait for audio chunks from the frontend
            data = await websocket.receive_bytes()
            print(f"🎙️ Received audio chunk: {len(data)} bytes")
            
            # LEGO 1 ECHO TEST: Send the exact same audio back to the frontend
            await websocket.send_bytes(data)
            
    except WebSocketDisconnect:
        print("🔴 Client disconnected.")

if __name__ == "__main__":
    # Runs the server on port 8000
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)