from typing import List, Dict, Optional, Any, Tuple
from abc import ABC, abstractmethod
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time
from dataclasses import dataclass
from enum import Enum

class SearchStrategy(Enum):
    VECTOR_FIRST = "vector_first"
    GRAPH_FIRST = "graph_first"
    PARALLEL = "parallel"
    HYBRID = "hybrid"
    ENTITY_FOCUSED = "entity_focused"

@dataclass
class SearchResult:
    content: str
    score: float
    source: str
    metadata: Dict[str, Any]
    strategy_used: str

class BaseSearchAgent(ABC):
    """Abstract base class for search agents"""
    
    def __init__(self, name: str, priority: int = 1):
        self.name = name
        self.priority = priority
        self.execution_time = 0.0
        self.success_rate = 1.0
        
    @abstractmethod
    async def search(self, query: str, context: Dict = None) -> List[SearchResult]:
        """Execute the search strategy"""
        pass
    
    def update_performance(self, execution_time: float, success: bool):
        """Update agent performance metrics"""
        self.execution_time = execution_time
        if success:
            self.success_rate = min(1.0, self.success_rate + 0.01)
        else:
            self.success_rate = max(0.0, self.success_rate - 0.05)

class VectorSearchAgent(BaseSearchAgent):
    """Agent specialized in vector/semantic search"""
    
    def __init__(self, qdrant_client, sentence_model):
        super().__init__("VectorSearchAgent", priority=2)
        self.qdrant_client = qdrant_client
        self.sentence_model = sentence_model
        
    async def search(self, query: str, context: Dict = None) -> List[SearchResult]:
        """Perform vector search with enhanced strategies"""
        start_time = time.time()
        results = []
        
        try:
            # Generate query embedding
            query_vector = self.sentence_model.encode(query).tolist()
            
            # Perform main search
            search_result = self.qdrant_client.search(
                collection_name="documents",
                query_vector=query_vector,
                limit=10,  # Get more results for better filtering
                with_payload=True,
                with_vectors=False
            )
            
            # Convert to SearchResult objects
            for hit in search_result:
                if hit.payload:
                    results.append(SearchResult(
                        content=hit.payload.get('text', ''),
                        score=float(hit.score),
                        source="vector_search",
                        metadata=hit.payload,
                        strategy_used="vector_semantic"
                    ))
            
            # If we have context, try entity-focused search
            if context and context.get('entities'):
                entity_results = await self._entity_focused_search(context['entities'])
                results.extend(entity_results)
            
            execution_time = time.time() - start_time
            self.update_performance(execution_time, True)
            
        except Exception as e:
            print(f"Error in vector search: {e}")
            execution_time = time.time() - start_time
            self.update_performance(execution_time, False)
        
        return results[:5]  # Return top 5 results
    
    async def _entity_focused_search(self, entities: Dict[str, List[str]]) -> List[SearchResult]:
        """Search focused on specific entities"""
        results = []
        
        for entity_type, entity_list in entities.items():
            for entity in entity_list:
                if entity:  # Skip empty entities
                    try:
                        entity_vector = self.sentence_model.encode(entity).tolist()
                        search_result = self.qdrant_client.search(
                            collection_name="documents",
                            query_vector=entity_vector,
                            limit=3,
                            with_payload=True,
                            with_vectors=False
                        )
                        
                        for hit in search_result:
                            if hit.payload:
                                results.append(SearchResult(
                                    content=hit.payload.get('text', ''),
                                    score=float(hit.score) * 0.8,  # Slightly lower weight
                                    source="vector_search",
                                    metadata={**hit.payload, 'entity_type': entity_type, 'entity': entity},
                                    strategy_used="entity_focused"
                                ))
                    except Exception as e:
                        print(f"Error in entity search for {entity}: {e}")
                        continue
        
        return results

