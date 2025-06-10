from typing import Dict, List, Optional, Any
import asyncio
import time
from dataclasses import asdict
from .query_rewriter import QueryRewriter
from .agent_retrieval import (
    VectorSearchAgent, GraphSearchAgent, HybridSearchAgent, 
    AgentOrchestrator, SearchResult
)
from .topic_ranker import TopicBasedRanker, RankedResult
from .query_optimizer import QueryOptimizer

class AdvancedSearchController:
    """
    Main controller for advanced search features including:
    - Query rewriting and optimization
    - Agent-based retrieval
    - Topic-based ranking
    - Real-time query improvement
    """
    
    def __init__(self, qdrant_client, neo4j_driver, sentence_model):
        """Initialize advanced search controller"""
        # Initialize components
        self.query_rewriter = QueryRewriter()
        self.query_optimizer = QueryOptimizer()
        self.topic_ranker = TopicBasedRanker()
        
        # Initialize search agents
        self.vector_agent = VectorSearchAgent(qdrant_client, sentence_model)
        self.graph_agent = GraphSearchAgent(neo4j_driver)
        self.hybrid_agent = HybridSearchAgent(self.vector_agent, self.graph_agent)
        
        # Initialize orchestrator
        self.orchestrator = AgentOrchestrator(
            self.vector_agent, 
            self.graph_agent, 
            self.hybrid_agent
        )
        
        # Track search sessions
        self.active_sessions = {}
        
        print("✅ Advanced Search Controller initialized")
    
    async def advanced_search(self, query: str, session_id: Optional[str] = None,
                            user_preferences: Dict = None) -> Dict[str, Any]:
        """
        Perform advanced search with all enhancements
        
        Args:
            query: Original search query
            session_id: Optional session ID for tracking
            user_preferences: User preferences for search customization
            
        Returns:
            Enhanced search results with metadata
        """
        start_time = time.time()
        
        try:
            # Step 1: Query Analysis and Rewriting
            rewrite_result = self.query_rewriter.rewrite_query(query)
            
            # Step 2: Query Optimization
            optimization_result = self.query_optimizer.optimize_query(
                rewrite_result['rewritten_query'],
                context={
                    'entities': rewrite_result['entities'],
                    'intent': rewrite_result['intent']
                }
            )
            
            # Step 3: Agent-based Retrieval
            final_query = optimization_result['optimized_query']
            search_results = await self.orchestrator.orchestrated_search(
                final_query,
                intent=rewrite_result['intent'],
                entities=rewrite_result['entities']
            )
            
            # Step 4: Topic-based Ranking (if topic models are fitted)
            if self.topic_ranker.topic_models_fitted and search_results:
                # Convert SearchResult objects to dictionaries for ranking
                result_dicts = []
                for sr in search_results:
                    result_dict = {
                        'text': sr.content,
                        'content': sr.content,
                        'score': sr.score,
                        **sr.metadata
                    }
                    result_dicts.append(result_dict)
                
                ranked_results = self.topic_ranker.rank_results(query, result_dicts)
                
                # Convert back to SearchResult format with enhanced scores
                enhanced_results = []
                for rr in ranked_results:
                    enhanced_results.append(SearchResult(
                        content=rr.content,
                        score=rr.final_score,
                        source="advanced_search",
                        metadata=rr.metadata,
                        strategy_used="topic_enhanced"
                    ))
                
                final_results = enhanced_results
            else:
                final_results = search_results
            
            # Step 5: Prepare response
            end_time = time.time()
            
            response = {
                'query_processing': {
                    'original_query': query,
                    'rewritten_query': rewrite_result['rewritten_query'],
                    'optimized_query': optimization_result['optimized_query'],
                    'entities': rewrite_result['entities'],
                    'intent': rewrite_result['intent'],
                    'optimizations_applied': optimization_result['optimizations_applied']
                },
                'search_results': [
                    {
                        'content': sr.content,
                        'score': sr.score,
                        'source': sr.source,
                        'strategy': sr.strategy_used,
                        'metadata': sr.metadata
                    }
                    for sr in final_results[:5]  # Top 5 results
                ],
                'metadata': {
                    'total_results': len(final_results),
                    'processing_time': end_time - start_time,
                    'rewrite_confidence': rewrite_result['confidence'],
                    'optimization_confidence': optimization_result['confidence'],
                    'expected_improvement': optimization_result['expected_improvement'],
                    'agents_used': self._get_agents_used(final_results),
                    'topic_enhanced': self.topic_ranker.topic_models_fitted
                },
                'query_suggestions': rewrite_result.get('query_variations', [])
            }
            
            # Track session if provided
            if session_id:
                self._track_session(session_id, query, response)
            
            return response
            
        except Exception as e:
            print(f"Error in advanced search: {e}")
            return {
                'error': str(e),
                'query_processing': {'original_query': query},
                'search_results': [],
                'metadata': {'processing_time': time.time() - start_time}
            }
    
    def _get_agents_used(self, results: List[SearchResult]) -> List[str]:
        """Extract which agents were used in the search"""
        agents = set()
        for result in results:
            if 'vector' in result.source:
                agents.add('vector')
            if 'graph' in result.source:
                agents.add('graph')
            if result.strategy_used == 'hybrid':
                agents.add('hybrid')
        return list(agents)
    
    def _track_session(self, session_id: str, query: str, response: Dict):
        """Track search session for learning"""
        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = {
                'queries': [],
                'responses': [],
                'start_time': time.time()
            }
        
        session = self.active_sessions[session_id]
        session['queries'].append(query)
        session['responses'].append(response)
    
    def record_user_feedback(self, session_id: str, query: str, 
                           clicked_results: List[int], satisfaction: Optional[int] = None):
        """Record user feedback for learning and improvement"""
        try:
            # Record feedback in query optimizer
            self.query_optimizer.learn_from_feedback(
                query, 
                success=len(clicked_results) > 0,
                clicked_results=clicked_results
            )
            
            # Update session tracking
            if session_id in self.active_sessions:
                session = self.active_sessions[session_id]
                session['feedback'] = {
                    'clicked_results': clicked_results,
                    'satisfaction': satisfaction,
                    'query': query
                }
            
            print(f"✅ Recorded feedback for query: {query}")
            
        except Exception as e:
            print(f"Error recording feedback: {e}")
    
    def initialize_topic_models(self, documents: List[str]):
        """Initialize topic models with document corpus"""
        try:
            print("🔄 Initializing topic models...")
            self.topic_ranker.fit_topic_models(documents)
            print("✅ Topic models initialized")
        except Exception as e:
            print(f"Error initializing topic models: {e}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        return {
            'query_optimizer': self.query_optimizer.get_optimization_stats(),
            'agent_performance': self.orchestrator.get_agent_performance(),
            'topic_summary': self.topic_ranker.get_topic_summary(),
            'active_sessions': len(self.active_sessions)
        }
    
    def get_query_suggestions(self, partial_query: str) -> List[str]:
        """Get query suggestions based on learned patterns"""
        try:
            rewrite_result = self.query_rewriter.rewrite_query(partial_query)
            return rewrite_result.get('query_variations', [])
        except Exception as e:
            print(f"Error getting query suggestions: {e}")
            return []
    
    def optimize_single_query(self, query: str) -> Dict[str, Any]:
        """Optimize a single query without full search"""
        try:
            # Rewrite query
            rewrite_result = self.query_rewriter.rewrite_query(query)
            
            # Optimize query
            optimization_result = self.query_optimizer.optimize_query(
                rewrite_result['rewritten_query'],
                context={
                    'entities': rewrite_result['entities'],
                    'intent': rewrite_result['intent']
                }
            )
            
            return {
                'original': query,
                'rewritten': rewrite_result['rewritten_query'],
                'optimized': optimization_result['optimized_query'],
                'entities': rewrite_result['entities'],
                'intent': rewrite_result['intent'],
                'confidence': rewrite_result['confidence'],
                'variations': rewrite_result.get('query_variations', [])
            }
            
        except Exception as e:
            print(f"Error optimizing query: {e}")
            return {'error': str(e), 'original': query}
    
    def export_learned_patterns(self, filepath: str):
        """Export learned optimization patterns"""
        try:
            patterns = self.query_optimizer.pattern_cache
            pattern_data = {}
            
            for key, pattern in patterns.items():
                pattern_data[key] = {
                    'type': pattern.pattern_type,
                    'original_terms': pattern.original_terms,
                    'improved_terms': pattern.improved_terms,
                    'success_rate': pattern.success_rate,
                    'usage_count': pattern.usage_count,
                    'confidence': pattern.confidence
                }
            
            import json
            with open(filepath, 'w') as f:
                json.dump(pattern_data, f, indent=2)
            
            print(f"✅ Exported {len(pattern_data)} patterns to {filepath}")
            
        except Exception as e:
            print(f"Error exporting patterns: {e}") 