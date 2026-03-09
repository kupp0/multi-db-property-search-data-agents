#!/bin/bash
set -e

# Resolve project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"
echo "📂 Project Root: $PROJECT_ROOT"

# --- 1. PRE-CHECKS ---
echo "🔍 Running pre-checks..."

# Check for .env
if [ -f "backend/.env" ]; then
    echo "📄 Loading configuration from backend/.env..."
    set -a
    source backend/.env
    set +a
else
    echo "❌ backend/.env not found. Please run ./scripts/setup_env.sh first."
    exit 1
fi

# Check required commands
for cmd in psql gcloud docker python3; do
    if ! command -v $cmd &> /dev/null; then
        echo "❌ Required command '$cmd' is not installed or not in PATH."
        exit 1
    fi
done

# Set variables
PROJECT_ID=${GCP_PROJECT_ID:-$(gcloud config get-value project)}
REGION=${GCP_LOCATION:-"europe-west1"}
ALLOYDB_CLUSTER_ID=${ALLOYDB_CLUSTER_ID:-search-cluster}
ALLOYDB_INSTANCE_ID=${ALLOYDB_INSTANCE_ID:-search-primary}
INSTANCE_CONNECTION_NAME=${INSTANCE_CONNECTION_NAME:-"projects/${PROJECT_ID}/locations/${REGION}/clusters/${ALLOYDB_CLUSTER_ID}/instances/${ALLOYDB_INSTANCE_ID}"}

SPANNER_INSTANCE_ID=${SPANNER_INSTANCE_ID:-search-instance}
SPANNER_DATABASE_ID=${SPANNER_DATABASE_ID:-search-db}
CLOUDSQL_PG_INSTANCE_ID=${CLOUDSQL_PG_INSTANCE_ID:-search-pg}
CLOUDSQL_PG_DB_NAME=${CLOUDSQL_PG_DB_NAME:-search}

DB_USER=${DB_USER:-postgres}
DB_PASSWORD=${DB_PASSWORD:-${DB_PASS}}

# Cleanup function
cleanup() {
    echo "🧹 Closing SSH Tunnel..."
    pkill -f "ssh.*db-bastion" || true
}
trap cleanup EXIT

# --- 2. START AUTH PROXIES (VIA BASTION) ---
echo "🔒 Establishing SSH Tunnel to Bastion Host..."

# Check if ports are in use
for port in 5432 5433; do
    if lsof -i :$port -t >/dev/null; then
        echo "⚠️  Port $port is in use. Killing existing process..."
        kill -9 $(lsof -i :$port -t)
    fi
done

# Start background SSH tunnel
gcloud compute ssh db-bastion \
    --tunnel-through-iap \
    --project=$PROJECT_ID \
    --zone=${REGION}-b \
    -- -L 5432:127.0.0.1:5432 -L 5433:127.0.0.1:5433 -N -f

echo "⏳ Waiting for SSH Tunnel and Proxies to initialize (10s)..."
sleep 10

# --- 3. SCHEMA DEPLOYMENT ---
echo "🔍 Checking if schemas already exist..."
schema_exists="0"
if PGPASSWORD=$DB_PASSWORD psql -h 127.0.0.1 -p 5432 -U $DB_USER -d ${DB_NAME:-search} -tAc "SELECT 1 FROM information_schema.tables WHERE table_name='property_listings';" 2>/dev/null | grep -q 1; then
    schema_exists="1"
fi

deploy_schemas=true
if [ "$schema_exists" == "1" ]; then
    read -p "⚠️  Database schemas already exist. Do you want to DROP and RECREATE them? (All data will be lost) [y/N]: " recreate_schema
    if [[ ! "$recreate_schema" =~ ^[Yy]$ ]]; then
        deploy_schemas=false
        echo "⏭️ Skipping schema deployment."
    fi
fi

if [ "$deploy_schemas" = true ]; then
    echo "🛠️ Deploying Schemas..."
    echo "➡️ Deploying AlloyDB Schema..."
    sed -e "s/{PROJECT_ID}/$PROJECT_ID/g" database_artefacts/alloydb_setup.sql > /tmp/alloydb_setup_clean.sql
    PGPASSWORD=$DB_PASSWORD psql -h 127.0.0.1 -p 5432 -U $DB_USER -d postgres -P pager=off -f /tmp/alloydb_setup_clean.sql

    echo "➡️ Deploying Cloud SQL PG Schema..."
    sed -e "s/{PROJECT_ID}/$PROJECT_ID/g" database_artefacts/cloudsql_pg_setup.sql > /tmp/cloudsql_pg_setup_clean.sql
    PGPASSWORD=$DB_PASSWORD psql -h 127.0.0.1 -p 5433 -U $DB_USER -d postgres -P pager=off -f /tmp/cloudsql_pg_setup_clean.sql

    echo "➡️ Deploying Spanner Schema..."
    # Remove comments from SQL file before passing to gcloud to avoid parsing errors
    # Also replace placeholders for the Spanner model endpoint
    sed -e "s/{PROJECT_ID}/$PROJECT_ID/g" -e "s/{REGION}/$REGION/g" database_artefacts/spanner_setup.sql | grep -v '^--' | grep -v '^/\*' | grep -v '^\*' > /tmp/spanner_clean.sql
    gcloud spanner databases ddl update $SPANNER_DATABASE_ID \
        --instance=$SPANNER_INSTANCE_ID \
        --project=$PROJECT_ID \
        --ddl-file=/tmp/spanner_clean.sql
