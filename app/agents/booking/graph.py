from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import ToolNode
from langgraph.types import Command
from typing import Literal
from datetime import datetime
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
)
from langchain.messages import SystemMessage

from app.core.llm import gpt_5_mini
from app.agents.booking.state import BookingState
from app.agents.booking.tools import (
    check_availability,
    schedule_appointment,
    transfer_to_parent,
)
from app.agents.booking.prompts import booking_system_prompt

booking_tools = [check_availability, schedule_appointment, transfer_to_parent]

booking_prompt_template = ChatPromptTemplate(
    [
        SystemMessagePromptTemplate.from_template(booking_system_prompt),
        MessagesPlaceholder("messages"),
    ]
)

booking_with_tools = gpt_5_mini.bind_tools(booking_tools)
booking_chain = booking_prompt_template | booking_with_tools


def should_continue(state: BookingState):
    """Check if the booking process needs to execute tools."""
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tool_node"
    return END


booking_tool_node = ToolNode(booking_tools)


async def booking_run_tool_node(state: BookingState, **kwargs) -> Command[Literal[END]]:
    """Execute the booking tools."""
    return await booking_tool_node.ainvoke(state, **kwargs)


async def booking(state: BookingState):
    """Invoke the booking chain."""
    current_time = datetime.now().isoformat()
    result = await booking_chain.ainvoke(
        {"current_time": current_time, "messages": state["messages"]}
    )
    return {"messages": [result]}


checkpointer = InMemorySaver()

booking_builder = StateGraph(BookingState)
booking_builder.add_node("booking", booking)
booking_builder.add_node("tool_node", booking_run_tool_node)
booking_builder.set_entry_point("booking")
booking_builder.add_conditional_edges("booking", should_continue, ["tool_node", END])
booking_builder.add_edge("tool_node", "booking")
booking_graph = booking_builder.compile(name="booking_graph", checkpointer=checkpointer)
