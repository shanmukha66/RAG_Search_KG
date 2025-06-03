import pytest
from pathlib import Path
import tempfile
import os

from src.ingestion import TextIngestionPipeline

pytestmark = pytest.mark.asyncio

@pytest.fixture
def text_pipeline():
    config = {
        "chunk_size": 1000
    }
    return TextIngestionPipeline(config)

@pytest.fixture
def sample_text_file():
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
        f.write("This is a sample text file.\nIt has multiple lines.\nWe will use it for testing.")
        return Path(f.name)

async def test_text_validation(text_pipeline, sample_text_file):
    assert await text_pipeline.validate(sample_text_file)
    
    # Test invalid file
    invalid_file = Path("nonexistent.txt")
    assert not await text_pipeline.validate(invalid_file)

async def test_metadata_extraction(text_pipeline, sample_text_file):
    metadata = await text_pipeline.extract_metadata(sample_text_file)
    
    assert metadata.content_type == "text"
    assert metadata.source_path == str(sample_text_file)
    assert metadata.metadata["extension"] == ".txt"
    assert metadata.metadata["size_bytes"] > 0

async def test_content_extraction(text_pipeline, sample_text_file):
    preprocessed = await text_pipeline.preprocess(sample_text_file)
    content = await text_pipeline.extract_content(preprocessed)
    
    assert "raw_text" in content
    assert "chunks" in content
    assert "char_count" in content
    assert "word_count" in content
    
    assert content["raw_text"] == "This is a sample text file.\nIt has multiple lines.\nWe will use it for testing."
    assert content["word_count"] == 16

def teardown_module(module):
    # Cleanup any temporary files
    for file in Path(tempfile.gettempdir()).glob("tmp*.txt"):
        try:
            os.unlink(file)
        except Exception:
            pass 