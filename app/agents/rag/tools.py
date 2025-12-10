from langchain.tools import tool
from app.agents.rag.retrieval import final_retriever

@tool
async def get_relevant_documents(query: str):
    """Get relevant documents by user query
    Args:
        query: La solicitud del usuario"""
    if final_retriever:
        docs = final_retriever.invoke(query)
        return {"documents": [doc.page_content for doc in docs]}
    return {"documents": ["Error: Retrieval system not initialized."]}
