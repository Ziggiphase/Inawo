from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver 
from langchain_groq import ChatGroq
from langchain_core.runnables import RunnableConfig  # <--- Add this import
import os
from dotenv import load_dotenv

load_dotenv()

class InawoState(TypedDict):
    messages: Annotated[list, add_messages]

llm = ChatGroq(model="llama-3.3-70b-versatile")

# --- UPDATED FUNCTION SIGNATURE ---
def assistant(state: InawoState, config: RunnableConfig):
    configurable = config.get("configurable", {})
    # 1. Check if the human has taken over
    is_manual = configurable.get("is_manual_mode", False)
    
    if is_manual:
        # The AI returns a "None" or empty response to stay silent
        # This allows the vendor to type freely in Telegram/WhatsApp
        return {"messages": []} 

    # 2. Otherwise, proceed with the usual AI sales logic
    business_context = configurable.get("business_data", "General Vendor")
    # ... rest of your AI logic
    
    system_msg = (
        f"You are an AI assistant for {business_name}. Current Status: {is_manual_mode}. If status is True, the owner is currently talking to the customer. Your role shifts to 'Silent Observer'—only provide suggestions if the owner asks you. If status is False, you are the primary 24/7 responder."
        "Use the provided info to answer accurately. Speak warmly in a Nigerian tone. "
        "Remember the user's name and details from previous messages in this chat."
    )
    
    input_messages = [{"role": "system", "content": system_msg}] + state["messages"]
    response = llm.invoke(input_messages)
    return {"messages": [response]}

memory = MemorySaver()

workflow = StateGraph(InawoState)
workflow.add_node("assistant_node", assistant)
workflow.add_edge(START, "assistant_node")
workflow.add_edge("assistant_node", END)

inawo_app = workflow.compile(checkpointer=memory)
