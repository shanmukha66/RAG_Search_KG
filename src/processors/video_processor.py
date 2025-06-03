from typing import Dict, Any, List
import cv2
import numpy as np
from scenedetect import detect, ContentDetector
import tempfile
import os
from pathlib import Path
from ..config.settings import MODEL_CONFIGS, VIDEO_MAX_LENGTH
from .image_processor import ImageProcessor
from .audio_processor import AudioProcessor

class VideoProcessor:
    def __init__(self):
        self.image_processor = ImageProcessor()
        self.audio_processor = AudioProcessor()
        self.frame_rate = MODEL_CONFIGS["video"]["frame_extraction_rate"]
    
    async def process(self, content: bytes, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process video content by extracting frames, detecting scenes,
        and analyzing both visual and audio content
        
        Args:
            content: Raw video bytes
            metadata: Video metadata
        """
        # Save video temporarily for processing
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=True) as temp_video:
            temp_video.write(content)
            temp_video.flush()
            
            # Open video file
            cap = cv2.VideoCapture(temp_video.name)
            
            # Get video properties
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration = total_frames / fps
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # Check duration limit
            if duration > VIDEO_MAX_LENGTH:
                raise ValueError(
                    f"Video duration ({duration}s) exceeds maximum allowed "
                    f"length ({VIDEO_MAX_LENGTH}s)"
                )
            
            # Detect scene changes
            scenes = detect(temp_video.name, ContentDetector())
            scene_list = [
                {
                    "start_time": scene[0].get_seconds(),
                    "end_time": scene[1].get_seconds()
                }
                for scene in scenes
            ]
            
            # Extract and process key frames
            frames = []
            frame_embeddings = []
            
            for scene in scenes:
                # Get middle frame of each scene
                middle_frame_time = (
                    scene[0].get_seconds() +
                    scene[1].get_seconds()
                ) / 2
                cap.set(
                    cv2.CAP_PROP_POS_FRAMES,
                    middle_frame_time * fps
                )
                ret, frame = cap.read()
                
                if ret:
                    # Convert frame to bytes
                    success, buffer = cv2.imencode(".jpg", frame)
                    if success:
                        frame_bytes = buffer.tobytes()
                        
                        # Process frame using image processor
                        frame_result = await self.image_processor.process(
                            frame_bytes,
                            {
                                "timestamp": middle_frame_time,
                                "scene_index": len(frames)
                            }
                        )
                        
                        frames.append({
                            "timestamp": middle_frame_time,
                            "caption": frame_result["metadata"]["caption"],
                            "objects": frame_result["metadata"]["objects"],
                            "ocr_text": frame_result["metadata"]["ocr_text"]
                        })
                        
                        frame_embeddings.append(frame_result["embeddings"])
            
            # Extract and process audio
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as temp_audio:
                # Extract audio using ffmpeg
                os.system(
                    f"ffmpeg -i {temp_video.name} -vn -acodec pcm_s16le "
                    f"-ar 44100 -ac 2 {temp_audio.name}"
                )
                
                # Process audio
                with open(temp_audio.name, "rb") as audio_file:
                    audio_result = await self.audio_processor.process(
                        audio_file.read(),
                        {"source": "video"}
                    )
            
            # Combine frame embeddings
            if frame_embeddings:
                combined_embedding = np.mean(frame_embeddings, axis=0)
            else:
                combined_embedding = np.zeros(768)  # Default embedding size
            
            # Combine all entities
            entities = []
            
            # Add entities from frames
            for frame in frames:
                if "objects" in frame:
                    entities.extend([
                        {
                            "text": obj["label"],
                            "type": "OBJECT",
                            "source": "video_frame",
                            "confidence": obj["confidence"],
                            "timestamp": frame["timestamp"]
                        }
                        for obj in frame["objects"]
                    ])
            
            # Add entities from audio
            if "entities" in audio_result:
                entities.extend([
                    {**entity, "source": "audio"}
                    for entity in audio_result["entities"]
                ])
            
            # Combine results
            result = {
                "content_type": "video",
                "embeddings": combined_embedding,
                "entities": entities,
                "metadata": {
                    **metadata,
                    "duration": duration,
                    "fps": fps,
                    "resolution": {
                        "width": width,
                        "height": height
                    },
                    "scenes": scene_list,
                    "frames": frames,
                    "audio": {
                        "transcription": audio_result["metadata"]["transcription"],
                        "speaker_segments": audio_result["metadata"]["speaker_segments"]
                    }
                }
            }
            
            cap.release()
            return result
    
    def _extract_frame_features(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Extract features from a video frame
        TODO: Implement more sophisticated frame analysis
        """
        # Basic frame statistics
        return {
            "mean_brightness": float(frame.mean()),
            "std_brightness": float(frame.std()),
        } 