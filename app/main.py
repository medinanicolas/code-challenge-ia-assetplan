import asyncio
from uuid import uuid4
from langchain.messages import HumanMessage
from app.agents.router.graph import router_graph
from app.core.utils import print_debug_event

async def main():
    run_id = uuid4()
    print(f"Starting run {run_id}")
    
    # Example interaction
    async for event in router_graph.astream(
        input={"messages": [HumanMessage("Hola, que sintomas puede tener un perro estresado?")]}, 
        config={"configurable": {"thread_id": run_id}},
        stream_mode="debug",
        subgraphs=True
    ):
        print_debug_event(event)

if __name__ == "__main__":
    asyncio.run(main())
