import json
import pickle
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

FAISS_INDEX_PATH = "data/faiss_index.bin"
USER_DATA_PATH = "data/user_data.pkl"

class FaissRAG:
    def __init__(self):
        # Load index
        self.index = faiss.read_index(FAISS_INDEX_PATH)
        # Load user data
        with open(USER_DATA_PATH, 'rb') as f:
            data = pickle.load(f)
        self.ids = data["ids"]
        self.records = data["records"]

        # We’ll use same embedder as we used to build index:
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

    def find_similar_users(self, query_text, top_k=3):
        """Embed query_text and find top_k similar user records."""
        query_vec = self.model.encode([query_text], convert_to_numpy=True)
        # faiss expects shape [n, d]
        query_vec = np.array(query_vec, dtype=np.float32).reshape(1, -1)

        distances, indices = self.index.search(query_vec, top_k)

        # We'll return the actual user JSON plus distances
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            user_id = self.ids[idx]
            user_record = next((rec for rec in self.records if rec["id"] == user_id), None)
            results.append((dist, user_record))
        return results
