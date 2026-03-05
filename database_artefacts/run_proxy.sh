#!/bin/bash
set -e

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load environment variables from backend/.env
ENV_FILE="$PROJECT_ROOT/backend/.env"
if [ -f "$ENV_FILE" ]; then
    echo "📄 Loading configuration from backend/.env..."
    export $(grep -v '^#' "$ENV_FILE" | xargs)
else
    echo "❌ backend/.env not found. Please run ../terraform/generate_env.sh first."
    exit 1
fi

PROJECT_ID=${GCP_PROJECT_ID:-$(gcloud config get-value project)}
REGION=${GCP_LOCATION:-"europe-west1"}
INSTANCE_URI="${INSTANCE_CONNECTION_NAME}"

echo "🔧 Setting up AlloyDB Auth Proxy..."

# Bastion Configuration
BASTION_NAME="search-demo-bastion"
BASTION_ZONE="${REGION}-b"

# Ensure local proxy binary exists
if [ ! -f "alloydb-auth-proxy" ]; then
    echo "⬇️  Downloading proxy binary locally..."
    wget -q https://storage.googleapis.com/alloydb-auth-proxy/v1.10.0/alloydb-auth-proxy.linux.amd64 -O alloydb-auth-proxy
    chmod +x alloydb-auth-proxy
fi

# Copy proxy to Bastion
echo "📤 Copying proxy to Bastion..."
# Kill existing proxy process on Bastion to avoid "Text file busy"
gcloud compute ssh $BASTION_NAME --zone $BASTION_ZONE --command "killall alloydb-auth-proxy || true" --quiet
gcloud compute scp alloydb-auth-proxy $BASTION_NAME:~/alloydb-auth-proxy --zone $BASTION_ZONE --quiet
gcloud compute ssh $BASTION_NAME --zone $BASTION_ZONE --command "chmod +x alloydb-auth-proxy"

# Start Proxy on Bastion and Tunnel
echo "🔌 Establishing SSH tunnel and starting remote proxy..."
echo "   Forwarding localhost:5432 -> Bastion -> AlloyDB ($INSTANCE_URI)"

gcloud compute ssh $BASTION_NAME --zone $BASTION_ZONE \
    --command "./alloydb-auth-proxy \"$INSTANCE_URI\" --address=127.0.0.1 --port=5432" \
    -- -L 5432:127.0.0.1:5432
