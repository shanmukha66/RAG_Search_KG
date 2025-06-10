from typing import Dict, List, Any
import time
from dataclasses import dataclass
import json

@dataclass
class QueryResult:
    query: str
    response: str
    context: List[str]
    latency: float
    query_type: str
    timestamp: float

class BaseEvaluator:
    def __init__(self):
        self.results: List[QueryResult] = []
    
    def classify_query(self, query: str) -> str:
        """Classify query into types: factual, reasoning, lookup, etc."""
        # TODO: Implement query classification logic
        return "general"
    
    def measure_hallucination(self, context: List[str], response: str) -> float:
        """Measure hallucination score between 0 and 1"""
        # Simple implementation - check if response terms are in context
        if not response or not context:
            return 0.5
            
        response_terms = set(response.lower().split())
        context_terms = set(" ".join(context).lower().split())
        
        overlap = len(response_terms.intersection(context_terms))
        score = overlap / len(response_terms) if response_terms else 0.5
        
        return min(1.0, max(0.0, score))
    
    def measure_relevance(self, query: str, response: str) -> float:
        """Measure relevance score between 0 and 1"""
        if not query or not response:
            return 0.5
            
        query_terms = set(query.lower().split())
        response_terms = set(response.lower().split())
        
        overlap = len(query_terms.intersection(response_terms))
        score = overlap / len(query_terms) if query_terms else 0.5
        
        return min(1.0, max(0.0, score))
    
    def evaluate_response(self, query: str, response: str, context: List[str], start_time: float = None, end_time: float = None) -> Dict[str, float]:
        """Evaluate a single response using multiple metrics"""
        if start_time is None:
            start_time = time.time()
        if end_time is None:
            end_time = time.time()
        
        # Store result
        result = QueryResult(
            query=query,
            response=response,
            context=context,
            latency=end_time - start_time,
            query_type=self.classify_query(query),
            timestamp=time.time()
        )
        self.results.append(result)
        
        try:
            # Calculate metrics
            metrics = {
                'hallucination_score': self.measure_hallucination(context, response),
                'relevance_score': self.measure_relevance(query, response),
                'latency': result.latency
            }
        except Exception as e:
            print(f"Error calculating metrics: {e}")
            # Fallback metrics
            metrics = {
                'hallucination_score': 0.5,  # Middle ground
                'relevance_score': 0.5,      # Middle ground
                'latency': result.latency
            }
        
        return metrics
    
    def save_results(self, filepath: str):
        """Save evaluation results to file"""
        with open(filepath, 'w') as f:
            json.dump([vars(r) for r in self.results], f, indent=2)
    
    def load_results(self, filepath: str):
        """Load evaluation results from file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
            self.results = [QueryResult(**r) for r in data] 