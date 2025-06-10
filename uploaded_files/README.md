# Document Search & QA System with RAG

[![Watch the Demo Video](https://img.youtube.com/vi/YOUR_VIDEO_ID/0.jpg)](https://www.youtube.com/watch?v=YOUR_VIDEO_ID)

*👆 Click the image above to watch the demo video (Update VIDEO_ID with your YouTube video ID)*

## Overview

This project implements a powerful Document Search and Question-Answering system using Retrieval-Augmented Generation (RAG). It combines vector search (Qdrant), graph database (Neo4j), and large language models (OpenAI) to provide accurate answers to questions about your documents.

### Key Features

- 🔍 Hybrid Search System (Vector + Graph)
- 🖼️ Image Support and Visualization
- 🤖 AI-Powered Question Answering
- 📊 Real-time Performance Metrics
- 🌐 Modern Web Interface
- 🚀 Parallel Processing for Data Ingestion

## System Architecture

The system consists of three main components:

1. **Vector Search (Qdrant)**
   - Stores document embeddings for semantic search
   - Enables finding similar documents based on meaning

2. **Graph Database (Neo4j)**
   - Stores relationships between documents and questions
   - Enables traversing document-question relationships

3. **Language Model Integration (OpenAI)**
   - Generates human-like responses
   - Combines information from multiple sources

## Prerequisites

- Python 3.8+
- Docker and Docker Compose
- 16GB RAM (minimum)
- 50GB free disk space
- NVIDIA GPU (optional, for faster embedding generation)

## Installation

1. **Clone the Repository**
   ```bash
   git clone <your-repo-url>
   cd RAG_Search_KG
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up Environment Variables**
   Create a `.env` file in the project root:
   ```env
   OPENAI_API_KEY=your_openai_api_key
   QDRANT_HOST=localhost
   QDRANT_PORT=6333
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=password
   ```

5. **Start Docker Services**
   ```bash
   docker-compose up -d
   ```

## Data Preparation and Ingestion

1. **Prepare Your Data**
   - Place your images in `spdocvqa_images/`
   - Ensure you have:
     - `qa_data.json`: Question-answer pairs
     - `ocr_data.json`: OCR text from documents
     - `vector_chunks.json`: Chunked text for vector search

2. **Initialize Vector Database**
   ```bash
   python init_qdrant.py
   ```

3. **Initialize Graph Database**
   ```bash
   python init_neo4j.py
   ```

## Running the Application

1. **Start the Flask Server**
   ```bash
   python app.py
   ```

2. **Access the Web Interface**
   Open your browser and navigate to:
   ```
   http://localhost:5001
   ```

## Project Structure

```
RAG_Search_KG/
├── app.py                    # Main Flask application
├── init_qdrant.py           # Qdrant initialization and data ingestion
├── init_neo4j.py            # Neo4j initialization and data ingestion
├── docker-compose.yml       # Docker services configuration
├── requirements.txt         # Python dependencies
├── templates/              # HTML templates
│   └── index.html          # Main web interface
├── spdocvqa_images/        # Document images
├── evaluation/             # Evaluation metrics
└── README.md              # This file
```

## API Endpoints

### 1. Search Endpoint
- **URL**: `/search`
- **Method**: `POST`
- **Form Data**:
  ```json
  {
    "query": "your search query"
  }
  ```
- **Response**:
  ```json
  {
    "vector_results": [...],
    "graph_results": [...],
    "ai_response": "...",
    "metrics": {
      "latency": "123.45ms",
      "relevance_score": "85.0%"
    }
  }
  ```

### 2. Image Serving Endpoint
- **URL**: `/images/<filename>`
- **Method**: `GET`
- **Response**: Image file

## Performance Optimization

The system uses several optimization techniques:

1. **Parallel Processing**
   - Multi-threaded data ingestion
   - Batch processing for database operations

2. **Caching**
   - Document embeddings are pre-computed
   - Database indexes for faster queries

3. **Error Handling**
   - Automatic retry mechanism
   - Graceful degradation

## Troubleshooting

### Common Issues

1. **Port 5000 Already in Use (MacOS)**
   ```bash
   # Solution: Use port 5001 instead (already configured)
   # Or disable AirPlay Receiver in System Preferences
   ```

2. **Neo4j Connection Issues**
   ```bash
   # Check if Neo4j is running
   docker ps | grep neo4j
   # Reset Neo4j if needed
   docker-compose restart neo4j
   ```

3. **Qdrant Connection Issues**
   ```bash
   # Check Qdrant logs
   docker logs rag_search_kg_qdrant_1
   ```

### Memory Usage

- Vector Search: ~4GB RAM
- Graph Database: ~2GB RAM
- Flask Application: ~1GB RAM

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- OpenAI for GPT models
- Qdrant team for vector database
- Neo4j team for graph database
- SentenceTransformers team for embeddings

## Contact

For questions and support, please open an issue in the GitHub repository.

---

[⭐ Star this repo](https://github.com/your-username/RAG_Search_KG) if you find it helpful! 