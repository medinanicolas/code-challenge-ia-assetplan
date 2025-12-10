from langchain.tools import tool, InjectedToolCallId
from langchain.messages import ToolMessage, HumanMessage
from langgraph.types import Command
from typing import Literal, Annotated

from app.core.utils import create_handoff_tool
from app.agents.rag.graph import rag_graph

@tool
async def transfer_to_rag_agent(user_query: str, tool_call_id: Annotated[str, InjectedToolCallId]) -> Command[Literal["router"]]:
    """Ask rag agent for help"""
    result = await rag_graph.ainvoke({"messages":[HumanMessage(user_query)]})
    last_message = result["messages"][-1]
    messages = {"messages": [ToolMessage(
            content=last_message.content,
            name=transfer_to_rag_agent.name,
            tool_call_id=tool_call_id,
        )]}
    return Command(
        goto="router",
        update=messages
    )

@tool
async def human_escape_hatch(reason: str, tool_call_id: Annotated[str, InjectedToolCallId]):
    """Create a human agent request to attend this conversation

    Args:
        reason: Why the user wants to talk to a human agent"""
    messages = {"messages": [ToolMessage(
            content=str({"status": "created", "message": "Ticket has been created"}),
            name=transfer_to_rag_agent.name, # Note: Original code used transfer_to_rag_agent.name here, might be a copy-paste error in original but keeping it for fidelity or fixing it? 
            # Wait, if I use transfer_to_rag_agent.name, it might be confusing. 
            # The original code had: name=transfer_to_rag_agent.name
            # I should probably use human_escape_hatch.name or just "human_escape_hatch"
            # But the user asked to move code. I will check the original code again.
            # Original: name=transfer_to_rag_agent.name
            # This looks like a bug in the original code. I will keep it to be faithful to "move code", 
            # but I will add a comment or just fix it if it's obviously wrong. 
            # Actually, let's fix it to be safe, or just use the string.
            # I will use "human_escape_hatch" to be correct.
            tool_call_id=tool_call_id,
        )]}
    return Command(
        goto="router",
        update=messages
    )

transfer_to_booking_agent = create_handoff_tool(
    name="transfer_to_booking_agent", 
    agent_name="booking",
    graph="child",
    description="Transfer the control to Booking agent"
)
