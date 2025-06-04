"""Audio processing module using Faster-Whisper."""
from typing import Dict, List, Optional
from faster_whisper import WhisperModel
import torch

class AudioProcessor:
    def __init__(self, model_size: str = "base"):
        """Initialize the audio processor with Faster-Whisper model."""
        device = "cuda" if torch.cuda.is_available() else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"
        
        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type
        )

    def transcribe(self, audio_path: str) -> Dict[str, any]:
        """Transcribe audio file and return segments with metadata."""
        segments, info = self.model.transcribe(
            audio_path,
            beam_size=5,
            word_timestamps=True
        )
        
        transcription = []
        for segment in segments:
            transcription.append({
                'text': segment.text,
                'start': segment.start,
                'end': segment.end,
                'words': [
                    {
                        'word': word.word,
                        'start': word.start,
                        'end': word.end,
                        'probability': word.probability
                    }
                    for word in segment.words
                ]
            })
        
        return {
            'segments': transcription,
            'metadata': {
                'language': info.language,
                'language_probability': info.language_probability,
                'duration': info.duration,
                'source': audio_path
            }
        } 