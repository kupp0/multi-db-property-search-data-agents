import os

# Disable Spanner metrics export to prevent Cloud Run errors
os.environ["SPANNER_ENABLE_METRICS"] = "false"
os.environ["SPANNER_DISABLE_BUILTIN_METRICS"] = "true"
os.environ["GOOGLE_CLOUD_SPANNER_ENABLE_METRICS"] = "false"
os.environ["OTEL_SDK_DISABLED"] = "true"

import json
import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import google.auth
from google.cloud import storage
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import logging
import sys
import re
from typing import List, Any
from sqlalchemy import table, column, select, cast, String, or_, and_
from google.cloud import spanner
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
AGENT_CONTEXT_SET_ID_CLOUDSQL_MYSQL = os.getenv("AGENT_CONTEXT_SET_ID_CLOUDSQL_MYSQL")

# Security: SSRF Protection
# Explicitly whitelist the allowed GCS bucket for image serving.
# If not set, default to the convention used by bootstrap_images.py if PROJECT_ID is available.
ALLOWED_GCS_BUCKET = os.getenv("ALLOWED_GCS_BUCKET")
if not ALLOWED_GCS_BUCKET and PROJECT_ID:
    ALLOWED_GCS_BUCKET = f"property-images-data-agent-{PROJECT_ID}"
    logger.info(f"ALLOWED_GCS_BUCKET not set. Defaulting to: {ALLOWED_GCS_BUCKET}")
elif ALLOWED_GCS_BUCKET:
    logger.info(f"ALLOWED_GCS_BUCKET set to: {ALLOWED_GCS_BUCKET}")
else:
    logger.warning("ALLOWED_GCS_BUCKET not set and PROJECT_ID unavailable. Image serving security check may fail open or block all requests depending on implementation.")

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

# Cloud SQL MySQL Configuration
CLOUDSQL_MYSQL_HOST = os.getenv("CLOUDSQL_MYSQL_HOST", "127.0.0.1")
CLOUDSQL_MYSQL_PORT = os.getenv("CLOUDSQL_MYSQL_PORT", "3306")
CLOUDSQL_MYSQL_USER = os.getenv("CLOUDSQL_MYSQL_USER", "mysql")
CLOUDSQL_MYSQL_PASSWORD = os.getenv("CLOUDSQL_MYSQL_PASSWORD")
CLOUDSQL_MYSQL_DB_NAME = os.getenv("CLOUDSQL_MYSQL_DB_NAME", "search")


# Spanner Configuration
SPANNER_INSTANCE_ID = os.getenv("SPANNER_INSTANCE_ID", "search-instance")
SPANNER_DATABASE_ID = os.getenv("SPANNER_DATABASE_ID", "search-db")

# Global DB Engines/Clients
engines = {}
spanner_client = None
spanner_db = None

