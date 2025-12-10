from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import ToolNode
from langgraph.types import Command
from typing import Literal
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.messages import SystemMessage

from app.core.llm import model
from app.agents.booking.state import BookingState
from app.agents.booking.tools import check_availability, schedule_appointment, transfer_to_parent
from app.agents.booking.prompts import booking_system_prompt

booking_tools = [check_availability, schedule_appointment, transfer_to_parent]

booking_prompt_template = ChatPromptTemplate(
    [
        SystemMessage(booking_system_prompt),
        MessagesPlaceholder("messages")
    ]
)

booking_with_tools = model.bind_tools(booking_tools)
booking_chain = booking_prompt_template | booking_with_tools

def should_continue(state: BookingState):
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tool_node"
    return END

booking_tool_node = ToolNode(booking_tools)

async def booking_run_tool_node(state: BookingState, **kwargs) -> Command[Literal[END]]:
    return await booking_tool_node.ainvoke(state, **kwargs)

async def booking(state: BookingState):
    result = await booking_chain.ainvoke(state["messages"])
    return {"messages": [result]}

checkpointer = InMemorySaver()

booking_builder = StateGraph(BookingState)
booking_builder.add_node("booking", booking)
booking_builder.add_node("tool_node", booking_run_tool_node)
booking_builder.set_entry_point("booking")
booking_builder.add_conditional_edges("booking", should_continue, ["tool_node", END])
booking_builder.add_edge("tool_node", "booking")
booking_graph = booking_builder.compile(name="booking_graph", checkpointer=checkpointer)
