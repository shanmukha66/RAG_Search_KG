from typing import Dict, Any, List
from deepeval.metrics import (
    HallucinationMetric,
    RelevancyMetric,
    LatencyMetric,
    AnswerCorrectness
)
import time
from dataclasses import dataclass
from enum import Enum

class QueryType(Enum):
    FACTUAL = "factual"
    SUMMARIZATION = "summarization"
    SEMANTIC_LINKAGE = "semantic_linkage"
    REASONING = "reasoning"

@dataclass
class QueryResult:
    query_type: QueryType
    answer: str
    context: List[str]
    latency: float
    confidence: float
    sources: List[Dict[str, Any]]
    cross_references: List[Dict[str, Any]]

class EvaluationMetrics:
    def __init__(self):
        self.hallucination_metric = HallucinationMetric()
        self.relevancy_metric = RelevancyMetric()
        self.latency_metric = LatencyMetric()
        self.correctness_metric = AnswerCorrectness()
    
    async def evaluate_query_result(
        self,
        query: str,
        result: QueryResult,
        expected: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a query result using multiple metrics
        """
        start_time = time.time()
        
        # Evaluate hallucination
        hallucination_score = await self.hallucination_metric.calculate(
            prediction=result.answer,
            context=result.context
        )
        
        # Evaluate relevancy
        relevancy_score = await self.relevancy_metric.calculate(
            prediction=result.answer,
            context=result.context,
            query=query
        )
        
        # Calculate latency
        latency = result.latency
        
        # Evaluate correctness if expected result is provided
        correctness_score = None
        if expected:
            correctness_score = await self.correctness_metric.calculate(
                prediction=result.answer,
                expected=expected.get("answer", "")
            )
        
        # Calculate cross-reference accuracy
        cross_ref_accuracy = self._calculate_cross_ref_accuracy(
            result.cross_references,
            expected.get("cross_references", []) if expected else []
        )
        
        return {
            "query_type": result.query_type.value,
            "metrics": {
                "hallucination_score": hallucination_score,
                "relevancy_score": relevancy_score,
                "latency": latency,
                "correctness_score": correctness_score,
                "cross_reference_accuracy": cross_ref_accuracy,
                "confidence": result.confidence
            },
            "sources": result.sources,
            "evaluation_time": time.time() - start_time
        }
    
    def _calculate_cross_ref_accuracy(
        self,
        predicted_refs: List[Dict[str, Any]],
        expected_refs: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate accuracy of cross-modal entity linking
        """
        if not expected_refs:
            return None
        
        correct_refs = 0
        total_refs = len(expected_refs)
        
        for exp_ref in expected_refs:
            for pred_ref in predicted_refs:
                if self._match_cross_reference(exp_ref, pred_ref):
                    correct_refs += 1
                    break
        
        return correct_refs / total_refs if total_refs > 0 else 0.0
    
    def _match_cross_reference(
        self,
        ref1: Dict[str, Any],
        ref2: Dict[str, Any]
    ) -> bool:
        """
        Check if two cross-references match
        """
        # Basic matching - can be enhanced based on requirements
        return (
            ref1.get("entity_id") == ref2.get("entity_id") and
            ref1.get("modality") == ref2.get("modality") and
            ref1.get("reference_type") == ref2.get("reference_type")
        ) 