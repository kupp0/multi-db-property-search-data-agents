import os
import json
import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import google.auth
from google.cloud import storage
import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import logging
import sys
import re
from typing import List, Optional, Any
from sqlalchemy import text, bindparam
from google.cloud import spanner
import aiomysql

# ==============================================================================
# LOGGING CONFIGURATION
# ==============================================================================
# Configure JSON-style logging for production
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)
# ==============================================================================
# CONFIGURATION & INITIALIZATION
# ==============================================================================

# Load environment variables from .env file
backend_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(backend_dir, '.env')
load_dotenv(dotenv_path=dotenv_path)

app = FastAPI(title="AlloyDB Property Search Demo")

# Configure CORS
# In production, this should be restricted to specific domains.
ALLOWED_ORIGINS_STR = os.getenv("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS_STR.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Google Cloud Clients
storage_client = None
PROJECT_ID = os.getenv("GCP_PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT")
AGENT_CONTEXT_SET_ID_ALLOYDB = os.getenv("AGENT_CONTEXT_SET_ID_ALLOYDB")
AGENT_CONTEXT_SET_ID_CLOUDSQL_PG = os.getenv("AGENT_CONTEXT_SET_ID_CLOUDSQL_PG")
AGENT_CONTEXT_SET_ID_SPANNER = os.getenv("AGENT_CONTEXT_SET_ID_SPANNER")

try:
    # Initialize credentials with Cloud Platform scope
    credentials, _ = google.auth.default(
        scopes=['https://www.googleapis.com/auth/cloud-platform']
    )
    
    # Initialize Storage Client for image serving
    storage_client = storage.Client(project=PROJECT_ID, credentials=credentials)
    print("Google Cloud Storage client initialized successfully.")
    
except Exception as e:
    print(f"Warning: Google Cloud initialization failed. Image serving may not work.\nError: {e}")

# AlloyDB Configuration
# AlloyDB Configuration
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_NAME = os.environ.get("DB_NAME", "search")

# Cloud SQL PG Configuration
CLOUDSQL_PG_HOST = os.getenv("CLOUDSQL_PG_HOST", "127.0.0.1")
CLOUDSQL_PG_PORT = os.getenv("CLOUDSQL_PG_PORT", "5433")
CLOUDSQL_PG_USER = os.getenv("CLOUDSQL_PG_USER", "postgres")
CLOUDSQL_PG_PASSWORD = os.getenv("CLOUDSQL_PG_PASSWORD")
CLOUDSQL_PG_DB_NAME = os.getenv("CLOUDSQL_PG_DB_NAME", "search")


# Spanner Configuration
SPANNER_INSTANCE_ID = os.getenv("SPANNER_INSTANCE_ID", "search-instance")
SPANNER_DATABASE_ID = os.getenv("SPANNER_DATABASE_ID", "search-db")

# Global DB Engines/Clients
engines = {}
spanner_client = None

async def get_db_connection(backend: str):
    global engines, spanner_client
    
    if backend == "alloydb":
        if "alloydb" not in engines:
            db_url = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:5432/{DB_NAME}"
            engines["alloydb"] = create_async_engine(db_url)
        return engines["alloydb"], "sqlalchemy"
        
    elif backend == "cloudsql_pg":
        if "cloudsql_pg" not in engines:
            db_url = f"postgresql+asyncpg://{CLOUDSQL_PG_USER}:{CLOUDSQL_PG_PASSWORD}@{CLOUDSQL_PG_HOST}:{CLOUDSQL_PG_PORT}/{CLOUDSQL_PG_DB_NAME}"
            engines["cloudsql_pg"] = create_async_engine(db_url)
        return engines["cloudsql_pg"], "sqlalchemy"
        

    elif backend == "spanner":
        if not spanner_client:
            spanner_client = spanner.Client(project=PROJECT_ID)
        instance = spanner_client.instance(SPANNER_INSTANCE_ID)
        database = instance.database(SPANNER_DATABASE_ID)
        return database, "spanner"
        
    else:
        raise ValueError(f"Unknown backend: {backend}")

@app.on_event("shutdown")
async def shutdown_event():
    for engine in engines.values():
        await engine.dispose()
    logger.info("Database engines disposed.")

# ==============================================================================
# DATA MODELS
# ==============================================================================

class SearchRequest(BaseModel):
    query: str
    backend: str = "alloydb"

class FilterCondition(BaseModel):
    column: str
    operator: str
    value: Any
    logic: str = "AND"

class HistoryRequest(BaseModel):
    backend: str = "alloydb"
    filters: List[FilterCondition] = []

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

# Global variable to cache GDA credentials
_gda_credentials = None

def get_gda_credentials():
    """
    Retrieves and caches Google credentials for GDA access.
    This optimization prevents repetitive file I/O or metadata server calls.
    """
    global _gda_credentials
    scopes = ['https://www.googleapis.com/auth/cloud-platform', 'https://www.googleapis.com/auth/userinfo.email']

    if _gda_credentials is None:
        _gda_credentials, _ = google.auth.default(scopes=scopes)

    if not _gda_credentials.valid:
        _gda_credentials.refresh(google.auth.transport.requests.Request())

    return _gda_credentials

def query_gda(prompt: str, backend: str = "alloydb") -> dict:
    """
    Queries the Gemini Data Agent (GDA) API to get property listings and natural language answers.
    """
    # GDA API Endpoint
    gda_location = os.getenv("GCP_LOCATION", "europe-west1")
    url = f"https://geminidataanalytics.googleapis.com/v1beta/projects/{PROJECT_ID}/locations/{gda_location}:queryData"
    
    # Obtain credentials for the API request
    creds = get_gda_credentials()
    
    headers = {
        "Authorization": f"Bearer {creds.token}",
        "Content-Type": "application/json"
    }
    
    # Construct datasourceReferences based on backend
    datasource_references = {}
    if backend == "alloydb":
        if not AGENT_CONTEXT_SET_ID_ALLOYDB:
            raise HTTPException(500, "AGENT_CONTEXT_SET_ID_ALLOYDB is not configured.")
        datasource_references["alloydb"] = {
            "databaseReference": {
                "project_id": PROJECT_ID,
                "region": os.getenv("GCP_LOCATION", gda_location),
                "cluster_id": os.getenv("ALLOYDB_CLUSTER_ID", "search-cluster"),
                "instance_id": os.getenv("ALLOYDB_INSTANCE_ID", "search-primary"),
                "database_id": DB_NAME
            },
            "agentContextReference": {"context_set_id": AGENT_CONTEXT_SET_ID_ALLOYDB}
        }
    elif backend == "spanner":
        if not AGENT_CONTEXT_SET_ID_SPANNER:
            raise HTTPException(500, "AGENT_CONTEXT_SET_ID_SPANNER is not configured.")
        datasource_references["spanner"] = {
            "databaseReference": {
                "project_id": PROJECT_ID,
                "instance_id": SPANNER_INSTANCE_ID,
                "database_id": SPANNER_DATABASE_ID
            },
            "agentContextReference": {"context_set_id": AGENT_CONTEXT_SET_ID_SPANNER}
        }
    elif backend == "cloudsql_pg":
        if not AGENT_CONTEXT_SET_ID_CLOUDSQL_PG:
            raise HTTPException(500, "AGENT_CONTEXT_SET_ID_CLOUDSQL_PG is not configured.")
        datasource_references["cloudSqlReference"] = {
            "databaseReference": {
                "engine": "POSTGRESQL",
                "project_id": PROJECT_ID,
                "region": os.getenv("GCP_LOCATION", gda_location),
                "instance_id": os.getenv("CLOUDSQL_PG_INSTANCE_ID", "search-pg"),
                "database_id": CLOUDSQL_PG_DB_NAME
            },
            "agentContextReference": {"context_set_id": AGENT_CONTEXT_SET_ID_CLOUDSQL_PG}
        }
    else:
        raise ValueError(f"Unknown backend: {backend}")

    # Construct the GDA API payload
    payload = {
        "parent": f"projects/{PROJECT_ID}/locations/{gda_location}",
        "prompt": prompt,
        "context": {
            "datasourceReferences": datasource_references
        },
        "generation_options": {
            "generate_query_result": True,
            "generate_natural_language_answer": True,
            "generate_explanation": True
        }
    }
    
    try:
        logger.info(f"Sending request to GDA API: {url}")
        resp = requests.post(url, headers=headers, data=json.dumps(payload))
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"GDA API Request Failed: {e}")
        if hasattr(e, 'response') and e.response:
             logger.error(f"GDA Error Response: {e.response.text}")
        raise HTTPException(500, f"Failed to query Gemini Data Agent: {e}")

