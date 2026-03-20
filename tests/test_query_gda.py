import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Add the backend directory to the sys.path to easily import backend.main
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.main import query_gda
from fastapi import HTTPException
import requests

class TestQueryGDA(unittest.TestCase):
    def setUp(self):
        # We need to mock environment variables that are checked in query_gda
        self.patcher_env = patch.dict(os.environ, {
            "GCP_LOCATION": "test-location",
            "ALLOYDB_CLUSTER_ID": "test-cluster",
            "ALLOYDB_INSTANCE_ID": "test-instance",
        })
        self.patcher_env.start()

        # Patch the global variables in backend.main
        self.patcher_project_id = patch('backend.main.PROJECT_ID', 'test-project')
        self.patcher_context_id = patch('backend.main.AGENT_CONTEXT_SET_ID_ALLOYDB', 'test-context-id')
        self.patcher_project_id.start()
        self.patcher_context_id.start()

        # Mock get_gda_credentials
        self.patcher_creds = patch('backend.main.get_gda_credentials')
        self.mock_creds = self.patcher_creds.start()
        mock_cred_obj = MagicMock()
        mock_cred_obj.token = "test-token"
        self.mock_creds.return_value = mock_cred_obj

    def tearDown(self):
        self.patcher_env.stop()
        self.patcher_project_id.stop()
        self.patcher_context_id.stop()
        self.patcher_creds.stop()

    @patch('backend.main.requests.post')
    def test_query_gda_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True}
        mock_post.return_value = mock_response

        result = query_gda("test prompt", "alloydb")

        self.assertEqual(result, {"success": True})
        mock_post.assert_called_once()

    @patch('backend.main.requests.post')
    def test_query_gda_request_exception(self, mock_post):
        mock_post.side_effect = requests.exceptions.RequestException("Connection error")

        with self.assertRaises(HTTPException) as context:
            query_gda("test prompt", "alloydb")

        self.assertEqual(context.exception.status_code, 500)
        self.assertIn("Failed to query Gemini Data Agent: Connection error", str(context.exception.detail))

    @patch('backend.main.requests.post')
    def test_query_gda_http_error_with_response(self, mock_post):
        mock_response = MagicMock()
        mock_response.text = "Bad Request Details"

        # Create an exception that has a response attribute
        error = requests.exceptions.HTTPError("400 Client Error")
        error.response = mock_response

        mock_post.side_effect = error

        with self.assertRaises(HTTPException) as context:
            query_gda("test prompt", "alloydb")

        self.assertEqual(context.exception.status_code, 500)
        self.assertIn("Failed to query Gemini Data Agent: 400 Client Error", str(context.exception.detail))


if __name__ == '__main__':
    unittest.main()
