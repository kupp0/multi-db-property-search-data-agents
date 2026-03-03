

# AlloyDB AI Search Demo (Gemini Data Agent)

This application demonstrates a **Natural Language to SQL (NL2SQL)** pipeline powered by the **Gemini Data Agent**. It allows users to search for property listings using natural language queries, which are translated into SQL and executed against an AlloyDB database.

## Architecture

![Architecture Diagram](assets/data_agent_diagram.png)

*   **Frontend**: React application (Vite) with a modern UI.
*   **Backend**: FastAPI (Python) service that proxies requests to the Gemini Data Agent API and serves images securely from Google Cloud Storage.
*   **Gemini Data Agent**: A managed service that understands natural language and interacts with your data.
*   **AlloyDB**: PostgreSQL-compatible database storing property listings.

## Features

*   **Natural Language Search**: Ask questions like "Show me 2-bedroom apartments in Zurich under 3000 CHF".
*   **Generative AI Answers**: Get natural language summaries alongside data results.
*   **Secure Image Serving**: Images are served securely from a private GCS bucket via the backend.
*   **Modern UI**: Responsive design with dark mode support. 

## Prerequisites

*   Google Cloud Project with billing enabled.
*   AlloyDB Cluster and Instance.
*   Gemini Data Agent configured with AlloyDB as a data source.
*   Google Cloud Storage bucket for images.
*   If Data Agent feature is still in gated preview, whitelist your project first. Details: https://docs.cloud.google.com/alloydb/docs/ai/data-agent-overview

## Local Development

1.  **Configure Environment**:
    Copy `.env.example` to `backend/.env` and fill in your values:
    ```bash
    cp .env.example backend/.env
    ```

2.  **Start Services**:
    Run the development script to start both Backend and Frontend:
    ```bash
    ./scripts/dev_local.sh
    ```
    *   Backend: http://localhost:8080
    *   Frontend: http://localhost:8081

    **Alternatively (Recommended with Docker):**
    ```bash
    ./scripts/debug_local.sh
    ```

## Data Bootstrapping & AlloyDB Setup

Follow these steps to initialize the database, generate sample data, and create indexes.

### 1. Start AlloyDB Auth Proxy

To connect to your AlloyDB instance from your local machine, start the Auth Proxy:

```bash
cd "alloydb artefacts"
./run_proxy.sh
```
*Keep this terminal open.*

### 2. Initialize Database & Schema

Connect to your AlloyDB instance (e.g., using `psql` or a database client at `localhost:5432`) and run the following SQL scripts in order:

1.  **`alloydb_setup.sql`**: Creates extensions, tables, and triggers.
2.  **`100 _sample records.sql`**: Inserts sample property listings.

```bash
# Example using psql (adjust username/database as needed)
export PGPASSWORD=your_password
psql -h localhost -U postgres -d postgres -f "alloydb artefacts/alloydb_setup.sql"
psql -h localhost -U postgres -d postgres -f "alloydb artefacts/100 _sample records.sql"
```

### 3. Generate Images & Embeddings

Run the Python script to generate AI images and embeddings for the listings.

**Prerequisites:**
```bash
cd "alloydb artefacts"
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Run:**
```bash
python bootstrap_images.py
```

**What it does:**
1.  Connects to AlloyDB via localhost:5432.
2.  Finds listings with `image_gcs_uri IS NULL`.
3.  Generates an image using Vertex AI Imagen.
4.  Uploads the image to the GCS bucket.
5.  Generates a multimodal embedding.
6.  Updates the `property_listings` table.

### 4. Create Indexes

After data is populated and enriched, create the ScaNN indexes for fast search:

```bash
psql -h localhost -U postgres -d postgres -f "alloydb artefacts/create_indexes.sql"
```

### 5. Data Agent Configuration

The `data_agent_context_file.json` file contains example SQL templates and fragments (e.g., definitions for "cheap", "luxury", "studio") that can be used to configure the Gemini Data Agent's reasoning capabilities. You can upload this context to your Data Agent instance.

## Deployment

To deploy to Google Cloud Run:

```bash
./scripts/deploy.sh
```

This script will:
1.  Build Docker images for Backend and Frontend.
2.  Push images to Artifact Registry.
3.  Deploy services to Cloud Run.

## Project Structure

*   `backend/`: FastAPI application.
*   `frontend/`: React application.
*   `terraform/`: Infrastructure as Code (optional).
