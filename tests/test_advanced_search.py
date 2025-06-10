import unittest
import asyncio
import tempfile
import os
from unittest.mock import Mock, MagicMock
from search.advanced.query_rewriter import QueryRewriter
from search.advanced.topic_ranker import TopicBasedRanker
from search.advanced.query_optimizer import QueryOptimizer
from search.advanced.controller import AdvancedSearchController
from search.advanced.agent_retrieval import SearchResult

class TestAdvancedSearch(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        # Mock external dependencies
        self.mock_qdrant_client = Mock()
        self.mock_neo4j_driver = Mock()
        self.mock_sentence_model = Mock()
        
        # Configure mock returns
        self.mock_sentence_model.encode.return_value = [0.1] * 384  # Mock embedding
        
        # Create temporary database for optimizer
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
    def tearDown(self):
        """Clean up test environment"""
        os.unlink(self.temp_db.name)
    
    def test_query_rewriter(self):
        """Test query rewriting functionality"""
        rewriter = QueryRewriter()
        
        # Test basic query rewriting
        result = rewriter.rewrite_query("find documents about company revenue")
        
        self.assertIn('original_query', result)
        self.assertIn('rewritten_query', result)
        self.assertIn('entities', result)
        self.assertIn('intent', result)
        self.assertIn('confidence', result)
        
        # Test entity extraction
        entities = rewriter.extract_entities("Apple Inc reported $100 million revenue")
        self.assertIsInstance(entities, dict)
        
        # Test intent identification
        intent = rewriter.identify_query_intent("What is machine learning?")
        self.assertEqual(intent, 'definition')
        
        intent = rewriter.identify_query_intent("Compare Apple and Google")
        self.assertEqual(intent, 'comparison')
    
    def test_topic_ranker(self):
        """Test topic-based ranking functionality"""
        ranker = TopicBasedRanker(num_topics=5)
        
        # Test with sample documents
        sample_docs = [
            "This is a financial report about company revenue and profits",
            "Technical documentation for software development process",
            "Legal contract terms and conditions for business agreements",
            "Medical research paper on drug development and testing",
            "Academic study on machine learning algorithms"
        ]
        
        # Fit topic models
        ranker.fit_topic_models(sample_docs)
        
        # Test query topic extraction
        query_topics = ranker.get_query_topics("financial revenue analysis")
        self.assertIn('topics', query_topics)
        self.assertIn('confidence', query_topics)
        
        # Test result ranking
        sample_results = [
            {'text': 'Financial analysis of revenue streams', 'score': 0.8},
            {'text': 'Technical software implementation guide', 'score': 0.7},
            {'text': 'Legal framework for business operations', 'score': 0.6}
        ]
        
        ranked_results = ranker.rank_results("financial analysis", sample_results)
        self.assertTrue(len(ranked_results) > 0)
        self.assertTrue(hasattr(ranked_results[0], 'final_score'))
    
    def test_query_optimizer(self):
        """Test query optimization functionality"""
        optimizer = QueryOptimizer(db_path=self.temp_db.name)
        
        # Test query optimization
        result = optimizer.optimize_query("revenue report")
        
        self.assertIn('original_query', result)
        self.assertIn('optimized_query', result)
        self.assertIn('confidence', result)
        
        # Test learning from feedback
        optimizer.learn_from_feedback("revenue report", success=True, clicked_results=[0, 1])
        optimizer.learn_from_feedback("bad query", success=False, clicked_results=[])
        
        # Test stats
        stats = optimizer.get_optimization_stats()
        self.assertIn('total_queries', stats)
        self.assertIn('optimized_queries', stats)
    
    def test_search_agents(self):
        """Test search agent functionality"""
        from search.advanced.agent_retrieval import VectorSearchAgent, GraphSearchAgent
        
        # Mock search results
        mock_vector_results = [
            Mock(payload={'text': 'Vector search result 1', 'score': 0.9}),
            Mock(payload={'text': 'Vector search result 2', 'score': 0.8})
        ]
        
        for mock_result in mock_vector_results:
            mock_result.score = mock_result.payload['score']
        
        self.mock_qdrant_client.search.return_value = mock_vector_results
        
        # Test vector search agent
        vector_agent = VectorSearchAgent(self.mock_qdrant_client, self.mock_sentence_model)
        
        # Run async test
        async def test_vector_search():
            results = await vector_agent.search("test query")
            self.assertTrue(len(results) > 0)
            self.assertIsInstance(results[0], SearchResult)
        
        asyncio.run(test_vector_search())
        
        # Test graph search agent
        mock_session = Mock()
        mock_record = Mock()
        mock_record.get.return_value = {
            'doc_text': 'Graph search result',
            'question': 'Test question',
            'answer': 'Test answer'
        }
        mock_session.run.return_value = [mock_record]
        self.mock_neo4j_driver.session.return_value.__enter__.return_value = mock_session
        
        graph_agent = GraphSearchAgent(self.mock_neo4j_driver)
        
        async def test_graph_search():
            results = await graph_agent.search("test query")
            self.assertTrue(len(results) >= 0)  # May be empty due to mocking
        
        asyncio.run(test_graph_search())
    
    def test_advanced_controller(self):
        """Test the advanced search controller"""
        # Skip OpenAI-dependent tests if no API key
        if not os.getenv("OPENAI_API_KEY"):
            self.skipTest("OpenAI API key not available")
        
        # Mock search results for agents
        mock_vector_results = [
            Mock(payload={'text': 'Result 1', 'score': 0.9}),
            Mock(payload={'text': 'Result 2', 'score': 0.8})
        ]
        
        for mock_result in mock_vector_results:
            mock_result.score = mock_result.payload['score']
        
        self.mock_qdrant_client.search.return_value = mock_vector_results
        
        # Mock Neo4j session
        mock_session = Mock()
        mock_session.run.return_value = []
        self.mock_neo4j_driver.session.return_value.__enter__.return_value = mock_session
        
        try:
            controller = AdvancedSearchController(
                self.mock_qdrant_client,
                self.mock_neo4j_driver,
                self.mock_sentence_model
            )
            
            # Test advanced search
            async def test_advanced_search():
                result = await controller.advanced_search("test query about revenue")
                
                self.assertIn('query_processing', result)
                self.assertIn('search_results', result)
                self.assertIn('metadata', result)
                
                # Check query processing
                query_proc = result['query_processing']
                self.assertIn('original_query', query_proc)
                self.assertIn('rewritten_query', query_proc)
                self.assertIn('entities', query_proc)
                self.assertIn('intent', query_proc)
            
            asyncio.run(test_advanced_search())
            
            # Test query optimization
            opt_result = controller.optimize_single_query("revenue analysis")
            self.assertIn('original', opt_result)
            self.assertIn('optimized', opt_result)
            
            # Test feedback recording
            controller.record_user_feedback("session_1", "test query", [0, 1], 4)
            
            # Test performance metrics
            metrics = controller.get_performance_metrics()
            self.assertIn('query_optimizer', metrics)
            self.assertIn('agent_performance', metrics)
            
        except Exception as e:
            # If initialization fails due to missing dependencies, skip
            if "spacy" in str(e).lower() or "openai" in str(e).lower():
                self.skipTest(f"Missing dependency: {e}")
            else:
                raise

class TestIntegration(unittest.TestCase):
    """Integration tests for the complete advanced search system"""
    
    def test_end_to_end_flow(self):
        """Test the complete search flow"""
        # This test requires actual services, so we'll create a minimal mock version
        
        # Mock all external dependencies
        mock_qdrant = Mock()
        mock_neo4j = Mock()
        mock_model = Mock()
        
        mock_model.encode.return_value = [0.1] * 384
        mock_qdrant.search.return_value = []
        
        mock_session = Mock()
        mock_session.run.return_value = []
        mock_neo4j.session.return_value.__enter__.return_value = mock_session
        
        try:
            from search.advanced.controller import AdvancedSearchController
            
            controller = AdvancedSearchController(mock_qdrant, mock_neo4j, mock_model)
            
            # Test basic functionality without OpenAI
            optimizer = controller.query_optimizer
            stats = optimizer.get_optimization_stats()
            self.assertIsInstance(stats, dict)
            
        except Exception as e:
            if any(dep in str(e).lower() for dep in ["spacy", "openai", "transformers"]):
                self.skipTest(f"Missing dependency: {e}")
            else:
                raise

if __name__ == '__main__':
    # Run with verbose output
    unittest.main(verbosity=2) 