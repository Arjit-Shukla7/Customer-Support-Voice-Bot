import os
import asyncio
from dotenv import load_dotenv
from cartesia import AsyncCartesia
load_dotenv()

class CartesiaTTS:
    def __init__(self):
        self.api_key = os.getenv("CARTESIA_API_KEY")
        if not self.api_key:
            raise ValueError("CARTESIA_API_KEY is not set")
            
        # We will initialize the client inside the task for better lifecycle management
        self.model_id = "sonic-3"
        self.voice_id = "694f9389-aac1-45b6-b726-9d9369183238" 

    async def generate_test_audio(self, text: str, output_filename: str = "test_voice.wav"):
        """Verification Lego using the exact GitHub v3.x WebSocket pattern."""
        print(f"🎙️ Sending text to Cartesia via v3.x WebSocket: '{text}'")
        
        try:
            # Using the AsyncCartesia context manager as shown in GitHub
            async with AsyncCartesia(api_key=self.api_key) as client:
                async with client.tts.websocket_connect() as connection:
                    
                    # Create context with configuration
                    ctx = connection.context(
                        model_id=self.model_id,
                        voice={"mode": "id", "id": self.voice_id},
                        output_format={
                            "container": "raw",  # MUST be raw for WebSocket
                            "encoding": "pcm_s16le",
                            "sample_rate": 44100
                        }
                    )
                    
                    await ctx.push(text)
                    await ctx.no_more_inputs()
                    
                    # Save as .pcm instead of .wav for the test
                    with open("test_voice.pcm", "wb") as f:
                        async for response in ctx.receive():
                            if response.type == "chunk" and response.audio:
                                f.write(response.audio)
                                
                    print(f"✅ Audio saved successfully to test_voice.pcm")
            
        except Exception as e:
             print(f"🔴 Cartesia Error: {e}")

# --- ISOLATED TEST LOOP ---
if __name__ == "__main__":
    async def run_test():
        print("🔊 Starting Cartesia TTS Test...")
        tts = CartesiaTTS()
        test_text = "Hmm, I see. I'm really glad your tooth is feeling a bit better today!"
        await tts.generate_test_audio(test_text)

    asyncio.run(run_test())