import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from backend.main import app, HistoryRequest, FilterCondition
from google.cloud import spanner

client = TestClient(app)

@pytest.fixture
def mock_get_db_connection():
    with patch('backend.main.get_db_connection', new_callable=AsyncMock) as mock_get_db_connection:
        yield mock_get_db_connection

def test_get_history_sqlalchemy_no_filters(mock_get_db_connection):
    mock_conn_obj = MagicMock()
    mock_conn = AsyncMock()
    mock_result = MagicMock()

    mock_result.mappings.return_value = [{"user_prompt": "test", "query_template_used": "temp", "query_template_id": "1", "query_explanation": "exp"}]
    mock_conn.execute.return_value = mock_result
    mock_conn_obj.connect.return_value.__aenter__.return_value = mock_conn

    mock_get_db_connection.return_value = (mock_conn_obj, "sqlalchemy")

    response = client.post("/api/history", json={"backend": "alloydb", "filters": []})

    assert response.status_code == 200
    assert response.json() == {"rows": [{"user_prompt": "test", "query_template_used": "temp", "query_template_id": "1", "query_explanation": "exp"}]}
    mock_conn.execute.assert_called_once()

    # Check that query doesn't have WHERE clause
    called_query = mock_conn.execute.call_args[0][0].text
    assert "WHERE" not in called_query
    assert "LIMIT 1000" in called_query

def test_get_history_sqlalchemy_with_filters(mock_get_db_connection):
    mock_conn_obj = MagicMock()
    mock_conn = AsyncMock()
    mock_result = MagicMock()

    mock_result.mappings.return_value = []
    mock_conn.execute.return_value = mock_result
    mock_conn_obj.connect.return_value.__aenter__.return_value = mock_conn

    mock_get_db_connection.return_value = (mock_conn_obj, "sqlalchemy")

    filters = [
        {"column": "user_prompt", "operator": "ILIKE", "value": "%test%", "logic": "AND"},
        {"column": "query_template_id", "operator": "=", "value": "123", "logic": "OR"},
        {"column": "invalid_col", "operator": "=", "value": "bad"}, # Should be skipped
        {"column": "user_prompt", "operator": "INVALID", "value": "bad"} # Should be skipped
    ]

    response = client.post("/api/history", json={"backend": "alloydb", "filters": filters})

    assert response.status_code == 200
    mock_conn.execute.assert_called_once()

    called_query = mock_conn.execute.call_args[0][0].text
    called_params = mock_conn.execute.call_args[0][1]

    assert "WHERE user_prompt ILIKE :p0" in called_query
    assert "OR query_template_id = :p1" in called_query
    assert "invalid_col" not in called_query
    assert "INVALID" not in called_query

    assert called_params["p0"] == "%test%"
    assert called_params["p1"] == "123"

def test_get_history_spanner_with_filters(mock_get_db_connection):
    mock_conn_obj = MagicMock()
    mock_snapshot = MagicMock()

    # Spanner execute_sql returns a list of lists
    mock_snapshot.execute_sql.return_value = [["test_spanner", "temp_s", "2", "exp_s"]]
    mock_conn_obj.snapshot.return_value.__enter__.return_value = mock_snapshot

    mock_get_db_connection.return_value = (mock_conn_obj, "spanner")

    filters = [
        {"column": "query_template_used", "operator": "=", "value": "abc", "logic": "AND"},
        {"column": "query_explanation", "operator": "!=", "value": "def", "logic": "AND"}
    ]

    response = client.post("/api/history", json={"backend": "spanner", "filters": filters})

    assert response.status_code == 200
    assert response.json() == {"rows": [{"user_prompt": "test_spanner", "query_template_used": "temp_s", "query_template_id": "2", "query_explanation": "exp_s"}]}

    mock_snapshot.execute_sql.assert_called_once()

    called_query = mock_snapshot.execute_sql.call_args[0][0]
    called_kwargs = mock_snapshot.execute_sql.call_args[1]

    assert "WHERE query_template_used = @p0" in called_query
    assert "AND query_explanation != @p1" in called_query

    params = called_kwargs["params"]
    param_types = called_kwargs["param_types"]

    assert params["p0"] == "abc"
    assert params["p1"] == "def"

    assert param_types["p0"] == spanner.param_types.STRING
    assert param_types["p1"] == spanner.param_types.STRING

def test_get_history_spanner_types(mock_get_db_connection):
    mock_conn_obj = MagicMock()
    mock_snapshot = MagicMock()
    mock_snapshot.execute_sql.return_value = []
    mock_conn_obj.snapshot.return_value.__enter__.return_value = mock_snapshot
    mock_get_db_connection.return_value = (mock_conn_obj, "spanner")

    filters = [
        {"column": "query_template_id", "operator": "=", "value": 123},
        {"column": "user_prompt", "operator": "=", "value": True}
    ]

    response = client.post("/api/history", json={"backend": "spanner", "filters": filters})

    assert response.status_code == 200

    called_kwargs = mock_snapshot.execute_sql.call_args[1]
    param_types = called_kwargs["param_types"]

    assert param_types["p0"] == spanner.param_types.INT64
    assert param_types["p1"] == spanner.param_types.BOOL

def test_get_history_sqlalchemy_cast(mock_get_db_connection):
    mock_conn_obj = MagicMock()
    mock_conn = AsyncMock()
    mock_result = MagicMock()

    mock_result.mappings.return_value = []
    mock_conn.execute.return_value = mock_result
    mock_conn_obj.connect.return_value.__aenter__.return_value = mock_conn

    mock_get_db_connection.return_value = (mock_conn_obj, "sqlalchemy")

    filters = [
        {"column": "query_template_id", "operator": "ILIKE", "value": "%123%"}
    ]

    response = client.post("/api/history", json={"backend": "alloydb", "filters": filters})

    assert response.status_code == 200

    called_query = mock_conn.execute.call_args[0][0].text

    assert "CAST(query_template_id AS TEXT) ILIKE :p0" in called_query

def test_get_history_exception(mock_get_db_connection):
    mock_get_db_connection.side_effect = Exception("DB Connection Failed")

    response = client.post("/api/history", json={"backend": "alloydb", "filters": []})

    assert response.status_code == 500
    assert "DB Connection Failed" in response.json()["detail"]
