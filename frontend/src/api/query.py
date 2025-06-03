from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio

from ..processors.query_processor import QueryProcessor
from ..storage.vector_store import QdrantVectorStore
from ..storage.graph_store import GraphStore
from ..evaluation.metrics import EvaluationMetrics, QueryType
from ..llm.openai_client import OpenAIClient

# Initialize components
query_processor = QueryProcessor()
vector_store = QdrantVectorStore()
graph_store = GraphStore()
evaluation = EvaluationMetrics()
llm = OpenAIClient()

async def process_query(
    query: str,
    query_type: QueryType,
    filters: Optional[Dict[str, Any]] = None,
    modalities: List[str] = ["text", "image", "audio", "video"]
) -> Dict[str, Any]:
    """
    Process a query and return relevant results
    """
    try:
        # Preprocess query
        processed_query = await preprocess_query(query, query_type)
        
        # Retrieve relevant context
        context = await retrieve_context(
            processed_query,
            filters,
            modalities
        )
        
        # Generate answer
        answer = await generate_answer(
            processed_query,
            context,
            query_type
        )
        
        # Post-process and evaluate
        result = await postprocess_result(
            query=query,
            answer=answer,
            context=context,
            query_type=query_type
        )
        
        return result
        
    except Exception as e:
        print(f"Error processing query: {str(e)}")
        raise

async def preprocess_query(
    query: str,
    query_type: QueryType
) -> Dict[str, Any]:
    """
    Preprocess and validate the query
    """
    # Clean and normalize query
    cleaned_query = await query_processor.clean_text(query)
    
    # Extract query intent and entities
    intent = await query_processor.extract_intent(cleaned_query)
    entities = await query_processor.extract_entities(cleaned_query)
    
    # Generate query embedding
    embedding = await query_processor.generate_embedding(cleaned_query)
    
    return {
        "original": query,
        "cleaned": cleaned_query,
        "intent": intent,
        "entities": entities,
        "embedding": embedding,
        "type": query_type
    }

async def retrieve_context(
    processed_query: Dict[str, Any],
    filters: Optional[Dict[str, Any]] = None,
    modalities: List[str] = ["text", "image", "audio", "video"]
) -> List[Dict[str, Any]]:
    """
    Retrieve relevant context from vector and graph stores
    """
    # Vector similarity search
    vector_results = await vector_store.search(
        query_vector=processed_query["embedding"],
        filters={
            "type": {"$in": modalities},
            **(filters or {})
        },
        limit=10
    )
    
    # Graph-based search using entities
    graph_results = []
    for entity in processed_query["entities"]:
        related_entities = await graph_store.search_related(
            entity_name=entity["name"],
            entity_type=entity["type"],
            max_distance=2
        )
        graph_results.extend(related_entities)
    
    # Combine and rank results
    combined_results = await query_processor.rank_results(
        vector_results=vector_results,
        graph_results=graph_results,
        query=processed_query
    )
    
    return combined_results

async def generate_answer(
    processed_query: Dict[str, Any],
    context: List[Dict[str, Any]],
    query_type: QueryType
) -> Dict[str, Any]:
    """
    Generate answer using retrieved context
    """
    # Format context for LLM
    formatted_context = await query_processor.format_context(context)
    
    # Generate system prompt based on query type
    system_prompt = await query_processor.generate_system_prompt(
        query_type=query_type,
        context_length=len(formatted_context)
    )
    
    # Generate answer using LLM
    response = await llm.generate(
        system_prompt=system_prompt,
        user_message=processed_query["cleaned"],
        context=formatted_context
    )
    
    return {
        "text": response["text"],
        "reasoning": response.get("reasoning"),
        "confidence": response.get("confidence", 0.0)
    }

async def postprocess_result(
    query: str,
    answer: Dict[str, Any],
    context: List[Dict[str, Any]],
    query_type: QueryType
) -> Dict[str, Any]:
    """
    Post-process and evaluate the generated answer
    """
    # Evaluate answer
    evaluation_result = await evaluation.evaluate(
        query=query,
        answer=answer["text"],
        context=context,
        query_type=query_type
    )
    
    # Extract cross-references
    cross_references = await query_processor.extract_cross_references(
        answer=answer["text"],
        context=context
    )
    
    # Format sources
    sources = await query_processor.format_sources(context)
    
    return {
        "answer": answer["text"],
        "confidence": min(
            answer["confidence"],
            evaluation_result["confidence"]
        ),
        "sources": sources,
        "cross_references": cross_references,
        "evaluation": {
            "relevance": evaluation_result["relevance"],
            "factuality": evaluation_result["factuality"],
            "coherence": evaluation_result["coherence"]
        }
    } 