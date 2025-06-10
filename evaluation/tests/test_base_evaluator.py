import pytest
from ..metrics.base_evaluator import BaseEvaluator, QueryResult
import time

@pytest.fixture
def evaluator():
    return BaseEvaluator()

def test_query_classification(evaluator):
    query = "What is the capital of France?"
    query_type = evaluator.classify_query(query)
    assert isinstance(query_type, str)
    assert len(query_type) > 0

def test_response_evaluation(evaluator):
    query = "What is the capital of France?"
    response = "The capital of France is Paris."
    context = ["France is a country in Europe.", "Paris is the capital of France."]
    
    metrics = evaluator.evaluate_response(query, response, context)
    
    assert 'hallucination_score' in metrics
    assert 'relevancy_score' in metrics
    assert 'latency' in metrics
    assert metrics['latency'] >= 0

def test_results_storage(evaluator, tmp_path):
    # Create a test result
    query = "Test query"
    response = "Test response"
    context = ["Test context"]
    evaluator.evaluate_response(query, response, context)
    
    # Save results
    filepath = tmp_path / "test_results.json"
    evaluator.save_results(str(filepath))
    
    # Load results in a new evaluator
    new_evaluator = BaseEvaluator()
    new_evaluator.load_results(str(filepath))
    
    assert len(new_evaluator.results) == len(evaluator.results)
    assert new_evaluator.results[0].query == query
    assert new_evaluator.results[0].response == response 