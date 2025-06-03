from typing import Dict, Any, List
import spacy
from sentence_transformers import SentenceTransformer
from transformers import pipeline

class TextProcessor:
    def __init__(self):
        # Load models
        self.nlp = spacy.load("en_core_web_sm")
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        self.zero_shot = pipeline(
            "zero-shot-classification",
            model="facebook/bart-large-mnli"
        )
        
    async def process(self, content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process text content to extract entities, generate embeddings, and classify content
        
        Args:
            content: Text content to process
            metadata: File metadata
        """
        # Process with spaCy for entity extraction
        doc = self.nlp(content)
        
        # Extract entities
        entities = []
        for ent in doc.ents:
            entities.append({
                "text": ent.text,
                "type": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char
            })
        
        # Generate embeddings
        embeddings = self.encoder.encode(content, convert_to_tensor=True).numpy()
        
        # Classify content
        candidate_labels = ["document", "article", "email", "report", "code", "other"]
        classification = self.zero_shot(
            content[:1024],  # Truncate for classification
            candidate_labels,
            multi_label=False
        )
        
        # Extract key phrases (basic implementation)
        key_phrases = [
            chunk.text
            for chunk in doc.noun_chunks
            if len(chunk.text.split()) > 1  # Multi-word phrases
        ]
        
        # Summarize (basic implementation)
        sentences = list(doc.sents)
        summary = " ".join([sent.text for sent in sentences[:3]])  # First 3 sentences
        
        # Combine results
        result = {
            "content_type": "text",
            "embeddings": embeddings,
            "entities": entities,
            "metadata": {
                **metadata,
                "document_type": classification["labels"][0],
                "confidence": classification["scores"][0],
                "key_phrases": key_phrases[:10],  # Top 10 phrases
                "summary": summary,
                "language": doc.lang_,
                "word_count": len(doc),
                "sentence_count": len(sentences)
            }
        }
        
        return result
    
    def _extract_relationships(self, doc) -> List[Dict[str, Any]]:
        """
        Extract relationships between entities
        Basic implementation focusing on subject-verb-object patterns
        """
        relationships = []
        
        for sent in doc.sents:
            for token in sent:
                if token.dep_ == "ROOT" and token.pos_ == "VERB":
                    # Find subject
                    subject = None
                    for child in token.children:
                        if child.dep_ in ["nsubj", "nsubjpass"]:
                            subject = child
                            break
                    
                    # Find object
                    obj = None
                    for child in token.children:
                        if child.dep_ in ["dobj", "pobj"]:
                            obj = child
                            break
                    
                    if subject and obj:
                        relationships.append({
                            "subject": subject.text,
                            "predicate": token.text,
                            "object": obj.text,
                            "sentence": sent.text
                        })
        
        return relationships 