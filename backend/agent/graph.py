import os
import uuid
import asyncio
from dotenv import load_dotenv
from typing import Annotated, TypedDict
from langchain_core.messages import SystemMessage, HumanMessage, AnyMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

# Load API keys
load_dotenv()

# 1. Define the Strictly-Typed State
# 'messages' uses the add_messages reducer.
# 'patient_context' and 'appointment_booked' use the default "override" reducer.
class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    patient_context: str
    appointment_booked: bool

# 2. Initialize the LLM
# llama3-8b-8192 is currently the gold standard for Groq voice latency
llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model_name="llama-3.1-8b-instant", 
    temperature=0.5,
    streaming=True
)

# 3. Define the Core Node
def call_model(state: AgentState):
    messages = state["messages"]
    patient_context = state.get("patient_context", "No specific context provided.")
    
    # Inject the system prompt dynamically with the patient's context
    system_prompt = SystemMessage(content=f"""
You are a highly empathetic, professional healthcare support agent. 
Your job is to call the patient after their appointment, check how they are feeling, and see if they need anything else.
Be concise, conversational, and warm. Since your text will be spoken by a text-to-speech engine, avoid markdown, bullet points, or emojis.
Use natural filler words (like "Hmm", "I see", "Oh") occasionally to sound human.

Patient Context: {patient_context}
""")
    
    # Prepend the system prompt to the conversation history and invoke
    response = llm.invoke([system_prompt] + messages)
    
    # Return the new message to be appended to the state
    return {"messages": [response]}

# 4. Build the Graph
workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_edge(START, "agent")
workflow.add_edge("agent", END)

# 5. Attach Memory and Compile
memory = MemorySaver()
app = workflow.compile(checkpointer=memory)

# --- ISOLATED TEST LOOP ---
if __name__ == "__main__":
    async def test_streaming():
        print("🧠 Starting LangGraph + Groq Test...")
        
        # Create a unique thread ID for this specific call session's memory
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        
        # Initial context overrides
        initial_state = {
            "patient_context": "Patient had a root canal yesterday. Might be experiencing mild pain.",
            "appointment_booked": False
        }
        
        while True:
            user_input = input("\nYou: ")
            if user_input.lower() in ["quit", "exit"]:
                break
                
            print("Agent: ", end="", flush=True)
            
            # Using astream_events to catch tokens the millisecond they are generated
            async for event in app.astream_events(
                {"messages": [HumanMessage(content=user_input)], **initial_state}, 
                config, 
                version="v2"
            ):
                kind = event["event"]
                # Filter strictly for the streaming tokens from Groq
                if kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if chunk.content:
                        print(chunk.content, end="", flush=True)
            print() 

    # Run the async test loop
    asyncio.run(test_streaming())