class GraphSearchAgent(BaseSearchAgent):
    """Agent specialized in graph-based search"""
    
    def __init__(self, neo4j_driver):
        super().__init__("GraphSearchAgent", priority=2)
        self.neo4j_driver = neo4j_driver
        
    async def search(self, query: str, context: Dict = None) -> List[SearchResult]:
        """Perform graph search with relationship traversal"""
        start_time = time.time()
        results = []
        
        try:
            with self.neo4j_driver.session() as session:
                # Main graph search
                main_results = await self._main_graph_search(session, query)
                results.extend(main_results)
                
                # Relationship-based expansion
                if main_results and context:
                    expanded_results = await self._relationship_expansion(session, main_results, query)
                    results.extend(expanded_results)
            
            execution_time = time.time() - start_time
            self.update_performance(execution_time, True)
            
        except Exception as e:
            print(f"Error in graph search: {e}")
            execution_time = time.time() - start_time
            self.update_performance(execution_time, False)
        
        return results[:5]
    
    async def _main_graph_search(self, session, query: str) -> List[SearchResult]:
        """Perform main graph search"""
        cypher_query = """
        MATCH (d:Document)-[r:HAS_QUESTION]->(q:Question)
        WHERE toLower(q.text) CONTAINS toLower($query_text)
           OR toLower(d.text) CONTAINS toLower($query_text)
        WITH d, q, toLower(q.text) CONTAINS toLower($query_text) as exact_match,
             size(split(toLower(q.text), toLower($query_text))) - 1 as relevance_score
        ORDER BY exact_match DESC, relevance_score DESC
        LIMIT 5
        RETURN DISTINCT {
            doc_id: d.id,
            doc_text: d.text,
            question: q.text,
            answer: q.answer,
            image_path: d.image_path,
            relevance: relevance_score
        } as result
        """
        
        result = session.run(cypher_query, query_text=query)
        search_results = []
        
        for record in result:
            result_dict = record.get('result', {})
            search_results.append(SearchResult(
                content=result_dict.get('doc_text', ''),
                score=float(result_dict.get('relevance', 0)),
                source="graph_search",
                metadata=result_dict,
                strategy_used="graph_traversal"
            ))
        
        return search_results
    
    async def _relationship_expansion(self, session, initial_results: List[SearchResult], query: str) -> List[SearchResult]:
        """Expand search using graph relationships"""
        expanded_results = []
        
        for result in initial_results[:2]:  # Expand from top 2 results
            doc_id = result.metadata.get('doc_id')
            if doc_id:
                try:
                    expansion_query = """
                    MATCH (d:Document {id: $doc_id})-[r]-(related)
                    WHERE toLower(related.text) CONTAINS toLower($query_text)
                    RETURN related.text as text, type(r) as relationship_type
                    LIMIT 3
                    """
                    
                    expansion_result = session.run(expansion_query, doc_id=doc_id, query_text=query)
                    
                    for record in expansion_result:
                        expanded_results.append(SearchResult(
                            content=record.get('text', ''),
                            score=result.score * 0.7,  # Lower weight for expanded results
                            source="graph_search",
                            metadata={
                                'original_doc_id': doc_id,
                                'relationship_type': record.get('relationship_type', '')
                            },
                            strategy_used="relationship_expansion"
                        ))
                except Exception as e:
                    print(f"Error in relationship expansion: {e}")
                    continue
        
        return expanded_results