# ==============================================================================
# API ENDPOINTS
# ==============================================================================

@app.get("/api/image")
async def get_image(gcs_uri: str):
    """
    Serves images from Google Cloud Storage (GCS).
    
    This endpoint acts as a secure proxy, allowing the frontend to display images
    from a private GCS bucket without exposing the bucket publicly.
    It attempts to generate a signed URL for direct access (efficient) or streams
    the file content if signing fails.
    """
    if not storage_client:
        raise HTTPException(500, "Storage client is not initialized.")

    try:
        # Parse the GCS URI to extract bucket and blob names
        if gcs_uri.startswith("gs://"):
            path = gcs_uri[5:]
        elif gcs_uri.startswith("https://storage.googleapis.com/"):
            path = gcs_uri[31:]
        else:
            raise HTTPException(400, "Invalid GCS URI format.")
            
        if "/" not in path:
             raise HTTPException(400, "Invalid GCS URI: Missing object path.")

        bucket_name, blob_name = path.split("/", 1)
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        # Method 1: Generate a Signed URL (Preferred for performance)
        try:
            signed_url = blob.generate_signed_url(
                version="v4",
                expiration=3600, # URL valid for 1 hour
                method="GET"
            )
            return RedirectResponse(
                url=signed_url, 
                status_code=307,
                headers={"Cache-Control": "public, max-age=300"}
            )
        except Exception as sign_err:
            # Method 2: Stream content (Fallback)
            logger.warning(f"Signed URL generation failed, falling back to streaming: {sign_err}")
            file_obj = blob.open("rb")
            return StreamingResponse(
                file_obj, 
                media_type="image/jpeg", 
                headers={"Cache-Control": "public, max-age=86400"}
            )

    except Exception as e:
        logger.error(f"Error serving image: {e}")
        raise HTTPException(404, "Image not found or inaccessible.")

