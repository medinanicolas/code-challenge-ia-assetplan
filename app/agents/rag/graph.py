from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.messages import SystemMessage, ToolMessage

from app.core.llm import model
from app.agents.rag.state import RagState
from app.agents.rag.tools import get_relevant_documents
from app.agents.rag.prompts import rag_system_prompt

rag_tools = [get_relevant_documents]
rag_tools_by_name = {tool.name: tool for tool in rag_tools}

rag_prompt_template = ChatPromptTemplate(
    [SystemMessage(rag_system_prompt), MessagesPlaceholder("messages")]
)

rag_with_tools = model.bind_tools(rag_tools)
rag_chain = rag_prompt_template | rag_with_tools


async def tool_node(state: RagState):
    """Execute the retrieval tool."""
    result = []
    for tool_call in state["messages"][-1].tool_calls:
        tool = rag_tools_by_name[tool_call["name"]]
        observation = await tool.ainvoke(tool_call["args"])
        result.append(ToolMessage(content=observation, tool_call_id=tool_call["id"]))
    return {"messages": result}


def should_continue(state: RagState):
    """Determine if the conversation should continue to tools or end."""
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tool_node"
    return END


async def rag(state: RagState):
    """Invoke the RAG chain (LLM with retrieval tools)."""
    result = await rag_chain.ainvoke(state["messages"])
    return {"messages": [result]}


rag_builder = StateGraph(RagState)
rag_builder.add_node("rag", rag)
rag_builder.add_node("tool_node", tool_node)
rag_builder.set_entry_point("rag")
rag_builder.add_conditional_edges("rag", should_continue, ["tool_node", END])
rag_builder.add_edge("tool_node", "rag")
rag_graph = rag_builder.compile(name="rag_graph")
