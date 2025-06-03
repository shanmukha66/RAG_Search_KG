from typing import List, Dict, Any, Optional
import torch
from transformers import pipeline
from sentence_transformers import SentenceTransformer
import spacy

class AdvancedProcessor:
    """Advanced content processing features."""
    
    def __init__(self):
        # Initialize models
        self.ner_model = spacy.load("en_core_web_sm")
        self.qa_pipeline = pipeline("question-answering")
        self.summarizer = pipeline("summarization")
        self.image_captioner = pipeline("image-to-text", model="Salesforce/blip-image-captioning-base")
        self.text_classifier = pipeline("text-classification")
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
    
    async def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract named entities from text."""
        doc = self.ner_model(text)
        return [{
            "text": ent.text,
            "label": ent.label_,
            "start": ent.start_char,
            "end": ent.end_char
        } for ent in doc.ents]
    
    async def answer_question(self, context: str, question: str) -> Dict[str, Any]:
        """Answer questions based on context."""
        return self.qa_pipeline(question=question, context=context)
    
    async def generate_summary(self, text: str, max_length: int = 130) -> str:
        """Generate a summary of the text."""
        summary = self.summarizer(text, max_length=max_length, min_length=30)
        return summary[0]["summary_text"]
    
    async def generate_image_caption(self, image) -> str:
        """Generate a caption for an image."""
        caption = self.image_captioner(image)
        return caption[0]["generated_text"]
    
    async def classify_text(self, text: str) -> Dict[str, float]:
        """Classify text into categories."""
        result = self.text_classifier(text)
        return {
            "label": result[0]["label"],
            "score": result[0]["score"]
        }
    
    async def generate_embeddings(self, texts: List[str]) -> torch.Tensor:
        """Generate embeddings for text."""
        return self.embedder.encode(texts, convert_to_tensor=True)
    
    async def semantic_search(
        self,
        query: str,
        documents: List[str],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Perform semantic search on documents."""
        query_embedding = self.embedder.encode(query, convert_to_tensor=True)
        document_embeddings = self.embedder.encode(documents, convert_to_tensor=True)
        
        # Calculate cosine similarities
        cos_scores = torch.nn.functional.cosine_similarity(
            query_embedding.unsqueeze(0),
            document_embeddings,
            dim=1
        )
        
        # Get top-k results
        top_results = torch.topk(cos_scores, k=min(top_k, len(documents)))
        
        return [{
            "document": documents[idx],
            "score": score.item()
        } for score, idx in zip(top_results.values, top_results.indices)] 