@app.post("/api/search")
async def search_properties(request: SearchRequest):
    """
    Handles property search requests using the Gemini Data Agent.
    
    Accepts a natural language query, sends it to GDA, and returns:
    1. A list of property listings.
    2. The generated SQL query.
    3. A natural language answer.
    4. An explanation of the reasoning (if available).
    """
    logger.info(f"Processing search query: '{request.query}'")
    
    try:
        # Query the Gemini Data Agent
        gda_resp = query_gda(request.query, request.backend)
        
        # Extract components from the response
        nl_answer = gda_resp.get("naturalLanguageAnswer", "")
        query_result = gda_resp.get("queryResult", {})
        rows = query_result.get("rows", [])
        cols = query_result.get("columns", [])
        
        # Process rows into a list of dictionaries
        results = []
        if rows and cols:
            col_names = [c["name"] for c in cols]
            for row in rows:
                values = row.get("values", [])
                
                # Flatten the response structure:
                # GDA returns values as {"value": "actual_value"}, we extract "actual_value".
                # We also filter out large embedding fields to reduce payload size.
                item = {
                    k: (v["value"] if isinstance(v, dict) and "value" in v else v)
                    for k, v in zip(col_names, values)
                    if k not in ("description_embedding", "image_embedding")
                }
                
                # Update image URIs to use the local proxy endpoint
                # This prevents mixed content warnings and handles auth
                if item.get("image_gcs_uri"):
                    item["image_gcs_uri"] = f"/api/image?gcs_uri={item['image_gcs_uri']}"
                
                results.append(item)
        
        # Construct the System Output for the UI
        generated_sql = gda_resp.get("generatedQuery") or gda_resp.get("queryResult", {}).get("query", "SQL not returned by GDA")
        explanation = gda_resp.get('intentExplanation', '')
        total_row_count = gda_resp.get("queryResult", {}).get("totalRowCount", "0")
        
        # Create a preview of the raw query results (first 3 rows)
        query_result_preview = {
            "columns": cols,
            "rows": rows[:3] if rows else []
        }
        
        display_sql = f"// GEMINI DATA AGENT CALL\n// Generated SQL: {generated_sql}\n// Answer: {nl_answer}"
        if explanation:
            display_sql += f"\n// Explanation: {explanation}"
        
        # Log to Database
        try:
            conn_obj, conn_type = await get_db_connection(request.backend)
            
            # Determine template usage
            query_template_used = False
            query_template_id = None
            
            if explanation:
                match = re.search(r"Template\s+(\d+)", explanation, re.IGNORECASE)
                if match:
                    query_template_used = True
                    query_template_id = int(match.group(1))
            
            if conn_type == "sqlalchemy":
                async with conn_obj.begin() as conn:
                    await conn.execute(
                        text("""
                        INSERT INTO user_prompt_history 
                        (user_prompt, query_template_used, query_template_id, query_explanation)
                        VALUES (:prompt, :used, :id, :explanation)
                        """),
                        {
                            "prompt": request.query, 
                            "used": query_template_used, 
                            "id": query_template_id,
                            "explanation": explanation
                        }
                    )
            elif conn_type == "spanner":
                def insert_history(transaction):
                    transaction.execute_update(
                        """
                        INSERT INTO user_prompt_history 
                        (user_prompt, query_template_used, query_template_id, query_explanation)
                        VALUES (@prompt, @used, @id, @explanation)
                        """,
                        params={
                            "prompt": request.query, 
                            "used": query_template_used, 
                            "id": query_template_id,
                            "explanation": explanation
                        },
                        param_types={
                            "prompt": spanner.param_types.STRING,
                            "used": spanner.param_types.BOOL,
                            "id": spanner.param_types.INT64,
                            "explanation": spanner.param_types.STRING
                        }
                    )
                conn_obj.run_in_transaction(insert_history)

            logger.info(f"User prompt history saved to {request.backend}.")
        except Exception as db_err:
            logger.error(f"Failed to save user prompt history to {request.backend}: {db_err}")

        return {
            "listings": results, 
            "sql": display_sql, 
            "nl_answer": nl_answer,
            "details": {
                "generated_query": generated_sql,
                "intent_explanation": explanation,
                "total_row_count": total_row_count,
                "query_result_preview": query_result_preview
            }
        }

    except Exception as e:
        logger.error(f"Search failed: {e}")
        return {
            "listings": [], 
            "sql": f"An error occurred during search: {str(e)}",
            "nl_answer": "I encountered an error while processing your request."
        }

