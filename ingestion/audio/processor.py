from typing import Dict, List, Optional
import whisper
import torch
import os
from pathlib import Path
import json
import numpy as np
from pydub import AudioSegment

class AudioProcessor:
    def __init__(self, model_name: str = "base"):
        """Initialize the audio processor with Whisper model"""
        self.model = whisper.load_model(model_name)
        self.supported_formats = ['.mp3', '.wav', '.m4a', '.flac']
        
    def convert_to_wav(self, file_path: str) -> str:
        """Convert audio file to WAV format if needed"""
        path = Path(file_path)
        if path.suffix.lower() not in self.supported_formats:
            raise ValueError(f"Unsupported audio format: {path.suffix}")
            
        if path.suffix.lower() != '.wav':
            wav_path = path.with_suffix('.wav')
            audio = AudioSegment.from_file(file_path)
            audio.export(wav_path, format='wav')
            return str(wav_path)
        return file_path
        
    def transcribe(self, file_path: str, chunk_size: int = 30) -> Dict:
        """
        Transcribe audio file with timestamps and speaker detection
        Args:
            file_path: Path to audio file
            chunk_size: Size of audio chunks in seconds
        Returns:
            Dictionary containing transcription and metadata
        """
        # Convert to WAV if needed
        wav_path = self.convert_to_wav(file_path)
        
        try:
            # Transcribe with Whisper
            result = self.model.transcribe(
                wav_path,
                task="transcribe",
                language=None,  # Auto-detect language
                verbose=False
            )
            
            # Process segments and add metadata
            processed_segments = []
            for segment in result["segments"]:
                processed_segments.append({
                    "start": segment["start"],
                    "end": segment["end"],
                    "text": segment["text"].strip(),
                    "confidence": float(segment["confidence"]),
                    "language": result["language"]
                })
            
            # Clean up temporary WAV file if it was converted
            if wav_path != file_path:
                os.remove(wav_path)
            
            return {
                "text": result["text"],
                "segments": processed_segments,
                "language": result["language"],
                "file_path": file_path,
                "duration": float(result["segments"][-1]["end"] if result["segments"] else 0)
            }
            
        except Exception as e:
            print(f"Error transcribing audio: {str(e)}")
            if wav_path != file_path:
                os.remove(wav_path)
            raise
    
    def detect_speakers(self, audio_path: str, min_speakers: int = 1, max_speakers: int = 2) -> Dict:
        """
        Detect and separate different speakers in the audio
        Note: This is a placeholder for speaker diarization
        In a full implementation, you would use a proper speaker diarization model
        """
        # TODO: Implement proper speaker diarization using a model like pyannote.audio
        return {
            "speaker_count": 1,
            "speakers": ["Speaker 1"]
        }
    
    def extract_audio_features(self, file_path: str) -> Dict:
        """Extract audio features for embedding generation"""
        # TODO: Implement audio feature extraction
        # This could include:
        # - Mel spectrograms
        # - MFCC features
        # - Acoustic embeddings
        return {
            "features": [],
            "file_path": file_path
        }
    
    def save_transcription(self, transcription: Dict, output_path: str):
        """Save transcription results to file"""
        with open(output_path, 'w') as f:
            json.dump(transcription, f, indent=2)
    
    def load_transcription(self, input_path: str) -> Dict:
        """Load transcription results from file"""
        with open(input_path, 'r') as f:
            return json.load(f) 