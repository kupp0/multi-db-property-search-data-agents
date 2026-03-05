#!/bin/bash
set -euo pipefail

# ==============================================================================
# DEPLOYMENT SCRIPT
# ==============================================================================
# This script deploys the Data Agent services (Backend, Frontend, Agent) to Cloud Run.
# It assumes Terraform has already been applied and necessary infrastructure exists.
#
# Usage: ./scripts/deploy.sh
# ==============================================================================

# --- 1. PRE-FLIGHT CHECKS ---

command -v gcloud >/dev/null 2>&1 || { echo "❌ 'gcloud' is required but not installed. Aborting." >&2; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "❌ 'docker' is required but not installed. Aborting." >&2; exit 1; }
command -v envsubst >/dev/null 2>&1 || { echo "❌ 'envsubst' is required but not installed. Aborting." >&2; exit 1; }

# Resolve project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"
echo "📂 Project Root: $PROJECT_ROOT"

# --- 2. CONFIGURATION ---

# Source .env if it exists
if [ -f "backend/.env" ]; then
    echo "📄 Sourcing backend/.env..."
    set -a
    source backend/.env
    set +a
fi

# Set Defaults (can be overridden by env vars)
export PROJECT_ID=$(gcloud config get-value project)
export GCP_LOCATION=${GCP_LOCATION:-europe-west1}
export REGION=$GCP_LOCATION

# AlloyDB Config
export ALLOYDB_CLUSTER_ID=${ALLOYDB_CLUSTER_ID:-search-cluster}
export ALLOYDB_INSTANCE_ID=${ALLOYDB_INSTANCE_ID:-search-primary}
export INSTANCE_CONNECTION_NAME="projects/${PROJECT_ID}/locations/${REGION}/clusters/${ALLOYDB_CLUSTER_ID}/instances/${ALLOYDB_INSTANCE_ID}"

# Database Credentials (Defaults match Terraform/setup)
export DB_PASSWORD=${DB_PASSWORD:-Welcome01}
export DB_USER=${DB_USER:-postgres}
export DB_NAME=${DB_NAME:-search}
# For Cloud Run with Sidecar, DB_HOST is always localhost
export DB_HOST=127.0.0.1

REPO_NAME="search-app-repo"

# Service Names
export BACKEND_SERVICE="data-agent-search-backend"
export FRONTEND_SERVICE="data-agent-search-frontend"
export AGENT_SERVICE="data-agent-service"

# Service Account
export SERVICE_ACCOUNT="search-backend-sa@${PROJECT_ID}.iam.gserviceaccount.com"

# Images
export BACKEND_IMAGE="europe-west1-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${BACKEND_SERVICE}"
export FRONTEND_IMAGE="europe-west1-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${FRONTEND_SERVICE}"
export AGENT_IMAGE="europe-west1-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${AGENT_SERVICE}"

export TAG=$(date +%Y%m%d-%H%M%S)

echo "🚀 Starting Deployment..."
echo "   Project: ${PROJECT_ID}"
echo "   Region: ${REGION}"
echo "   Tag: ${TAG}"

# Validation
if [ -z "${AGENT_CONTEXT_SET_ID_ALLOYDB:-}" ] || [ -z "${AGENT_CONTEXT_SET_ID_CLOUDSQL_PG:-}" ] || [ -z "${AGENT_CONTEXT_SET_ID_SPANNER:-}" ]; then
    echo "⚠️  AGENT_CONTEXT_SET_ID variables are not fully set!"
    echo "   Please set AGENT_CONTEXT_SET_ID_ALLOYDB, AGENT_CONTEXT_SET_ID_CLOUDSQL_PG, and AGENT_CONTEXT_SET_ID_SPANNER in backend/.env or export them before running this script."
    exit 1
fi

# --- 3. SETUP (APIs & IAM) ---
# Note: Ideally handled by Terraform, but kept here for robustness/idempotency

echo "🔧 Verifying APIs..."
gcloud services enable \
    alloydb.googleapis.com \
    geminidataanalytics.googleapis.com \
    aiplatform.googleapis.com \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    secretmanager.googleapis.com \
    --project "${PROJECT_ID}" >/dev/null

echo "👤 Verifying Service Account: ${SERVICE_ACCOUNT}..."
if ! gcloud iam service-accounts describe "${SERVICE_ACCOUNT}" --project "${PROJECT_ID}" > /dev/null 2>&1; then
    echo "⚠️  Service Account ${SERVICE_ACCOUNT} not found. Creating..."
    gcloud iam service-accounts create search-backend-sa --display-name "Search Backend SA" --project "${PROJECT_ID}"
fi

# Grant roles (Idempotent)
ROLES=(
    "roles/alloydb.client"
    "roles/alloydb.databaseUser"
    "roles/cloudaicompanion.user"
    "roles/aiplatform.user"
    "roles/serviceusage.serviceUsageConsumer"
    "roles/logging.logWriter"
    "roles/secretmanager.secretAccessor"
    "roles/geminidataanalytics.dataAgentUser"
    "roles/geminidataanalytics.queryDataUser"
)

