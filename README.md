# Multimodal Enterprise RAG System

A powerful Retrieval-Augmented Generation system that supports multiple content types (text, image, audio, video) with a modular pipeline architecture.

## Features

- **Multiple Content Types Support**:
  - Text: Entity extraction, embedding generation, document classification
  - Image: OCR, captioning, object detection
  - Audio: Transcription, speaker diarization
  - Video: Frame extraction, scene detection, combined audio-visual analysis

- **Advanced Search Capabilities**:
  - Hybrid search combining vector and graph approaches
  - Multi-modal content retrieval
  - Entity-based filtering

- **Modern Tech Stack**:
  - FastAPI backend
  - React frontend with Material-UI
  - Qdrant vector store
  - Neo4j graph database

## Prerequisites

- Docker and Docker Compose
- Python 3.9+
- Node.js 18+
- HuggingFace API key

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd <repository-name>
```

2. Create and configure environment variables:
```bash
# Create .env file with the following variables:

# API Settings
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=True

# Database Settings
QDRANT_HOST=qdrant
QDRANT_PORT=6333
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Model Settings
HUGGINGFACE_API_KEY=your_huggingface_api_key_here

# Storage Settings
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE=104857600  # 100MB in bytes

# Processing Settings
TEXT_CHUNK_SIZE=1000
TEXT_CHUNK_OVERLAP=200
IMAGE_MAX_SIZE=1920,1080
VIDEO_MAX_LENGTH=300  # seconds
AUDIO_MAX_LENGTH=300  # seconds

# Search Settings
MAX_SEARCH_RESULTS=10
MIN_SIMILARITY_SCORE=0.7

# Monitoring Settings
ENABLE_PROMETHEUS=True
PROMETHEUS_PORT=9090
LOG_LEVEL=INFO
```

3. Build and start the services:
```bash
docker-compose up --build
```

4. Access the applications:
- Frontend: http://localhost:3000
- API Documentation: http://localhost:8000/docs
- Neo4j Browser: http://localhost:7474
- Qdrant Dashboard: http://localhost:6333/dashboard

## Development

### Backend Development

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Run the FastAPI application:
```bash
python run.py
```

### Frontend Development

1. Install Node.js dependencies:
```bash
cd frontend
npm install
```

2. Start the development server:
```bash
npm start
```

## Project Structure

```
.
├── src/
│   ├── api/              # FastAPI application
│   ├── processors/       # Content processors
│   ├── storage/         # Database interfaces
│   ├── search/          # Search implementations
│   ├── config/          # Configuration
│   └── ingestion/       # Ingestion pipelines
├── frontend/           # React application
├── tests/             # Test suite
├── docker/            # Docker configurations
├── uploads/           # Upload directory
└── models/            # Cached ML models
```

## API Endpoints

- `POST /upload/`: Upload and process files
- `POST /search/`: Search across all content types
- `GET /health/`: Health check endpoint

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 