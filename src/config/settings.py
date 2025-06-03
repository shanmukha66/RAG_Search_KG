from pathlib import Path
from typing import Dict, Any
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Settings
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

# Database Settings
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

# Model Settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")

# Storage Settings
BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads")))
MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", "104857600"))  # 100MB in bytes

# Processing Settings
TEXT_CHUNK_SIZE = int(os.getenv("TEXT_CHUNK_SIZE", "1000"))
TEXT_CHUNK_OVERLAP = int(os.getenv("TEXT_CHUNK_OVERLAP", "200"))
IMAGE_MAX_SIZE = tuple(map(int, os.getenv("IMAGE_MAX_SIZE", "1920,1080").split(",")))
VIDEO_MAX_LENGTH = int(os.getenv("VIDEO_MAX_LENGTH", "300"))  # seconds
AUDIO_MAX_LENGTH = int(os.getenv("AUDIO_MAX_LENGTH", "300"))  # seconds

# Search Settings
MAX_SEARCH_RESULTS = int(os.getenv("MAX_SEARCH_RESULTS", "10"))
MIN_SIMILARITY_SCORE = float(os.getenv("MIN_SIMILARITY_SCORE", "0.7"))

# Monitoring Settings
ENABLE_PROMETHEUS = os.getenv("ENABLE_PROMETHEUS", "True").lower() == "true"
PROMETHEUS_PORT = int(os.getenv("PROMETHEUS_PORT", "9090"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Model Configurations
MODEL_CONFIGS: Dict[str, Any] = {
    "text": {
        "embedding_model": "all-MiniLM-L6-v2",
        "classification_model": "facebook/bart-large-mnli",
        "ner_model": "en_core_web_sm",
    },
    "image": {
        "captioning_model": "Salesforce/blip-image-captioning-large",
        "object_detection_model": "facebook/detr-resnet-50",
        "ocr_engine": "tesseract",
    },
    "audio": {
        "transcription_model": "openai/whisper-base",
        "speaker_diarization": "pyannote/speaker-diarization",
    },
    "video": {
        "scene_detection": "opencv",
        "frame_extraction_rate": 1,  # frames per second
    }
} 