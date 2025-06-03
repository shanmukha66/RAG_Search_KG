import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import tempfile
import json
import os

from src.api.main import app
from src.auth.security import create_access_token

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def test_user_token():
    access_token = create_access_token(
        data={"sub": "testuser", "scopes": ["read", "write"]}
    )
    return {"Authorization": f"Bearer {access_token}"}

@pytest.fixture
def sample_text_file():
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
        f.write("This is a sample text file for testing.")
        return Path(f.name)

@pytest.fixture
def sample_image_file():
    # Create a simple test image
    from PIL import Image
    import numpy as np
    
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        # Create a 100x100 white image with some black text
        img = Image.fromarray(np.full((100, 100, 3), 255, dtype=np.uint8))
        img.save(f.name, format="PNG")
        return Path(f.name)

def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_login(client):
    """Test user login and token generation."""
    response = client.post(
        "/token",
        data={
            "username": "admin",
            "password": "admin",
            "scope": "read write"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_ingest_text_file(client, test_user_token, sample_text_file):
    """Test text file ingestion."""
    with open(sample_text_file, "rb") as f:
        response = client.post(
            "/ingest/file",
            files={"file": ("test.txt", f, "text/plain")},
            data={"content_type": "text"},
            headers=test_user_token
        )
    
    assert response.status_code == 200
    data = response.json()
    assert "content_id" in data
    assert data["status"] == "success"
    assert "metadata" in data

def test_ingest_image_file(client, test_user_token, sample_image_file):
    """Test image file ingestion."""
    with open(sample_image_file, "rb") as f:
        response = client.post(
            "/ingest/file",
            files={"file": ("test.png", f, "image/png")},
            data={"content_type": "image"},
            headers=test_user_token
        )
    
    assert response.status_code == 200
    data = response.json()
    assert "content_id" in data
    assert data["status"] == "success"
    assert "metadata" in data

def test_search(client, test_user_token):
    """Test content search."""
    query = {
        "query": "test content",
        "content_type": "text",
        "limit": 10,
        "expand_results": True
    }
    
    response = client.post(
        "/search",
        json=query,
        headers=test_user_token
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "total" in data
    assert "query_time_ms" in data

def test_get_content(client, test_user_token):
    """Test content retrieval."""
    # First ingest a file
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w") as f:
        f.write("Test content for retrieval")
        f.seek(0)
        
        response = client.post(
            "/ingest/file",
            files={"file": ("test.txt", f, "text/plain")},
            data={"content_type": "text"},
            headers=test_user_token
        )
        
        content_id = response.json()["content_id"]
    
    # Then retrieve it
    response = client.get(
        f"/content/{content_id}",
        headers=test_user_token
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "content" in data
    assert "related_entities" in data

def test_unauthorized_access(client):
    """Test unauthorized access to protected endpoints."""
    endpoints = [
        ("/search", "POST"),
        ("/ingest/file", "POST"),
        ("/content/123", "GET")
    ]
    
    for endpoint, method in endpoints:
        if method == "POST":
            response = client.post(endpoint)
        else:
            response = client.get(endpoint)
        
        assert response.status_code == 401
        assert "detail" in response.json()

def teardown_module(module):
    """Cleanup any temporary files."""
    # Clean up test files
    for pattern in ["*.txt", "*.png"]:
        for file in Path(tempfile.gettempdir()).glob(pattern):
            try:
                os.unlink(file)
            except Exception:
                pass 