fi

# --- 4. BASE DATA GENERATION ---
echo "📦 Creating Python virtual environment and installing dependencies..."
python3 -m venv .venv
source .venv/bin/activate
pip install -q -r backend/requirements.txt

read -p "🧠 Do you want to (re)generate base enriched data (Text Embeddings)? (This overwrites enriched_property_data.json) [y/N]: " regen_data
if [[ "$regen_data" =~ ^[Yy]$ ]]; then
    echo "🧠 Generating base enriched data (Text Embeddings)..."
    python3 database_artefacts/generate_data.py
else
    if [ ! -f "database_artefacts/enriched_property_data.json" ]; then
        echo "❌ Error: database_artefacts/enriched_property_data.json not found! You must generate data first."
        exit 1
    else
        echo "⏭️ Keeping existing enriched_property_data.json."
    fi
fi

# --- 5. IMAGE BOOTSTRAP ---
echo "🖼️ Checking for existing images..."
BUCKET_NAME="property-images-data-agent-${PROJECT_ID}"
images_exist="0"
if gcloud storage ls "gs://${BUCKET_NAME}/listings/" &> /dev/null; then
    images_exist="1"
fi

run_image_bootstrap=false
if [ "$images_exist" == "1" ]; then
    read -p "🖼️  Images already exist in GCS. Do you want to RE-GENERATE them? (This deletes existing images and incurs Vertex AI costs) [y/N]: " regen_images
    if [[ "$regen_images" =~ ^[Yy]$ ]]; then
        echo "🗑️ Deleting existing images from GCS..."
        gcloud storage rm -r "gs://${BUCKET_NAME}/listings" || true
        
        # If they want to regenerate images, they MUST have a fresh JSON file without URIs.
        # If they didn't regenerate data in step 4, we should do it now to clear the URIs.
        if [[ ! "$regen_data" =~ ^[Yy]$ ]]; then
            echo "🧠 Re-generating base enriched data to clear old URIs..."
            python3 database_artefacts/generate_data.py
        fi
        
        run_image_bootstrap=true
    else
        echo "⏭️ Keeping existing images."
    fi
else
    read -p "🖼️ Do you want to generate and upload images using Imagen 4.0? (This takes a few minutes and incurs Vertex AI costs) [y/N]: " generate_images
    if [[ "$generate_images" =~ ^[Yy]$ ]]; then
        run_image_bootstrap=true
    else
        echo "⏭️ Skipping image generation."
    fi
fi

if [ "$run_image_bootstrap" = true ]; then
    echo "🚀 Starting Image Bootstrap..."
    python3 database_artefacts/bootstrap_images.py
fi

# --- 6. DATA LOADING ---
if [ "$deploy_schemas" = true ] || [ "$run_image_bootstrap" = true ]; then
    echo "💾 Loading data into databases..."
    python3 database_artefacts/load_data.py
else
    read -p "💾 Schemas and images were kept. Do you still want to reload the data into the databases? [y/N]: " reload_data
    if [[ "$reload_data" =~ ^[Yy]$ ]]; then
        echo "💾 Loading data into databases..."
        python3 database_artefacts/load_data.py
    else
        echo "⏭️ Skipping data loading."
    fi
fi

# --- 7. INDEX CREATION ---
if [ "$deploy_schemas" = true ] || [ "$run_image_bootstrap" = true ] || [[ "$reload_data" =~ ^[Yy]$ ]]; then
    echo "🏗️ Creating Vector Indexes..."
    echo "➡️ Creating AlloyDB Indexes..."
    PGPASSWORD=$DB_PASSWORD psql -h 127.0.0.1 -p 5432 -U $DB_USER -d search -P pager=off -f database_artefacts/alloydb_indexes.sql

    echo "➡️ Creating Cloud SQL PG Indexes..."
    PGPASSWORD=$DB_PASSWORD psql -h 127.0.0.1 -p 5433 -U $DB_USER -d search -P pager=off -f database_artefacts/cloudsql_pg_indexes.sql

    echo "➡️ Creating Spanner Indexes..."
    gcloud spanner databases ddl update $SPANNER_DATABASE_ID \
        --instance=$SPANNER_INSTANCE_ID \
        --project=$PROJECT_ID \
        --ddl-file=database_artefacts/spanner_indexes.sql
fi

# Deactivate virtual environment
deactivate

echo "🎉 Database Installation Complete!"