async def get_db_connection(backend: str):
    global engines, spanner_client, spanner_db
    
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
        
    elif backend == "cloudsql_mysql":
        if "cloudsql_mysql" not in engines:
            # 65536 is the value for pymysql.constants.CLIENT.MULTI_STATEMENTS
            # This is required because the GDA context queries for MySQL use multiple statements
            # (e.g., SELECT ... INTO @var; SELECT ...)
            db_url = f"mysql+aiomysql://{CLOUDSQL_MYSQL_USER}:{CLOUDSQL_MYSQL_PASSWORD}@{CLOUDSQL_MYSQL_HOST}:{CLOUDSQL_MYSQL_PORT}/{CLOUDSQL_MYSQL_DB_NAME}?client_flag=65536"
            engines["cloudsql_mysql"] = create_async_engine(db_url)
        return engines["cloudsql_mysql"], "sqlalchemy"
        

    elif backend == "spanner":
        if not spanner_db:
            if not spanner_client:
                # Explicitly disable metrics to prevent Cloud Run errors
                # and configure keepalive to prevent _InactiveRpcError
                client_options = {"api_endpoint": "spanner.googleapis.com"}
                spanner_client = spanner.Client(
                    project=PROJECT_ID, 
                    client_options=client_options
                )
            instance = spanner_client.instance(SPANNER_INSTANCE_ID)
            spanner_db = instance.database(SPANNER_DATABASE_ID)
        return spanner_db, "spanner"
        
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
        datasource_references["spannerReference"] = {
            "databaseReference": {
                "engine": "GOOGLE_SQL",
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
    elif backend == "cloudsql_mysql":
        if not AGENT_CONTEXT_SET_ID_CLOUDSQL_MYSQL:
            raise HTTPException(500, "AGENT_CONTEXT_SET_ID_CLOUDSQL_MYSQL is not configured.")
        datasource_references["cloudSqlReference"] = {
            "databaseReference": {
                "engine": "MYSQL",
                "project_id": PROJECT_ID,
                "region": os.getenv("GCP_LOCATION", gda_location),
                "instance_id": os.getenv("CLOUDSQL_MYSQL_INSTANCE_ID", "search-mysql"),
                "database_id": CLOUDSQL_MYSQL_DB_NAME
            },
            "agentContextReference": {"context_set_id": AGENT_CONTEXT_SET_ID_CLOUDSQL_MYSQL}
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

        # Security Check: SSRF Protection
        # Verify that the requested bucket is the allowed one.
        if ALLOWED_GCS_BUCKET:
            if bucket_name != ALLOWED_GCS_BUCKET:
                logger.warning(f"Blocked SSRF attempt. Requested bucket: '{bucket_name}', Allowed: '{ALLOWED_GCS_BUCKET}'")
                raise HTTPException(403, "Access to this bucket is restricted.")
        else:
             # Fail secure if no allowed bucket is configured
             logger.error("ALLOWED_GCS_BUCKET is not configured. Rejecting request to prevent SSRF.")
             raise HTTPException(500, "Server configuration error: Image source not trusted.")

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

    except HTTPException:
        raise
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
                if item.get("image_gcs_uri") and item["image_gcs_uri"] != "NULL":
                    item["image_gcs_uri"] = f"/api/image?gcs_uri={item['image_gcs_uri']}"
                else:
                    item["image_gcs_uri"] = None
                
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
                        (user_prompt, query_template_used, query_template_id, query_explanation, timestamp)
                        VALUES (@prompt, @used, @id, @explanation, PENDING_COMMIT_TIMESTAMP())
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
        
        ALLOWED_COLUMNS = {"user_prompt", "query_template_used", "query_template_id", "query_explanation", "timestamp"}
        ALLOWED_OPERATORS = {"=", "!=", "LIKE", "ILIKE", ">", "<", ">=", "<="}
        
        rows = []

        if conn_type == "sqlalchemy":
            t = table("user_prompt_history",
                column("user_prompt"),
                column("query_template_used"),
                column("query_template_id"),
                column("query_explanation"),
                column("id"),
                column("timestamp")
            )
            stmt = select(
                t.c.user_prompt,
                t.c.query_template_used,
                t.c.query_template_id,
                t.c.query_explanation,
                t.c.timestamp
            )

            combined_expr = None

            if request.filters:
                for idx, f in enumerate(request.filters):
                    if f.column not in ALLOWED_COLUMNS:
                        continue
                    if f.operator not in ALLOWED_OPERATORS:
                        continue

                    col = t.c[f.column]
                    if f.column in ("query_template_id", "query_template_used") and f.operator.upper() in ("LIKE", "ILIKE"):
                        col = cast(col, String)

                    op = f.operator.upper()
                    param_value = f.value
                    
                    if op in ("LIKE", "ILIKE"):
                        if not str(param_value).startswith("%") and not str(param_value).endswith("%"):
                            param_value = f"%{param_value}%"

                    if op == "=":
                        expr = col == param_value
                    elif op == "!=":
                        expr = col != param_value
                    elif op == ">":
                        expr = col > param_value
                    elif op == "<":
                        expr = col < param_value
                    elif op == ">=":
                        expr = col >= param_value
                    elif op == "<=":
                        expr = col <= param_value
                    elif op == "LIKE":
                        expr = col.like(param_value)
                    elif op == "ILIKE":
                        expr = col.ilike(param_value)

                    if combined_expr is None:
                        combined_expr = expr
                    else:
                        logic_op = f.logic.upper() if f.logic.upper() in ("AND", "OR") else "AND"
                        if logic_op == "OR":
                            combined_expr = or_(combined_expr, expr)
                        else:
                            combined_expr = and_(combined_expr, expr)

            if combined_expr is not None:
                stmt = stmt.where(combined_expr)
            stmt = stmt.order_by(t.c.timestamp.desc()).limit(1000)

            async with conn_obj.connect() as conn:
                result = await conn.execute(stmt)
                rows = [dict(row) for row in result.mappings()]

        elif conn_type == "spanner":
            base_query = """
                SELECT user_prompt, query_template_used, query_template_id, query_explanation, timestamp
                FROM user_prompt_history
            """
            params = {}
            spanner_param_types = {}
            query_str = base_query
            first_condition = True

            if request.filters:
                for idx, f in enumerate(request.filters):
                    if f.column not in ALLOWED_COLUMNS:
                        continue
                    if f.operator not in ALLOWED_OPERATORS:
                        continue

                    param_name = f"p{idx}"

                    # Ensure strict usage of allowed string values instead of formatting from user input
                    safe_column = next(col for col in ALLOWED_COLUMNS if col == f.column)
                    safe_operator = next(op for op in ALLOWED_OPERATORS if op == f.operator)

                    param_value = f.value
                    if safe_operator in ("LIKE", "ILIKE"):
                        if not str(param_value).startswith("%") and not str(param_value).endswith("%"):
                            param_value = f"%{param_value}%"

                    if safe_operator == "ILIKE":
                        clause = f"LOWER({safe_column}) LIKE LOWER(@{param_name})"
                    elif safe_operator == "LIKE":
                        clause = f"{safe_column} LIKE @{param_name}"
                    else:
                        clause = f"{safe_column} {safe_operator} @{param_name}"
                        
                    params[param_name] = param_value

                    # Basic type mapping for Spanner
                    if isinstance(param_value, bool):
                        spanner_param_types[param_name] = spanner.param_types.BOOL
                    elif isinstance(param_value, int):
                        spanner_param_types[param_name] = spanner.param_types.INT64
                    else:
                        spanner_param_types[param_name] = spanner.param_types.STRING

                    if first_condition:
                        query_str += f" WHERE {clause}"
                        first_condition = False
                    else:
                        logic_op = f.logic.upper() if f.logic.upper() in ("AND", "OR") else "AND"
                        query_str += f" {logic_op} {clause}"

            query_str += " ORDER BY timestamp DESC LIMIT 1000"

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
                        "query_explanation": row[3],
                        "timestamp": row[4] if len(row) > 4 else None
                    })
            
        return {"rows": rows}
        
    except Exception as e:
        logger.error(f"History fetch failed: {e}")
        raise HTTPException(500, f"Failed to fetch history: {e}")
