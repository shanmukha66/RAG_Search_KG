import time
from typing import Dict, List, Any
import numpy as np

class BaseMetric:
    def __init__(self):
        self.name = "base_metric"
    
    def measure(self, test_case: Dict[str, Any]) -> float:
        raise NotImplementedError

class LatencyMetric(BaseMetric):
    def __init__(self):
        super().__init__()
        self.name = "latency"
    
    def measure(self, start_time: float, end_time: float) -> float:
        return end_time - start_time

class RelevanceMetric(BaseMetric):
    def __init__(self, threshold: float = 0.5):
        super().__init__()
        self.name = "relevance"
        self.threshold = threshold
    
    def measure(self, query: str, response: str, context: List[str]) -> float:
        # Simple relevance check - can be enhanced with embeddings
        query_terms = set(query.lower().split())
        response_terms = set(response.lower().split())
        context_terms = set(" ".join(context).lower().split())
        
        # Calculate overlap between response and context
        response_context_overlap = len(response_terms.intersection(context_terms))
        response_query_overlap = len(response_terms.intersection(query_terms))
        
        # Normalize scores
        context_relevance = response_context_overlap / (len(response_terms) + 1e-6)
        query_relevance = response_query_overlap / (len(query_terms) + 1e-6)
        
        return (context_relevance + query_relevance) / 2

class HallucinationMetric(BaseMetric):
    def __init__(self):
        super().__init__()
        self.name = "hallucination"
    
    def measure(self, context: List[str], response: str) -> float:
        """Measure hallucination score - higher values mean less hallucination"""
        if not response or not context:
            return 0.5
            
        response_terms = set(response.lower().split())
        context_terms = set(" ".join(context).lower().split())
        
        # Calculate overlap between response and context
        overlap = len(response_terms.intersection(context_terms))
        score = overlap / len(response_terms) if response_terms else 0.5
        
        return min(1.0, max(0.0, score))

class RAGEvaluator:
    def __init__(self):
        self.metrics = {
            'latency': LatencyMetric(),
            'relevance': RelevanceMetric(),
            'hallucination': HallucinationMetric()
        }
        self.results_history = []
    
    def evaluate_response(self, 
                         query: str,
                         response: str,
                         context: List[str],
                         start_time: float,
                         end_time: float) -> Dict[str, float]:
        """
        Evaluate a RAG response using multiple metrics
        
        Args:
            query: The user's query
            response: The generated response
            context: List of context passages used for generation
            start_time: Query processing start time
            end_time: Response generation end time
            
        Returns:
            Dictionary of metric names and scores
        """
        results = {}
        
        # Measure latency
        results['latency'] = self.metrics['latency'].measure(start_time, end_time)
        
        # Measure relevance
        results['relevance'] = self.metrics['relevance'].measure(query, response, context)
        
        # Measure hallucination (higher score = less hallucination)
        results['hallucination_score'] = self.metrics['hallucination'].measure(context, response)
        
        # Store results
        self.results_history.append({
            'query': query,
            'response': response,
            'metrics': results
        })
        
        return results
    
    def get_average_metrics(self) -> Dict[str, float]:
        """Calculate average scores across all evaluations"""
        if not self.results_history:
            return {}
            
        avg_metrics = {}
        for metric in self.metrics:
            scores = [r['metrics'][metric] for r in self.results_history]
            avg_metrics[metric] = np.mean(scores)
        
        return avg_metrics 