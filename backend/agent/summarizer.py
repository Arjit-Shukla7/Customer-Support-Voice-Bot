import os
import json
from dotenv import load_dotenv
from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, AnyMessage
from sqlmodel import Session

# Import our database setup from Lego 5
from core.database import engine, CallRecord, Patient

load_dotenv()

# 1. Define the Strict JSON Schema for the Admin Dashboard
class CallSummary(BaseModel):
    sentiment: str = Field(description="The emotional state of the patient (e.g., 'Positive', 'Frustrated', 'In Pain', 'Neutral'). Keep it to 1-2 words.")
    summary: str = Field(description="A concise 2-3 sentence summary of the call's outcome.")
    action_items: List[str] = Field(description="A list of specific follow-up actions required by the clinic (e.g., 'Call back tomorrow', 'Adjust medication'). Empty list if none.")

class PostCallAnalyst:
    def __init__(self):
        # We can use a slightly larger or standard model for summarization since it's post-call (latency isn't as critical)
        # But llama3-8b-8192 is still blazing fast and handles structured JSON perfectly.
        self.llm = ChatGroq(
            api_key=os.getenv("GROQ_API_KEY"),
            model_name="llama-3.1-8b-instant", 
            temperature=0.1 # Low temperature for factual extraction
        )
        # Force the LLM to output the exact Pydantic schema
        self.structured_llm = self.llm.with_structured_output(CallSummary)

    def _format_transcript(self, messages: List[AnyMessage]) -> str:
        """Converts LangChain message objects into a readable string efficiently."""
        transcript_parts = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                transcript_parts.append(f"Patient: {msg.content}")
            elif isinstance(msg, AIMessage) and msg.content:
                transcript_parts.append(f"Agent: {msg.content}")
                
        # Joins the list efficiently, and falls back if the call dropped immediately
        return "\n".join(transcript_parts) or "No conversation transcript available."

    def analyze_and_save(self, messages: List[AnyMessage], patient_id: int) -> CallRecord:
        """Runs the analysis and saves the result to SQLite."""
        
        # 1. Generate the raw text transcript
        raw_transcript = self._format_transcript(messages)
        
        # 2. Prompt Groq to extract the structured data
        print("🧠 Analyzing call transcript...")
        analysis_prompt = f"""
        Analyze the following healthcare support call transcript.
        Extract the sentiment, a brief summary, and any required action items for the clinic staff.
        
        Transcript:
        {raw_transcript}
        """
        
        # The output is automatically parsed into our CallSummary Pydantic object!
        result: CallSummary = self.structured_llm.invoke(analysis_prompt)
        
        # 3. Save to the Database
        with Session(engine) as session:
            # We convert the action_items list to a JSON string so it stores nicely in SQLite
            action_items_str = json.dumps(result.action_items)
            
            # Combine the summary and action items for the DB column
            full_summary_text = f"{result.summary}\nAction Items: {action_items_str}"
            
            new_record = CallRecord(
                patient_id=patient_id,
                transcript=raw_transcript,
                summary=full_summary_text,
                sentiment=result.sentiment
            )
            
            session.add(new_record)
            session.commit()
            session.refresh(new_record)
            
            print(f"✅ Call Record #{new_record.id} saved to database!")
            print(f"   Sentiment: {new_record.sentiment}")
            print(f"   Summary: {result.summary}")
            
            return new_record

# --- ISOLATED TEST LOOP ---
if __name__ == "__main__":
    # Let's simulate a call history that LangGraph would typically pass to us
    dummy_messages = [
        AIMessage(content="Hello John, I'm calling from the dental clinic to check on you after your wisdom tooth extraction yesterday. How are you feeling?"),
        HumanMessage(content="Hi. Honestly, it hurts a lot more than I expected, and the swelling is pretty bad on my left side."),
        AIMessage(content="I'm so sorry to hear you're in pain, John. Have you been taking the prescribed Ibuprofen?"),
        HumanMessage(content="Yes, but it doesn't seem to be doing much. I think I might need something stronger."),
        AIMessage(content="I understand. I will immediately flag this for Dr. Smith so they can review your chart and potentially adjust your medication. Someone will call you back within the hour."),
        HumanMessage(content="Okay, thank you. I'd appreciate that.")
    ]

    analyst = PostCallAnalyst()
    # We pass patient_id=1 (John Doe from our DB seed script)
    analyst.analyze_and_save(messages=dummy_messages, patient_id=1)