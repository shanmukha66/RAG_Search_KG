from typing import Dict, Any, List
import numpy as np
import torch
import whisper
from pyannote.audio import Pipeline
from transformers import pipeline
from ..config.settings import MODEL_CONFIGS, HUGGINGFACE_API_KEY

class AudioProcessor:
    def __init__(self):
        # Initialize Whisper model for transcription
        self.transcriber = whisper.load_model("base")
        
        # Initialize speaker diarization pipeline
        self.diarization = Pipeline.from_pretrained(
            MODEL_CONFIGS["audio"]["speaker_diarization"],
            use_auth_token=HUGGINGFACE_API_KEY
        )
        
        # Initialize sentiment analysis
        self.sentiment_analyzer = pipeline(
            "sentiment-analysis",
            model="distilbert-base-uncased-finetuned-sst-2-english"
        )
    
    async def process(self, content: bytes, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process audio content for transcription and analysis
        
        Args:
            content: Raw audio bytes
            metadata: Audio metadata
        """
        # Save audio temporarily for processing
        import tempfile
        import soundfile as sf
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as temp_file:
            # Convert bytes to numpy array and save as wav
            audio_data, sample_rate = sf.read(content)
            sf.write(temp_file.name, audio_data, sample_rate)
            
            # Transcribe audio
            transcription = self.transcriber.transcribe(temp_file.name)
            
            # Perform speaker diarization
            diarization = self.diarization(temp_file.name)
            
            # Process diarization results
            segments = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                segments.append({
                    "speaker": speaker,
                    "start": turn.start,
                    "end": turn.end
                })
            
            # Analyze sentiment for each segment
            for segment in segments:
                text_portion = self._get_text_for_timespan(
                    transcription["segments"],
                    segment["start"],
                    segment["end"]
                )
                if text_portion:
                    sentiment = self.sentiment_analyzer(text_portion)[0]
                    segment["sentiment"] = {
                        "label": sentiment["label"],
                        "score": sentiment["score"]
                    }
        
        # Generate embedding from transcription
        from sentence_transformers import SentenceTransformer
        encoder = SentenceTransformer('all-MiniLM-L6-v2')
        embedding = encoder.encode(
            transcription["text"],
            convert_to_tensor=True
        ).numpy()
        
        # Extract entities from transcription
        import spacy
        nlp = spacy.load("en_core_web_sm")
        doc = nlp(transcription["text"])
        
        entities = [
            {
                "text": ent.text,
                "type": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char
            }
            for ent in doc.ents
        ]
        
        # Combine results
        result = {
            "content_type": "audio",
            "embeddings": embedding,
            "entities": entities,
            "metadata": {
                **metadata,
                "transcription": transcription["text"],
                "segments": transcription["segments"],
                "speaker_segments": segments,
                "language": transcription["language"],
                "duration": float(transcription["segments"][-1]["end"]),
            }
        }
        
        return result
    
    def _get_text_for_timespan(
        self,
        segments: List[Dict[str, Any]],
        start_time: float,
        end_time: float
    ) -> str:
        """
        Extract text from segments that fall within the given timespan
        """
        relevant_segments = []
        for segment in segments:
            if (
                segment["start"] >= start_time and
                segment["end"] <= end_time
            ):
                relevant_segments.append(segment["text"])
        
        return " ".join(relevant_segments)
    
    def _analyze_audio_features(self, audio_data: np.ndarray) -> Dict[str, Any]:
        """
        Extract audio features like volume, pitch, etc.
        TODO: Implement audio feature extraction
        """
        return {
            "mean_volume": float(np.abs(audio_data).mean()),
            "max_volume": float(np.abs(audio_data).max()),
        } 