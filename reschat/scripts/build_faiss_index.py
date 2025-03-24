import json
import pickle
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

JSON_PATH = "../data/users.json"
FAISS_INDEX_PATH = "../data/faiss_index.bin"
USER_DATA_PATH = "../data/user_data.pkl"

def build_faiss_index():
    # 1. Load the data
    with open(JSON_PATH, 'r') as f:
        records = json.load(f)

    # 2. Prepare text and IDs
    texts = []
    ids = []
    for record in records:
        user_text = record["name"] + " " + " ".join(record["orders"])
        texts.append(user_text)
        ids.append(record["id"])

    # 3. Embed using SentenceTransformers
    model = SentenceTransformer('all-MiniLM-L6-v2')
    embeddings = model.encode(texts, convert_to_numpy=True)

    # 4. Create FAISS index (FlatL2)
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)

    # Add embeddings to index
    index.add(embeddings)

    # 5. Persist the index and the mapping
    faiss.write_index(index, FAISS_INDEX_PATH)

    # We also need to store how to map from index → user record.
    # We'll store the embeddings order’s record ID plus the entire user record if needed.
    user_mapping = {
        "ids": ids,      # the i-th embedding corresponds to user_records[i]
        "records": records
    }
    with open(USER_DATA_PATH, 'wb') as f:
        pickle.dump(user_mapping, f)

    print("FAISS index built and saved.")

if __name__ == "__main__":
    build_faiss_index()
