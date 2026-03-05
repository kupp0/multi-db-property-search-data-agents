# Terraform Infrastructure Setup

This directory contains Terraform scripts to automate the deployment of the Search Demo infrastructure on Google Cloud.

## Prerequisites

1.  **Terraform**: Ensure Terraform is installed (v1.0+).
    -   [Install Terraform](https://developer.hashicorp.com/terraform/install)

2.  **Google Cloud SDK**: Ensure `gcloud` is installed and authenticated. 

Terraform scripts include the project creation.Rename and add your input into terraform.tfvars file.

Your gcloud login project needs billing account and service usage api enabled. If not you'll see error during tf apply.
Check the following APIs that they are enabled in the project:
A. https://console.cloud.google.com/apis/library/cloudbilling.googleapis.com
B. https://console.developers.google.com/apis/api/serviceusage.googleapis.com


3.  **Billing Account ID**: You need the ID of the billing account to associate with the new project.
    -   Find it via `gcloud beta billing accounts list`.

## Quick Start

### 1. Initialize Terraform
Navigate to this directory and initialize the provider plugins:
```bash
cd terraform
terraform init
```

### 2. Configure Variables
Create a `terraform.tfvars` file to specify your project details. 

**`terraform.tfvars` example:**
```hcl
project_id         = "my-search-demo-project-123"
billing_account_id = "000000-000000-000000"
region             = "europe-west1"
zone               = "europe-west1-b"
db_password        = "StrongPassword123!" # Must meet complexity requirements
```

### 3. Review the Plan
Run `terraform plan` to see what resources will be created.
```bash
terraform plan
```
*Review the output to ensure it matches your expectations (Project, AlloyDB Cluster, IAM bindings, Regions, Zones, etc.).*

### 4. Apply the Configuration
Run `terraform apply` to create the infrastructure.
```bash
terraform apply
```
*Type `yes` when prompted to confirm.*
    
### 5. Manual Database Setup
**IMPORTANT:** After applying Terraform, you must manually initialize the database schema and extensions.
Please refer to the **[Database & AI Setup](../README.md#1-alloydb-setup)** section in the root `README.md` for detailed instructions on running the SQL scripts.

## What gets created?

-   **Project**: A new Google Cloud Project with enabled APIs (including Spanner and Cloud SQL).
-   **Network**: A VPC network (`search-demo-vpc`) with Private Service Access for AlloyDB and Cloud SQL.
-   **Subnet**: A subnet in your region with **Private Google Access** enabled.
-   **Firewall**: `allow-internal` rule to permit internal traffic (required for Bastion -> Databases) and IAP SSH ingress.
-   **AlloyDB**:
    -   Cluster: `search-cluster`
    -   Instance: `search-primary` (2 vCPU, Private IP only)
    -   Flags: AI & ML integration enabled.
-   **Cloud Spanner**:
    -   Instance: `search-instance` (100 Processing Units)
    -   Database: `search-db` (Google Standard SQL dialect)
-   **Cloud SQL for PostgreSQL**:
    -   Instance: `search-pg` (Enterprise Plus, Private IP only)
    -   Flags: `cloudsql.enable_pgvector`, `google_ml_integration.enable_model_support`
-   **Bastion Host**: `search-demo-bastion` (e2-micro) for SSH tunneling to private databases.
-   **Artifact Registry**: Repository `search-app-repo`.
-   **IAM**: Creates a dedicated Service Account `search-backend-sa` and grants necessary roles for all three databases.


## 5. Deploy Application (Optional)

Once the infrastructure is ready, you can automatically generate the configuration file for the application deployment.

1.  **Generate Environment Config**:
    ```bash
    ./generate_env.sh
    ```
    This script reads the Terraform outputs and creates `backend/.env`.

2.  **Deploy Application**:
    Navigate back to the root directory and run the deploy script:
    ```bash
    cd ..
    ./deploy.sh
    ```

## Outputs
After a successful apply, Terraform will output:
-   `project_id`
-   `alloydb_cluster_id`
-   `alloydb_instance_id`
-   `spanner_instance_id`
-   `cloudsql_pg_instance_id`
-   `backend_service_account`
-   `bastion_instance_name`
-   `bastion_zone`

You can use these values to configure your `backend/.env` file.