echo "🛡️  Ensuring IAM roles..."
for role in "${ROLES[@]}"; do
    gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
        --member="serviceAccount:${SERVICE_ACCOUNT}" \
        --role="${role}" \
        --condition=None \
        --quiet > /dev/null 2>&1 || true
done

# AlloyDB Service Agent Roles
PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format="value(projectNumber)")
ALLOYDB_SA="service-${PROJECT_NUMBER}@gcp-sa-alloydb.iam.gserviceaccount.com"
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${ALLOYDB_SA}" \
    --role="roles/aiplatform.user" \
    --condition=None \
    --quiet > /dev/null 2>&1 || true

# Default Compute SA Roles
COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${COMPUTE_SA}" \
    --role="roles/geminidataanalytics.dataAgentUser" \
    --condition=None \
    --quiet > /dev/null 2>&1 || true


# --- 4. UPDATE SECRETS ---

echo "🔐 Updating 'tools' secret..."
if ! gcloud secrets describe tools --project "${PROJECT_ID}" > /dev/null 2>&1; then
    gcloud secrets create tools --replication-policy="automatic" --project "${PROJECT_ID}"
fi

# Generate resolved tools configuration
envsubst < backend/mcp_server/tools.yaml > backend/mcp_server/tools_resolved.yaml

# Add new version
gcloud secrets versions add tools --data-file=backend/mcp_server/tools_resolved.yaml --project "${PROJECT_ID}" --quiet > /dev/null

rm -f backend/mcp_server/tools_resolved.yaml


# --- 5. BUILD & PUSH IMAGES (PARALLEL) ---

echo "📦 Starting Parallel Builds..."
PIDS=""

# Function to handle build errors
handle_build_error() {
    echo "❌ Build failed for $1"
    exit 1
}

# --- AGENT ---
(
    echo "📦 [Agent] Building..."
    gcloud builds submit ./backend/agent --tag "${AGENT_IMAGE}:${TAG}" --quiet > /dev/null 2>&1 || handle_build_error "Agent"
    echo "✅ [Agent] Built"
) &
PIDS="$PIDS $!"

# --- BACKEND ---
(
    echo "📦 [Backend] Building..."
    gcloud builds submit ./backend --tag "${BACKEND_IMAGE}:${TAG}" --quiet > /dev/null 2>&1 || handle_build_error "Backend"
    echo "✅ [Backend] Built"
) &
PIDS="$PIDS $!"

# --- FRONTEND ---
(
    echo "📦 [Frontend] Building..."
    gcloud builds submit . --config=frontend/cloudbuild.yaml --substitutions=_IMAGE_NAME="${FRONTEND_IMAGE}:${TAG}" --quiet > /dev/null 2>&1 || handle_build_error "Frontend"
    echo "✅ [Frontend] Built"
) &
PIDS="$PIDS $!"

# Wait for all builds
wait

echo "🎉 All builds completed successfully!"


# --- 6. DEPLOY TO CLOUD RUN ---

# --- DEPLOY AGENT ---
echo "🚀 Deploying Agent..."
envsubst < backend/agent/service.yaml > backend/agent/service_resolved.yaml

gcloud run services replace backend/agent/service_resolved.yaml --region "${REGION}" --quiet
gcloud run services add-iam-policy-binding "${AGENT_SERVICE}" --region "${REGION}" --member=allUsers --role=roles/run.invoker --quiet > /dev/null

rm -f backend/agent/service_resolved.yaml
AGENT_URL=$(gcloud run services describe "${AGENT_SERVICE}" --region "${REGION}" --format 'value(status.url)')
echo "✅ Agent: ${AGENT_URL}"

# --- DEPLOY BACKEND ---
echo "🚀 Deploying Backend..."
envsubst < backend/service.yaml > backend/service_resolved.yaml

gcloud run services replace backend/service_resolved.yaml --region "${REGION}" --quiet
gcloud run services add-iam-policy-binding "${BACKEND_SERVICE}" --region "${REGION}" --member=allUsers --role=roles/run.invoker --quiet > /dev/null

rm -f backend/service_resolved.yaml
BACKEND_URL=$(gcloud run services describe "${BACKEND_SERVICE}" --region "${REGION}" --format 'value(status.url)')
echo "✅ Backend: ${BACKEND_URL}"

# --- DEPLOY FRONTEND ---
echo "🚀 Deploying Frontend..."
gcloud run deploy "${FRONTEND_SERVICE}" \
    --image "${FRONTEND_IMAGE}:${TAG}" \
    --region "${REGION}" \
    --platform managed \
    --allow-unauthenticated \
    --set-env-vars BACKEND_URL="${BACKEND_URL}",AGENT_URL="${AGENT_URL}" \
    --quiet > /dev/null

FRONTEND_URL=$(gcloud run services describe "${FRONTEND_SERVICE}" --region "${REGION}" --format 'value(status.url)')

echo ""
echo "🎉 Deployment Complete!"
echo "---------------------------------------------------"
echo "Frontend: ${FRONTEND_URL}"
echo "Backend:  ${BACKEND_URL}"
echo "Agent:    ${AGENT_URL}"
echo "---------------------------------------------------"
