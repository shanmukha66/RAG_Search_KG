from datetime import timedelta
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, Security, Form
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import uuid
from pathlib import Path

from ..config import config
from ..auth.security import (
    Token, User, authenticate_user, create_access_token,
    get_current_active_user, ACCESS_TOKEN_EXPIRE_MINUTES
)
from ..ingestion import TextIngestionPipeline, ImageIngestionPipeline, VideoIngestionPipeline
from ..storage import ChromaVectorStore, KnowledgeGraph
from ..retrieval import HybridSearch

app = FastAPI(
    title="Multimodal Enterprise RAG",
    description="API for multimodal content ingestion and retrieval",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components with configuration
vector_store = ChromaVectorStore(
    collection_name="content",
    persist_directory=config["vector_store"]["dir"]
)

knowledge_graph = KnowledgeGraph(
    uri=config["neo4j"]["uri"],
    username=config["neo4j"]["user"],
    password=config["neo4j"]["password"]
)

hybrid_search = HybridSearch(
    vector_store=vector_store,
    knowledge_graph=knowledge_graph
)

# Pipeline registry with configuration
PIPELINES = {
    "text": TextIngestionPipeline({"chunk_size": 1000}),
    "image": ImageIngestionPipeline({
        "ocr_lang": config["ocr"]["lang"],
        "min_confidence": 80
    }),
    "video": VideoIngestionPipeline({
        "frame_sample_rate": 1,
        "audio_segment_length": 10,
        "temp_dir": config["storage"]["temp_dir"]
    })
}

class SearchQuery(BaseModel):
    query: str
    content_type: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    limit: int = 10
    expand_results: bool = False

class SearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    total: int
    query_time_ms: float

@app.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """Get access token."""
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "scopes": form_data.scopes},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/ingest/file")
async def ingest_file(
    file: UploadFile = File(...),
    content_type: str = Form(...),
    metadata: Optional[Dict[str, Any]] = Form(None),
    current_user: User = Security(get_current_active_user, scopes=["write"])
):
    """Ingest a file into the system."""
    try:
        if content_type not in PIPELINES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported content type: {content_type}"
            )
        
        pipeline = PIPELINES[content_type]
        content_path = Path(file.filename)
        
        # Validate file
        if not await pipeline.validate(content_path):
            raise HTTPException(
                status_code=400,
                detail="Invalid file format"
            )
        
        # Process content
        metadata = await pipeline.extract_metadata(content_path)
        preprocessed = await pipeline.preprocess(content_path)
        content = await pipeline.extract_content(preprocessed)
        enriched = await pipeline.enrich(content)
        
        # Generate unique ID
        content_id = str(uuid.uuid4())
        
        # Store in vector store
        await vector_store.store(
            vectors=[enriched["embedding"]],
            metadata=[{
                "id": content_id,
                "content_type": content_type,
                **metadata.__dict__,
                **enriched
            }]
        )
        
        # Store in knowledge graph
        await knowledge_graph.add_content_node(
            content_id=content_id,
            content_type=content_type,
            metadata=metadata.__dict__
        )
        
        # Add relationships based on extracted entities
        if "entities" in enriched:
            for entity in enriched["entities"]:
                entity_id = await knowledge_graph.add_entity(
                    entity_type=entity["type"],
                    name=entity["name"],
                    properties=entity["properties"]
                )
                await knowledge_graph.add_relationship(
                    from_id=content_id,
                    to_id=entity_id,
                    relationship_type="CONTAINS",
                    properties={"confidence": entity["confidence"]}
                )
        
        return {
            "content_id": content_id,
            "status": "success",
            "metadata": metadata.__dict__
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await pipeline.cleanup()

@app.post("/search", response_model=SearchResponse)
async def search(
    query: SearchQuery,
    current_user: User = Security(get_current_active_user, scopes=["read"])
):
    """Search across ingested content."""
    try:
        results = await hybrid_search.search(
            query=query.query,
            content_type=query.content_type,
            k=query.limit
        )
        
        if query.expand_results:
            results = await hybrid_search.expand_results(results)
        
        return SearchResponse(
            results=results,
            total=len(results),
            query_time_ms=0.0  # Should be measured
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/content/{content_id}")
async def get_content(
    content_id: str,
    current_user: User = Security(get_current_active_user, scopes=["read"])
):
    """Get content by ID."""
    try:
        # Get from knowledge graph
        content = await knowledge_graph.search_content(
            properties={"id": content_id},
            limit=1
        )
        
        if not content:
            raise HTTPException(status_code=404, detail="Content not found")
        
        # Get related entities
        related = await knowledge_graph.get_related_entities(content_id)
        
        return {
            "content": content[0],
            "related_entities": related
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Check if the API is running."""
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 