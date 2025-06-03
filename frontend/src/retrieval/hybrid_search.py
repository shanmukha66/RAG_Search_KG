from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer

from ..storage.vector_store import VectorStore
from ..storage.knowledge_graph import KnowledgeGraph

class HybridSearch:
    """Hybrid search combining vector similarity and graph traversal."""
    
    def __init__(
        self,
        vector_store: VectorStore,
        knowledge_graph: KnowledgeGraph,
        model_name: str = "all-MiniLM-L6-v2",
        vector_weight: float = 0.7,
        graph_weight: float = 0.3
    ):
        self.vector_store = vector_store
        self.knowledge_graph = knowledge_graph
        self.encoder = SentenceTransformer(model_name)
        self.vector_weight = vector_weight
        self.graph_weight = graph_weight
    
    async def search(
        self,
        query: str,
        content_type: Optional[str] = None,
        k: int = 10,
        max_graph_depth: int = 2
    ) -> List[Dict[str, Any]]:
        """Perform hybrid search using both vector similarity and graph relationships."""
        # Get query embedding
        query_embedding = self.encoder.encode(query)
        
        # Perform vector search
        vector_results = await self.vector_store.search(
            query_vector=query_embedding,
            k=k * 2,  # Get more results to allow for reranking
            filter={"content_type": content_type} if content_type else None
        )
        
        # Get graph-enhanced results
        enhanced_results = []
        seen_ids = set()
        
        for result in vector_results:
            if result["id"] in seen_ids:
                continue
                
            # Get graph context
            graph_context = await self._get_graph_context(
                result["id"],
                max_depth=max_graph_depth
            )
            
            # Combine scores
            vector_score = 1 - result["distance"]  # Convert distance to similarity
            graph_score = self._calculate_graph_score(graph_context)
            
            combined_score = (
                self.vector_weight * vector_score +
                self.graph_weight * graph_score
            )
            
            enhanced_results.append({
                "content": result,
                "graph_context": graph_context,
                "scores": {
                    "vector": float(vector_score),
                    "graph": float(graph_score),
                    "combined": float(combined_score)
                }
            })
            
            seen_ids.add(result["id"])
        
        # Sort by combined score
        enhanced_results.sort(key=lambda x: x["scores"]["combined"], reverse=True)
        
        return enhanced_results[:k]
    
    async def _get_graph_context(
        self,
        content_id: str,
        max_depth: int = 2
    ) -> Dict[str, Any]:
        """Get the graph context for a content node."""
        # Get directly related entities
        related_entities = await self.knowledge_graph.get_related_entities(content_id)
        
        # Get paths to other content through entities
        paths = []
        for entity in related_entities:
            entity_paths = await self.knowledge_graph.find_paths(
                content_id,
                entity["entity"]["id"],
                max_depth=max_depth
            )
            paths.extend(entity_paths)
        
        return {
            "related_entities": related_entities,
            "paths": paths
        }
    
    def _calculate_graph_score(self, graph_context: Dict[str, Any]) -> float:
        """Calculate a score based on graph relationships."""
        # This is a simple scoring method that could be enhanced
        score = 0.0
        
        # Score based on number of direct relationships
        n_relations = len(graph_context["related_entities"])
        if n_relations > 0:
            score += 0.5 * min(n_relations / 10, 1.0)  # Cap at 10 relations
        
        # Score based on path diversity
        n_paths = len(graph_context["paths"])
        if n_paths > 0:
            score += 0.5 * min(n_paths / 5, 1.0)  # Cap at 5 paths
        
        return score
    
    async def expand_results(
        self,
        results: List[Dict[str, Any]],
        max_related: int = 5
    ) -> List[Dict[str, Any]]:
        """Expand search results with related content through graph relationships."""
        expanded_results = []
        seen_ids = set()
        
        for result in results:
            if result["content"]["id"] in seen_ids:
                continue
            
            # Get related content through graph relationships
            related_content = []
            for entity in result["graph_context"]["related_entities"]:
                entity_content = await self.knowledge_graph.search_content(
                    properties={"related_to": entity["entity"]["id"]},
                    limit=max_related
                )
                related_content.extend(entity_content)
            
            # Add to expanded results
            expanded_results.append({
                **result,
                "related_content": related_content[:max_related]
            })
            
            seen_ids.add(result["content"]["id"])
        
        return expanded_results 