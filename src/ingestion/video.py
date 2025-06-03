import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
import numpy as np
import moviepy.editor as mpy
import tempfile

from .base import BaseIngestionPipeline, ContentMetadata

class VideoIngestionPipeline(BaseIngestionPipeline):
    """Pipeline for ingesting video content."""
    
    SUPPORTED_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.frame_sample_rate = config.get('frame_sample_rate', 1)  # Sample every n seconds
        self.audio_segment_length = config.get('audio_segment_length', 10)  # Seconds
        self.temp_dir = config.get('temp_dir', tempfile.gettempdir())
    
    async def validate(self, content_path: Path) -> bool:
        """Validate if the file is a supported video file."""
        if not content_path.is_file():
            return False
        return content_path.suffix.lower() in self.SUPPORTED_EXTENSIONS
    
    async def extract_metadata(self, content_path: Path) -> ContentMetadata:
        """Extract metadata from the video file."""
        stats = os.stat(content_path)
        
        with mpy.VideoFileClip(str(content_path)) as video:
            metadata = {
                "size_bytes": stats.st_size,
                "extension": content_path.suffix.lower(),
                "duration": video.duration,
                "fps": video.fps,
                "size": (video.size[0], video.size[1]),
                "has_audio": video.audio is not None
            }
            
            if video.audio:
                metadata.update({
                    "audio_fps": video.audio.fps,
                    "audio_duration": video.audio.duration
                })
        
        return ContentMetadata(
            content_type="video",
            source_path=str(content_path),
            creation_date=datetime.fromtimestamp(stats.st_ctime).isoformat(),
            modified_date=datetime.fromtimestamp(stats.st_mtime).isoformat(),
            metadata=metadata
        )
    
    async def preprocess(self, content_path: Path) -> mpy.VideoFileClip:
        """Load and preprocess the video."""
        return mpy.VideoFileClip(str(content_path))
    
    async def extract_content(self, preprocessed_content: mpy.VideoFileClip) -> Dict[str, Any]:
        """Extract frames and audio from the video."""
        video = preprocessed_content
        
        # Sample frames
        frame_times = np.arange(0, video.duration, self.frame_sample_rate)
        frames = []
        
        for t in frame_times:
            frame = video.get_frame(t)
            frames.append({
                "time": t,
                "frame": frame.mean(axis=(0, 1)).tolist()  # Basic frame features
            })
        
        # Process audio if available
        audio_features = []
        if video.audio:
            audio = video.audio
            segment_times = np.arange(0, audio.duration, self.audio_segment_length)
            
            for t in segment_times:
                end_time = min(t + self.audio_segment_length, audio.duration)
                segment = audio.subclip(t, end_time)
                
                # Extract basic audio features
                samples = segment.to_soundarray()
                audio_features.append({
                    "time_start": t,
                    "time_end": end_time,
                    "mean_amplitude": float(np.mean(np.abs(samples))),
                    "max_amplitude": float(np.max(np.abs(samples))),
                    "rms": float(np.sqrt(np.mean(samples**2)))
                })
        
        return {
            "frames": frames,
            "audio_features": audio_features,
            "total_frames": len(frames),
            "total_audio_segments": len(audio_features)
        }
    
    async def enrich(self, extracted_content: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich the extracted content with additional information."""
        # Here we could add:
        # - Scene detection
        # - Object tracking
        # - Action recognition
        # - Speech recognition
        # - Caption generation
        return {
            **extracted_content,
            "enriched_at": datetime.utcnow().isoformat()
        }
    
    async def cleanup(self) -> None:
        """Cleanup temporary files."""
        # Cleanup any temporary files created during processing
        pass 