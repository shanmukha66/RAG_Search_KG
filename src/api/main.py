from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from neo4j import GraphDatabase
from qdrant_client import QdrantClient
from qdrant_client.http import models
import os

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Neo4j client
neo4j_uri = "bolt://neo4j:7687"
neo4j_client = GraphDatabase.driver(
    neo4j_uri,
    auth=("neo4j", "password")
)

# Initialize Qdrant client
qdrant_client = QdrantClient(host="qdrant", port=6333)

class QueryRequest(BaseModel):
    text: str
    type: str

class VectorSearchRequest(BaseModel):
    text: str
    limit: int = 10

class GraphSearchRequest(BaseModel):
    entity: str
    relationship: Optional[str] = None

@app.post("/api/query")
async def process_query(request: QueryRequest):
    try:
        # Mock response for testing
        return {
            "results": [
                {
                    "content": f"Mock response for: {request.text}",
                    "confidence": 0.95,
                    "source": "test.pdf"
                }
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/vector-search")
async def vector_search(request: VectorSearchRequest):
    try:
        # Create a collection if it doesn't exist
        collection_name = "documents"
        try:
            qdrant_client.get_collection(collection_name)
        except:
            qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(size=768, distance=models.Distance.COSINE)
            )
        
        # Mock vector for demonstration
        mock_vector = [0.1] * 768
        
        # Search in Qdrant
        search_result = qdrant_client.search(
            collection_name=collection_name,
            query_vector=mock_vector,
            limit=request.limit
        )
        
        return {
            "results": [
                {
                    "content": "Mock vector search result",
                    "score": 0.95,
                    "metadata": {}
                }
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/graph-search")
async def graph_search(request: GraphSearchRequest):
    try:
        with neo4j_client.session() as session:
            # Basic Cypher query
            query = """
            MATCH (n:Entity {name: $entity})
            OPTIONAL MATCH (n)-[r]->(m)
            RETURN n, r, m LIMIT 10
            """
            result = session.run(query, entity=request.entity)
            records = [record.data() for record in result]
            
            return {"results": records}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    status = {
        "neo4j": "unknown",
        "qdrant": "unknown"
    }
    
    # Check Neo4j
    try:
        with neo4j_client.session() as session:
            result = session.run("RETURN 1")
            list(result)
            status["neo4j"] = "healthy"
    except:
        status["neo4j"] = "unhealthy"
    
    # Check Qdrant
    try:
        collections = qdrant_client.get_collections()
        status["qdrant"] = "healthy"
    except:
        status["qdrant"] = "unhealthy"
    
    return status
