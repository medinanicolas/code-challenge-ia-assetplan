from langchain.tools import tool, InjectedToolCallId
from langchain.messages import ToolMessage, HumanMessage
from langgraph.types import Command
from typing import Literal, Annotated

from app.core.utils import create_handoff_tool
from app.agents.rag.graph import rag_graph


@tool
async def transfer_to_rag_agent(
    user_query: str, tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command[Literal["router"]]:
    """Ask rag agent for help"""
    try:
        result = await rag_graph.ainvoke({"messages": [HumanMessage(user_query)]})
        last_message = result["messages"][-1]
        content = last_message.content
    except Exception as e:
        content = f"Error in RAG agent: {str(e)}"

    messages = {
        "messages": [
            ToolMessage(
                content=content,
                name="transfer_to_rag_agent",
                tool_call_id=tool_call_id,
            )
        ]
    }
    return Command(goto="router", update=messages)


@tool
async def human_escape_hatch(
    reason: str, tool_call_id: Annotated[str, InjectedToolCallId]
):
    """Create a human agent request to attend this conversation

    Args:
        reason: Why the user wants to talk to a human agent"""
    try:
        content = str({"status": "created", "message": "Ticket has been created"})
    except Exception as e:
        content = f"Error creating ticket: {str(e)}"

    messages = {
        "messages": [
            ToolMessage(
                content=content,
                name="human_escape_hatch",
                tool_call_id=tool_call_id,
            )
        ]
    }
    return Command(goto="router", update=messages)


transfer_to_booking_agent = create_handoff_tool(
    name="transfer_to_booking_agent",
    agent_name="booking",
    graph="child",
    description="Transfer the control to Booking agent",
)
