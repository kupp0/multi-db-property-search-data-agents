import sys
import os
import types
from unittest.mock import MagicMock, patch

# --- MOCKING SETUP START ---
# We must mock 'google.auth' and 'google.cloud.storage' BEFORE importing backend.main
# because backend.main initializes them at module level.

# 1. Mock 'google' package
mock_google = types.ModuleType("google")
sys.modules["google"] = mock_google

# 2. Mock 'google.auth' module
mock_google_auth = types.ModuleType("google.auth")
mock_google_auth.default = MagicMock(return_value=(MagicMock(), "test-project"))
mock_google_auth.transport = MagicMock()
mock_google_auth.transport.requests = MagicMock()

# Bind 'auth' to 'google' so `google.auth` works
mock_google.auth = mock_google_auth
sys.modules["google.auth"] = mock_google_auth

# 3. Mock 'google.cloud' package
mock_google_cloud = types.ModuleType("google.cloud")
mock_google.cloud = mock_google_cloud
sys.modules["google.cloud"] = mock_google_cloud

# 4. Mock 'google.cloud.storage' module
mock_storage_module = types.ModuleType("google.cloud.storage")
mock_storage_client_cls = MagicMock()
mock_storage_module.Client = mock_storage_client_cls

# Bind 'storage' to 'google.cloud'
mock_google_cloud.storage = mock_storage_module
sys.modules["google.cloud.storage"] = mock_storage_module

# --- MOCKING SETUP END ---

from fastapi.testclient import TestClient
import pytest

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import main
from main import app

# Initialize TestClient. Note: httpx defaults follow_redirects=False, but Starlette TestClient might default to True.
# Explicitly set it to False to be sure, or pass it in request.
# Starlette/FastAPI TestClient constructor args depend on version.
# Safest is to pass it to .get() if supported, or rely on default and check behavior.
client = TestClient(app)

def test_ssrf_protection():
    """
    Test that the application BLOCKS accessing arbitrary buckets
    and ALLOWS accessing the whitelisted bucket.
    """
    allowed_bucket = "safe-bucket"

    # Patch the ALLOWED_GCS_BUCKET variable in the loaded main module
    with patch.object(main, "ALLOWED_GCS_BUCKET", allowed_bucket):

        # --- TEST 1: Malicious Bucket (Should be BLOCKED) ---
        malicious_bucket = "secret-internal-bucket"
        malicious_uri = f"gs://{malicious_bucket}/passwd"

        # Reset mocks
        mock_client_instance = mock_storage_client_cls.return_value
        mock_client_instance.reset_mock()

        # Pass follow_redirects=False to be explicit
        response = client.get(f"/api/image?gcs_uri={malicious_uri}", follow_redirects=False)

        print(f"Malicious Access - Status: {response.status_code}")
        print(f"Malicious Access - Body: {response.text}")

        # Assertions
        assert response.status_code == 403
        mock_client_instance.bucket.assert_not_called()


        # --- TEST 2: Allowed Bucket (Should be ALLOWED) ---
        safe_uri = f"gs://{allowed_bucket}/image.jpg"

        # Setup mock for success
        # We need to make sure we are attaching to the SAME instance object
        mock_client_instance = mock_storage_client_cls.return_value

        mock_bucket = MagicMock()
        mock_client_instance.bucket.return_value = mock_bucket
        mock_blob = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        mock_blob.generate_signed_url.return_value = "https://example.com/signed_url"

        response = client.get(f"/api/image?gcs_uri={safe_uri}", follow_redirects=False)

        print(f"Safe Access - Status: {response.status_code}")
        print(f"Safe Access - Body: {response.text}")

        assert response.status_code == 307
        mock_client_instance.bucket.assert_called_with(allowed_bucket)
        assert response.headers["location"] == "https://example.com/signed_url"
