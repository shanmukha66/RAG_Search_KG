from typing import Dict, Any, List
import io
import numpy as np
from PIL import Image
import pytesseract
from transformers import (
    BlipProcessor,
    BlipForConditionalGeneration,
    DetrImageProcessor,
    DetrForObjectDetection
)
import torch
from ..config.settings import MODEL_CONFIGS, IMAGE_MAX_SIZE

class ImageProcessor:
    def __init__(self):
        # Initialize image captioning models
        self.blip_processor = BlipProcessor.from_pretrained(
            MODEL_CONFIGS["image"]["captioning_model"]
        )
        self.blip_model = BlipForConditionalGeneration.from_pretrained(
            MODEL_CONFIGS["image"]["captioning_model"]
        )
        
        # Initialize object detection models
        self.detr_processor = DetrImageProcessor.from_pretrained(
            MODEL_CONFIGS["image"]["object_detection_model"]
        )
        self.detr_model = DetrForObjectDetection.from_pretrained(
            MODEL_CONFIGS["image"]["object_detection_model"]
        )
        
        # Move models to GPU if available
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.blip_model.to(self.device)
        self.detr_model.to(self.device)
    
    async def process(self, content: bytes, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process image content using multiple models
        
        Args:
            content: Raw image bytes
            metadata: Image metadata
        """
        # Convert bytes to PIL Image
        image = Image.open(io.BytesIO(content))
        
        # Resize if needed
        if image.size[0] > IMAGE_MAX_SIZE[0] or image.size[1] > IMAGE_MAX_SIZE[1]:
            image.thumbnail(IMAGE_MAX_SIZE)
        
        # Extract text using OCR
        ocr_text = pytesseract.image_to_string(image)
        
        # Generate image caption
        caption_inputs = self.blip_processor(
            image,
            return_tensors="pt"
        ).to(self.device)
        caption_output = self.blip_model.generate(
            **caption_inputs,
            max_length=50,
            num_beams=5,
            num_return_sequences=1
        )
        caption = self.blip_processor.decode(
            caption_output[0],
            skip_special_tokens=True
        )
        
        # Detect objects
        object_inputs = self.detr_processor(
            image,
            return_tensors="pt"
        ).to(self.device)
        object_outputs = self.detr_model(**object_inputs)
        
        # Post-process object detection results
        target_sizes = torch.tensor([image.size[::-1]])
        results = self.detr_processor.post_process_object_detection(
            object_outputs,
            target_sizes=target_sizes,
            threshold=0.7
        )[0]
        
        detected_objects = []
        for score, label, box in zip(
            results["scores"],
            results["labels"],
            results["boxes"]
        ):
            detected_objects.append({
                "label": self.detr_model.config.id2label[label.item()],
                "confidence": score.item(),
                "box": {
                    "x1": box[0].item(),
                    "y1": box[1].item(),
                    "x2": box[2].item(),
                    "y2": box[3].item()
                }
            })
        
        # Extract visual features for embedding
        # Using the caption and detected objects as a proxy for visual features
        visual_features = f"{caption} {' '.join([obj['label'] for obj in detected_objects])}"
        
        # Generate embedding using the combined text
        # TODO: Replace with actual visual embedding model
        from sentence_transformers import SentenceTransformer
        encoder = SentenceTransformer('all-MiniLM-L6-v2')
        embedding = encoder.encode(visual_features, convert_to_tensor=True).numpy()
        
        # Combine results
        result = {
            "content_type": "image",
            "embeddings": embedding,
            "metadata": {
                **metadata,
                "size": image.size,
                "mode": image.mode,
                "format": image.format,
                "caption": caption,
                "ocr_text": ocr_text.strip() if ocr_text else None,
                "objects": detected_objects,
            }
        }
        
        # Extract entities from caption and OCR text
        if ocr_text:
            # Use spaCy for entity extraction from OCR text
            import spacy
            nlp = spacy.load("en_core_web_sm")
            doc = nlp(ocr_text)
            
            result["entities"] = [
                {
                    "text": ent.text,
                    "type": ent.label_,
                    "source": "ocr"
                }
                for ent in doc.ents
            ]
            
            # Add detected objects as entities
            result["entities"].extend([
                {
                    "text": obj["label"],
                    "type": "OBJECT",
                    "source": "detection",
                    "confidence": obj["confidence"]
                }
                for obj in detected_objects
            ])
        
        return result
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image for better OCR results
        """
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # TODO: Add more preprocessing steps if needed
        # - Contrast enhancement
        # - Noise reduction
        # - Deskewing
        
        return image 