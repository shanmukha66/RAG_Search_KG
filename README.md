# Multimodal Enterprise RAG System

A sophisticated Retrieval-Augmented Generation (RAG) system that supports text, image, audio, and video ingestion, builds a searchable knowledge graph, and enables hybrid search using keyword and vector retrieval.

## Features

- Multi-modal content ingestion (text, image, audio, video)
- Knowledge graph construction using Neo4j
- Hybrid search combining structured graph traversal and semantic vector retrieval
- Support for various query types (factual, lookup, reasoning)
- Real-time feedback and query improvement
- Security-aware design with access control
- Modular and scalable pipeline architecture

## System Requirements

- Python 3.9+
- Neo4j Database
- GPU recommended for optimal performance
- FFmpeg for video/audio processing
- Tesseract OCR for image text extraction

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Environment Configuration:
- Copy `.env.example` to `.env`
- Configure your API keys and database credentials

## Project Structure

```
.
├── src/
│   ├── ingestion/         # Content ingestion pipelines
│   ├── processing/        # Content processing and enrichment
│   ├── storage/           # Vector store and knowledge graph
│   ├── retrieval/         # Search and retrieval logic
│   ├── api/              # FastAPI endpoints
│   └── utils/            # Helper functions
├── tests/                # Test suite
├── config/              # Configuration files
└── examples/            # Usage examples
```

## Getting Started

[Documentation to be added as the project develops]

## Testing

```bash
pytest tests/
```

## License

[License information to be added] 