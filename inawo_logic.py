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
def assistant(state: InawoState, config: RunnableConfig): # <--- Use RunnableConfig
    # Access the business data from the config
    # We use .get() on the 'configurable' key
    configurable = config.get("configurable", {})
    business_context = configurable.get("business_data", "General Vendor")
    
    system_msg = (
        f"You are a helpful AI assistant for a business in Nigeria.\n"
        f"LATEST BUSINESS INFO: {business_context}\n"
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
