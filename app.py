from flask import Flask, render_template, request, jsonify, send_from_directory, url_for
from qdrant_client import QdrantClient
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer
from openai import OpenAI
import os
import time
import functools
from dotenv import load_dotenv

# Suppress tokenizer warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"
import json
from qdrant_client.models import Distance, VectorParams
from evaluation.metrics import RAGEvaluator
from search.advanced.controller import AdvancedSearchController
import uuid

# Import monitoring and error handling
from monitoring import (
    setup_logging, get_logger, get_performance_logger,
    ErrorHandler, handle_errors, RetryConfig, FallbackConfig,
    HealthChecker, SystemStateRecovery, RecoveryPlan, RecoveryAction,
    MetricsCollector, set_log_context, log_api_request, log_error_with_context
)

# Load environment variables
load_dotenv()

# Initialize logging and monitoring
setup_logging(
    log_level=os.getenv("LOG_LEVEL", "WARNING"),  # Changed to WARNING to reduce noise
    enable_json=False,  # Human readable format for console
    enable_file=True,
    enable_console=True
)

app = Flask(__name__)

# Initialize monitoring components
logger = get_logger(__name__)
perf_logger = get_performance_logger()
metrics_collector = MetricsCollector()
health_checker = HealthChecker()
state_recovery = SystemStateRecovery()

# Initialize evaluator
evaluator = RAGEvaluator()

# Initialize advanced search controller (will be set in initialize_services)
advanced_controller = None

@handle_errors(
    retry_config=RetryConfig(max_attempts=3, delay=2.0),
    fallback_config=FallbackConfig(default_value=False)
)
def initialize_services():
    """Initialize all required services"""
    global qdrant_client, neo4j_driver, model, openai_client, advanced_controller
    
    with perf_logger.log_operation("service_initialization"):
        try:
            # Connect to existing Qdrant server
            print("🔗 Connecting to Qdrant...")
            qdrant_client = QdrantClient(
                host=os.getenv("QDRANT_HOST", "localhost"),
                port=int(os.getenv("QDRANT_PORT", 6333))
            )
            
            # Connect to Neo4j
            print("🔗 Connecting to Neo4j...")
            neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
            neo4j_user = os.getenv("NEO4J_USER", "neo4j")
            neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
            neo4j_driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
            
            # Initialize SentenceTransformer model
            print("🤖 Loading AI models...")
            model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Initialize OpenAI client
            openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            # Initialize Advanced Search Controller
            print("⚙️  Setting up advanced search...")
            advanced_controller = AdvancedSearchController(qdrant_client, neo4j_driver, model)
            
            # Register health checks
            _register_health_checks()
            
            # Register services for recovery
            _register_recovery_services()
            
            # Start monitoring
            print("📊 Starting monitoring systems...")
            health_checker.start_monitoring()
            state_recovery.start_monitoring()
            
            print("✅ RAG Search System Ready!")
            print("🌐 Server will start at http://localhost:5001")
            return True
        except Exception as e:
            log_error_with_context(logger, e, "service_initialization")
            return False

def _register_health_checks():
    """Register health checks for all services"""
    # Qdrant health check
    health_checker.register_check(
        "qdrant",
        lambda: health_checker.check_vector_database(qdrant_client),
        critical=True
    )
    
    # Neo4j health check
    health_checker.register_check(
        "neo4j",
        lambda: health_checker.check_database_connection(neo4j_driver),
        critical=True
    )
    
    # Log files health check
    health_checker.register_check(
        "log_files",
        lambda: health_checker.check_log_files(),
        critical=False
    )

def _register_recovery_services():
    """Register services for automatic recovery"""
    # Qdrant recovery plan
    qdrant_plan = RecoveryPlan(
        service_name="qdrant",
        actions=[RecoveryAction.RESET_CONNECTION, RecoveryAction.RESTART_SERVICE],
        max_attempts=3,
        timeout=30.0
    )
    
    state_recovery.register_service(
        "qdrant",
        health_check_func=lambda: _check_qdrant_health(),
        recovery_plan=qdrant_plan
    )
    
    # Neo4j recovery plan
    neo4j_plan = RecoveryPlan(
        service_name="neo4j",
        actions=[RecoveryAction.RESET_CONNECTION, RecoveryAction.RESTART_SERVICE],
        max_attempts=3,
        timeout=30.0
    )
    
    state_recovery.register_service(
        "neo4j",
        health_check_func=lambda: _check_neo4j_health(),
        recovery_plan=neo4j_plan
    )

def _check_qdrant_health():
    """Check Qdrant health"""
    try:
        qdrant_client.get_collections()
        return True
    except:
        return False

