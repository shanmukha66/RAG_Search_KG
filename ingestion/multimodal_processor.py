from typing import Dict, List, Optional
import whisper
import cv2
import numpy as np
from pathlib import Path
import json

class MultiModalProcessor:
    def __init__(self, model_path: Optional[str] = None):
        self.audio_model = whisper.load_model("base")
        self.supported_audio = ['.mp3', '.wav', '.m4a']
        self.supported_video = ['.mp4', '.avi', '.mov']
        
    def process_audio(self, file_path: str) -> Dict:
        """Process audio file and return transcription with timestamps"""
        if not Path(file_path).suffix in self.supported_audio:
            raise ValueError(f"Unsupported audio format. Supported: {self.supported_audio}")
            
        # Transcribe audio
        result = self.audio_model.transcribe(file_path)
        
        return {
            'text': result['text'],
            'segments': result['segments'],
            'language': result['language'],
            'file_path': file_path
        }
    
    def process_video(self, file_path: str, frame_interval: int = 30) -> Dict:
        """Process video file and extract frames, audio, and perform OCR"""
        if not Path(file_path).suffix in self.supported_video:
            raise ValueError(f"Unsupported video format. Supported: {self.supported_video}")
        
        cap = cv2.VideoCapture(file_path)
        frames = []
        timestamps = []
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            # Process frame at intervals
            if int(cap.get(cv2.CAP_PROP_POS_FRAMES)) % frame_interval == 0:
                timestamp = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
                frames.append(frame)
                timestamps.append(timestamp)
        
        cap.release()
        
        # Extract audio and transcribe
        # TODO: Implement audio extraction from video
        
        return {
            'frames': frames,
            'timestamps': timestamps,
            'frame_count': len(frames),
            'file_path': file_path
        }
    
    def save_processing_results(self, results: Dict, output_path: str):
        """Save processing results to file"""
        # Convert numpy arrays to lists for JSON serialization
        if 'frames' in results:
            results['frames'] = [frame.tolist() for frame in results['frames']]
            
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
    
    def load_processing_results(self, input_path: str) -> Dict:
        """Load processing results from file"""
        with open(input_path, 'r') as f:
            results = json.load(f)
            
        # Convert lists back to numpy arrays
        if 'frames' in results:
            results['frames'] = [np.array(frame) for frame in results['frames']]
            
        return results 