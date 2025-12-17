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
llm = ChatGroq(model="llama-3.3-70b-versatile") 

def assistant(state: InawoState):
    business_context = state.get("business_type", "General Support")
    system_msg = (
        f"You are the AI manager for a business in Nigeria. "
        f"Business Details: {business_context}. Speak warmly and helpful."
    )
    input_messages = [{"role": "system", "content": system_msg}] + state["messages"]
    response = llm.invoke(input_messages)
    return {"messages": [response]}

workflow = StateGraph(InawoState)
workflow.add_node("assistant_node", assistant)
workflow.add_edge(START, "assistant_node")
workflow.add_edge("assistant_node", END)

inawo_app = workflow.compile()
