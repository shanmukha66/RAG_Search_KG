from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv
import os

def load_config() -> Dict[str, Any]:
    """Load configuration from environment variables."""
    # Load environment variables from config.env
    env_path = Path(__file__).parent / "config.env"
    load_dotenv(env_path)
    
    # Create required directories
    for dir_path in [
        os.getenv("VECTOR_STORE_DIR", "./data/vector_store"),
        os.getenv("TEMP_STORAGE_DIR", "./data/temp"),
        os.getenv("PROCESSED_STORAGE_DIR", "./data/processed"),
        os.path.dirname(os.getenv("LOG_FILE", "./logs/app.log"))
    ]:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    return {
        "neo4j": {
            "uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            "user": os.getenv("NEO4J_USER", "neo4j"),
            "password": os.getenv("NEO4J_PASSWORD", "your_password")
        },
        "vector_store": {
            "dir": os.getenv("VECTOR_STORE_DIR", "./data/vector_store")
        },
        "api": {
            "secret_key": os.getenv("API_SECRET_KEY", "your_secret_key_here"),
            "access_token_expire_minutes": int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
        },
        "ocr": {
            "lang": os.getenv("TESSERACT_LANG", "eng")
        },
        "storage": {
            "temp_dir": os.getenv("TEMP_STORAGE_DIR", "./data/temp"),
            "processed_dir": os.getenv("PROCESSED_STORAGE_DIR", "./data/processed")
        },
        "logging": {
            "level": os.getenv("LOG_LEVEL", "INFO"),
            "file": os.getenv("LOG_FILE", "./logs/app.log")
        }
    }

# Global configuration instance
config = load_config() 