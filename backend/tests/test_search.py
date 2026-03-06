import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from backend.main import app, SearchRequest
from google.cloud import spanner

client = TestClient(app)

# The tests will be added here
import re

@patch('backend.main.query_gda')
@patch('backend.main.get_db_connection')
def test_search_properties_success_sqlalchemy(mock_get_db_connection, mock_query_gda):
    """Test successful search using SQLAlchemy (AlloyDB/Cloud SQL PG)."""
    mock_query_gda.return_value = {
        "naturalLanguageAnswer": "Here are some results.",
        "queryResult": {
            "columns": [{"name": "id"}, {"name": "title"}, {"name": "price"}],
            "rows": [
                {"values": [{"value": 1}, {"value": "House"}, {"value": 1000}]}
            ],
            "query": "SELECT * FROM properties",
            "totalRowCount": "1"
        },
        "generatedQuery": "SELECT * FROM properties",
        "intentExplanation": "Template 1 used."
    }

    mock_conn = MagicMock()
    mock_async_conn = AsyncMock()
    mock_async_conn.__aenter__.return_value = mock_async_conn
    mock_conn.begin.return_value = mock_async_conn

    mock_get_db_connection.return_value = (mock_conn, "sqlalchemy")

    response = client.post("/api/search", json={"query": "test query", "backend": "alloydb"})
    assert response.status_code == 200

    data = response.json()
    assert data["nl_answer"] == "Here are some results."
    assert len(data["listings"]) == 1
    assert data["listings"][0]["title"] == "House"

    mock_get_db_connection.assert_called_once_with("alloydb")
    mock_async_conn.execute.assert_called_once()


@patch('backend.main.query_gda')
@patch('backend.main.get_db_connection')
def test_search_properties_success_spanner(mock_get_db_connection, mock_query_gda):
    """Test successful search using Spanner."""
    mock_query_gda.return_value = {
        "naturalLanguageAnswer": "Spanner results.",
        "queryResult": {
            "columns": [{"name": "id"}, {"name": "title"}],
            "rows": [
                {"values": [{"value": 2}, {"value": "Apartment"}]}
            ],
            "query": "SELECT id, title FROM properties",
            "totalRowCount": "1"
        },
        "generatedQuery": "SELECT id, title FROM properties",
        "intentExplanation": "Template 2 used."
    }

    mock_conn = MagicMock()
    mock_get_db_connection.return_value = (mock_conn, "spanner")

    response = client.post("/api/search", json={"query": "spanner query", "backend": "spanner"})
    assert response.status_code == 200

    data = response.json()
    assert data["nl_answer"] == "Spanner results."
    assert len(data["listings"]) == 1
    assert data["listings"][0]["title"] == "Apartment"

    mock_get_db_connection.assert_called_once_with("spanner")
    mock_conn.run_in_transaction.assert_called_once()

    # Get the function passed to run_in_transaction and call it to ensure coverage
    transaction_func = mock_conn.run_in_transaction.call_args[0][0]
    mock_transaction = MagicMock()
    transaction_func(mock_transaction)
    mock_transaction.execute_update.assert_called_once()


@patch('backend.main.query_gda')
def test_search_properties_empty_results(mock_query_gda):
    """Test search with no results from GDA."""
    mock_query_gda.return_value = {
        "naturalLanguageAnswer": "No properties found.",
        "queryResult": {
            "columns": [],
            "rows": [],
            "query": "SELECT * FROM properties WHERE false",
            "totalRowCount": "0"
        },
        "generatedQuery": "SELECT * FROM properties WHERE false",
        "intentExplanation": "Template 3 used."
    }

    with patch('backend.main.get_db_connection') as mock_get_db_connection:
        mock_conn = MagicMock()
        mock_async_conn = AsyncMock()
        mock_async_conn.__aenter__.return_value = mock_async_conn
        mock_conn.begin.return_value = mock_async_conn
        mock_get_db_connection.return_value = (mock_conn, "sqlalchemy")

        response = client.post("/api/search", json={"query": "empty query", "backend": "cloudsql_pg"})

        assert response.status_code == 200
        data = response.json()
        assert len(data["listings"]) == 0
        assert data["nl_answer"] == "No properties found."

        # Connection logic is still executed for history
        mock_get_db_connection.assert_called_once_with("cloudsql_pg")


@patch('backend.main.query_gda')
def test_search_properties_gda_failure(mock_query_gda):
    """Test when GDA throws an exception."""
    mock_query_gda.side_effect = Exception("GDA API Error")

    response = client.post("/api/search", json={"query": "error query", "backend": "alloydb"})

    assert response.status_code == 200
    data = response.json()
    assert len(data["listings"]) == 0
    assert "error" in data["sql"]
    assert "error" in data["nl_answer"].lower()


@patch('backend.main.query_gda')
@patch('backend.main.get_db_connection')
def test_search_properties_db_failure(mock_get_db_connection, mock_query_gda):
    """Test when database logging fails but search succeeds."""
    mock_query_gda.return_value = {
        "naturalLanguageAnswer": "Results despite DB error.",
        "queryResult": {
            "columns": [{"name": "id"}],
            "rows": [{"values": [{"value": 3}]}],
            "query": "SELECT id FROM properties",
            "totalRowCount": "1"
        },
        "generatedQuery": "SELECT id FROM properties",
        "intentExplanation": "Template 4 used."
    }

    mock_get_db_connection.side_effect = Exception("Database connection failed")

    response = client.post("/api/search", json={"query": "db error query", "backend": "alloydb"})

    assert response.status_code == 200
    data = response.json()
    assert data["nl_answer"] == "Results despite DB error."
    assert len(data["listings"]) == 1
    assert data["listings"][0]["id"] == 3


@patch('backend.main.query_gda')
@patch('backend.main.get_db_connection')
def test_search_properties_image_and_embeddings(mock_get_db_connection, mock_query_gda):
    """Test image URI translation and embedding filtering."""
    mock_query_gda.return_value = {
        "naturalLanguageAnswer": "Image and embedding test.",
        "queryResult": {
            "columns": [
                {"name": "id"},
                {"name": "image_gcs_uri"},
                {"name": "description_embedding"},
                {"name": "image_embedding"}
            ],
            "rows": [
                {"values": [
                    {"value": 4},
                    {"value": "gs://bucket/image.jpg"},
                    {"value": "[0.1, 0.2]"},
                    {"value": "[0.3, 0.4]"}
                ]}
            ],
            "query": "SELECT * FROM properties",
            "totalRowCount": "1"
        },
        "generatedQuery": "SELECT * FROM properties",
        "intentExplanation": ""
    }

    mock_conn = MagicMock()
    mock_async_conn = AsyncMock()
    mock_async_conn.__aenter__.return_value = mock_async_conn
    mock_conn.begin.return_value = mock_async_conn
    mock_get_db_connection.return_value = (mock_conn, "sqlalchemy")

    response = client.post("/api/search", json={"query": "image query", "backend": "alloydb"})
    assert response.status_code == 200

    data = response.json()
    assert len(data["listings"]) == 1

    listing = data["listings"][0]
    assert listing["id"] == 4
    # Check URI translation
    assert listing["image_gcs_uri"] == "/api/image?gcs_uri=gs://bucket/image.jpg"
    # Check embedding filtering
    assert "description_embedding" not in listing
    assert "image_embedding" not in listing
