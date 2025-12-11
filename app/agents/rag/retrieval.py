import os
import pickle
from typing import List, Dict, Any, Sequence
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import Callbacks
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever, ContextualCompressionRetriever
from langchain_classic.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder

class ScoreInjectedReranker(CrossEncoderReranker):
    def compress_documents(
        self,
        documents: Sequence[Document],
        query: str,
        callbacks: Callbacks = None,
    ) -> Sequence[Document]:
        if len(documents) == 0:
            return []
        pairs = [(query, doc.page_content) for doc in documents]
        scores = self.model.score(pairs)
        docs_with_scores = list(zip(documents, scores))
        result = sorted(docs_with_scores, key=lambda x: x[1], reverse=True)
        final_results = []
        for doc, score in result[:self.top_n]:
            new_doc = Document(
                page_content=doc.page_content,
                metadata=doc.metadata.copy()
            )
            new_doc.metadata["relevance_score"] = float(score)
            final_results.append(new_doc)         
        return final_results

class CustomHybridParentRetriever(BaseRetriever):
    child_retriever: Any
    docstore: Dict[str, Document] = {}
    id_key: str = "parent_id"
    def _get_relevant_documents(self, query: str, *, run_manager=None) -> List[Document]:
        optimized_children = self.child_retriever.invoke(query)
        parent_map = {}
        for child in optimized_children:
            p_id = child.metadata.get(self.id_key)
            score = child.metadata.get("relevance_score", -999.0)
            if p_id:
                if p_id not in parent_map:
                    parent_map[p_id] = score
                else:
                    parent_map[p_id] = max(parent_map[p_id], score)
        final_docs = []
        for p_id, score in parent_map.items():
            if p_id in self.docstore:
                parent_doc = self.docstore[p_id]
                enriched_doc = Document(
                    page_content=parent_doc.page_content,
                    metadata=parent_doc.metadata.copy()
                )
                enriched_doc.metadata["retrieved_parent_id"] = p_id
                enriched_doc.metadata["final_score"] = score
                header_context = ""
                meta = enriched_doc.metadata
                if "Module" in meta: header_context += f"# {meta['Module']}\n"
                if "Section" in meta: header_context += f"## {meta['Section']}\n"
                if "Topic" in meta: header_context += f"# {meta['Topic']}\n"
                if "Subtopic" in meta: header_context += f"## {meta['Subtopic']}\n"
                if header_context:
                    enriched_doc.page_content = header_context + "\n" + enriched_doc.page_content
                final_docs.append(enriched_doc)    
        final_docs.sort(key=lambda x: x.metadata.get("final_score", -999), reverse=True)
        return final_docs

CHROMA_PATH = "data/chroma_db"
def get_vectorstore_connection():
    return Chroma(
        collection_name="rag_final",
        embedding_function=OpenAIEmbeddings(),
        persist_directory=CHROMA_PATH
    )

# Setup retrievers
DOCSTORE_PATH = "data/docstore_parents.pkl"
BM25_PATH = "data/bm25_index.pkl"
RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"

# Note: This logic assumes files exist. In a real app, this might need to be wrapped or checked.
# For now, we keep the logic as is, but we might need to adjust paths if running from app/
# The original code assumed running from root.

if not os.path.exists(DOCSTORE_PATH):
    # raise Exception("❌ Ejecuta ingesta primero.")
    # Commented out to avoid immediate crash if files are missing during refactor
    pass

try:
    with open(DOCSTORE_PATH, "rb") as f: docstore = pickle.load(f)
    with open(BM25_PATH, "rb") as f: bm25_retriever = pickle.load(f)
    vector_db = get_vectorstore_connection()
    chroma_retriever = vector_db.as_retriever(search_kwargs={"k": 20})
    ensemble_retriever = EnsembleRetriever(
        retrievers=[bm25_retriever, chroma_retriever], weights=[0.4, 0.6]
    )
    rerank_model = HuggingFaceCrossEncoder(model_name=RERANKER_MODEL)
    compressor = ScoreInjectedReranker(model=rerank_model, top_n=3)
    compression_retriever = ContextualCompressionRetriever(
        base_compressor=compressor, base_retriever=ensemble_retriever
    )
    final_retriever = CustomHybridParentRetriever(child_retriever=compression_retriever)
    final_retriever.docstore = docstore
except Exception as e:
    print(f"Warning: Could not initialize retrievers: {e}")
    final_retriever = None
