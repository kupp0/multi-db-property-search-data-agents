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
#PROMPT=${2:-Show me cheap apartments in basel}

PROMPT="Show me Lovely Mountain Cabins under 15k"

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

# Make the API call using curl
curl -X POST \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json; charset=utf-8" \
  -d "${JSON_PAYLOAD}" \
  "${API_ENDPOINT}"

echo
