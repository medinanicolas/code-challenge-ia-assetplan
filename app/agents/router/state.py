from langgraph.graph import MessagesState

default_active_agent = "router"

class RouterState(MessagesState):
    active_agent: str = default_active_agent
