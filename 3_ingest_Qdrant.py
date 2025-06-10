import json
import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance
from sentence_transformers import SentenceTransformer

# 1. Load chunks
with open("vector_chunks.json", "r") as f:
    chunks = json.load(f)
print(f"Loaded {len(chunks)} chunks for ingestion.")

# 2. Connect to Qdrant
client = QdrantClient(url="http://localhost:6333")

collection_name = "spdocvqa_chunks"

# 3. Delete existing collection if it exists (ignore errors)
try:
    client.delete_collection(collection_name=collection_name)
    print(f"Deleted existing collection '{collection_name}'.")
except Exception:
    pass

# 4. Create a new collection
client.create_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(size=384, distance=Distance.COSINE)
)
print(f"Created collection '{collection_name}'.")

# 5. Prepare embedder
embedder = SentenceTransformer("all-MiniLM-L6-v2")

# 6. Ingest in batches
batch_size = 500
for i in range(0, len(chunks), batch_size):
    batch = chunks[i : i + batch_size]
    texts = [c["text"] for c in batch]
    embeddings = embedder.encode(texts).tolist()

    # Assign a UUID for each point
    point_ids = [str(uuid.uuid4()) for _ in batch]

    # Keep original chunk ID in payload
    payloads = [
        {
            "chunk_id": c["id"],
            "doc_id": c["doc_id"],
            "question": c["question"],
            "answer": c["answer"],
            "source": c["source"],
        }
        for c in batch
    ]

    # Upsert points into Qdrant
    client.upsert(
        collection_name=collection_name,
        points=[{"id": pid, "vector": emb, "payload": meta} for pid, emb, meta in zip(point_ids, embeddings, payloads)]
    )

    print(f" • Ingested batch {i}–{i + len(batch)}")

print(f"✅ Finished ingesting {len(chunks)} chunks into Qdrant.")
