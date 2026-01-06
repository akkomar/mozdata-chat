# Mozilla Data Documentation Ingestion Pipeline

This pipeline automates the ingestion of Mozilla's data documentation from [docs.telemetry.mozilla.org](https://docs.telemetry.mozilla.org) into Vertex AI Search, enabling Retrieval Augmented Generation (RAG) capabilities for the agent.

It orchestrates the complete workflow: fetching HTML documentation pages, uploading them to GCS, and importing the processed data into your Vertex AI Search datastore. Vertex AI Search's native layout parser handles document chunking for optimal RAG performance.

You can trigger the pipeline for an initial data load or schedule it to run periodically, ensuring your search index remains current. Vertex AI Pipelines provides the orchestration and monitoring capabilities for this process.

## Prerequisites

Before running any commands, ensure you have set your Google Cloud Project ID as an environment variable. This variable will be used by the subsequent `make` commands.

```bash
export PROJECT_ID="YOUR_PROJECT_ID"
```

Replace `"YOUR_PROJECT_ID"` with your actual Google Cloud Project ID.

### Infrastructure Requirements

1. **GCS Bucket**: A bucket for storing HTML documents (created during setup)
   - Name format: `${PROJECT_ID}-mozilla-data-docs`

2. **Vertex AI Search Datastore**: Must be created with chunking enabled
   - Name: `mozilla-data-docs-datastore`
   - Region: `us`
   - **Important**: Enable layout-based chunking during creation (cannot be changed after)

3. **Service Account**: Pipeline service account with required permissions
   - Name format: `mozdata-agent-rag@${PROJECT_ID}.iam.gserviceaccount.com`

Now, you can set up the development environment:

1. **Set up Dev Environment:** Use the following command from the root of the repository to provision the necessary resources in your development environment using Terraform.

    ```bash
    make setup-dev-env
    ```
    This command requires `terraform` to be installed and configured.

## Running the Data Ingestion Pipeline

After setting up the infrastructure using `make setup-dev-env`, you can run the data ingestion pipeline.

> **Note:** The initial pipeline execution might take longer as your project is configured for Vertex AI Pipelines.

**Steps:**

**a. Execute the Pipeline:**
Run the following command from the root of the repository. Ensure the `PROJECT_ID` environment variable is still set in your current shell session (as configured in Prerequisites).

```bash
make data-ingestion
```

This command handles installing dependencies (if needed via `make install`) and submits the pipeline job. The pipeline will:

1. Fetch the page index from the data-docs GitHub repository
2. Download ~150 HTML pages from docs.telemetry.mozilla.org
3. Upload HTML files to the GCS bucket
4. Generate JSONL metadata for Vertex AI Search
5. Import documents into the Vertex AI Search datastore

**b. Pipeline Scheduling:**

The `make data-ingestion` command triggers an immediate pipeline run. For production environments, the underlying `submit_pipeline.py` script supports scheduling options with flags like `--schedule-only` and `--cron-schedule` for periodic execution.

**c. Monitoring Pipeline Progress:**

The pipeline's configuration and execution status link will be printed to the console upon submission. For detailed monitoring, use the Vertex AI Pipelines dashboard in the Google Cloud Console.

## Testing Your RAG Application

Once the data ingestion pipeline completes successfully, you can test your RAG application with Vertex AI Search.

```bash
make playground
```

Try asking questions about Mozilla telemetry, BigQuery datasets, Glean, or other data-related topics.

> **Troubleshooting:** If you encounter errors after the initial data ingestion, wait a few minutes and try again. This delay allows Vertex AI Search to fully index the ingested data.

## Pipeline Architecture

```
docs.telemetry.mozilla.org
          ↓
    fetch_docs (Vertex AI Pipelines Component)
        - Fetch SUMMARY.md from GitHub
        - Download HTML pages
        - Upload to GCS bucket
        - Generate JSONL metadata
          ↓
    ingest_data (Vertex AI Pipelines Component)
        - Import documents to Vertex AI Search
        - Native layout parser handles chunking
          ↓
Vertex AI Search Datastore
          ↓
    Agent uses VertexAISearchRetriever
```
