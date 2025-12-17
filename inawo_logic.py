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

# Use a verified Groq model ID
llm = ChatGroq(model="llama-3.1-8b-instant") 

def assistant(state: InawoState):
    business_context = state.get("business_type", "General Support")
    
    # We add a STRICT command to the AI here
    system_msg = (
        f"You are a factual assistant/ AI manager in Nigeria. If the user asks for a price, look at the BUSINESS DATA. Provide the exact price listed there. If the price is not there, say: 'I don't have the price for that yet, please contact the manager directly.\n"
        f"STRCT RULE: Use ONLY the following information to answer. "
        f"If a price or item is not listed here, say you don't have that information.\n"
        f"BUSINESS DATA: {business_context}\n"
        f"Speak warmly and helpful."
        f"Keep your responses concise and under 3 sentences unless asked for details."
    )
    # Rest of the code remains the same...
    input_messages = [{"role": "system", "content": system_msg}] + state["messages"]
    response = llm.invoke(input_messages)
    return {"messages": [response]}

workflow = StateGraph(InawoState)
workflow.add_node("assistant_node", assistant)
workflow.add_edge(START, "assistant_node")
workflow.add_edge("assistant_node", END)

inawo_app = workflow.compile()
