#!/bin/bash
set -e

# Resolve project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"
echo "📂 Project Root: $PROJECT_ROOT"

# Load environment variables
# Load environment variables
if [ -f "backend/.env" ]; then
    echo "📄 Loading configuration from backend/.env..."
    set -a
    source backend/.env
    set +a
    # Map GCP_PROJECT_ID to PROJECT_ID for tools.yaml
    if [ -n "$GCP_PROJECT_ID" ] && [ -z "$PROJECT_ID" ]; then
        export PROJECT_ID=$GCP_PROJECT_ID
    fi
else
    echo "❌ backend/.env not found. Please run ./setup_env.sh first."
    exit 1
fi

PROJECT_ID=${GCP_PROJECT_ID:-$(gcloud config get-value project)}
REGION=${GCP_LOCATION:-"europe-west1"}
ALLOYDB_CLUSTER_ID=${ALLOYDB_CLUSTER_ID:-search-cluster}
ALLOYDB_INSTANCE_ID=${ALLOYDB_INSTANCE_ID:-search-primary}
INSTANCE_CONNECTION_NAME="projects/${PROJECT_ID}/locations/${REGION}/clusters/${ALLOYDB_CLUSTER_ID}/instances/${ALLOYDB_INSTANCE_ID}"
INSTANCE_URI="${INSTANCE_CONNECTION_NAME}"

SPANNER_INSTANCE_ID=${SPANNER_INSTANCE_ID:-search-instance}
SPANNER_DATABASE_ID=${SPANNER_DATABASE_ID:-search-db}
CLOUDSQL_PG_INSTANCE_ID=${CLOUDSQL_PG_INSTANCE_ID:-search-pg}
CLOUDSQL_PG_DB_NAME=${CLOUDSQL_PG_DB_NAME:-search}

# Validation
if [ -z "${AGENT_CONTEXT_SET_ID_ALLOYDB:-}" ] || [ -z "${AGENT_CONTEXT_SET_ID_CLOUDSQL_PG:-}" ] || [ -z "${AGENT_CONTEXT_SET_ID_SPANNER:-}" ]; then
    echo "⚠️  AGENT_CONTEXT_SET_ID variables are not fully set!"
    echo "   Please set AGENT_CONTEXT_SET_ID_ALLOYDB, AGENT_CONTEXT_SET_ID_CLOUDSQL_PG, and AGENT_CONTEXT_SET_ID_SPANNER in backend/.env or export them before running this script."
    exit 1
fi

# 1. Prepare Configuration
echo "🔧 Preparing configuration..."

# Generate resolved tools configuration
cd backend/mcp_server
envsubst < tools.yaml > tools_resolved.yaml
cd ../..

# Cleanup function
cleanup() {
    echo "🧹 Stopping containers and closing SSH tunnel..."
    docker stop search-backend search-frontend agent-service toolbox-service 2>/dev/null || true
    pkill -f "ssh.*db-bastion" || true
}
trap cleanup EXIT

# --- PRE-CLEANUP ---
echo "🧹 Cleaning up existing containers..."
docker rm -f search-backend search-frontend agent-service toolbox-service 2>/dev/null || true

# --- BUILD LOCALLY ---
echo "🔨 Building images locally..."
docker build -t local-search-backend backend/
docker build -t local-search-frontend -f frontend/Dockerfile .

# Check if ports are in use
for port in 5432 5433; do
    if lsof -i :$port -t >/dev/null; then
        echo "⚠️  Port $port is in use. Killing existing process..."
        kill -9 $(lsof -i :$port -t)
    fi
done

# 2. Start Auth Proxies (via Bastion Host)
echo "🔒 Establishing SSH Tunnel to Bastion Host..."
gcloud compute ssh db-bastion \
    --tunnel-through-iap \
    --project=$PROJECT_ID \
    --zone=${REGION}-b \
    -- -L 5432:127.0.0.1:5432 -L 5433:127.0.0.1:5433 -N -f

echo "⏳ Waiting for SSH Tunnel and Proxies to initialize (10s)..."
sleep 10


