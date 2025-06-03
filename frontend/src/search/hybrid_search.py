from typing import List, Dict, Any
import numpy as np
from sentence_transformers import SentenceTransformer
from ..storage.vector_store import QdrantVectorStore
from ..storage.graph_store import GraphStore

class HybridSearchEngine:
    def __init__(self):
        self.vector_store = QdrantVectorStore()
        self.graph_store = GraphStore()
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        
    async def search(
        self,
        query: str,
        modalities: List[str] = ["text", "image", "audio", "video"],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining vector similarity and graph traversal
        
        Args:
            query: Search query
            modalities: List of modalities to search in
            limit: Maximum number of results to return
        """
        # Generate query embedding
        query_embedding = self.encoder.encode(query, convert_to_tensor=True).numpy()
        
        # Vector search
        vector_results = await self.vector_store.search(
            query_vector=query_embedding,
            filter_conditions={"content_type": {"$in": modalities}},
            limit=limit
        )
        
        # Graph search for entities mentioned in query
        # TODO: Implement entity extraction from query
        graph_results = []
        for modality in modalities:
            entities = await self.graph_store.search_entities(
                entity_type=modality,
                limit=limit
            )
            graph_results.extend(entities)
        
        # Combine and rank results
        combined_results = self._merge_and_rank_results(
            vector_results=vector_results,
            graph_results=graph_results,
            limit=limit
        )
        
        return combined_results
    
    def _merge_and_rank_results(
        self,
        vector_results: List[Dict[str, Any]],
        graph_results: List[Dict[str, Any]],
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Merge and rank results from vector and graph search
        """
        # Convert graph results to common format
        formatted_graph_results = [
            {
                "id": str(result.get("id", "unknown")),
                "score": 0.5,  # Default score for graph results
                "metadata": result
            }
            for result in graph_results
        ]
        
        # Combine results
        all_results = vector_results + formatted_graph_results
        
        # Sort by score
        ranked_results = sorted(
            all_results,
            key=lambda x: x["score"],
            reverse=True
        )
        
        # Return top results
        return ranked_results[:limit]
    
    async def rewrite_query(self, query: str) -> str:
        """
        Rewrite the query to improve search results
        TODO: Implement query rewriting using LLM
        """
        return query 