import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from main import app

client = TestClient(app)

@pytest.fixture
def mock_storage_client():
    with patch("main.storage_client") as mock_client:
        yield mock_client

def test_serve_image_invalid_uri(mock_storage_client):
    response = client.get("/api/image?gcs_uri=invalid_uri")
    assert response.status_code == 404
    assert "Image not found or inaccessible" in response.json()["detail"]

def test_serve_image_missing_path(mock_storage_client):
    response = client.get("/api/image?gcs_uri=gs://bucket_only")
    assert response.status_code == 404
    assert "Image not found or inaccessible" in response.json()["detail"]

def test_serve_image_signed_url_success(mock_storage_client):
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    mock_storage_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob

    expected_url = "https://signed.url/image.jpg"
    mock_blob.generate_signed_url.return_value = expected_url

    # By default, TestClient follows redirects. We want to check the redirect itself.
    response = client.get("/api/image?gcs_uri=gs://bucket/image.jpg", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == expected_url

def test_serve_image_fallback_to_streaming(mock_storage_client):
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    mock_storage_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob

    # Force signed URL to fail
    mock_blob.generate_signed_url.side_effect = Exception("Signing failed")

    # Mock file-like object for streaming
    # Using magic method for iteration over chunks
    class MockFile:
        def __init__(self):
            self.read_called = False

        def read(self, size=-1):
            if not self.read_called:
                self.read_called = True
                return b"image_data"
            return b""

        def __iter__(self):
            yield b"image_data"

    mock_blob.open.return_value = MockFile()

    response = client.get("/api/image?gcs_uri=gs://bucket/image.jpg")

    assert response.status_code == 200
    assert response.content == b"image_data"
    assert response.headers["content-type"] == "image/jpeg"

def test_serve_image_not_found(mock_storage_client):
    mock_storage_client.bucket.side_effect = Exception("Bucket not found")

    response = client.get("/api/image?gcs_uri=gs://bucket/image.jpg")

    assert response.status_code == 404
    assert "Image not found or inaccessible" in response.json()["detail"]

def test_serve_image_no_storage_client():
    with patch("main.storage_client", None):
        response = client.get("/api/image?gcs_uri=gs://bucket/image.jpg")
        assert response.status_code == 500
        assert "Storage client is not initialized." in response.json()["detail"]
