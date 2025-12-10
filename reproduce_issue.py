import os
import sys

# Add the current directory to sys.path to make app importable
sys.path.append(os.getcwd())

from dotenv import load_dotenv

load_dotenv()

try:
    from app.agents.rag.retrieval import final_retriever, vector_db

    if final_retriever:
        print("Retriever initialized successfully.")
    else:
        print("Retriever failed to initialize (final_retriever is None).")
except Exception as e:
    print(f"Exception during import: {e}")
