from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_groq import ChatGroq
import os
from dotenv import load_dotenv

load_dotenv()

# 1. Define the 'State'. This is the memory shared by all nodes.
class InawoState(TypedDict):
    # 'add_messages' tells the graph to append new messages to history
    messages: Annotated[list, add_messages]
    business_type: str  # This tracks if we are in 'Food' or 'Fashion' mode

# 2. Initialize the Brain
llm = ChatGroq(model="meta-llama/llama-4-maverick-17b-128e-instruct")

# 3. Define the 'Assistant' Node
def assistant(state: InawoState):
    # This logic looks at the state and decides how to reply
    business = state.get("business_type", "General")
    
    # We create a specific instruction based on the business type
    system_msg = f"You are a helpful assistant for an {business} business in Nigeria. Speak warmly."
    
    # We combine the system message with the conversation history
    input_messages = [{"role": "system", "content": system_msg}] + state["messages"]
    response = llm.invoke(input_messages)
    
    return {"messages": [response]}

# 4. Build the Graph
workflow = StateGraph(InawoState)

# Add our assistant node
workflow.add_node("assistant_node", assistant)

# Tell the graph where to start and end
workflow.add_edge(START, "assistant_node")
workflow.add_edge("assistant_node", END)

# Compile the graph into an 'app'
inawo_app = workflow.compile()

# 5. Test it manually
if __name__ == "__main__":
    # Test as a FOOD business
    inputs = {
        "messages": [("user", "What do you have on the menu?")],
        "business_type": "Food"
    }
    for event in inawo_app.stream(inputs):
        for value in event.values():
            print("AI:", value["messages"][-1].content)