import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
import pytesseract
from PIL import Image
import numpy as np

from .base import BaseIngestionPipeline, ContentMetadata

class ImageIngestionPipeline(BaseIngestionPipeline):
    """Pipeline for ingesting image content."""
    
    SUPPORTED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif'}
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.ocr_lang = config.get('ocr_lang', 'eng')
        self.min_confidence = config.get('min_confidence', 80)
    
    async def validate(self, content_path: Path) -> bool:
        """Validate if the file is a supported image file."""
        if not content_path.is_file():
            return False
        return content_path.suffix.lower() in self.SUPPORTED_EXTENSIONS
    
    async def extract_metadata(self, content_path: Path) -> ContentMetadata:
        """Extract metadata from the image file."""
        stats = os.stat(content_path)
        image = Image.open(content_path)
        
        metadata = {
            "size_bytes": stats.st_size,
            "extension": content_path.suffix.lower(),
            "dimensions": image.size,
            "mode": image.mode,
            "format": image.format
        }
        
        if hasattr(image, '_getexif') and image._getexif():
            exif = {
                pytesseract.pytesseract.METADATA_KEYS[k]: v
                for k, v in image._getexif().items()
                if k in pytesseract.pytesseract.METADATA_KEYS
            }
            metadata["exif"] = exif
        
        return ContentMetadata(
            content_type="image",
            source_path=str(content_path),
            creation_date=datetime.fromtimestamp(stats.st_ctime).isoformat(),
            modified_date=datetime.fromtimestamp(stats.st_mtime).isoformat(),
            metadata=metadata
        )
    
    async def preprocess(self, content_path: Path) -> Image.Image:
        """Preprocess the image for better OCR results."""
        image = Image.open(content_path)
        
        # Convert to RGB if necessary
        if image.mode not in ('L', 'RGB'):
            image = image.convert('RGB')
        
        # Basic image enhancement could be added here
        # - Contrast adjustment
        # - Noise reduction
        # - Deskewing
        
        return image
    
    async def extract_content(self, preprocessed_content: Image.Image) -> Dict[str, Any]:
        """Extract text and features from the image."""
        # Perform OCR
        ocr_result = pytesseract.image_to_data(
            preprocessed_content,
            lang=self.ocr_lang,
            output_type=pytesseract.Output.DICT
        )
        
        # Filter low-confidence results
        confident_text = [
            word for word, conf in zip(ocr_result['text'], ocr_result['conf'])
            if conf > self.min_confidence and word.strip()
        ]
        
        # Extract image features (could be extended with more sophisticated feature extraction)
        features = self._extract_features(preprocessed_content)
        
        return {
            "extracted_text": " ".join(confident_text),
            "features": features,
            "ocr_confidence": float(np.mean([
                conf for conf in ocr_result['conf']
                if conf > self.min_confidence
            ]))
        }
    
    async def enrich(self, extracted_content: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich the extracted content with additional information."""
        # Here we could add:
        # - Object detection
        # - Scene classification
        # - Face detection (if allowed)
        # - Color analysis
        return {
            **extracted_content,
            "enriched_at": datetime.utcnow().isoformat()
        }
    
    async def cleanup(self) -> None:
        """Cleanup any resources."""
        pass
    
    def _extract_features(self, image: Image.Image) -> Dict[str, Any]:
        """Extract basic image features."""
        # Convert to numpy array
        img_array = np.array(image)
        
        # Calculate basic statistics
        if len(img_array.shape) == 3:  # Color image
            features = {
                "mean_color": img_array.mean(axis=(0, 1)).tolist(),
                "std_color": img_array.std(axis=(0, 1)).tolist(),
            }
        else:  # Grayscale
            features = {
                "mean_intensity": float(img_array.mean()),
                "std_intensity": float(img_array.std()),
            }
        
        features.update({
            "dimensions": image.size,
            "aspect_ratio": image.size[0] / image.size[1],
        })
        
        return features 