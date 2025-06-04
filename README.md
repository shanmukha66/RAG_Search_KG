# APARAVI Project

## Local Foundations Setup

### 1. Environment Setup
- Python 3.11 (via pyenv or conda)
- Poetry for dependency management
- Create a `.env` file with the following keys:
  ```
  # API Keys
  OPENAI_API_KEY=your_openai_api_key_here
  HUGGINGFACE_API_KEY=your_huggingface_api_key_here
  
  # Service Configuration
  NEO4J_URI=bolt://localhost:7687
  NEO4J_USER=neo4j
  NEO4J_PASSWORD=your_password_here
  
  # Weaviate Configuration
  WEAVIATE_URL=http://localhost:8080
  ```

### 2. Local Services
- Neo4j Desktop for graph database
  - Download and install from [Neo4j Desktop](https://neo4j.com/download/)
  - Create a new project and database
  - Set password in `.env` file
- Weaviate in "bare-metal" mode
  - Download pre-built binary
  - Run as background process or systemd service

### 3. Repository Structure
```
.
├── bash/           # Bash scripts
├── copydist/       # Distribution related files
├── project/        # Main project code
│   ├── ingres/     # Ingestion related code
│   ├── retrieval/  # Retrieval related code
│   └── generation/ # Generation related code
├── eval/           # Evaluation code
├── ui/            # User interface code
└── scripts/       # Utility scripts
```

## Ingestion Pipeline

The ingestion pipeline supports three modalities:

### 1. Text & PDF Processing
- Uses LangChain's PyPDFLoader for PDF processing
- Splits text on headings or 1000-token windows
- Stores chunk metadata (source, page, chunk_id)

### 2. Image Processing
- LLAVA captioning for image understanding
- CLIP zero-shot classifier for tag extraction
- Supports various image formats

### 3. Audio Processing
- Faster-Whisper for transcription
- Extracts word-level timestamps
- Supports multiple languages

### Entity Processing
- Named Entity Recognition (NER) for entity extraction
- Entity deduplication using Levenshtein distance
- Semantic-based entity matching

### Data Storage
- Text chunks stored in Weaviate with embeddings
- Entities and relations stored in Neo4j
- Metadata preserved for all modalities

### Usage Example
```python
from project.ingres import TextProcessor, ImageProcessor, AudioProcessor, EntityProcessor, DataLoader

# Initialize processors
text_processor = TextProcessor()
image_processor = ImageProcessor()
audio_processor = AudioProcessor()
entity_processor = EntityProcessor()
data_loader = DataLoader()

# Process text
chunks = text_processor.process_pdf("document.pdf")
for chunk in chunks:
    # Extract entities
    entities = entity_processor.extract_entities(chunk['text'])
    entities = entity_processor.deduplicate_entities(entities)
    
    # Store data
    data_loader.store_chunk(chunk['text'], chunk['metadata'], chunk['metadata']['source'])
    for entity in entities:
        data_loader.store_entity(entity)

# Process image
image_info = image_processor.process_image("image.jpg")
for tag in image_info['tags']:
    if tag['confidence'] > 0.5:
        data_loader.store_entity({
            'word': tag['tag'],
            'entity': 'IMAGE_TAG',
            'confidence': tag['confidence']
        })

# Process audio
audio_info = audio_processor.transcribe("audio.mp3")
for segment in audio_info['segments']:
    data_loader.store_chunk(
        segment['text'],
        {'start': segment['start'], 'end': segment['end']},
        audio_info['metadata']['source']
    )
```

### Getting Started

1. Clone the repository
2. Install Python 3.11
3. Install Poetry:
   ```bash
   pip install poetry
   ```
4. Install dependencies:
   ```bash
   poetry install
   ```
5. Set up your `.env` file with appropriate API keys and configurations
6. Install and configure Neo4j Desktop
7. Download and run Weaviate

### Development

To activate the virtual environment:
```bash
poetry shell
```

To add new dependencies:
```bash
poetry add package-name
``` 