def _check_neo4j_health():
    """Check Neo4j health"""
    try:
        with neo4j_driver.session() as session:
            session.run("RETURN 1")
        return True
    except:
        return False

def monitor_request(func):
    """Decorator to monitor API requests"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        # Set logging context
        set_log_context(
            request_id=request_id,
            user_id=request.headers.get('X-User-ID'),
            component='api'
        )
        
        # Log request
        log_api_request(
            logger,
            request.method,
            request.path,
            request.headers.get('X-User-ID')
        )
        
        try:
            # Execute request
            response = func(*args, **kwargs)
            duration = time.time() - start_time
            
            # Record metrics
            status_code = getattr(response, 'status_code', 200)
            metrics_collector.record_request(
                request.method,
                request.path,
                status_code,
                duration
            )
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            
            # Record error metrics
            metrics_collector.record_error(
                type(e).__name__,
                str(e),
                'api'
            )
            
            # Log error
            log_error_with_context(logger, e, f"{request.method} {request.path}")
            
            # Record failed request
            metrics_collector.record_request(
                request.method,
                request.path,
                500,
                duration
            )
            
            raise
    
    return wrapper

@app.route('/')
@monitor_request
def home():
    return render_template('enhanced_ui.html')

@app.route('/basic')
@monitor_request
def basic_ui():
    return render_template('index.html')

def search_qdrant(query, limit=5):
    try:
        # Generate query embedding
        query_vector = model.encode(query).tolist()
        
        # Search in Qdrant (using deprecated method - will fix later)
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            search_result = qdrant_client.search(
                collection_name="documents",
                query_vector=query_vector,
                limit=limit,
                with_payload=True,
                with_vectors=False
            )
        
        # Process and validate results
        processed_results = []
        for hit in search_result:
            if hit.payload:
                processed_results.append({
                    'score': float(hit.score),
                    'text': str(hit.payload.get('text', '')),
                    'question': str(hit.payload.get('question', '')),
                    'answer': str(hit.payload.get('answer', '')),
                    'doc_id': str(hit.payload.get('doc_id', '')),
                    'image_path': str(hit.payload.get('image_path', ''))
                })
        return processed_results
    except Exception as e:
        print(f"Error in Qdrant search: {str(e)}")
        return []

def search_neo4j(query_text):
    try:
        with neo4j_driver.session() as session:
            # Fixed query that properly handles DISTINCT and ORDER BY
            cypher_query = """
            MATCH (d:Document)-[r:HAS_QUESTION]->(q:Question)
            WHERE toLower(q.text) CONTAINS toLower($query_text)
               OR toLower(d.text) CONTAINS toLower($query_text)
            WITH d, q, toLower(q.text) CONTAINS toLower($query_text) as exact_match
            ORDER BY exact_match DESC
            LIMIT 5
            RETURN DISTINCT {
                doc_id: d.id,
                doc_text: d.text,
                question: q.text,
                answer: q.answer,
                image_path: d.image_path
            } as result
            """
            result = session.run(cypher_query, query_text=query_text)
            
            # Process and validate results
            processed_results = []
            for record in result:
                result_dict = record.get('result', {})
                processed_results.append({
                    'doc_id': str(result_dict.get('doc_id', '')),
                    'doc_text': str(result_dict.get('doc_text', '')),
                    'question': str(result_dict.get('question', '')),
                    'answer': str(result_dict.get('answer', '')),
                    'image_path': str(result_dict.get('image_path', ''))
                })
            return processed_results
    except Exception as e:
        print(f"Error in Neo4j search: {str(e)}")
        return []

def generate_ai_response(query, vector_results, graph_results):
    """Generate AI response based on search results"""
    try:
        # Combine context from both vector and graph results
        context = []
        
        # Add vector search results to context
        for result in vector_results[:2]:  # Limit to top 2 results
            if result.get('text'):
                context.append(f"Document text: {result['text']}")
            if result.get('question'):
                context.append(f"Question: {result['question']}")
            if result.get('answer'):
                context.append(f"Answer: {result['answer']}")
        
        # Add graph search results to context
        for result in graph_results[:2]:  # Limit to top 2 results
            if result.get('doc_text'):
                context.append(f"Document text: {result['doc_text']}")
            if result.get('question'):
                context.append(f"Question: {result['question']}")
            if result.get('answer'):
                context.append(f"Answer: {result['answer']}")
        
        # If no context available, return default message
        if not context:
            return "I couldn't find any relevant information to answer your question."
        
        # Prepare messages for OpenAI
        messages = [
            {"role": "system", "content": "You are a helpful assistant that answers questions based on the provided context. Keep your answers concise and relevant."},
            {"role": "user", "content": f"Based on the following context, answer this question: {query}\n\nContext:\n" + "\n".join(context)}
        ]
        
        # Get response from OpenAI
        try:
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=150,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            # Fallback to simple response based on available information
            if context:
                return f"Based on the available information: {context[0]}"
            return "I apologize, but I couldn't generate a detailed response at this time."
            
    except Exception as e:
        print(f"Error generating AI response: {e}")
        return "I apologize, but I couldn't generate a response at this time."

@app.route('/images/<path:filename>')
def serve_image(filename):
    # Serve images from the spdocvqa_images directory
    return send_from_directory('spdocvqa_images', filename)

@app.route('/search', methods=['POST'])
@monitor_request
@handle_errors(
    fallback_config=FallbackConfig(default_value={
        'error': 'Search service temporarily unavailable',
        'vector_results': [],
        'graph_results': [],
        'ai_response': 'Search service is currently unavailable. Please try again later.',
        'metrics': {'latency': '0ms', 'relevance_score': '0.0%', 'hallucination_score': '0.0%'}
    })
)
def search():
    try:
        # Get query from form data
        query = request.form.get('query', '')
        if not query:
            return jsonify({
                'error': 'No query provided',
                'vector_results': [],
                'graph_results': [],
                'ai_response': 'Please provide a search query.',
                'metrics': {
                    'latency': '0ms',
                    'relevance_score': '0.0%',
                    'hallucination_score': '0.0%'
                }
            })
        
        # Start timing
        start_time = time.time()
        
        # Get vector search results
        vector_results = search_qdrant(query)
        
        # Get graph search results
        graph_results = search_neo4j(query)
        
        # Generate AI response
        ai_response = generate_ai_response(query, vector_results, graph_results)
        
        # End timing
        end_time = time.time()
        
        # Get context for evaluation
        context = []
        for result in vector_results + graph_results:
            if result.get('text'):
                context.append(result['text'])
            if result.get('doc_text'):
                context.append(result['doc_text'])
        
        # Evaluate response using RAGEvaluator
        eval_metrics = evaluator.evaluate_response(
            query=query,
            response=ai_response,
            context=context,
            start_time=start_time,
            end_time=end_time
        )
        
        # Format metrics for response
        metrics = {
            'latency': f"{eval_metrics.get('latency', 0)*1000:.2f}ms",
            'relevance_score': f"{eval_metrics.get('relevance', 0)*100:.1f}%",
            'hallucination_score': f"{eval_metrics.get('hallucination_score', 0.5)*100:.1f}%"
        }
        
        # Record search metrics
        search_duration = end_time - start_time
        total_results = len(vector_results) + len(graph_results)
        metrics_collector.record_search_metrics(
            query,
            total_results,
            search_duration,
            'standard'
        )
        
        # Add image serving URL to results
        for result in vector_results + graph_results:
            if result.get('image_path'):
                result['image_url'] = url_for('serve_image', filename=os.path.basename(result['image_path']), _external=True)
        
        return jsonify({
            'vector_results': vector_results,
            'graph_results': graph_results,
            'ai_response': ai_response,
            'metrics': metrics
        })
    except Exception as e:
        print(f"Error in search endpoint: {str(e)}")
        return jsonify({
            'error': str(e),
            'vector_results': [],
            'graph_results': [],
            'ai_response': 'An error occurred while processing your request.',
            'metrics': {
                'latency': '0ms',
                'relevance_score': '0.0%',
                'hallucination_score': '0.0%'
            }
        }), 500

@app.route('/search_advanced', methods=['POST'])
def search_advanced():
    """Advanced search endpoint with all enhancements"""
    try:
        # Get query from form data
        query = request.form.get('query', '')
        session_id = request.form.get('session_id', str(uuid.uuid4()))
        
        if not query:
            return jsonify({
                'error': 'No query provided',
                'search_results': [],
                'metadata': {'processing_time': 0}
            })
        
        # Use advanced search if available
        if advanced_controller:
            import asyncio
            result = asyncio.run(advanced_controller.advanced_search(query, session_id))
            return jsonify(result)
        else:
            return jsonify({
                'error': 'Advanced search not available',
                'search_results': [],
                'metadata': {'processing_time': 0}
            })
            
    except Exception as e:
        print(f"Error in advanced search endpoint: {str(e)}")
        return jsonify({
            'error': str(e),
            'search_results': [],
            'metadata': {'processing_time': 0}
        }), 500

@app.route('/query_optimize', methods=['POST'])
def optimize_query():
    """Endpoint to optimize a query without performing search"""
    try:
        query = request.form.get('query', '')
        if not query:
            return jsonify({'error': 'No query provided'})
        
        if advanced_controller:
            result = advanced_controller.optimize_single_query(query)
            return jsonify(result)
        else:
            return jsonify({'error': 'Advanced search not available'})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/feedback', methods=['POST'])
def record_feedback():
    """Record user feedback for learning"""
    try:
        data = request.get_json()
        session_id = data.get('session_id', '')
        query = data.get('query', '')
        clicked_results = data.get('clicked_results', [])
        satisfaction = data.get('satisfaction', None)
        
        if advanced_controller and session_id and query:
            advanced_controller.record_user_feedback(
                session_id, query, clicked_results, satisfaction
            )
            return jsonify({'status': 'success'})
        else:
            return jsonify({'error': 'Missing required data'})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/performance_metrics', methods=['GET'])
def get_performance_metrics():
    """Get advanced search performance metrics"""
    try:
        if advanced_controller:
            metrics = advanced_controller.get_performance_metrics()
            return jsonify(metrics)
        else:
            return jsonify({'error': 'Advanced search not available'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/metrics', methods=['GET'])
@monitor_request
def get_metrics():
    try:
        return jsonify({
            'average_metrics': evaluator.get_average_metrics(),
            'total_queries': len(evaluator.results_history)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
@monitor_request
def health_check():
    """Comprehensive health check endpoint"""
    try:
        health_summary = health_checker.get_health_summary()
        
        # Determine HTTP status code based on health
        if health_summary['overall_status'] == 'healthy':
            status_code = 200
        elif health_summary['overall_status'] == 'degraded':
            status_code = 207  # Multi-Status
        else:
            status_code = 503  # Service Unavailable
        
        return jsonify(health_summary), status_code
        
    except Exception as e:
        log_error_with_context(logger, e, "health_check")
        return jsonify({
            'overall_status': 'unhealthy',
            'overall_message': 'Health check system failure',
            'error': str(e)
        }), 503

@app.route('/system/status', methods=['GET'])
@monitor_request
def system_status():
    """System status and recovery information"""
    try:
        return jsonify(state_recovery.get_system_status())
    except Exception as e:
        log_error_with_context(logger, e, "system_status")
        return jsonify({'error': str(e)}), 500

@app.route('/system/metrics', methods=['GET'])
@monitor_request
def system_metrics():
    """Detailed system metrics"""
    try:
        time_window = int(request.args.get('window', 300))  # 5 minutes default
        
        return jsonify({
            'system_health': metrics_collector.get_system_health_metrics(),
            'performance_report': metrics_collector.get_performance_report(time_window),
            'metric_summaries': {
                name: summary.__dict__ 
                for name, summary in metrics_collector.get_all_metrics_summary(time_window).items()
            }
        })
    except Exception as e:
        log_error_with_context(logger, e, "system_metrics")
        return jsonify({'error': str(e)}), 500

@app.route('/system/errors', methods=['GET'])
@monitor_request
def system_errors():
    """Error statistics and recent errors"""
    try:
        from monitoring.error_handler import error_handler
        
        error_stats = error_handler.get_error_stats()
        
        # Format recent errors for response
        recent_errors = []
        for error in error_stats.get('recent_errors', [])[-20:]:  # Last 20 errors
            recent_errors.append({
                'timestamp': error.timestamp,
                'error_type': error.error_type,
                'message': error.message,
                'category': error.category.value,
                'severity': error.severity.value,
                'user_id': error.user_id,
                'session_id': error.session_id
            })
        
        return jsonify({
            'total_errors': error_stats['total_errors'],
            'errors_by_category': error_stats['errors_by_category'],
            'errors_by_severity': error_stats['errors_by_severity'],
            'recent_errors': recent_errors
        })
        
    except Exception as e:
        log_error_with_context(logger, e, "system_errors")
        return jsonify({'error': str(e)}), 500

@app.route('/system/recovery', methods=['POST'])
@monitor_request
def trigger_recovery():
    """Manually trigger service recovery"""
    try:
        service_name = request.json.get('service_name')
        if not service_name:
            return jsonify({'error': 'service_name required'}), 400
        
        success = state_recovery.recover_service(service_name)
        
        return jsonify({
            'service': service_name,
            'recovery_triggered': True,
            'success': success,
            'message': f"Recovery {'successful' if success else 'failed'} for {service_name}"
        })
        
    except Exception as e:
        log_error_with_context(logger, e, "trigger_recovery")
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    try:
        # Initialize services
        if initialize_services():
            # Run Flask app with host set to 0.0.0.0 to allow external access
            app.run(host='0.0.0.0', port=5001, debug=True)
        else:
            print("❌ Failed to initialize services. Server not started.")
    except Exception as e:
        print(f"Error starting server: {e}") 