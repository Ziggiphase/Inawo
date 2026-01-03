from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver 
from langchain_groq import ChatGroq
from langchain_core.runnables import RunnableConfig
import os
from dotenv import load_dotenv

load_dotenv()

class InawoState(TypedDict):
    messages: Annotated[list, add_messages]

llm = ChatGroq(model="llama-3.3-70b-versatile")

def assistant(state: InawoState, config: RunnableConfig):
    # 1. Access the configuration passed from inawo_bot.py
    configurable = config.get("configurable", {})
    is_manual = configurable.get("is_manual_mode", False)
    business_context = configurable.get("business_data", "General Vendor")

    # 2. HUMAN-IN-THE-LOOP CHECK
    # If the vendor is in the chat, the AI stays silent.
    if is_manual:
        # Return an empty list so no message is sent to the customer
        return {"messages": []}

    # 3. NORMAL AI MODE
    system_msg = (
        f"You are a helpful AI assistant for a business in Nigeria.\n"
        f"BUSINESS DATA: {business_context}\n"
        "Use this data to answer prices. Speak warmly in a Nigerian tone. "
        "If the user sends a receipt, acknowledge it was sent to the vendor."
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
