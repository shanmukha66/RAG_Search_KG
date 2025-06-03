import os
import mimetypes
from typing import Dict, Any
import asyncio
from ..processors.image_processor import ImageProcessor
from ..processors.audio_processor import AudioProcessor
from ..processors.video_processor import VideoProcessor
from ..processors.text_processor import TextProcessor
from ..storage.vector_store import QdrantVectorStore
from ..storage.graph_store import GraphStore

# Initialize processors
image_processor = ImageProcessor()
audio_processor = AudioProcessor()
video_processor = VideoProcessor()
text_processor = TextProcessor()

# Initialize storage
vector_store = QdrantVectorStore()
graph_store = GraphStore()

async def process_file(file_path: str) -> Dict[str, Any]:
    """
    Process uploaded file based on its type
    """
    try:
        # Determine file type
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            raise ValueError(f"Unknown file type for {file_path}")
        
        # Process based on file type
        if mime_type.startswith('image/'):
            result = await process_image(file_path)
        elif mime_type.startswith('audio/'):
            result = await process_audio(file_path)
        elif mime_type.startswith('video/'):
            result = await process_video(file_path)
        elif mime_type.startswith('text/') or mime_type == 'application/pdf':
            result = await process_text(file_path)
        else:
            raise ValueError(f"Unsupported file type: {mime_type}")
        
        # Store processing results
        await store_results(result)
        
        return result
        
    except Exception as e:
        # Log error and cleanup
        print(f"Error processing file {file_path}: {str(e)}")
        cleanup_file(file_path)
        raise

async def process_image(file_path: str) -> Dict[str, Any]:
    """Process image file"""
    # Extract text using OCR
    text = await image_processor.extract_text(file_path)
    
    # Generate image caption
    caption = await image_processor.generate_caption(file_path)
    
    # Detect objects
    objects = await image_processor.detect_objects(file_path)
    
    # Extract entities
    entities = await image_processor.extract_entities(text + " " + caption)
    
    # Generate embeddings
    embedding = await image_processor.generate_embedding(text + " " + caption)
    
    return {
        "type": "image",
        "text": text,
        "caption": caption,
        "objects": objects,
        "entities": entities,
        "embedding": embedding,
        "metadata": {
            "file_path": file_path,
            "mime_type": mimetypes.guess_type(file_path)[0]
        }
    }

async def process_audio(file_path: str) -> Dict[str, Any]:
    """Process audio file"""
    # Transcribe audio
    transcript = await audio_processor.transcribe(file_path)
    
    # Perform speaker diarization
    speakers = await audio_processor.diarize_speakers(file_path)
    
    # Extract entities
    entities = await audio_processor.extract_entities(transcript)
    
    # Generate embeddings
    embedding = await audio_processor.generate_embedding(transcript)
    
    return {
        "type": "audio",
        "transcript": transcript,
        "speakers": speakers,
        "entities": entities,
        "embedding": embedding,
        "metadata": {
            "file_path": file_path,
            "mime_type": mimetypes.guess_type(file_path)[0]
        }
    }

async def process_video(file_path: str) -> Dict[str, Any]:
    """Process video file"""
    # Extract frames
    frames = await video_processor.extract_frames(file_path)
    
    # Detect scenes
    scenes = await video_processor.detect_scenes(file_path)
    
    # Process audio track
    audio_result = await process_audio(file_path)
    
    # Process key frames
    frame_results = []
    for frame in frames:
        frame_result = await process_image(frame)
        frame_results.append(frame_result)
    
    # Combine embeddings
    combined_embedding = await video_processor.combine_embeddings(
        [r["embedding"] for r in frame_results],
        audio_result["embedding"]
    )
    
    return {
        "type": "video",
        "frames": frame_results,
        "scenes": scenes,
        "audio": audio_result,
        "embedding": combined_embedding,
        "metadata": {
            "file_path": file_path,
            "mime_type": mimetypes.guess_type(file_path)[0]
        }
    }

async def process_text(file_path: str) -> Dict[str, Any]:
    """Process text file"""
    # Extract text content
    text = await text_processor.extract_text(file_path)
    
    # Extract entities
    entities = await text_processor.extract_entities(text)
    
    # Generate embeddings
    embedding = await text_processor.generate_embedding(text)
    
    return {
        "type": "text",
        "text": text,
        "entities": entities,
        "embedding": embedding,
        "metadata": {
            "file_path": file_path,
            "mime_type": mimetypes.guess_type(file_path)[0]
        }
    }

async def store_results(result: Dict[str, Any]):
    """Store processing results in vector and graph stores"""
    # Store in vector store
    vector_id = await vector_store.store(
        vectors=[result["embedding"]],
        metadata=[{
            "type": result["type"],
            "file_path": result["metadata"]["file_path"],
            "mime_type": result["metadata"]["mime_type"]
        }]
    )
    
    # Store entities in graph store
    entity_ids = []
    for entity in result.get("entities", []):
        entity_id = await graph_store.store_entity(
            entity={
                "name": entity["name"],
                "type": entity["type"],
                "source": result["metadata"]["file_path"]
            }
        )
        entity_ids.append(entity_id)
    
    # Create relationships between entities
    for i, entity_id in enumerate(entity_ids):
        for other_id in entity_ids[i+1:]:
            await graph_store.store_entity(
                entity_id,
                relationships=[{
                    "to_id": other_id,
                    "type": "co_occurs",
                    "properties": {
                        "source": result["metadata"]["file_path"]
                    }
                }]
            )

def cleanup_file(file_path: str):
    """Clean up temporary files"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"Error cleaning up file {file_path}: {str(e)}") 