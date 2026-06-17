import os
import pickle

import faiss
import numpy as np


class VectorStore:
    def __init__(self, dimension: int = 1536):
        self.dimension = dimension
        self.index = faiss.IndexFlatL2(dimension)
        self.metadata = []

    def _reset_index(self):
        self.index = faiss.IndexFlatL2(self.dimension)

    def add_vectors(self, vectors, metadata):
        vectors_np = np.array(vectors).astype("float32")

        if len(vectors_np.shape) != 2:
            raise ValueError("Vectors must be a 2D array.")

        if vectors_np.shape[1] != self.dimension:
            raise ValueError(
                f"Expected dimension {self.dimension}, got {vectors_np.shape[1]}"
            )

        self.index.add(vectors_np)
        self.metadata.extend(metadata)

    def search(self, query_vector, top_k: int = 5):
        if self.index.ntotal == 0:
            return []

        query_np = np.array([query_vector]).astype("float32")
        distances, indices = self.index.search(query_np, top_k)

        results = []

        for distance, index in zip(distances[0], indices[0]):
            if index == -1:
                continue

            item = self.metadata[index].copy()
            item.pop("embedding", None)  # do not return embedding to frontend
            item["distance"] = float(distance)
            results.append(item)

        return results

    def count(self):
        return self.index.ntotal

    def save(self, index_path: str, metadata_path: str):
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        faiss.write_index(self.index, index_path)

        with open(metadata_path, "wb") as file:
            pickle.dump(self.metadata, file)

    def load(self, index_path: str, metadata_path: str):
        if not os.path.exists(index_path) or not os.path.exists(metadata_path):
            return False

        self.index = faiss.read_index(index_path)

        with open(metadata_path, "rb") as file:
            self.metadata = pickle.load(file)

        return True

    def list_documents(self):
        documents = {}

        for item in self.metadata:
            filename = item["filename"]

            if filename not in documents:
                documents[filename] = {
                    "filename": filename,
                    "chunks": 0,
                    "pages": set()
                }

            documents[filename]["chunks"] += 1
            documents[filename]["pages"].add(item["page"])

        result = []

        for filename, info in documents.items():
            result.append({
                "filename": filename,
                "chunks": info["chunks"],
                "pages": len(info["pages"])
            })

        result.sort(key=lambda x: x["filename"].lower())
        return result

    def _rebuild_index_from_metadata(self):
        self._reset_index()

        if not self.metadata:
            return

        vectors = np.array(
            [item["embedding"] for item in self.metadata],
            dtype="float32"
        )

        self.index.add(vectors)

    def delete_document(self, filename: str):
        original_count = len(self.metadata)

        self.metadata = [
            item for item in self.metadata
            if item["filename"] != filename
        ]

        removed_count = original_count - len(self.metadata)

        if removed_count == 0:
            return False, 0

        self._rebuild_index_from_metadata()
        return True, removed_count

    def clear_all(self):
        self.metadata = []
        self._reset_index()