from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pathlib import Path

class ContentMetadata:
    def __init__(
        self,
        content_type: str,
        source_path: str,
        creation_date: str,
        modified_date: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.content_type = content_type
        self.source_path = source_path
        self.creation_date = creation_date
        self.modified_date = modified_date
        self.metadata = metadata or {}

class BaseIngestionPipeline(ABC):
    """Base class for all content ingestion pipelines."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
    @abstractmethod
    async def validate(self, content_path: Path) -> bool:
        """Validate if the content can be processed by this pipeline."""
        pass
    
    @abstractmethod
    async def extract_metadata(self, content_path: Path) -> ContentMetadata:
        """Extract metadata from the content."""
        pass
    
    @abstractmethod
    async def preprocess(self, content_path: Path) -> Any:
        """Preprocess the content for ingestion."""
        pass
    
    @abstractmethod
    async def extract_content(self, preprocessed_content: Any) -> Dict[str, Any]:
        """Extract the actual content and convert to processable format."""
        pass
    
    @abstractmethod
    async def enrich(self, extracted_content: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich the content with additional information."""
        pass
    
    async def process(self, content_path: Path) -> Dict[str, Any]:
        """Main processing pipeline."""
        if not await self.validate(content_path):
            raise ValueError(f"Content at {content_path} is not valid for this pipeline")
        
        metadata = await self.extract_metadata(content_path)
        preprocessed = await self.preprocess(content_path)
        extracted = await self.extract_content(preprocessed)
        enriched = await self.enrich(extracted)
        
        return {
            "metadata": metadata.__dict__,
            "content": enriched
        }
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup any resources used during processing."""
        pass 