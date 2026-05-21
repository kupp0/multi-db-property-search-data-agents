#!/bin/bash

# Resolve project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
cd "$PROJECT_ROOT"

if [ -f "backend/.env" ]; then
    set -a
    source backend/.env
    set +a
else
    echo "❌ backend/.env not found."
    exit 1
fi

PROJECT_ID=${GCP_PROJECT_ID:-$(gcloud config get-value project)}
GDA_LOCATION=${GCP_LOCATION:-"europe-west1"}
API_ENDPOINT="https://geminidataanalytics.googleapis.com/v1beta/projects/${PROJECT_ID}/locations/${GDA_LOCATION}:queryData"

BACKEND=${1:-alloydb}
PROMPT=${2:-"Show me family apartments in Zurich with a nice view up to 16k"}
UPLOAD_TO_GCS=${3:-false}

echo "Testing backend: $BACKEND"

if [ "$BACKEND" == "alloydb" ]; then
  read -r -d '' DATASOURCE_REF << INNER_EOF
      "alloydb": {
        "databaseReference": {
          "project_id": "${PROJECT_ID}",
          "region": "${GDA_LOCATION}",
          "cluster_id": "${ALLOYDB_CLUSTER_ID:-search-cluster}",
          "instance_id": "${ALLOYDB_INSTANCE_ID:-search-primary}",
          "database_id": "${DB_NAME:-search}"
        },
        "agentContextReference": {
          "context_set_id": "${AGENT_CONTEXT_SET_ID_ALLOYDB}"
        }
      }
INNER_EOF
elif [ "$BACKEND" == "cloudsql_pg" ]; then
  read -r -d '' DATASOURCE_REF << INNER_EOF
      "cloudSqlReference": {
        "databaseReference": {
          "engine": "POSTGRESQL",
          "project_id": "${PROJECT_ID}",
          "region": "${GDA_LOCATION}",
          "instance_id": "${CLOUDSQL_PG_INSTANCE_ID:-search-pg}",
          "database_id": "${CLOUDSQL_PG_DB_NAME:-search}"
        },
        "agentContextReference": {
          "context_set_id": "${AGENT_CONTEXT_SET_ID_CLOUDSQL_PG}"
        }
      }
INNER_EOF
elif [ "$BACKEND" == "cloudsql_mysql" ]; then
  read -r -d '' DATASOURCE_REF << INNER_EOF
      "cloudSqlReference": {
        "databaseReference": {
          "engine": "MYSQL",
          "project_id": "${PROJECT_ID}",
          "region": "${GDA_LOCATION}",
          "instance_id": "${CLOUDSQL_MYSQL_INSTANCE_ID:-search-mysql}",
          "database_id": "${CLOUDSQL_MYSQL_DB_NAME:-search}"
        },
        "agentContextReference": {
          "context_set_id": "${AGENT_CONTEXT_SET_ID_CLOUDSQL_MYSQL}"
        }
      }
INNER_EOF
elif [ "$BACKEND" == "spanner" ]; then
  read -r -d '' DATASOURCE_REF << INNER_EOF
      "spannerReference": {
        "databaseReference": {
          "engine": "GOOGLE_SQL",
          "project_id": "${PROJECT_ID}",
          "instance_id": "${SPANNER_INSTANCE_ID:-search-instance}",
          "database_id": "${SPANNER_DATABASE_ID:-search-db}"
        },
        "agentContextReference": {
          "context_set_id": "${AGENT_CONTEXT_SET_ID_SPANNER}"
        }
      }
INNER_EOF
else
  echo "Unknown backend: $BACKEND"
  exit 1
fi

# Get OAuth access token
TOKEN=$(gcloud auth print-access-token)

# Check if token retrieval was successful
if [ -z "$TOKEN" ]; then
  echo "Failed to get gcloud auth token. Make sure you are authenticated."
  exit 1
fi

# JSON Payload
read -r -d '' JSON_PAYLOAD << INNER_EOF
{
  "parent": "projects/${PROJECT_ID}/locations/${GDA_LOCATION}",
  "prompt": "${PROMPT}",
  "context": {
    "datasourceReferences": {
${DATASOURCE_REF}
    }
  },
  "generation_options": {
    "generate_query_result": true,
    "generate_natural_language_answer": true,
    "generate_explanation": true,
    "generate_disambiguation_question": true
  }
}
INNER_EOF

echo "Sending request to: ${API_ENDPOINT}"
echo "Payload:"
echo "${JSON_PAYLOAD}"
echo "---"

# Slugify helper
slugify() {
  echo "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/_/g' | sed -E 's/^_+|_+$//g'
}

SLUG=$(slugify "$PROMPT")
OUTPUT_FILE="/tmp/${BACKEND}_${SLUG}.json"

# Make the API call using curl
curl -s -X POST \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json; charset=utf-8" \
  -d "${JSON_PAYLOAD}" \
  "${API_ENDPOINT}" > "${OUTPUT_FILE}"

# Output to stdout
cat "${OUTPUT_FILE}"
echo

if [ "$UPLOAD_TO_GCS" == "true" ]; then
  BUCKET_NAME="property-images-data-agent-${PROJECT_ID}"
  if [ -n "${ALLOWED_GCS_BUCKET:-}" ]; then
    BUCKET_NAME="${ALLOWED_GCS_BUCKET}"
  fi
  
  GCS_DEST="gs://${BUCKET_NAME}/demo/${BACKEND}/${SLUG}.json"
  echo "📤 Uploading raw GDA response to GCS: ${GCS_DEST}"
  gcloud storage cp "${OUTPUT_FILE}" "${GCS_DEST}"
fi
