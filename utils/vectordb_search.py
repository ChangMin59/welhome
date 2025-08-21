from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from transformers import AutoTokenizer
from typing import List
from langchain.schema import Document

tokenizer = AutoTokenizer.from_pretrained("BAAI/bge-m3")
embedding_model = HuggingFaceEmbeddings(
    model_name="BAAI/bge-m3",
    model_kwargs={"device": "cuda"},
    encode_kwargs={"normalize_embeddings": True}
)

persist_dir = "/home/alpaco/lyj0622/chromaDB"
vectordb = Chroma(
    collection_name="housing_collection",
    persist_directory=persist_dir,
    embedding_function=embedding_model
)

def search_notice_in_vectordb(query: str, notice_id: str, top_k: int = 1) -> List[Document]:
    try:
        results = vectordb.similarity_search(
            query,
            k=top_k,
            filter={"notice_id": notice_id}
        )
        return results
    except Exception as e:
        print(f"❗ 벡터 검색 오류: {e}")
        return []
