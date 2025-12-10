from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import ToolNode
from langgraph.types import Command
from typing import Literal
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.messages import SystemMessage

from app.core.llm import model
from app.agents.router.state import RouterState, default_active_agent
from app.agents.router.tools import (
    transfer_to_rag_agent,
    transfer_to_booking_agent,
    human_escape_hatch,
)
from app.agents.router.prompts import coordinator_system_prompt
from app.agents.booking.graph import booking_graph
from app.agents.rag.graph import rag_graph

router_tools = [transfer_to_rag_agent, transfer_to_booking_agent, human_escape_hatch]

router_prompt_template = ChatPromptTemplate(
    [SystemMessage(coordinator_system_prompt), MessagesPlaceholder("messages")]
)

router_with_tools = model.bind_tools(router_tools)
router_chain = router_prompt_template | router_with_tools


def should_continue(state: RouterState):
    """Determine the next step based on the result of the last message."""
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tool_node"
    print("Nothing more to do")
    return END


async def router(state: RouterState):
    """Invoke the router chain (LLM with tools)."""
    result = await router_chain.ainvoke(state["messages"])
    return {"messages": [result]}


def route_active_agent(state: RouterState):
    """Route to the active agent or default agent."""
    # print("Current state:", state)
    return state.get("active_agent", default_active_agent)


router_tool_node = ToolNode(router_tools)


async def router_run_tool_node(
    state: RouterState, **kwargs
) -> Command[Literal["booking", "rag"]]:
    """Execute the tool node and return the command to switch agents."""
    return await router_tool_node.ainvoke(state, **kwargs)


router_builder = StateGraph(RouterState)
router_builder.add_node("router", router)
router_builder.add_node("booking", booking_graph)
router_builder.add_node("rag", rag_graph)
router_builder.add_node("tool_node", router_run_tool_node)
router_builder.add_conditional_edges(
    START, route_active_agent, ["router", "booking", END]
)
router_builder.add_conditional_edges("router", should_continue, ["tool_node", END])
router_graph = router_builder.compile(name="router_graph", checkpointer=InMemorySaver())
