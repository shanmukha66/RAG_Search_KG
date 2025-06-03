from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http import models

class VectorStore(ABC):
    """Abstract base class for vector storage implementations."""
    
    @abstractmethod
    async def store(
        self,
        vectors: np.ndarray,
        metadata: List[Dict[str, Any]],
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """Store vectors with their associated metadata.
        
        Args:
            vectors: Array of vectors to store
            metadata: List of metadata dictionaries for each vector
            ids: Optional list of IDs for the vectors
            
        Returns:
            List of IDs for the stored vectors
        """
        pass
    
    @abstractmethod
    async def search(
        self,
        query_vector: np.ndarray,
        k: int = 10,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors.
        
        Args:
            query_vector: Vector to search for
            k: Number of results to return
            filter: Optional metadata filter
            
        Returns:
            List of dictionaries containing matched vectors and their metadata
        """
        pass
    
    @abstractmethod
    async def delete(self, ids: List[str]) -> None:
        """Delete vectors by their IDs."""
        pass
    
    @abstractmethod
    async def update(
        self,
        id: str,
        vector: Optional[np.ndarray] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update a vector or its metadata."""
        pass

class QdrantVectorStore(VectorStore):
    """Implementation of vector storage using Qdrant."""
    
    def __init__(self, collection_name: str = "multimodal_rag"):
        self.client = QdrantClient("localhost", port=6333)
        self.collection_name = collection_name
        self._ensure_collection()
    
    def _ensure_collection(self):
        """Ensure collection exists with proper schema"""
        try:
            self.client.get_collection(self.collection_name)
        except:
            # Create collection with necessary vector size and metadata schema
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=1536,  # OpenAI embedding size
                    distance=models.Distance.COSINE
                )
            )
    
    async def store(
        self,
        embeddings: List[np.ndarray],
        metadata: List[Dict[str, Any]],
        ids: List[str] = None
    ):
        """
        Store vectors and metadata in Qdrant
        
        Args:
            embeddings: List of embedding vectors
            metadata: List of metadata dicts for each vector
            ids: Optional list of IDs for the vectors
        """
        if not ids:
            ids = [str(i) for i in range(len(embeddings))]
            
        points = [
            models.PointStruct(
                id=id_,
                vector=embedding.tolist(),
                payload=meta
            )
            for id_, embedding, meta in zip(ids, embeddings, metadata)
        ]
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
    
    async def search(
        self,
        query_vector: np.ndarray,
        filter_conditions: Dict[str, Any] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors with optional filtering
        
        Args:
            query_vector: Query embedding
            filter_conditions: Optional metadata filters
            limit: Maximum number of results
        """
        search_result = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector.tolist(),
            query_filter=models.Filter(
                must=filter_conditions
            ) if filter_conditions else None,
            limit=limit
        )
        
        return [
            {
                'id': point.id,
                'score': point.score,
                'metadata': point.payload
            }
            for point in search_result
        ]
    
    async def delete(self, ids: List[str]) -> None:
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.Filter(
                must=[
                    models.FieldCondition(
                        key="id",
                        range=models.ValueRange(
                            values=[id_ for id_ in ids]
                        )
                    )
                ]
            )
        )
    
    async def update(
        self,
        id: str,
        vector: Optional[np.ndarray] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        if vector is not None and metadata is not None:
            self.client.update_points(
                collection_name=self.collection_name,
                points=models.UpdatePoints(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="id",
                                value=models.Value(value=id)
                            )
                        ]
                    ),
                    update_operations=[
                        models.UpdateOperation(
                            key="vector",
                            operation=models.UpdateOperationType.Set,
                            value=vector.tolist()
                        ),
                        models.UpdateOperation(
                            key="metadata",
                            operation=models.UpdateOperationType.Set,
                            value=metadata
                        )
                    ]
                )
            )
        elif vector is not None:
            self.client.update_points(
                collection_name=self.collection_name,
                points=models.UpdatePoints(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="id",
                                value=models.Value(value=id)
                            )
                        ]
                    ),
                    update_operations=[
                        models.UpdateOperation(
                            key="vector",
                            operation=models.UpdateOperationType.Set,
                            value=vector.tolist()
                        )
                    ]
                )
            )
        elif metadata is not None:
            self.client.update_points(
                collection_name=self.collection_name,
                points=models.UpdatePoints(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="id",
                                value=models.Value(value=id)
                            )
                        ]
                    ),
                    update_operations=[
                        models.UpdateOperation(
                            key="metadata",
                            operation=models.UpdateOperationType.Set,
                            value=metadata
                        )
                    ]
                )
            ) 