"""Image processing module using CLIP and LLAVA."""
from typing import Dict, List, Optional
from transformers import CLIPProcessor, CLIPModel
import torch
from PIL import Image

class ImageProcessor:
    def __init__(self):
        self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        self.clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.clip_model.to(self.device)

    def extract_tags(self, image_path: str, candidate_labels: List[str]) -> List[Dict[str, float]]:
        """Extract tags from image using CLIP zero-shot classification."""
        image = Image.open(image_path)
        inputs = self.clip_processor(
            text=candidate_labels,
            images=image,
            return_tensors="pt",
            padding=True
        ).to(self.device)

        outputs = self.clip_model(**inputs)
        logits_per_image = outputs.logits_per_image
        probs = logits_per_image.softmax(dim=1).detach().cpu().numpy()[0]

        return [
            {"tag": label, "confidence": float(prob)}
            for label, prob in zip(candidate_labels, probs)
        ]

    def process_image(self, image_path: str, source: str = None) -> Dict:
        """Process an image and return extracted information."""
        # Default tags to detect - can be customized based on your needs
        default_tags = [
            "document", "chart", "graph", "table", "text",
            "photograph", "diagram", "screenshot", "illustration"
        ]
        
        tags = self.extract_tags(image_path, default_tags)
        
        return {
            'source': source or image_path,
            'tags': tags,
            'metadata': {
                'type': 'image',
                'path': image_path
            }
        } 