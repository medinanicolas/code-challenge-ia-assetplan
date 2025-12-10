from langgraph.graph import MessagesState

class BookingState(MessagesState):
    name: str
    pet_name: str
    active_agent: str
