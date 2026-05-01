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
    # 'add_messages' ensures new messages are appended to the history automatically
    messages: Annotated[list, add_messages]

# Using Llama 3.3 70B for high-quality Nigerian context understanding
llm = ChatGroq(model="llama-3.3-70b-specdec", groq_api_key=os.getenv("GROQ_API_KEY"))

def assistant(state: InawoState, config: RunnableConfig):
    # 1. Access dynamic configuration from the database/webhook
    configurable = config.get("configurable", {})
    is_paused = configurable.get("is_ai_paused", False)
    business_data = configurable.get("business_data", "A Nigerian Vendor")
    out_of_stock = configurable.get("out_of_stock", "None")

    # 2. HUMAN TAKE-OVER (Silent Mode)
    if is_paused:
        # If the vendor has paused the AI, we return no messages
        return {"messages": []}

    # 3. AI PERSONALITY & RULES
    # Optimized for speed and Nigerian business culture
    system_msg = (
        f"You are the AI Sales Assistant for {business_data}. "
        f"IMPORTANT: The following items are currently OUT OF STOCK: {out_of_stock}. "
        "Rules: "
        "1. Max 2 sentences per reply. "
        "2. Use friendly Nigerian business English (e.g., 'Welcome', 'Bless you'). "
        "3. If an item is out of stock, suggest an alternative politely. "
        "4. If the user sends an image/receipt, say 'I see your receipt! Verifying now...'"
    )
    
    # Combine system prompt with conversation history
    input_messages = [{"role": "system", "content": system_msg}] + state["messages"]
    
    try:
        response = llm.invoke(input_messages)
        return {"messages": [response]}
    except Exception as e:
        print(f"❌ AI Logic Error: {e}")
        return {"messages": [{"role": "assistant", "content": "I'm having a bit of trouble connecting. One moment please!"}]}

# 4. CONSTRUCT THE GRAPH
memory = MemorySaver()
workflow = StateGraph(InawoState)

workflow.add_node("assistant", assistant)
workflow.add_edge(START, "assistant")
workflow.add_edge("assistant", END)

# The checkpointer (memory) allows the AI to remember the customer's name across messages
inawo_app = workflow.compile(checkpointer=memory)
