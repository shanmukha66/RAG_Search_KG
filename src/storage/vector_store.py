from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import numpy as np

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

class ChromaVectorStore(VectorStore):
    """Implementation of vector storage using Chroma."""
    
    def __init__(self, collection_name: str, persist_directory: str):
        import chromadb
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection(name=collection_name)
    
    async def store(
        self,
        vectors: np.ndarray,
        metadata: List[Dict[str, Any]],
        ids: Optional[List[str]] = None
    ) -> List[str]:
        if ids is None:
            import uuid
            ids = [str(uuid.uuid4()) for _ in range(len(vectors))]
        
        self.collection.add(
            embeddings=vectors.tolist(),
            metadatas=metadata,
            ids=ids
        )
        return ids
    
    async def search(
        self,
        query_vector: np.ndarray,
        k: int = 10,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        results = self.collection.query(
            query_embeddings=[query_vector.tolist()],
            n_results=k,
            where=filter
        )
        
        return [
            {
                "id": id,
                "metadata": metadata,
                "distance": distance
            }
            for id, metadata, distance in zip(
                results["ids"][0],
                results["metadatas"][0],
                results["distances"][0]
            )
        ]
    
    async def delete(self, ids: List[str]) -> None:
        self.collection.delete(ids=ids)
    
    async def update(
        self,
        id: str,
        vector: Optional[np.ndarray] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        if vector is not None and metadata is not None:
            self.collection.update(
                ids=[id],
                embeddings=[vector.tolist()],
                metadatas=[metadata]
            )
        elif vector is not None:
            self.collection.update(
                ids=[id],
                embeddings=[vector.tolist()]
            )
        elif metadata is not None:
            self.collection.update(
                ids=[id],
                metadatas=[metadata]
            ) 