# 3. Run Backend Container
echo "📦 Running Backend Container..."
docker run -d --rm \
    --name search-backend \
    --network host \
    -e PORT=8080 \
    -e GCP_PROJECT_ID=$PROJECT_ID \
    -e GCP_LOCATION=$REGION \
    -e AGENT_CONTEXT_SET_ID_ALLOYDB=$AGENT_CONTEXT_SET_ID_ALLOYDB \
    -e AGENT_CONTEXT_SET_ID_SPANNER=$AGENT_CONTEXT_SET_ID_SPANNER \
    -e AGENT_CONTEXT_SET_ID_CLOUDSQL_PG=$AGENT_CONTEXT_SET_ID_CLOUDSQL_PG \
    -e DB_HOST=127.0.0.1 \
    -e DB_NAME=${DB_NAME:-search} \
    -e DB_USER=${DB_USER:-postgres} \
    -e DB_PASS=${DB_PASSWORD:-${DB_PASS}} \
    -e SPANNER_INSTANCE_ID=$SPANNER_INSTANCE_ID \
    -e SPANNER_DATABASE_ID=$SPANNER_DATABASE_ID \
    -e CLOUDSQL_PG_HOST=127.0.0.1 \
    -e CLOUDSQL_PG_PORT=5433 \
    -e CLOUDSQL_PG_USER=${DB_USER:-postgres} \
    -e CLOUDSQL_PG_PASSWORD=${DB_PASSWORD:-${DB_PASS}} \
    -e CLOUDSQL_PG_DB_NAME=$CLOUDSQL_PG_DB_NAME \
    -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/keys.json \
    -v $HOME/.config/gcloud/application_default_credentials.json:/tmp/keys.json:ro \
    local-search-backend

echo "   Backend running on localhost:8080"

# 4. Run Toolbox Container (MCP Server)
echo "📦 Running Toolbox Container..."

# Prepare credentials with correct permissions for Docker
cp $HOME/.config/gcloud/application_default_credentials.json /tmp/adc.json
chmod 644 /tmp/adc.json

# Check if port 8082 is in use
if lsof -i :8082 -t >/dev/null; then
    echo "   ⚠️  Port 8082 is in use. Killing existing process..."
    kill -9 $(lsof -i :8082 -t)
fi

docker run -d --rm \
    --name toolbox-service \
    --network host \
    -e PORT=8082 \
    -e PROJECT_ID=$PROJECT_ID \
    -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/keys.json \
    -v /tmp/adc.json:/tmp/keys.json:ro \
    -v $(pwd)/backend/mcp_server/tools_resolved.yaml:/secrets/tools.yaml:ro \
    us-central1-docker.pkg.dev/database-toolbox/toolbox/toolbox:latest \
    --tools-file=/secrets/tools.yaml --address=0.0.0.0 --port=8082 --ui

echo "   Toolbox running on localhost:8082"

# 5. Run Agent Container
echo "📦 Running Agent Container..."
# Try to build agent, but warn if it fails (likely due to missing google-adk)
if docker build -t local-agent-service backend/agent/; then
    docker run -d --rm \
        --name agent-service \
        --network host \
        -e PORT=8083 \
        -e GOOGLE_CLOUD_PROJECT=$PROJECT_ID \
        -e GOOGLE_CLOUD_REGION="$REGION" \
        -e GOOGLE_GENAI_USE_VERTEXAI=true \
        -e GOOGLE_CLOUD_LOCATION="global" \
        -e TOOLBOX_URL="http://localhost:8082" \
        -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/keys.json \
        -v $HOME/.config/gcloud/application_default_credentials.json:/tmp/keys.json:ro \
        local-agent-service
    echo "   Agent running on localhost:8083"
else
    echo "⚠️  WARNING: Failed to build Agent image (likely google-adk missing)."
    echo "⚠️  The 'AI Agent' chat feature will be unavailable."
fi

# 6. Run Frontend Container
echo "📦 Running Frontend Container..."
docker run -d --rm \
    --name search-frontend \
    --network host \
    -e PORT=8081 \
    -e BACKEND_URL="http://localhost:8080" \
    -e AGENT_URL="http://localhost:8083" \
    local-search-frontend

echo "   Frontend running on localhost:8081"
echo "🎉 Debug environment ready!"
echo "   Frontend: http://localhost:8081"
echo "   Backend logs: sudo docker logs -f search-backend"
echo "   Frontend logs: sudo docker logs -f search-frontend"
echo "   Press Ctrl+C to stop."

# Keep script running to maintain trap
while true; do sleep 1; done