@app.post("/api/history")
async def get_history(request: HistoryRequest):
    """
    Retrieves user prompt history using direct DB connection.
    Supports structured filtering to prevent SQL injection.
    """
    try:
        conn_obj, conn_type = await get_db_connection(request.backend)
        
        base_query = """
            SELECT user_prompt, query_template_used, query_template_id, query_explanation 
            FROM user_prompt_history
        """
        
        conditions = []
        params = {}
        spanner_param_types = {}
        
        ALLOWED_COLUMNS = {"user_prompt", "query_template_used", "query_template_id", "query_explanation"}
        ALLOWED_OPERATORS = {"=", "!=", "LIKE", "ILIKE", ">", "<", ">=", "<="}
        
        query_str = base_query
        first_condition = True

        if request.filters:
            for idx, f in enumerate(request.filters):
                if f.column not in ALLOWED_COLUMNS:
                    continue
                if f.operator not in ALLOWED_OPERATORS:
                    continue
                
                param_name = f"p{idx}"
                column_expr = f.column
                
                if conn_type == "sqlalchemy":
                    if f.column in ("query_template_id", "query_template_used") and f.operator.upper() in ("LIKE", "ILIKE"):
                        column_expr = f"CAST({f.column} AS TEXT)"
                    clause = f"{column_expr} {f.operator} :{param_name}"
                    params[param_name] = f.value
                else: # Spanner
                    clause = f"{column_expr} {f.operator} @{param_name}"
                    params[param_name] = f.value
                    # Basic type mapping for Spanner
                    if isinstance(f.value, bool):
                        spanner_param_types[param_name] = spanner.param_types.BOOL
                    elif isinstance(f.value, int):
                        spanner_param_types[param_name] = spanner.param_types.INT64
                    else:
                        spanner_param_types[param_name] = spanner.param_types.STRING
                
                if first_condition:
                    query_str += f" WHERE {clause}"
                    first_condition = False
                else:
                    logic_op = f.logic.upper() if f.logic.upper() in ("AND", "OR") else "AND"
                    query_str += f" {logic_op} {clause}"

        query_str += " LIMIT 1000"
        
        rows = []
        if conn_type == "sqlalchemy":
            async with conn_obj.connect() as conn:
                result = await conn.execute(text(query_str), params)
                rows = [dict(row) for row in result.mappings()]
        elif conn_type == "spanner":
            with conn_obj.snapshot() as snapshot:
                results = snapshot.execute_sql(
                    query_str,
                    params=params,
                    param_types=spanner_param_types
                )
                # Spanner returns a list of lists, we need to map to dicts
                for row in results:
                    rows.append({
                        "user_prompt": row[0],
                        "query_template_used": row[1],
                        "query_template_id": row[2],
                        "query_explanation": row[3]
                    })
            
        return {"rows": rows}
        
    except Exception as e:
        logger.error(f"History fetch failed: {e}")
        raise HTTPException(500, f"Failed to fetch history: {e}")
