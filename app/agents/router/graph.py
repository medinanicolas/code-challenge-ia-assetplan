from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import ToolNode
from langgraph.types import Command
from typing import Literal
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.messages import AIMessage, SystemMessage

from app.core.llm import gpt_5_mini, gpt_5_nano
from app.agents.router.state import RouterState, default_active_agent
from app.agents.router.tools import (
    transfer_to_rag_agent,
    transfer_to_booking_agent,
    human_escape_hatch,
)
from app.agents.router.prompts import (
    coordinator_system_prompt,
    guardrail_system_prompt,
    explanation_system_prompt,
)
from app.agents.booking.graph import booking_graph
from app.agents.rag.graph import rag_graph
from pydantic import BaseModel

guardrail_prompt_template = ChatPromptTemplate(
    [SystemMessage(guardrail_system_prompt), MessagesPlaceholder("messages")]
)

router_tools = [transfer_to_rag_agent, transfer_to_booking_agent, human_escape_hatch]

router_prompt_template = ChatPromptTemplate(
    [SystemMessage(coordinator_system_prompt), MessagesPlaceholder("messages")]
)


class GuardrailOutput(BaseModel):
    is_inapropiate: bool
    response: str


guardrail_chain = guardrail_prompt_template | gpt_5_nano.with_structured_output(
    GuardrailOutput
)

explanation_chain = (
    ChatPromptTemplate(
        [SystemMessage(explanation_system_prompt), MessagesPlaceholder("messages")]
    )
    | gpt_5_nano
)

router_with_tools = gpt_5_mini.bind_tools(router_tools)
router_chain = router_prompt_template | router_with_tools


async def guardrail(state: RouterState):
    """Apply guardrails to the conversation."""
    print(f"[DEBUG] Guardrail check started for latest message.")
    result: GuardrailOutput = await guardrail_chain.ainvoke({"messages": state["messages"]})  # type: ignore

    if result.is_inapropiate:
        print(f"[DEBUG] Guardrail BLOCKED conversation. Risk detected.")
        explanation = await explanation_chain.ainvoke({"messages": state["messages"]})
        print(f"[DEBUG] Generated explanation: {explanation.content[:50]}...")
        return Command(goto=END, update={"messages": AIMessage(explanation.content)})

    print(f"[DEBUG] Guardrail PASSED. Proceeding.")
    return state


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
    result = await router_chain.ainvoke({"messages": state["messages"]})
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
router_builder.add_node("guardrail", guardrail)
router_builder.add_node("router", router)
router_builder.add_node("booking", booking_graph)
router_builder.add_node("rag", rag_graph)
router_builder.add_node("tool_node", router_run_tool_node)
router_builder.add_edge(START, "guardrail")
router_builder.add_conditional_edges(
    "guardrail", route_active_agent, ["router", "booking", END]
)
router_builder.add_conditional_edges("router", should_continue, ["tool_node", END])
router_graph = router_builder.compile(name="router_graph", checkpointer=InMemorySaver())
