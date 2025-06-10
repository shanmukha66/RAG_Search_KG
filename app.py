from flask import Flask, render_template, request, jsonify, send_from_directory, url_for
from qdrant_client import QdrantClient
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer
from openai import OpenAI
import os
import time
from dotenv import load_dotenv
import json
from qdrant_client.models import Distance, VectorParams
from evaluation.metrics import RAGEvaluator

# Load environment variables
load_dotenv()

app = Flask(__name__)

def initialize_services():
    """Initialize all required services"""
    global qdrant_client, neo4j_driver, model, openai_client
    
    try:
        # Connect to existing Qdrant server
        qdrant_client = QdrantClient(
            host=os.getenv("QDRANT_HOST", "localhost"),
            port=int(os.getenv("QDRANT_PORT", 6333))
        )
        
        # Connect to Neo4j
        neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
        neo4j_driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        
        # Initialize SentenceTransformer model
        model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Initialize OpenAI client
        openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        print("✅ Successfully initialized all services")
        return True
    except Exception as e:
        print(f"❌ Error initializing services: {e}")
        return False

@app.route('/')
def home():
    return render_template('index.html')

def search_qdrant(query, limit=5):
    try:
        # Generate query embedding
        query_vector = model.encode(query).tolist()
        
        # Search in Qdrant
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
                    'relevance_score': '0.0%'
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
        
        # Calculate metrics
        end_time = time.time()
        latency = (end_time - start_time) * 1000  # Convert to milliseconds
        
        # Calculate simple relevance score based on number of results
        total_results = len(vector_results) + len(graph_results)
        relevance_score = min(total_results * 0.1, 1.0)  # 10% per result, max 100%
        
        # Add image serving URL to results
        for result in vector_results + graph_results:
            if result.get('image_path'):
                result['image_url'] = url_for('serve_image', filename=os.path.basename(result['image_path']), _external=True)
        
        return jsonify({
            'vector_results': vector_results,
            'graph_results': graph_results,
            'ai_response': ai_response,
            'metrics': {
                'latency': f"{latency:.2f}ms",
                'relevance_score': f"{relevance_score:.1%}"
            }
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
                'relevance_score': '0.0%'
            }
        }), 500

@app.route('/metrics', methods=['GET'])
def get_metrics():
    try:
        return jsonify({
            'average_metrics': evaluator.get_average_metrics(),
            'total_queries': len(evaluator.results_history)
        })
    except Exception as e:
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