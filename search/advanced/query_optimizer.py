from typing import List, Dict, Optional, Tuple, Any
import time
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
import json
import sqlite3
from pathlib import Path
import numpy as np
from datetime import datetime, timedelta
import threading
from concurrent.futures import ThreadPoolExecutor

@dataclass
class QuerySession:
    session_id: str
    user_id: Optional[str]
    queries: List[str]
    results_clicked: List[int]
    results_scores: List[float]
    timestamp: float
    satisfaction_score: Optional[float] = None
    query_success: bool = False

@dataclass
class QueryFeedback:
    query: str
    original_results: List[Dict]
    clicked_results: List[int]
    time_spent: float
    reformulated_query: Optional[str] = None
    satisfaction_rating: Optional[int] = None  # 1-5 scale

@dataclass
class QueryPattern:
    pattern_type: str  # 'reformulation', 'expansion', 'refinement'
    original_terms: List[str]
    improved_terms: List[str]
    success_rate: float
    usage_count: int
    confidence: float

class QueryOptimizer:
    def __init__(self, db_path: str = "query_optimization.db"):
        """Initialize real-time query optimizer"""
        self.db_path = db_path
        self.sessions = {}  # Active sessions
        self.query_history = deque(maxlen=1000)  # Recent query history
        self.pattern_cache = {}  # Cached optimization patterns
        self.learning_enabled = True
        
        # Threading for async operations
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.lock = threading.Lock()
        
        # Initialize database
        self._init_database()
        
        # Load existing patterns
        self._load_patterns()
        
        # Performance tracking
        self.optimization_stats = {
            'total_queries': 0,
            'optimized_queries': 0,
            'improvement_rate': 0.0,
            'avg_satisfaction': 0.0
        }
    
    def _init_database(self):
        """Initialize SQLite database for storing optimization data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Query sessions table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS query_sessions (
                        session_id TEXT PRIMARY KEY,
                        user_id TEXT,
                        queries TEXT,
                        results_clicked TEXT,
                        results_scores TEXT,
                        timestamp REAL,
                        satisfaction_score REAL,
                        query_success BOOLEAN
                    )
                ''')
                
                # Query patterns table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS query_patterns (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        pattern_type TEXT,
                        original_terms TEXT,
                        improved_terms TEXT,
                        success_rate REAL,
                        usage_count INTEGER,
                        confidence REAL,
                        created_at REAL,
                        updated_at REAL
                    )
                ''')
                
                # Query feedback table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS query_feedback (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        query TEXT,
                        original_results TEXT,
                        clicked_results TEXT,
                        time_spent REAL,
                        reformulated_query TEXT,
                        satisfaction_rating INTEGER,
                        timestamp REAL
                    )
                ''')
                
                conn.commit()
                print("✅ Initialized query optimization database")
                
        except Exception as e:
            print(f"Error initializing database: {e}")
    
    def _load_patterns(self):
        """Load existing optimization patterns from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT pattern_type, original_terms, improved_terms, 
                           success_rate, usage_count, confidence
                    FROM query_patterns
                    WHERE confidence > 0.5
                    ORDER BY success_rate DESC
                ''')
                
                for row in cursor.fetchall():
                    pattern_type, orig_terms, imp_terms, success_rate, usage_count, confidence = row
                    
                    pattern = QueryPattern(
                        pattern_type=pattern_type,
                        original_terms=json.loads(orig_terms),
                        improved_terms=json.loads(imp_terms),
                        success_rate=success_rate,
                        usage_count=usage_count,
                        confidence=confidence
                    )
                    
                    # Cache pattern for quick lookup
                    key = f"{pattern_type}:{'-'.join(pattern.original_terms)}"
                    self.pattern_cache[key] = pattern
                
                print(f"✅ Loaded {len(self.pattern_cache)} optimization patterns")
                
        except Exception as e:
            print(f"Error loading patterns: {e}")
    
    def start_session(self, session_id: str, user_id: Optional[str] = None) -> str:
        """Start a new query session"""
        with self.lock:
            session = QuerySession(
                session_id=session_id,
                user_id=user_id,
                queries=[],
                results_clicked=[],
                results_scores=[],
                timestamp=time.time()
            )
            self.sessions[session_id] = session
        return session_id
    
    def optimize_query(self, query: str, session_id: Optional[str] = None, 
                      context: Dict = None) -> Dict[str, Any]:
        """Optimize a query based on learned patterns"""
        self.optimization_stats['total_queries'] += 1
        
        # Analyze query for optimization opportunities
        optimization_result = {
            'original_query': query,
            'optimized_query': query,
            'optimizations_applied': [],
            'confidence': 0.0,
            'expected_improvement': 0.0
        }
        
        try:
            # Apply various optimization strategies
            optimized_query = query
            optimizations = []
            total_confidence = 0.0
            
            # 1. Term expansion based on successful patterns
            expanded_query, expansion_conf = self._apply_term_expansion(optimized_query)
            if expanded_query != optimized_query:
                optimizations.append({
                    'type': 'term_expansion',
                    'original': optimized_query,
                    'optimized': expanded_query,
                    'confidence': expansion_conf
                })
                optimized_query = expanded_query
                total_confidence += expansion_conf
            
            # 2. Query refinement based on context
            if context:
                refined_query, refinement_conf = self._apply_query_refinement(optimized_query, context)
                if refined_query != optimized_query:
                    optimizations.append({
                        'type': 'query_refinement',
                        'original': optimized_query,
                        'optimized': refined_query,
                        'confidence': refinement_conf
                    })
                    optimized_query = refined_query
                    total_confidence += refinement_conf
            
            # Update result
            optimization_result.update({
                'optimized_query': optimized_query,
                'optimizations_applied': optimizations,
                'confidence': total_confidence / max(len(optimizations), 1),
                'expected_improvement': self._estimate_improvement(query, optimized_query)
            })
            
            # Track session if provided
            if session_id and session_id in self.sessions:
                self.sessions[session_id].queries.append(query)
            
            # Update stats
            if optimizations:
                self.optimization_stats['optimized_queries'] += 1
                self.optimization_stats['improvement_rate'] = (
                    self.optimization_stats['optimized_queries'] / 
                    self.optimization_stats['total_queries']
                )
            
        except Exception as e:
            print(f"Error in query optimization: {e}")
        
        return optimization_result
    
    def _apply_term_expansion(self, query: str) -> Tuple[str, float]:
        """Apply term expansion based on learned patterns"""
        query_terms = query.lower().split()
        expanded_terms = query_terms.copy()
        confidence = 0.0
        
        for pattern in self.pattern_cache.values():
            if pattern.pattern_type == 'expansion' and pattern.success_rate > 0.7:
                # Check if any original terms match
                matches = set(pattern.original_terms).intersection(set(query_terms))
                if matches and len(matches) / len(pattern.original_terms) > 0.5:
                    # Add improved terms
                    for term in pattern.improved_terms:
                        if term not in expanded_terms:
                            expanded_terms.append(term)
                    confidence = max(confidence, pattern.confidence)
        
        expanded_query = ' '.join(expanded_terms)
        return expanded_query, confidence
    
    def _apply_query_refinement(self, query: str, context: Dict) -> Tuple[str, float]:
        """Apply query refinement based on context and patterns"""
        refined_query = query
        confidence = 0.0
        
        # Use entities from context for refinement
        entities = context.get('entities', {})
        if entities:
            # Add important entities if not already in query
            query_lower = query.lower()
            for entity_type, entity_list in entities.items():
                for entity in entity_list:
                    if entity and entity.lower() not in query_lower:
                        if entity_type in ['ORG', 'PERSON', 'GPE']:  # Important entity types
                            refined_query += f" {entity}"
                            confidence += 0.1
        
        return refined_query, min(confidence, 0.8)
    
    def _estimate_improvement(self, original: str, optimized: str) -> float:
        """Estimate expected improvement from optimization"""
        if original == optimized:
            return 0.0
        
        # Simple heuristic based on query length and term quality
        original_terms = len(original.split())
        optimized_terms = len(optimized.split())
        
        if optimized_terms > original_terms:
            # More terms generally improve recall
            return min((optimized_terms - original_terms) * 0.1, 0.3)
        else:
            # Refined terms may improve precision
            return 0.15
    
    def record_feedback(self, query: str, results: List[Dict], clicked_results: List[int],
                       time_spent: float, session_id: Optional[str] = None,
                       satisfaction_rating: Optional[int] = None):
        """Record user feedback for learning"""
        if not self.learning_enabled:
            return
        
        try:
            # Create feedback record
            feedback = QueryFeedback(
                query=query,
                original_results=results,
                clicked_results=clicked_results,
                time_spent=time_spent,
                satisfaction_rating=satisfaction_rating
            )
            
            # Update session if provided
            if session_id and session_id in self.sessions:
                session = self.sessions[session_id]
                session.results_clicked.extend(clicked_results)
                session.results_scores.extend([r.get('score', 0.0) for r in results])
                
                # Calculate satisfaction
                if clicked_results:
                    session.query_success = True
                    # Higher click rate and specific rating indicate satisfaction
                    click_rate = len(clicked_results) / len(results) if results else 0
                    rating_score = (satisfaction_rating or 3) / 5.0
                    session.satisfaction_score = (click_rate + rating_score) / 2
            
            # Store feedback asynchronously
            self.executor.submit(self._store_feedback, feedback)
            
            # Learn patterns asynchronously
            self.executor.submit(self._learn_from_feedback, feedback)
            
        except Exception as e:
            print(f"Error recording feedback: {e}")
    
    def _store_feedback(self, feedback: QueryFeedback):
        """Store feedback in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO query_feedback 
                    (query, original_results, clicked_results, time_spent, 
                     reformulated_query, satisfaction_rating, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    feedback.query,
                    json.dumps([asdict(r) if hasattr(r, '__dict__') else r for r in feedback.original_results]),
                    json.dumps(feedback.clicked_results),
                    feedback.time_spent,
                    feedback.reformulated_query,
                    feedback.satisfaction_rating,
                    time.time()
                ))
                conn.commit()
        except Exception as e:
            print(f"Error storing feedback: {e}")
    
    def _learn_from_feedback(self, feedback: QueryFeedback):
        """Learn optimization patterns from user feedback"""
        if not self.learning_enabled:
            return
        
        try:
            query_terms = feedback.query.lower().split()
            
            if feedback.clicked_results and feedback.satisfaction_rating and feedback.satisfaction_rating >= 4:
                # Learn successful patterns
                self._update_pattern('expansion', query_terms, [], True)
            else:
                # Learn from failures
                self._update_pattern('refinement', query_terms, [], False)
            
        except Exception as e:
            print(f"Error learning from feedback: {e}")
    
    def _update_pattern(self, pattern_type: str, original_terms: List[str], 
                       improved_terms: List[str], success: bool):
        """Update or create an optimization pattern"""
        try:
            key = f"{pattern_type}:{'-'.join(sorted(original_terms))}"
            
            if key in self.pattern_cache:
                # Update existing pattern
                pattern = self.pattern_cache[key]
                pattern.usage_count += 1
                
                if success:
                    pattern.success_rate = (pattern.success_rate * (pattern.usage_count - 1) + 1.0) / pattern.usage_count
                else:
                    pattern.success_rate = (pattern.success_rate * (pattern.usage_count - 1)) / pattern.usage_count
                
                # Update confidence based on usage and success
                pattern.confidence = min(pattern.success_rate * (pattern.usage_count / 10), 1.0)
            
            else:
                # Create new pattern
                pattern = QueryPattern(
                    pattern_type=pattern_type,
                    original_terms=original_terms,
                    improved_terms=improved_terms,
                    success_rate=1.0 if success else 0.0,
                    usage_count=1,
                    confidence=0.1  # Start with low confidence
                )
                self.pattern_cache[key] = pattern
            
            # Save to database
            self._save_pattern(pattern)
            
        except Exception as e:
            print(f"Error updating pattern: {e}")
    
    def _save_pattern(self, pattern: QueryPattern):
        """Save pattern to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if pattern exists
                cursor.execute('''
                    SELECT id FROM query_patterns 
                    WHERE pattern_type = ? AND original_terms = ?
                ''', (pattern.pattern_type, json.dumps(pattern.original_terms)))
                
                existing = cursor.fetchone()
                current_time = time.time()
                
                if existing:
                    # Update existing
                    cursor.execute('''
                        UPDATE query_patterns 
                        SET improved_terms = ?, success_rate = ?, usage_count = ?, 
                            confidence = ?, updated_at = ?
                        WHERE id = ?
                    ''', (
                        json.dumps(pattern.improved_terms),
                        pattern.success_rate,
                        pattern.usage_count,
                        pattern.confidence,
                        current_time,
                        existing[0]
                    ))
                else:
                    # Insert new
                    cursor.execute('''
                        INSERT INTO query_patterns 
                        (pattern_type, original_terms, improved_terms, success_rate, 
                         usage_count, confidence, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        pattern.pattern_type,
                        json.dumps(pattern.original_terms),
                        json.dumps(pattern.improved_terms),
                        pattern.success_rate,
                        pattern.usage_count,
                        pattern.confidence,
                        current_time,
                        current_time
                    ))
                
                conn.commit()
                
        except Exception as e:
            print(f"Error saving pattern: {e}")
    
    def end_session(self, session_id: str):
        """End a query session and save results"""
        if session_id not in self.sessions:
            return
        
        try:
            session = self.sessions[session_id]
            
            # Save session to database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO query_sessions 
                    (session_id, user_id, queries, results_clicked, results_scores, 
                     timestamp, satisfaction_score, query_success)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    session.session_id,
                    session.user_id,
                    json.dumps(session.queries),
                    json.dumps(session.results_clicked),
                    json.dumps(session.results_scores),
                    session.timestamp,
                    session.satisfaction_score,
                    session.query_success
                ))
                conn.commit()
            
            # Update stats
            if session.satisfaction_score:
                current_avg = self.optimization_stats['avg_satisfaction']
                total_sessions = len(self.query_history) + 1
                self.optimization_stats['avg_satisfaction'] = (
                    (current_avg * (total_sessions - 1) + session.satisfaction_score) / total_sessions
                )
            
            # Add to history and remove from active sessions
            self.query_history.append(session)
            del self.sessions[session_id]
            
        except Exception as e:
            print(f"Error ending session: {e}")
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get current optimization statistics"""
        return {
            **self.optimization_stats,
            'active_sessions': len(self.sessions),
            'cached_patterns': len(self.pattern_cache),
            'recent_queries': len(self.query_history)
        }
    
    def get_top_patterns(self, limit: int = 10) -> List[Dict]:
        """Get top performing optimization patterns"""
        patterns = list(self.pattern_cache.values())
        patterns.sort(key=lambda p: p.success_rate * p.confidence, reverse=True)
        
        return [
            {
                'type': p.pattern_type,
                'original_terms': p.original_terms,
                'improved_terms': p.improved_terms,
                'success_rate': p.success_rate,
                'usage_count': p.usage_count,
                'confidence': p.confidence
            }
            for p in patterns[:limit]
        ] 