class HybridSearchAgent(BaseSearchAgent):
    """Agent that combines multiple search strategies"""
    
    def __init__(self, vector_agent: VectorSearchAgent, graph_agent: GraphSearchAgent):
        super().__init__("HybridSearchAgent", priority=3)
        self.vector_agent = vector_agent
        self.graph_agent = graph_agent
        
    async def search(self, query: str, context: Dict = None) -> List[SearchResult]:
        """Perform hybrid search combining vector and graph results"""
        start_time = time.time()
        
        try:
            # Run both searches in parallel
            with ThreadPoolExecutor(max_workers=2) as executor:
                vector_future = executor.submit(asyncio.run, self.vector_agent.search(query, context))
                graph_future = executor.submit(asyncio.run, self.graph_agent.search(query, context))
                
                vector_results = vector_future.result()
                graph_results = graph_future.result()
            
            # Combine and deduplicate results
            combined_results = self._combine_results(vector_results, graph_results)
            
            execution_time = time.time() - start_time
            self.update_performance(execution_time, True)
            
            return combined_results[:5]
            
        except Exception as e:
            print(f"Error in hybrid search: {e}")
            execution_time = time.time() - start_time
            self.update_performance(execution_time, False)
            return []
    
    def _combine_results(self, vector_results: List[SearchResult], graph_results: List[SearchResult]) -> List[SearchResult]:
        """Combine and rank results from different sources"""
        all_results = []
        
        # Add vector results with boosted scores
        for result in vector_results:
            result.score *= 1.1  # Slight boost for vector results
            all_results.append(result)
        
        # Add graph results, avoiding duplicates
        for graph_result in graph_results:
            # Simple deduplication based on content similarity
            is_duplicate = False
            for existing in all_results:
                if self._is_similar_content(existing.content, graph_result.content):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                all_results.append(graph_result)
        
        # Sort by score
        all_results.sort(key=lambda x: x.score, reverse=True)
        return all_results
    
    def _is_similar_content(self, content1: str, content2: str, threshold: float = 0.8) -> bool:
        """Check if two content strings are similar"""
        if not content1 or not content2:
            return False
        
        # Simple similarity check based on word overlap
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())
        
        if not words1 or not words2:
            return False
        
        overlap = len(words1.intersection(words2))
        total_unique = len(words1.union(words2))
        
        return (overlap / total_unique) > threshold

class AgentOrchestrator:
    """Orchestrates multiple search agents based on query characteristics"""
    
    def __init__(self, vector_agent: VectorSearchAgent, graph_agent: GraphSearchAgent, hybrid_agent: HybridSearchAgent):
        self.agents = {
            'vector': vector_agent,
            'graph': graph_agent,
            'hybrid': hybrid_agent
        }
        
        self.strategy_rules = {
            'comparison': ['vector', 'graph'],  # Use both for comparison queries
            'definition': ['vector'],  # Vector search is better for definitions
            'factual': ['graph', 'vector'],  # Graph first for factual queries
            'analytical': ['hybrid'],  # Hybrid for analytical queries
            'general': ['hybrid'],  # Default to hybrid
            'temporal': ['graph']  # Graph for time-based queries
        }
    
    def select_strategy(self, query: str, intent: str, entities: Dict) -> List[str]:
        """Select appropriate search strategy based on query characteristics"""
        strategies = self.strategy_rules.get(intent, ['hybrid'])
        
        # Adjust based on entities
        if entities.get('ORG') or entities.get('PERSON'):
            if 'graph' not in strategies:
                strategies.append('graph')
        
        # Adjust based on query length
        if len(query.split()) > 10:
            if 'vector' not in strategies:
                strategies.append('vector')
        
        return strategies
    
    async def orchestrated_search(self, query: str, intent: str = 'general', entities: Dict = None) -> List[SearchResult]:
        """Orchestrate search across multiple agents"""
        strategies = self.select_strategy(query, intent, entities or {})
        all_results = []
        
        context = {'entities': entities} if entities else None
        
        # Execute selected strategies
        for strategy in strategies:
            if strategy in self.agents:
                try:
                    results = await self.agents[strategy].search(query, context)
                    all_results.extend(results)
                except Exception as e:
                    print(f"Error in {strategy} search: {e}")
                    continue
        
        # Deduplicate and rank final results
        final_results = self._deduplicate_results(all_results)
        return final_results[:5]
    
    def _deduplicate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """Remove duplicate results and rank by combined score"""
        seen_content = set()
        unique_results = []
        
        # Sort by score first
        results.sort(key=lambda x: x.score, reverse=True)
        
        for result in results:
            # Simple deduplication
            content_hash = hash(result.content[:100])  # Use first 100 chars as hash
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                unique_results.append(result)
        
        return unique_results
    
    def get_agent_performance(self) -> Dict[str, Dict[str, float]]:
        """Get performance metrics for all agents"""
        performance = {}
        for name, agent in self.agents.items():
            performance[name] = {
                'execution_time': agent.execution_time,
                'success_rate': agent.success_rate,
                'priority': agent.priority
            }
        return performance 