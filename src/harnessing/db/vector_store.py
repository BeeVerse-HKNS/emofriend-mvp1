from pathlib import Path
from typing import Any

import chromadb

VECTOR_DB_PATH = Path(__file__).parent.parent.parent.parent / "data" / "chroma_db"


class VectorStore:
    def __init__(self, db_path: Path | None = None) -> None:
        path = str(db_path or VECTOR_DB_PATH)
        self.client = chromadb.PersistentClient(path=path)
        self.collection = self.client.get_or_create_collection(
            name="harnessing_knowledge",
            metadata={"description": "Harnessing project knowledge base vectors"},
        )

    def add(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        self.collection.add(ids=ids, documents=documents, metadatas=metadatas)  # type: ignore[arg-type]

    def search(self, query: str, n_results: int = 5) -> list[dict[str, Any]]:
        results = self.collection.query(query_texts=[query], n_results=n_results)
        ids_list = results["ids"][0] if results["ids"] else []
        docs_list = results["documents"][0] if results["documents"] else []
        meta_list = results["metadatas"][0] if results["metadatas"] else []
        dist_list = results["distances"][0] if results["distances"] else []
        entries: list[dict[str, Any]] = []
        for i in range(len(ids_list)):
            entries.append({
                "id": ids_list[i],
                "document": docs_list[i],
                "metadata": meta_list[i] if meta_list else None,
                "distance": dist_list[i] if dist_list else None,
            })
        return entries

    def count(self) -> int:
        return self.collection.count()
