from typing import Dict, List, Optional, Union
from pathlib import Path
import json
import os
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
from .audio.processor import AudioProcessor
from .video.processor import VideoProcessor
import mimetypes
import magic
from datetime import datetime

class IngestionPipeline:
    def __init__(self, output_dir: str = "processed_data"):
        """Initialize the ingestion pipeline"""
        self.audio_processor = AudioProcessor()
        self.video_processor = VideoProcessor()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for different types
        (self.output_dir / "audio").mkdir(exist_ok=True)
        (self.output_dir / "video").mkdir(exist_ok=True)
        (self.output_dir / "text").mkdir(exist_ok=True)
        
    def detect_file_type(self, file_path: str) -> str:
        """Detect file type using magic numbers and extension"""
        mime = magic.from_file(file_path, mime=True)
        ext = Path(file_path).suffix.lower()
        
        if mime.startswith('audio/') or ext in self.audio_processor.supported_formats:
            return 'audio'
        elif mime.startswith('video/') or ext in self.video_processor.supported_formats:
            return 'video'
        elif mime.startswith('text/') or ext in ['.txt', '.md', '.pdf']:
            return 'text'
        else:
            raise ValueError(f"Unsupported file type: {mime} ({ext})")
            
    def process_file(self, file_path: str) -> Dict:
        """Process a single file based on its type"""
        file_type = self.detect_file_type(file_path)
        
        try:
            if file_type == 'audio':
                result = self.audio_processor.transcribe(file_path)
                output_path = self.output_dir / "audio" / f"{Path(file_path).stem}_processed.json"
                self.audio_processor.save_transcription(result, str(output_path))
                
            elif file_type == 'video':
                # Extract frames and scenes
                frames_result = self.video_processor.extract_frames(file_path)
                scenes = self.video_processor.detect_scenes(frames_result["frames"])
                
                # Extract and transcribe audio
                audio_result = self.video_processor.extract_audio(file_path)
                
                # Classify video content
                classification = self.video_processor.classify_video(frames_result["frames"])
                
                result = {
                    "frames_info": frames_result,
                    "scene_changes": scenes,
                    "audio_transcription": audio_result,
                    "classification": classification,
                    "metadata": {
                        "file_path": file_path,
                        "processed_at": datetime.now().isoformat()
                    }
                }
                
                output_path = self.output_dir / "video" / f"{Path(file_path).stem}_processed.json"
                self.video_processor.save_results(result, str(output_path))
                
            elif file_type == 'text':
                # TODO: Implement text processing
                # This could include:
                # - PDF parsing
                # - Text extraction
                # - Document structure analysis
                result = {"status": "Text processing not implemented yet"}
                
            return {
                "file_path": file_path,
                "file_type": file_type,
                "status": "success",
                "output_path": str(output_path) if 'output_path' in locals() else None
            }
            
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")
            return {
                "file_path": file_path,
                "file_type": file_type,
                "status": "error",
                "error": str(e)
            }
    
    def process_batch(self, file_paths: List[str], max_workers: int = 4) -> List[Dict]:
        """Process a batch of files in parallel"""
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self.process_file, path) for path in file_paths]
            
            # Process with progress bar
            for future in tqdm(futures, total=len(file_paths), desc="Processing files"):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"Error in batch processing: {str(e)}")
                    
        return results
    
    def save_batch_results(self, results: List[Dict], output_path: str):
        """Save batch processing results to file"""
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
    
    def load_batch_results(self, input_path: str) -> List[Dict]:
        """Load batch processing results from file"""
        with open(input_path, 'r') as f:
            return json.load(f) 