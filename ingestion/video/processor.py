from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np
from pathlib import Path
import json
import os
from PIL import Image
import torch
from transformers import AutoProcessor, AutoModelForVideoClassification
import tempfile
from ..audio.processor import AudioProcessor

class VideoProcessor:
    def __init__(self):
        """Initialize video processor with necessary models"""
        self.supported_formats = ['.mp4', '.avi', '.mov', '.mkv']
        self.audio_processor = AudioProcessor()
        
        # Initialize video classification model
        self.processor = AutoProcessor.from_pretrained("microsoft/xclip-base-patch32")
        self.model = AutoModelForVideoClassification.from_pretrained("microsoft/xclip-base-patch32")
        
    def extract_frames(self, video_path: str, frame_interval: int = 30) -> Dict:
        """
        Extract frames from video at specified intervals
        Args:
            video_path: Path to video file
            frame_interval: Number of frames to skip between extractions
        Returns:
            Dictionary containing frames and metadata
        """
        path = Path(video_path)
        if path.suffix.lower() not in self.supported_formats:
            raise ValueError(f"Unsupported video format: {path.suffix}")
        
        cap = cv2.VideoCapture(video_path)
        frames = []
        timestamps = []
        
        try:
            while cap.isOpened():
                frame_pos = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
                if frame_pos % frame_interval == 0:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    
                    # Convert BGR to RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frames.append(frame_rgb)
                    timestamps.append(cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0)
                else:
                    cap.read()  # Skip frame but keep reading
                    
            return {
                "frames": frames,
                "timestamps": timestamps,
                "frame_count": len(frames),
                "duration": cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0,
                "fps": cap.get(cv2.CAP_PROP_FPS),
                "total_frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            }
        finally:
            cap.release()
    
    def detect_scenes(self, frames: List[np.ndarray], threshold: float = 30.0) -> List[int]:
        """
        Detect scene changes in video frames
        Args:
            frames: List of video frames
            threshold: Difference threshold for scene change detection
        Returns:
            List of frame indices where scenes change
        """
        scene_changes = []
        if len(frames) < 2:
            return scene_changes
            
        for i in range(1, len(frames)):
            # Calculate frame difference
            diff = np.mean(np.abs(frames[i].astype(float) - frames[i-1].astype(float)))
            if diff > threshold:
                scene_changes.append(i)
                
        return scene_changes
    
    def extract_audio(self, video_path: str) -> Dict:
        """Extract and transcribe audio from video"""
        # Create temporary audio file
        temp_audio = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_audio.close()
        
        try:
            # Extract audio using ffmpeg
            os.system(f'ffmpeg -i "{video_path}" -q:a 0 -map a "{temp_audio.name}" -y')
            
            # Process audio using AudioProcessor
            transcription = self.audio_processor.transcribe(temp_audio.name)
            
            return transcription
        finally:
            # Clean up temporary file
            os.remove(temp_audio.name)
    
    def classify_video(self, frames: List[np.ndarray], sample_rate: int = 5) -> Dict:
        """
        Classify video content using pre-trained model
        Args:
            frames: List of video frames
            sample_rate: Number of frames to use for classification
        Returns:
            Dictionary containing classification results
        """
        # Sample frames evenly
        if len(frames) > sample_rate:
            frame_indices = np.linspace(0, len(frames)-1, sample_rate, dtype=int)
            sample_frames = [frames[i] for i in frame_indices]
        else:
            sample_frames = frames
        
        # Convert frames to PIL Images
        pil_frames = [Image.fromarray(frame) for frame in sample_frames]
        
        # Prepare inputs
        inputs = self.processor(images=pil_frames, return_tensors="pt")
        
        # Get predictions
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            
        # Get predicted label
        predicted_label = logits.argmax(-1).item()
        confidence = torch.softmax(logits, dim=-1)[0][predicted_label].item()
        
        return {
            "label": self.model.config.id2label[predicted_label],
            "confidence": confidence
        }
    
    def save_results(self, results: Dict, output_path: str):
        """Save processing results to file"""
        # Convert numpy arrays to lists for JSON serialization
        if 'frames' in results:
            results['frames'] = [frame.tolist() for frame in results['frames']]
            
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
    
    def load_results(self, input_path: str) -> Dict:
        """Load processing results from file"""
        with open(input_path, 'r') as f:
            results = json.load(f)
            
        # Convert lists back to numpy arrays
        if 'frames' in results:
            results['frames'] = [np.array(frame) for frame in results['frames']]
            
        return results 