import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from .base import BaseIngestionPipeline, ContentMetadata

class TextIngestionPipeline(BaseIngestionPipeline):
    """Pipeline for ingesting text content."""
    
    SUPPORTED_EXTENSIONS = {'.txt', '.md', '.rst', '.json', '.csv'}
    
    async def validate(self, content_path: Path) -> bool:
        """Validate if the file is a supported text file."""
        if not content_path.is_file():
            return False
        return content_path.suffix.lower() in self.SUPPORTED_EXTENSIONS
    
    async def extract_metadata(self, content_path: Path) -> ContentMetadata:
        """Extract metadata from the text file."""
        stats = os.stat(content_path)
        return ContentMetadata(
            content_type="text",
            source_path=str(content_path),
            creation_date=datetime.fromtimestamp(stats.st_ctime).isoformat(),
            modified_date=datetime.fromtimestamp(stats.st_mtime).isoformat(),
            metadata={
                "size_bytes": stats.st_size,
                "extension": content_path.suffix.lower()
            }
        )
    
    async def preprocess(self, content_path: Path) -> str:
        """Read and preprocess the text content."""
        with open(content_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content.strip()
    
    async def extract_content(self, preprocessed_content: str) -> Dict[str, Any]:
        """Extract and structure the text content."""
        # Split into chunks for better processing
        chunks = self._chunk_text(preprocessed_content)
        
        return {
            "raw_text": preprocessed_content,
            "chunks": chunks,
            "char_count": len(preprocessed_content),
            "word_count": len(preprocessed_content.split())
        }
    
    async def enrich(self, extracted_content: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich the text content with additional information."""
        # Here we could add:
        # - Language detection
        # - Named entity recognition
        # - Topic modeling
        # - Sentiment analysis
        # For now, we'll keep it simple
        return {
            **extracted_content,
            "enriched_at": datetime.utcnow().isoformat()
        }
    
    async def cleanup(self) -> None:
        """No cleanup needed for basic text processing."""
        pass
    
    def _chunk_text(self, text: str, chunk_size: int = 1000) -> list[str]:
        """Split text into chunks of approximately equal size."""
        words = text.split()
        chunks = []
        current_chunk = []
        current_size = 0
        
        for word in words:
            word_size = len(word) + 1  # +1 for space
            if current_size + word_size > chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_size = word_size
            else:
                current_chunk.append(word)
                current_size += word_size
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks 