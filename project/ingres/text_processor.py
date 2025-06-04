"""Text and PDF processing module."""
from typing import Dict, List, Optional
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

class TextProcessor:
    def __init__(self, chunk_size: int = 1000):
        self.chunk_size = chunk_size
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=200,
            length_function=len,
        )

    def process_pdf(self, file_path: str) -> List[Dict[str, str]]:
        """Process a PDF file and return chunks with metadata."""
        loader = PyPDFLoader(file_path)
        pages = loader.load()
        chunks = []
        
        for page in pages:
            text_chunks = self.text_splitter.split_text(page.page_content)
            for i, chunk in enumerate(text_chunks):
                chunks.append({
                    'text': chunk,
                    'metadata': {
                        'source': file_path,
                        'page': page.metadata['page'],
                        'chunk_id': i
                    }
                })
        
        return chunks

    def process_text(self, text: str, source: str = "text") -> List[Dict[str, str]]:
        """Process raw text and return chunks with metadata."""
        chunks = self.text_splitter.split_text(text)
        return [
            {
                'text': chunk,
                'metadata': {
                    'source': source,
                    'chunk_id': i
                }
            }
            for i, chunk in enumerate(chunks)
        ] 