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
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        collection_name: str = "multimodal_data"
    ):
        self.client = QdrantClient(host=host, port=port)
        self.collection_name = collection_name
        
        # Ensure collection exists
        self._init_collection()
    
    def _init_collection(self):
        """
        Initialize the vector collection if it doesn't exist
        """
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)
        
        if not exists:
            # Create collection with composite index for efficient filtering
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=1536,  # OpenAI embedding dimension
                    distance=models.Distance.COSINE
                )
            )
            
            # Create payload index for filtering
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="modality",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
    
    async def store(
        self,
        vectors: List[np.ndarray],
        metadata: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Store vectors with metadata
        """
        points = []
        for i, (vector, meta) in enumerate(zip(vectors, metadata)):
            points.append(
                models.PointStruct(
                    id=meta.get("id", i),
                    vector=vector.tolist(),
                    payload=meta
                )
            )
        
        # Batch insert points
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        
        return [str(p.id) for p in points]
    
    async def search(
        self,
        query: str,
        filter_by: Optional[Dict[str, Any]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search vectors by query embedding and optional filters
        """
        # Convert query to embedding
        query_vector = self._get_embedding(query)
        
        # Prepare search filters
        search_params = {}
        if filter_by:
            search_params["query_filter"] = models.Filter(
                must=[
                    models.FieldCondition(
                        key=k,
                        match=models.MatchValue(value=v)
                    )
                    for k, v in filter_by.items()
                ]
            )
        
        # Perform search
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=limit,
            **search_params
        )
        
        # Format results
        formatted_results = []
        for hit in results:
            result = {
                "id": str(hit.id),
                "score": hit.score,
                **hit.payload
            }
            formatted_results.append(result)
        
        return formatted_results
    
    def _get_embedding(self, text: str) -> List[float]:
        """
        Get embedding for text using OpenAI API
        """
        # TODO: Implement embedding generation
        # This is a placeholder that returns random vector
        return np.random.rand(1536).tolist()
    
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