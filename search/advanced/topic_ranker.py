from typing import List, Dict, Optional, Tuple, Any
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.decomposition import LatentDirichletAllocation
from transformers import pipeline
import re
from collections import defaultdict, Counter
from dataclasses import dataclass
import json

@dataclass
class TopicInfo:
    topic_id: int
    keywords: List[str]
    weight: float
    documents: List[str]
    coherence_score: float

@dataclass
class RankedResult:
    content: str
    original_score: float
    topic_score: float
    final_score: float
    topics: List[int]
    metadata: Dict[str, Any]

class TopicBasedRanker:
    def __init__(self, num_topics: int = 10):
        """Initialize topic-based ranking system"""
        self.num_topics = num_topics
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.8
        )
        
        # Initialize topic models
        self.lda_model = LatentDirichletAllocation(
            n_components=num_topics,
            random_state=42,
            max_iter=10
        )
        
        self.kmeans_model = KMeans(
            n_clusters=num_topics,
            random_state=42,
            n_init=10
        )
        
        # Initialize classification pipeline for domain detection
        try:
            self.classifier = pipeline(
                "zero-shot-classification",
                model="facebook/bart-large-mnli"
            )
        except Exception as e:
            print(f"Warning: Could not load classification model: {e}")
            self.classifier = None
        
        self.topic_models_fitted = False
        self.document_topics = {}
        self.topic_keywords = {}
        self.domain_categories = [
            'financial', 'legal', 'technical', 'medical', 'business',
            'academic', 'government', 'personal', 'news', 'general'
        ]
    
    def fit_topic_models(self, documents: List[str]):
        """Fit topic models on a corpus of documents"""
        if not documents:
            return
        
        try:
            # Preprocess documents
            cleaned_docs = [self._preprocess_text(doc) for doc in documents]
            cleaned_docs = [doc for doc in cleaned_docs if len(doc.strip()) > 0]
            
            if len(cleaned_docs) < 2:
                return
            
            # Fit TF-IDF vectorizer
            tfidf_matrix = self.vectorizer.fit_transform(cleaned_docs)
            
            # Fit LDA model
            self.lda_model.fit(tfidf_matrix)
            
            # Fit K-means model
            self.kmeans_model.fit(tfidf_matrix.toarray())
            
            # Extract topic keywords
            self._extract_topic_keywords()
            
            # Assign documents to topics
            self._assign_document_topics(cleaned_docs, tfidf_matrix)
            
            self.topic_models_fitted = True
            print(f"✅ Fitted topic models on {len(cleaned_docs)} documents")
            
        except Exception as e:
            print(f"Error fitting topic models: {e}")
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for topic modeling"""
        if not text:
            return ""
        
        # Remove special characters and digits
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\d+', '', text)
        
        # Convert to lowercase and remove extra whitespace
        text = ' '.join(text.lower().split())
        
        return text
    
    def _extract_topic_keywords(self):
        """Extract keywords for each topic from LDA model"""
        if not self.topic_models_fitted:
            return
        
        feature_names = self.vectorizer.get_feature_names_out()
        
        for topic_idx, topic in enumerate(self.lda_model.components_):
            # Get top words for this topic
            top_word_indices = topic.argsort()[-10:][::-1]
            top_words = [feature_names[i] for i in top_word_indices]
            self.topic_keywords[topic_idx] = top_words
    
    def _assign_document_topics(self, documents: List[str], tfidf_matrix):
        """Assign each document to topics"""
        # Get topic distributions from LDA
        doc_topic_distributions = self.lda_model.transform(tfidf_matrix)
        
        # Get cluster assignments from K-means
        cluster_assignments = self.kmeans_model.predict(tfidf_matrix.toarray())
        
        for doc_idx, doc in enumerate(documents):
            topic_dist = doc_topic_distributions[doc_idx]
            primary_topic = np.argmax(topic_dist)
            cluster = cluster_assignments[doc_idx]
            
            self.document_topics[doc] = {
                'primary_topic': primary_topic,
                'topic_distribution': topic_dist.tolist(),
                'cluster': cluster,
                'confidence': float(topic_dist[primary_topic])
            }
    
    def classify_query_domain(self, query: str) -> Dict[str, float]:
        """Classify query into domain categories"""
        if not self.classifier:
            return {'general': 1.0}
        
        try:
            result = self.classifier(query, self.domain_categories)
            domain_scores = {}
            for label, score in zip(result['labels'], result['scores']):
                domain_scores[label] = score
            return domain_scores
        except Exception as e:
            print(f"Error in domain classification: {e}")
            return {'general': 1.0}
    
    def get_query_topics(self, query: str) -> Dict[str, Any]:
        """Get topic information for a query"""
        if not self.topic_models_fitted:
            return {'topics': [], 'confidence': 0.0}
        
        try:
            # Preprocess and vectorize query
            cleaned_query = self._preprocess_text(query)
            if not cleaned_query:
                return {'topics': [], 'confidence': 0.0}
            
            query_tfidf = self.vectorizer.transform([cleaned_query])
            
            # Get topic distribution
            topic_dist = self.lda_model.transform(query_tfidf)[0]
            
            # Get top topics
            top_topic_indices = np.argsort(topic_dist)[-3:][::-1]  # Top 3 topics
            top_topics = []
            
            for topic_idx in top_topic_indices:
                if topic_dist[topic_idx] > 0.1:  # Only include topics with reasonable probability
                    top_topics.append({
                        'topic_id': int(topic_idx),
                        'probability': float(topic_dist[topic_idx]),
                        'keywords': self.topic_keywords.get(topic_idx, [])
                    })
            
            return {
                'topics': top_topics,
                'confidence': float(np.max(topic_dist)) if len(top_topics) > 0 else 0.0,
                'domain_scores': self.classify_query_domain(query)
            }
            
        except Exception as e:
            print(f"Error getting query topics: {e}")
            return {'topics': [], 'confidence': 0.0}
    
    def calculate_topic_relevance(self, query_topics: Dict, document_text: str) -> float:
        """Calculate topic-based relevance between query and document"""
        if not query_topics.get('topics') or not self.topic_models_fitted:
            return 0.5  # Neutral score if no topic information
        
        try:
            # Get document topics
            doc_topics = self.document_topics.get(document_text, {})
            if not doc_topics:
                # If document not in training set, classify it
                doc_topics = self._classify_new_document(document_text)
            
            if not doc_topics:
                return 0.5
            
            # Calculate topic similarity
            query_topic_scores = {t['topic_id']: t['probability'] for t in query_topics['topics']}
            doc_topic_dist = doc_topics.get('topic_distribution', [])
            
            if not doc_topic_dist:
                return 0.5
            
            # Calculate weighted similarity
            similarity = 0.0
            for topic_id, query_prob in query_topic_scores.items():
                if topic_id < len(doc_topic_dist):
                    doc_prob = doc_topic_dist[topic_id]
                    similarity += query_prob * doc_prob
            
            # Boost score if primary topics match
            primary_topic = doc_topics.get('primary_topic', -1)
            if primary_topic in query_topic_scores:
                similarity += 0.2
            
            return min(similarity, 1.0)
            
        except Exception as e:
            print(f"Error calculating topic relevance: {e}")
            return 0.5
    
    def _classify_new_document(self, document_text: str) -> Dict:
        """Classify a new document that wasn't in the training set"""
        try:
            cleaned_doc = self._preprocess_text(document_text)
            if not cleaned_doc:
                return {}
            
            doc_tfidf = self.vectorizer.transform([cleaned_doc])
            topic_dist = self.lda_model.transform(doc_tfidf)[0]
            primary_topic = np.argmax(topic_dist)
            
            return {
                'primary_topic': int(primary_topic),
                'topic_distribution': topic_dist.tolist(),
                'confidence': float(topic_dist[primary_topic])
            }
        except Exception as e:
            print(f"Error classifying new document: {e}")
            return {}
    
    def rank_results(self, query: str, results: List[Dict], weights: Dict[str, float] = None) -> List[RankedResult]:
        """Rank search results using topic-based scoring"""
        if not results:
            return []
        
        # Default weights for combining scores
        default_weights = {
            'original_score': 0.6,
            'topic_relevance': 0.3,
            'domain_match': 0.1
        }
        weights = weights or default_weights
        
        # Get query topic information
        query_topics = self.get_query_topics(query)
        query_domain = query_topics.get('domain_scores', {'general': 1.0})
        primary_domain = max(query_domain.keys(), key=query_domain.get)
        
        ranked_results = []
        
        for result in results:
            try:
                # Extract content for topic analysis
                content = result.get('text', '') or result.get('content', '') or result.get('doc_text', '')
                if not content:
                    continue
                
                # Calculate topic relevance
                topic_relevance = self.calculate_topic_relevance(query_topics, content)
                
                # Calculate domain match score
                doc_domain_scores = self.classify_query_domain(content[:500])  # Use first 500 chars
                domain_match = doc_domain_scores.get(primary_domain, 0.0)
                
                # Get original score
                original_score = float(result.get('score', 0.0))
                
                # Calculate final score
                final_score = (
                    weights['original_score'] * original_score +
                    weights['topic_relevance'] * topic_relevance +
                    weights['domain_match'] * domain_match
                )
                
                # Identify relevant topics
                relevant_topics = [t['topic_id'] for t in query_topics.get('topics', []) if t['probability'] > 0.15]
                
                ranked_results.append(RankedResult(
                    content=content,
                    original_score=original_score,
                    topic_score=topic_relevance,
                    final_score=final_score,
                    topics=relevant_topics,
                    metadata={
                        **result,
                        'domain_match': domain_match,
                        'primary_domain': primary_domain,
                        'topic_confidence': query_topics.get('confidence', 0.0)
                    }
                ))
                
            except Exception as e:
                print(f"Error ranking result: {e}")
                continue
        
        # Sort by final score
        ranked_results.sort(key=lambda x: x.final_score, reverse=True)
        return ranked_results
    
    def get_topic_summary(self) -> Dict[str, Any]:
        """Get summary of discovered topics"""
        if not self.topic_models_fitted:
            return {'error': 'Topic models not fitted'}
        
        topic_summary = {}
        for topic_id, keywords in self.topic_keywords.items():
            # Count documents in this topic
            doc_count = sum(1 for doc_info in self.document_topics.values() 
                          if doc_info.get('primary_topic') == topic_id)
            
            # Calculate average confidence
            confidences = [doc_info.get('confidence', 0.0) 
                         for doc_info in self.document_topics.values() 
                         if doc_info.get('primary_topic') == topic_id]
            avg_confidence = np.mean(confidences) if confidences else 0.0
            
            topic_summary[f"topic_{topic_id}"] = {
                'keywords': keywords,
                'document_count': doc_count,
                'average_confidence': float(avg_confidence)
            }
        
        return topic_summary
    
    def save_model(self, filepath: str):
        """Save the fitted topic models"""
        try:
            model_data = {
                'topic_keywords': self.topic_keywords,
                'document_topics': self.document_topics,
                'num_topics': self.num_topics,
                'topic_models_fitted': self.topic_models_fitted
            }
            
            with open(filepath, 'w') as f:
                json.dump(model_data, f, indent=2)
            
            print(f"✅ Saved topic model to {filepath}")
        except Exception as e:
            print(f"Error saving model: {e}")
    
    def load_model(self, filepath: str):
        """Load pre-fitted topic models"""
        try:
            with open(filepath, 'r') as f:
                model_data = json.load(f)
            
            self.topic_keywords = model_data.get('topic_keywords', {})
            self.document_topics = model_data.get('document_topics', {})
            self.num_topics = model_data.get('num_topics', 10)
            self.topic_models_fitted = model_data.get('topic_models_fitted', False)
            
            print(f"✅ Loaded topic model from {filepath}")
        except Exception as e:
            print(f"Error loading model: {e}") 