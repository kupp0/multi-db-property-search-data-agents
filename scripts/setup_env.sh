#!/bin/bash
set -e

# Resolve project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"
echo "📂 Project Root: $PROJECT_ROOT"

echo "🔧 Setting up environment configuration..."

ENV_FILE="backend/.env"

if [ -f "$ENV_FILE" ]; then
    echo "✅ $ENV_FILE already exists."
    read -p "Do you want to overwrite it? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping setup."
        exit 0
    fi
fi

echo "Please enter the following configuration values:"

read -p "GCP Project ID: " GCP_PROJECT_ID
read -p "GCP Region (default: europe-west1): " GCP_LOCATION
GCP_LOCATION=${GCP_LOCATION:-europe-west1}

read -p "AlloyDB Cluster ID (default: search-cluster): " ALLOYDB_CLUSTER_ID
ALLOYDB_CLUSTER_ID=${ALLOYDB_CLUSTER_ID:-search-cluster}

read -p "AlloyDB Instance ID (default: search-primary): " ALLOYDB_INSTANCE_ID
ALLOYDB_INSTANCE_ID=${ALLOYDB_INSTANCE_ID:-search-primary}

echo "--- Database Credentials ---"
read -p "Database User (default: postgres): " DB_USER
DB_USER=${DB_USER:-postgres}

read -s -p "Database Password: " DB_PASSWORD
echo ""

read -p "Database Name (default: search): " DB_NAME
DB_NAME=${DB_NAME:-search}

read -p "Agent Context Set ID: " AGENT_CONTEXT_SET_ID

echo "--- Spanner Configuration ---"
read -p "Spanner Instance ID (default: search-instance): " SPANNER_INSTANCE_ID
SPANNER_INSTANCE_ID=${SPANNER_INSTANCE_ID:-search-instance}
read -p "Spanner Database ID (default: search-db): " SPANNER_DATABASE_ID
SPANNER_DATABASE_ID=${SPANNER_DATABASE_ID:-search-db}

echo "--- Cloud SQL PG Configuration ---"
read -p "Cloud SQL PG Instance ID (default: search-pg): " CLOUDSQL_PG_INSTANCE_ID
CLOUDSQL_PG_INSTANCE_ID=${CLOUDSQL_PG_INSTANCE_ID:-search-pg}
read -p "Cloud SQL PG Database Name (default: search): " CLOUDSQL_PG_DB_NAME
CLOUDSQL_PG_DB_NAME=${CLOUDSQL_PG_DB_NAME:-search}

echo "--- Cloud SQL MySQL Configuration ---"
read -p "Cloud SQL MySQL Instance ID (default: search-mysql): " CLOUDSQL_MYSQL_INSTANCE_ID
CLOUDSQL_MYSQL_INSTANCE_ID=${CLOUDSQL_MYSQL_INSTANCE_ID:-search-mysql}
read -p "Cloud SQL MySQL Database Name (default: search): " CLOUDSQL_MYSQL_DB_NAME
CLOUDSQL_MYSQL_DB_NAME=${CLOUDSQL_MYSQL_DB_NAME:-search}

echo "📝 Writing to $ENV_FILE..."

cat > "$ENV_FILE" <<EOF
GCP_PROJECT_ID=$GCP_PROJECT_ID
GCP_LOCATION=$GCP_LOCATION
ALLOYDB_CLUSTER_ID=$ALLOYDB_CLUSTER_ID
ALLOYDB_INSTANCE_ID=$ALLOYDB_INSTANCE_ID
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
DB_NAME=$DB_NAME
AGENT_CONTEXT_SET_ID=$AGENT_CONTEXT_SET_ID
SPANNER_INSTANCE_ID=$SPANNER_INSTANCE_ID
SPANNER_DATABASE_ID=$SPANNER_DATABASE_ID
CLOUDSQL_PG_INSTANCE_ID=$CLOUDSQL_PG_INSTANCE_ID
CLOUDSQL_PG_DB_NAME=$CLOUDSQL_PG_DB_NAME
CLOUDSQL_MYSQL_INSTANCE_ID=$CLOUDSQL_MYSQL_INSTANCE_ID
CLOUDSQL_MYSQL_DB_NAME=$CLOUDSQL_MYSQL_DB_NAME
EOF

echo "✅ Configuration saved to $ENV_FILE"
echo "You can now run ./deploy.sh or ./debug_local.sh"
