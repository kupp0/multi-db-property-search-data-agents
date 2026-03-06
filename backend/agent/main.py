import os

# Disable Spanner metrics export to prevent Cloud Run errors
os.environ["SPANNER_ENABLE_METRICS"] = "false"

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agent import get_agent

from google.adk import Runner
from google.adk.sessions import InMemorySessionService

from fastapi.middleware.cors import CORSMiddleware
import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from google.cloud import spanner

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database Configuration
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "Welcome01")
DB_NAME = os.environ.get("DB_NAME", "search")

CLOUDSQL_PG_HOST = os.getenv("CLOUDSQL_PG_HOST", "127.0.0.1")
CLOUDSQL_PG_PORT = os.getenv("CLOUDSQL_PG_PORT", "5433")
CLOUDSQL_PG_USER = os.getenv("CLOUDSQL_PG_USER", "postgres")
CLOUDSQL_PG_PASSWORD = os.getenv("CLOUDSQL_PG_PASSWORD")
CLOUDSQL_PG_DB_NAME = os.getenv("CLOUDSQL_PG_DB_NAME", "search")

SPANNER_INSTANCE_ID = os.getenv("SPANNER_INSTANCE_ID", "search-instance")
SPANNER_DATABASE_ID = os.getenv("SPANNER_DATABASE_ID", "search-db")
PROJECT_ID = os.getenv("GCP_PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT")

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
    print("Database engines disposed.")

# Initialize Session Service
session_service = InMemorySessionService()

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default_session"
    backend: str = "alloydb"

from typing import Any, Optional

class ChatResponse(BaseModel):
    response: str
    tool_details: Optional[Any] = None
    used_prompt: Optional[str] = None

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # Use Runner to execute the agent
        user_id = "default_user"
        session_id = request.session_id
        app_name = f"property_agent_{request.backend}"
        
        # Instantiate the dynamic agent for this specific backend
        dynamic_agent = get_agent(request.backend)
        runner = Runner(agent=dynamic_agent, app_name=app_name, session_service=session_service)
        
        # Ensure session exists
        session = await session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
        if not session:

            await session_service.create_session(app_name=app_name, user_id=user_id, session_id=session_id)
        
        response_text = ""
        tool_details = None
        used_prompt = None
        
        # Runner.run_async returns AsyncGenerator[Event, None]
        # We need to pass new_message as google.genai.types.Content
        
        from google.genai.types import Content, Part
        import json
        
        message = Content(role="user", parts=[Part(text=request.message)])
        
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=message
        ):
            # DEBUG: Print event type and attributes
            print(f"DEBUG: Received event type: {type(event)}")
            # print(f"DEBUG: Event attributes: {dir(event)}")
            
            # Capture Tool Call (the prompt sent to the tool)
            if hasattr(event, 'tool_call') and event.tool_call:
                print(f"DEBUG: Found tool_call in event")
                # Assuming single tool call for now
                # event.tool_call might be a ToolCall object with 'function_calls'
                if hasattr(event.tool_call, 'function_calls'):
                    for fc in event.tool_call.function_calls:
                        if 'prompt' in fc.args:
                            used_prompt = fc.args['prompt']
                            print(f"DEBUG: Captured tool prompt: {used_prompt}")

            # Capture Tool Response (the output from the tool)
            if hasattr(event, 'tool_response') and event.tool_response:
                 print(f"DEBUG: Found tool_response in event")
                 if hasattr(event.tool_response, 'function_responses'):
                    for fr in event.tool_response.function_responses:
                        # The tool returns a JSON string in 'response' field (usually)
                        # We need to parse it.
                        try:
                            print(f"DEBUG: Processing function response: {fr.name}")
                            # The response content is likely in fr.response
                            # But structure depends on ADK/GenAI types.
                            # Let's inspect what we can.
                            # For GDA tool, it returns a dict which is then JSON serialized.
                            
                            response_payload = fr.response
                            print(f"DEBUG: Raw response payload type: {type(response_payload)}")
                            
                            # If fr.response is a dict:
                            if isinstance(response_payload, dict):
                                if 'result' in response_payload:
                                     tool_details = response_payload['result']
                                else:
                                     tool_details = response_payload
                                
                                # If tool_details is a string (e.g. nested JSON), try to parse it
                                if isinstance(tool_details, str):
                                    try:
                                        tool_details = json.loads(tool_details)
                                    except Exception:
                                        pass # Keep as string if parsing fails

                            # If it's a string, try to parse
                            elif isinstance(response_payload, str):
                                try:
                                    tool_details = json.loads(response_payload)
                                except Exception:
                                    tool_details = response_payload # Keep as string
                                
                            print(f"DEBUG: Captured tool details keys: {tool_details.keys() if isinstance(tool_details, dict) else 'Not a dict'}")
                        except Exception as e:
                            print(f"DEBUG: Failed to parse tool response: {e}")

            
            # Extract text response
            if hasattr(event, 'content') and event.content:
                for part in event.content.parts or []:
                    if part.text:
                        response_text += part.text
            elif hasattr(event, 'text') and event.text:
                response_text += event.text
            
        # Log to Database
        try:
            conn_obj, conn_type = await get_db_connection(request.backend)
            # Only save if a tool was used (used_prompt is set)
            if used_prompt:
                # Determine template usage (basic logic for now, can be improved if tool details has it)
                query_template_used = False
                query_template_id = None
                query_explanation = None
                
                # If tool_details has explanation, use it
                if tool_details and isinstance(tool_details, dict):
                    query_explanation = tool_details.get('intentExplanation') or tool_details.get('explanation')
                
                if conn_type == "sqlalchemy":
                    async with conn_obj.begin() as conn:
                        await conn.execute(
                            text("""
                            INSERT INTO user_prompt_history 
                            (user_prompt, query_template_used, query_template_id, query_explanation)
                            VALUES (:prompt, :used, :id, :explanation)
                            """),
                            {
                                "prompt": request.message, 
                                "used": query_template_used, 
                                "id": query_template_id,
                                "explanation": query_explanation
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
                                "prompt": request.message, 
                                "used": query_template_used, 
                                "id": query_template_id,
                                "explanation": query_explanation
                            },
                            param_types={
                                "prompt": spanner.param_types.STRING,
                                "used": spanner.param_types.BOOL,
                                "id": spanner.param_types.INT64,
                                "explanation": spanner.param_types.STRING
                            }
                        )
                    conn_obj.run_in_transaction(insert_history)

            print(f"User prompt history saved (Agent) to {request.backend}.")
        except Exception as db_err:
            print(f"Failed to save user prompt history (Agent) to {request.backend}: {db_err}")

        print(f"DEBUG: Final response text: {response_text}")
        return ChatResponse(
            response=response_text or "Agent executed (no text response)",
            tool_details=tool_details,
            used_prompt=used_prompt
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return ChatResponse(response=f"I encountered an issue processing your request: {str(e)}")

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
