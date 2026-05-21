#!/bin/bash
set -euo pipefail

# Resolve script directory and root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

BACKENDS=("alloydb" "cloudsql_pg" "cloudsql_mysql" "spanner")
QUERIES=(
    "Show me 2-bedroom apartments in Zurich under 3000 CHF"
    "Show me family apartments in Zurich with a nice view up to 16k"
    "Show me cheap studios in Geneva"
    "Show me Lovely Mountain Cabins under 15k"
)

echo "🚀 Starting one-time generation of GDA responses for all databases in demo mode..."

for backend in "${BACKENDS[@]}"; do
  for query in "${QUERIES[@]}"; do
    echo "========================================================================="
    echo "👉 Generating and Uploading for BACKEND: $backend | QUERY: $query"
    echo "========================================================================="
    ./gda_curl_test.sh "$backend" "$query" "true"
    echo "✅ Done"
    echo
    # Sleep to avoid hitting quota rate limits
    sleep 2
  done
done

echo "🎉 All demo files generated and uploaded to GCS successfully!"
