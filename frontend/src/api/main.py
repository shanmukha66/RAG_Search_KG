from datetime import timedelta
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, Security, Form, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import uuid
from pathlib import Path
import asyncio
import logging
import tempfile
import shutil
import os
from datetime import datetime

from ..config import config
from ..auth.security import (
    Token, User, authenticate_user, create_access_token,
    get_current_active_user, ACCESS_TOKEN_EXPIRE_MINUTES
)
from ..ingestion import TextIngestionPipeline, ImageIngestionPipeline, VideoIngestionPipeline
from ..storage import ChromaVectorStore, KnowledgeGraph
from ..retrieval import HybridSearch
from ..storage.vector_store import QdrantVectorStore
from ..storage.graph_store import GraphStore
from ..ingestion.pipeline import IngestionPipeline
from ..search.hybrid_search import HybridSearchEngine
from .processing import process_file
from .query import process_query
from ..evaluation.metrics import QueryType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Multimodal RAG API",
    description="API for multimodal document ingestion and retrieval",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
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

# Dependency Injection
async def get_vector_store():
    store = QdrantVectorStore()
    try:
        yield store
    finally:
        # Cleanup if needed
        pass

async def get_graph_store():
    store = GraphStore()
    try:
        yield store
    finally:
        store.close()

async def get_ingestion_pipeline():
    pipeline = IngestionPipeline()
    try:
        yield pipeline
    finally:
        # Cleanup if needed
        pass

async def get_search_engine():
    engine = HybridSearchEngine()
    try:
        yield engine
    finally:
        # Cleanup if needed
        pass

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

@app.post("/upload/")
async def upload_files(
    files: List[UploadFile] = File(...),
    pipeline: IngestionPipeline = Depends(get_ingestion_pipeline),
    vector_store: QdrantVectorStore = Depends(get_vector_store),
    graph_store: GraphStore = Depends(get_graph_store)
):
    """
    Upload and process multiple files
    """
    results = []
    
    for file in files:
        try:
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                shutil.copyfileobj(file.file, temp_file)
                temp_path = Path(temp_file.name)
            
            # Process the file
            try:
                processed_data = await pipeline.process_file(temp_path)
                
                # Store in vector database
                if 'embeddings' in processed_data:
                    await vector_store.store(
                        embeddings=[processed_data['embeddings']],
                        metadata=[processed_data['metadata']]
                    )
                
                # Store in graph database
                if 'entities' in processed_data:
                    for entity in processed_data['entities']:
                        entity_id = await graph_store.create_entity(
                            entity_type=entity['type'],
                            properties=entity['properties']
                        )
                        # Create relationships
                        if 'relationships' in entity:
                            for rel in entity['relationships']:
                                await graph_store.create_relationship(
                                    from_id=entity_id,
                                    to_id=rel['target_id'],
                                    relationship_type=rel['type'],
                                    properties=rel.get('properties', {})
                                )
                
                results.append({
                    "filename": file.filename,
                    "status": "success",
                    "metadata": processed_data.get('metadata', {})
                })
                
            finally:
                # Clean up temporary file
                temp_path.unlink()
                
        except Exception as e:
            logger.error(f"Error processing file {file.filename}: {str(e)}")
            results.append({
                "filename": file.filename,
                "status": "error",
                "error": str(e)
            })
            
    return {"results": results}

@app.post("/search/")
async def search(
    query: str,
    modalities: List[str] = ["text", "image", "audio", "video"],
    limit: int = 10,
    search_engine: HybridSearchEngine = Depends(get_search_engine)
):
    """
    Perform hybrid search across multiple modalities
    """
    try:
        results = await search_engine.search(
            query=query,
            modalities=modalities,
            limit=limit
        )
        return {"results": results}
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )

@app.get("/health/")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy"}

# Data models
class QueryRequest(BaseModel):
    text: str
    type: QueryType
    filters: Optional[dict] = None
    modalities: List[str] = ["text", "image", "audio", "video"]

class QueryResponse(BaseModel):
    answer: str
    confidence: float
    sources: List[dict]
    cross_references: List[dict]
    processing_time: float

class UploadResponse(BaseModel):
    file_id: str
    status: str
    message: str

# File upload endpoint
@app.post("/api/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    try:
        # Generate unique file ID
        file_id = str(uuid.uuid4())
        
        # Create upload directory if it doesn't exist
        upload_dir = os.path.join("data", "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save file with unique name
        file_path = os.path.join(
            upload_dir,
            f"{file_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
        )
        
        # Write file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Schedule background processing
        if background_tasks:
            background_tasks.add_task(process_file, file_path)
        
        return UploadResponse(
            file_id=file_id,
            status="success",
            message="File uploaded successfully and scheduled for processing"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error uploading file: {str(e)}"
        )

# Query endpoint
@app.post("/api/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    try:
        start_time = datetime.now()
        
        # Process query
        result = await process_query(
            query=request.text,
            query_type=request.type,
            filters=request.filters,
            modalities=request.modalities
        )
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return QueryResponse(
            answer=result["answer"],
            confidence=result["confidence"],
            sources=result["sources"],
            cross_references=result["cross_references"],
            processing_time=processing_time
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}"
        )

# Status endpoint
@app.get("/api/status")
async def status():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 