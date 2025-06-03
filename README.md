# Multimodal Enterprise RAG System

A robust Retrieval-Augmented Generation (RAG) system designed for enterprise use, supporting multiple modalities including text, images, audio, and video.

## Features

- **Multimodal Processing**
  - Text: Advanced NLP with entity extraction and semantic analysis
  - Images: OCR, captioning, and object detection
  - Audio: Transcription and speaker diarization
  - Video: Frame extraction and scene detection

- **Query Types**
  - Factual queries (direct information lookup)
  - Summarization queries
  - Semantic linkage queries (relationships between entities)
  - Reasoning queries (combining multiple pieces of information)

- **Evaluation Framework**
  - Retrieval quality metrics (precision, recall)
  - Hallucination control
  - Latency monitoring
  - Cross-modal linking accuracy

- **Modular Pipeline**
  - Input validation layer
  - Query preprocessing
  - Retrieval orchestration
  - Answer generation
  - Post-processing and validation

## Prerequisites

- Python 3.8+
- Docker and Docker Compose
- Tesseract OCR
- FFmpeg

### System Dependencies

```bash
# macOS
brew install tesseract ffmpeg

# Ubuntu
sudo apt-get update
sudo apt-get install -y tesseract-ocr ffmpeg
```

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd multimodal-rag
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp config.env.example config.env
# Edit config.env with your settings
```

## Docker Setup

1. Build and start the services:
```bash
docker-compose up -d
```

This will start:
- FastAPI backend (port 8000)
- React frontend (port 3000)
- Qdrant vector store (ports 6333, 6334)
- Neo4j database (ports 7474, 7687)

## Usage

### API Endpoints

- `POST /api/upload`: Upload multimodal content
- `POST /api/query`: Submit queries
- `GET /api/status`: Check system status
- `GET /api/metrics`: Get evaluation metrics

### Query Examples

```python
from src import QueryPipeline, QueryType

# Initialize pipeline
pipeline = QueryPipeline()

# Factual query
result = await pipeline.process_query({
    "text": "What was discussed in the last board meeting?",
    "type": QueryType.FACTUAL
})

# Semantic linkage query
result = await pipeline.process_query({
    "text": "How are Project X and Project Y related?",
    "type": QueryType.SEMANTIC_LINKAGE
})
```

## Development

### Project Structure

```
.
├── src/
│   ├── evaluation/     # Evaluation metrics and framework
│   ├── processors/     # Multimodal content processors
│   ├── query/         # Query pipeline and processing
│   └── storage/       # Vector and graph storage
├── data/
│   ├── uploads/       # Uploaded content
│   ├── processed/     # Processed data
│   └── vector_store/  # Vector store data
├── tests/            # Test suite
└── docker/           # Docker configuration
```

### Running Tests

```bash
pytest tests/
```

### Evaluation

```bash
python -m src.evaluation.run_benchmarks
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 