from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import json
from sentence_transformers import SentenceTransformer
import os
from typing import List, Dict
from tqdm import tqdm
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
import time

# Global model instance for multiprocessing
model = None

def init_worker():
    """Initialize the model in each worker process"""
    global model
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

def encode_texts(texts: List[str]) -> List[List[float]]:
    """Encode a batch of texts"""
    global model
    return [model.encode(text).tolist() for text in texts]

def process_chunk(chunk: Dict) -> Dict:
    """Process a single chunk of data"""
    global model
    if not model:
        model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    
    # Skip invalid chunks
    if not isinstance(chunk, dict) or not chunk:
        return None
    
    # Extract and validate text
    text = str(chunk.get('text', ''))
    if not text:
        return None
    
    try:
        # Generate embedding
        vector = model.encode(text).tolist()
        
        # Prepare payload with proper type checking
        return {
            'vector': vector,
            'payload': {
                'doc_id': str(chunk.get('doc_id', '')),
                'text': text,
                'question': str(chunk.get('question', '')),
                'answer': str(chunk.get('answer', [''])[0]) if isinstance(chunk.get('answer'), list) else str(chunk.get('answer', '')),
                'source': str(chunk.get('source', ''))
            }
        }
    except Exception as e:
        print(f"\nError processing chunk: {e}")
        return None

def init_qdrant():
    """Initialize Qdrant collection"""
    client = QdrantClient(host="localhost", port=6333)
    
    try:
        client.create_collection(
            collection_name="documents",
            vectors_config=VectorParams(size=384, distance=Distance.COSINE)
        )
        print("✅ Created Qdrant collection 'documents'")
    except Exception as e:
        print(f"Collection might already exist: {e}")
    
    return client

def ingest_vectors():
    """Ingest vectors using parallel processing"""
    if not os.path.exists("vector_chunks.json"):
        print("❌ vector_chunks.json not found!")
        return
    
    print("Loading vector chunks...")
    with open("vector_chunks.json", "r") as f:
        vector_chunks = json.load(f)
    
    # Initialize Qdrant client
    client = init_qdrant()
    
    # Calculate optimal batch size and number of workers
    num_cpus = multiprocessing.cpu_count()
    BATCH_SIZE = 100
    num_batches = (len(vector_chunks) + BATCH_SIZE - 1) // BATCH_SIZE
    
    print(f"Using {num_cpus} CPU cores for parallel processing")
    print(f"Processing {len(vector_chunks)} documents in {num_batches} batches")
    
    # Process chunks in parallel
    with ProcessPoolExecutor(max_workers=num_cpus, initializer=init_worker) as executor:
        with tqdm(total=len(vector_chunks), desc="Processing vectors") as pbar:
            for i in range(0, len(vector_chunks), BATCH_SIZE):
                batch = vector_chunks[i:i + BATCH_SIZE]
                
                # Process batch in parallel
                processed_chunks = list(executor.map(process_chunk, batch))
                
                # Filter out None results and prepare points
                points = []
                for idx, chunk in enumerate(processed_chunks):
                    if chunk is not None:
                        point = PointStruct(
                            id=i + idx,
                            vector=chunk['vector'],
                            payload=chunk['payload']
                        )
                        points.append(point)
                
                # Upload batch if not empty
                if points:
                    try:
                        client.upsert(
                            collection_name="documents",
                            points=points
                        )
                    except Exception as e:
                        print(f"\nError uploading batch: {e}")
                
                pbar.update(len(batch))
                
                # Small delay to prevent overwhelming Qdrant
                time.sleep(0.1)
    
    print("✅ Vector ingestion complete!")

if __name__ == "__main__":
    print("Starting vector ingestion process...")
    ingest_vectors() 