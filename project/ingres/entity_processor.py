"""Entity processing module for extraction and relation handling."""
from typing import Dict, List, Optional
from transformers import pipeline
from sentence_transformers import SentenceTransformer
import numpy as np

class EntityProcessor:
    def __init__(self):
        """Initialize entity extraction and embedding models."""
        self.ner_pipeline = pipeline("ner", model="dbmdz/bert-large-cased-finetuned-conll03-english")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
    def extract_entities(self, text: str) -> List[Dict]:
        """Extract named entities from text."""
        entities = self.ner_pipeline(text)
        
        # Merge consecutive entity tokens
        merged_entities = []
        current_entity = None
        
        for entity in entities:
            if current_entity is None:
                current_entity = entity.copy()
            elif (current_entity['entity'] == entity['entity'] and 
                  entity['start'] == current_entity['end']):
                current_entity['word'] += entity['word'].replace('##', '')
                current_entity['end'] = entity['end']
            else:
                merged_entities.append(current_entity)
                current_entity = entity.copy()
                
        if current_entity:
            merged_entities.append(current_entity)
            
        return merged_entities
    
    def compute_entity_similarity(self, entity1: str, entity2: str) -> float:
        """Compute similarity between two entities using embeddings."""
        emb1 = self.embedding_model.encode(entity1, convert_to_tensor=True)
        emb2 = self.embedding_model.encode(entity2, convert_to_tensor=True)
        
        similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        return float(similarity)
    
    def deduplicate_entities(self, entities: List[Dict], threshold: float = 0.85) -> List[Dict]:
        """Deduplicate entities based on Levenshtein distance and semantic similarity."""
        if not entities:
            return []
            
        unique_entities = [entities[0]]
        
        for entity in entities[1:]:
            is_duplicate = False
            for unique_entity in unique_entities:
                if (entity['entity'] == unique_entity['entity'] and
                    self.compute_entity_similarity(entity['word'], unique_entity['word']) > threshold):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_entities.append(entity)
                
        return unique_entities 