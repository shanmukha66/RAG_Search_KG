from typing import List, Dict, Optional, Tuple
import re
from transformers import T5ForConditionalGeneration, T5Tokenizer, pipeline
from sentence_transformers import SentenceTransformer
import spacy
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

class QueryRewriter:
    def __init__(self):
        """Initialize query rewriting components"""
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Load spaCy model for NER and POS tagging
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            print("Warning: spaCy model not found. Install with: python -m spacy download en_core_web_sm")
            self.nlp = None
        
        # Initialize sentence transformer for semantic similarity
        self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Common query expansion terms
        self.expansion_terms = {
            'document': ['file', 'paper', 'report', 'text'],
            'table': ['chart', 'graph', 'data', 'figure'],
            'image': ['picture', 'photo', 'diagram', 'illustration'],
            'company': ['organization', 'business', 'firm', 'corporation'],
            'financial': ['money', 'revenue', 'profit', 'income', 'cost']
        }
        
    def expand_query_terms(self, query: str) -> List[str]:
        """Expand query with synonyms and related terms"""
        expanded_queries = [query]  # Start with original query
        
        words = query.lower().split()
        for word in words:
            if word in self.expansion_terms:
                # Create variations with expanded terms
                for synonym in self.expansion_terms[word]:
                    expanded_query = query.lower().replace(word, synonym)
                    expanded_queries.append(expanded_query)
        
        return list(set(expanded_queries))  # Remove duplicates
    
    def extract_entities(self, query: str) -> Dict[str, List[str]]:
        """Extract named entities from query"""
        entities = {
            'PERSON': [],
            'ORG': [],
            'MONEY': [],
            'DATE': [],
            'GPE': [],  # Geopolitical entities
            'PRODUCT': []
        }
        
        if self.nlp:
            doc = self.nlp(query)
            for ent in doc.ents:
                if ent.label_ in entities:
                    entities[ent.label_].append(ent.text)
        
        return entities
    
    def identify_query_intent(self, query: str) -> str:
        """Identify the intent of the query"""
        query_lower = query.lower()
        
        # Define intent patterns
        intent_patterns = {
            'comparison': ['compare', 'difference', 'versus', 'vs', 'better', 'worse'],
            'definition': ['what is', 'define', 'meaning', 'definition'],
            'factual': ['when', 'where', 'who', 'how many', 'how much'],
            'analytical': ['why', 'how', 'analyze', 'explain', 'reason'],
            'procedural': ['how to', 'steps', 'process', 'procedure'],
            'temporal': ['latest', 'recent', 'current', 'new', 'updated']
        }
        
        for intent, patterns in intent_patterns.items():
            if any(pattern in query_lower for pattern in patterns):
                return intent
        
        return 'general'
    
    def rewrite_with_context(self, query: str, context_entities: List[str] = None) -> str:
        """Rewrite query with additional context"""
        entities = self.extract_entities(query)
        intent = self.identify_query_intent(query)
        
        # Add context-specific rewriting logic
        rewritten_parts = []
        
        # If query is too short, expand it
        if len(query.split()) <= 2:
            if context_entities:
                rewritten_parts.append(f"Find information about {query} related to {', '.join(context_entities)}")
            else:
                rewritten_parts.append(f"Search for documents containing information about {query}")
        else:
            rewritten_parts.append(query)
        
        # Add entity-specific expansions
        if entities['ORG']:
            rewritten_parts.append(f"Include results for organizations: {', '.join(entities['ORG'])}")
        
        if entities['PERSON']:
            rewritten_parts.append(f"Include results for people: {', '.join(entities['PERSON'])}")
        
        return " ".join(rewritten_parts)
    
    def generate_question_variations(self, query: str) -> List[str]:
        """Generate different question variations for the same intent"""
        try:
            prompt = f"""
            Given this search query: "{query}"
            
            Generate 3 alternative ways to ask the same question that might find different relevant documents:
            1. More specific version
            2. More general version  
            3. Different perspective/angle
            
            Return only the 3 alternative queries, one per line.
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.7
            )
            
            variations = response.choices[0].message.content.strip().split('\n')
            # Clean up the variations
            cleaned_variations = []
            for var in variations:
                cleaned = re.sub(r'^\d+\.\s*', '', var.strip())  # Remove numbering
                if cleaned and cleaned != query:
                    cleaned_variations.append(cleaned)
            
            return cleaned_variations
        except Exception as e:
            print(f"Error generating question variations: {e}")
            return []
    
    def rewrite_query(self, query: str, context: Dict = None) -> Dict[str, any]:
        """Main method to rewrite and enhance a query"""
        result = {
            'original_query': query,
            'rewritten_query': query,
            'expanded_queries': [],
            'query_variations': [],
            'entities': {},
            'intent': 'general',
            'confidence': 1.0
        }
        
        try:
            # Extract entities and intent
            result['entities'] = self.extract_entities(query)
            result['intent'] = self.identify_query_intent(query)
            
            # Expand query terms
            result['expanded_queries'] = self.expand_query_terms(query)
            
            # Generate question variations
            result['query_variations'] = self.generate_question_variations(query)
            
            # Context-aware rewriting
            context_entities = context.get('entities', []) if context else None
            result['rewritten_query'] = self.rewrite_with_context(query, context_entities)
            
            # Calculate confidence based on entity extraction and intent identification
            confidence = 0.5  # Base confidence
            if result['entities']:
                confidence += 0.2
            if result['intent'] != 'general':
                confidence += 0.2
            if len(query.split()) >= 3:
                confidence += 0.1
            
            result['confidence'] = min(confidence, 1.0)
            
        except Exception as e:
            print(f"Error in query rewriting: {e}")
        
        return result
    
    def semantic_similarity_rerank(self, query: str, candidates: List[str]) -> List[Tuple[str, float]]:
        """Rerank candidate queries by semantic similarity to original"""
        if not candidates:
            return []
        
        # Get embeddings
        query_embedding = self.sentence_model.encode([query])
        candidate_embeddings = self.sentence_model.encode(candidates)
        
        # Calculate similarities
        from sklearn.metrics.pairwise import cosine_similarity
        similarities = cosine_similarity(query_embedding, candidate_embeddings)[0]
        
        # Create ranked list
        ranked = list(zip(candidates, similarities))
        ranked.sort(key=lambda x: x[1], reverse=True)
        
        return ranked 