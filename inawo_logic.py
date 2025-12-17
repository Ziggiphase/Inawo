from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_groq import ChatGroq
import os
from dotenv import load_dotenv

load_dotenv()

class InawoState(TypedDict):
    messages: Annotated[list, add_messages]
    business_type: str 

# FIX: Using the correct stable Llama 3 model ID
llm = ChatGroq(model="llama-3.3-70b-versatile")

def assistant(state: InawoState):
    business_context = state.get("business_type", "General")
    
    # Strictly instruct the AI to use the provided data
    system_msg = (
        f"You are a helpful AI assistant for a business in Nigeria. "
        f"Context: {business_context}. "
        "Use the provided knowledge base to answer prices. Speak warmly in a Nigerian tone."
    )
    
    input_messages = [{"role": "system", "content": system_msg}] + state["messages"]
    response = llm.invoke(input_messages)
    return {"messages": [response]}

workflow = StateGraph(InawoState)
workflow.add_node("assistant_node", assistant)
workflow.add_edge(START, "assistant_node")
workflow.add_edge("assistant_node", END)
inawo_app = workflow.compile()
