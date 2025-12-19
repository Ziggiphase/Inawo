from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver 
from langchain_groq import ChatGroq
import os
from dotenv import load_dotenv

load_dotenv()

# We only keep 'messages' in the persistent state
class InawoState(TypedDict):
    messages: Annotated[list, add_messages]

llm = ChatGroq(model="llama-3.3-70b-versatile")

def assistant(state: InawoState, config: dict):
    # Retrieve the fresh business context passed during 'ainvoke'
    # This ensures the bot always uses the latest PDF data
    business_context = config.get("configurable", {}).get("business_data", "General Vendor")
    
    system_msg = (
        f"You are a helpful AI assistant for a business in Nigeria.\n"
        f"LATEST BUSINESS INFO: {business_context}\n"
        "Use the provided info to answer accurately. Speak warmly in a Nigerian tone. "
        "Remember the user's name and details from previous messages in this chat."
    )
    
    input_messages = [{"role": "system", "content": system_msg}] + state["messages"]
    response = llm.invoke(input_messages)
    return {"messages": [response]}

# Persistence layer
memory = MemorySaver()

workflow = StateGraph(InawoState)
workflow.add_node("assistant_node", assistant)
workflow.add_edge(START, "assistant_node")
workflow.add_edge("assistant_node", END)

# Compile with the memory checkpointer
inawo_app = workflow.compile(checkpointer=memory)
